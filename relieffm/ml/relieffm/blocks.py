"""Modern Transformer building blocks for ReliefFM Mini: RMSNorm, SwiGLU
feedforward, rotary position embeddings (RoPE), and attention via
`torch.nn.functional.scaled_dot_product_attention` (SDPA) — which
dispatches to flash-attention / memory-efficient kernels automatically on
CUDA, no extra dependency required. Nano keeps using plain
`nn.TransformerEncoder`/`Decoder`; these are Mini-only.

RoPE is applied only in self-attention (encoder layers, decoder query
self-attention) where a single sequence has a well-defined position axis.
Cross-attention between decoder queries (day-index / event-slot identity,
already encoded in the query embeddings themselves) and encoder memory
(a different positional space) uses no rotary bias, which is the standard
choice in RoPE-based decoder architectures.
"""
from __future__ import annotations

import math

import torch
import torch.nn.functional as F
from torch import nn
from torch.utils.checkpoint import checkpoint


class RMSNorm(nn.Module):
    def __init__(self, dim: int, eps: float = 1e-6):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(dim))
        self.eps = eps

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        norm = x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + self.eps)
        return norm * self.weight


class SwiGLU(nn.Module):
    def __init__(self, dim: int, hidden_dim: int, dropout: float = 0.0):
        super().__init__()
        self.w_gate = nn.Linear(dim, hidden_dim, bias=False)
        self.w_up = nn.Linear(dim, hidden_dim, bias=False)
        self.w_down = nn.Linear(hidden_dim, dim, bias=False)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.dropout(self.w_down(F.silu(self.w_gate(x)) * self.w_up(x)))


class RotaryEmbedding(nn.Module):
    def __init__(self, head_dim: int, max_seq_len: int = 4096, base: float = 10000.0):
        super().__init__()
        inv_freq = 1.0 / (base ** (torch.arange(0, head_dim, 2).float() / head_dim))
        self.register_buffer("inv_freq", inv_freq, persistent=False)
        self.max_seq_len = max_seq_len

    def forward(self, seq_len: int, device, dtype) -> tuple[torch.Tensor, torch.Tensor]:
        t = torch.arange(seq_len, device=device, dtype=self.inv_freq.dtype)
        freqs = torch.einsum("i,j->ij", t, self.inv_freq.to(device))
        emb = torch.cat([freqs, freqs], dim=-1)
        return emb.cos().to(dtype), emb.sin().to(dtype)


def _rotate_half(x: torch.Tensor) -> torch.Tensor:
    x1, x2 = x.chunk(2, dim=-1)
    return torch.cat([-x2, x1], dim=-1)


def apply_rotary(q: torch.Tensor, k: torch.Tensor, cos: torch.Tensor, sin: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """q, k: (B, heads, T, head_dim); cos, sin: (T, head_dim)."""
    cos = cos[None, None, :, :]
    sin = sin[None, None, :, :]
    q_rot = q * cos + _rotate_half(q) * sin
    k_rot = k * cos + _rotate_half(k) * sin
    return q_rot, k_rot


def _padding_bias(key_padding_mask: torch.Tensor | None, B: int, Tq: int, Tk: int, device, dtype) -> torch.Tensor | None:
    """key_padding_mask: (B, Tk), True = pad -> additive attention bias (B,1,Tq,Tk)."""
    if key_padding_mask is None:
        return None
    bias = torch.zeros(B, 1, Tq, Tk, device=device, dtype=dtype)
    bias.masked_fill_(key_padding_mask[:, None, None, :], float("-inf"))
    return bias


class SelfAttention(nn.Module):
    def __init__(self, hidden_dim: int, n_heads: int, dropout: float = 0.0, use_rope: bool = True, max_seq_len: int = 4096):
        super().__init__()
        assert hidden_dim % n_heads == 0
        self.n_heads = n_heads
        self.head_dim = hidden_dim // n_heads
        self.qkv = nn.Linear(hidden_dim, 3 * hidden_dim, bias=False)
        self.out = nn.Linear(hidden_dim, hidden_dim, bias=False)
        self.dropout = dropout
        self.use_rope = use_rope
        if use_rope:
            self.rope = RotaryEmbedding(self.head_dim, max_seq_len)

    def forward(self, x: torch.Tensor, key_padding_mask: torch.Tensor | None = None) -> torch.Tensor:
        B, T, H = x.shape
        qkv = self.qkv(x).view(B, T, 3, self.n_heads, self.head_dim).permute(2, 0, 3, 1, 4)
        q, k, v = qkv[0], qkv[1], qkv[2]  # (B, heads, T, head_dim)
        if self.use_rope:
            cos, sin = self.rope(T, x.device, x.dtype)
            q, k = apply_rotary(q, k, cos, sin)
        bias = _padding_bias(key_padding_mask, B, T, T, x.device, x.dtype)
        out = F.scaled_dot_product_attention(q, k, v, attn_mask=bias, dropout_p=self.dropout if self.training else 0.0)
        out = out.transpose(1, 2).reshape(B, T, H)
        return self.out(out)


class CrossAttention(nn.Module):
    def __init__(self, hidden_dim: int, n_heads: int, dropout: float = 0.0):
        super().__init__()
        assert hidden_dim % n_heads == 0
        self.n_heads = n_heads
        self.head_dim = hidden_dim // n_heads
        self.q_proj = nn.Linear(hidden_dim, hidden_dim, bias=False)
        self.kv_proj = nn.Linear(hidden_dim, 2 * hidden_dim, bias=False)
        self.out = nn.Linear(hidden_dim, hidden_dim, bias=False)
        self.dropout = dropout

    def forward(self, x: torch.Tensor, memory: torch.Tensor, memory_key_padding_mask: torch.Tensor | None = None) -> torch.Tensor:
        B, Tq, H = x.shape
        Tk = memory.shape[1]
        q = self.q_proj(x).view(B, Tq, self.n_heads, self.head_dim).transpose(1, 2)
        kv = self.kv_proj(memory).view(B, Tk, 2, self.n_heads, self.head_dim).permute(2, 0, 3, 1, 4)
        k, v = kv[0], kv[1]
        bias = _padding_bias(memory_key_padding_mask, B, Tq, Tk, x.device, x.dtype)
        out = F.scaled_dot_product_attention(q, k, v, attn_mask=bias, dropout_p=self.dropout if self.training else 0.0)
        out = out.transpose(1, 2).reshape(B, Tq, H)
        return self.out(out)


class EncoderBlock(nn.Module):
    def __init__(self, hidden_dim: int, n_heads: int, ff_dim: int, dropout: float, max_seq_len: int = 4096):
        super().__init__()
        self.norm1 = RMSNorm(hidden_dim)
        self.attn = SelfAttention(hidden_dim, n_heads, dropout, use_rope=True, max_seq_len=max_seq_len)
        self.norm2 = RMSNorm(hidden_dim)
        self.ff = SwiGLU(hidden_dim, ff_dim, dropout)

    def forward(self, x: torch.Tensor, key_padding_mask: torch.Tensor | None = None) -> torch.Tensor:
        x = x + self.attn(self.norm1(x), key_padding_mask)
        x = x + self.ff(self.norm2(x))
        return x


class EncoderStack(nn.Module):
    def __init__(self, hidden_dim: int, n_heads: int, ff_dim: int, n_layers: int, dropout: float, max_seq_len: int = 4096):
        super().__init__()
        self.layers = nn.ModuleList(
            [EncoderBlock(hidden_dim, n_heads, ff_dim, dropout, max_seq_len) for _ in range(n_layers)]
        )
        self.final_norm = RMSNorm(hidden_dim)

    def forward(self, x: torch.Tensor, key_padding_mask: torch.Tensor | None = None) -> torch.Tensor:
        for layer in self.layers:
            x = layer(x, key_padding_mask)
        return self.final_norm(x)


class DecoderBlock(nn.Module):
    """Self-attention among query tokens (no RoPE -- query identity is
    already encoded positionally via learned embeddings, not sequence
    order) + cross-attention into encoder memory + SwiGLU FFN."""

    def __init__(self, hidden_dim: int, n_heads: int, ff_dim: int, dropout: float):
        super().__init__()
        self.norm1 = RMSNorm(hidden_dim)
        self.self_attn = SelfAttention(hidden_dim, n_heads, dropout, use_rope=False)
        self.norm2 = RMSNorm(hidden_dim)
        self.cross_attn = CrossAttention(hidden_dim, n_heads, dropout)
        self.norm3 = RMSNorm(hidden_dim)
        self.ff = SwiGLU(hidden_dim, ff_dim, dropout)

    def forward(self, x: torch.Tensor, memory: torch.Tensor, memory_key_padding_mask: torch.Tensor | None = None) -> torch.Tensor:
        x = x + self.self_attn(self.norm1(x))
        x = x + self.cross_attn(self.norm2(x), memory, memory_key_padding_mask)
        x = x + self.ff(self.norm3(x))
        return x


class DecoderStack(nn.Module):
    def __init__(self, hidden_dim: int, n_heads: int, ff_dim: int, n_layers: int, dropout: float):
        super().__init__()
        self.layers = nn.ModuleList([DecoderBlock(hidden_dim, n_heads, ff_dim, dropout) for _ in range(n_layers)])
        self.final_norm = RMSNorm(hidden_dim)

    def forward(self, x: torch.Tensor, memory: torch.Tensor, memory_key_padding_mask: torch.Tensor | None = None) -> torch.Tensor:
        for layer in self.layers:
            x = layer(x, memory, memory_key_padding_mask)
        return self.final_norm(x)


def masked_mean_pool(x: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    """Same semantics as ml/relieffm/nn_utils.masked_mean_pool, duplicated
    here to keep Mini's module free of a Nano-nn_utils dependency."""
    m = mask.unsqueeze(-1)
    summed = (x * m).sum(dim=1)
    count = m.sum(dim=1).clamp(min=1.0)
    return summed / count


def safe_key_padding_mask(mask: torch.Tensor) -> torch.Tensor:
    """1=valid/0=pad -> bool True=pad, with an all-pad row forced to have
    one valid (zero-embedding) slot so SDPA never sees an all -inf row."""
    all_pad = mask.sum(dim=1, keepdim=True) < 0.5
    fixed = torch.zeros_like(mask)
    fixed[:, 0] = 1.0
    mask = torch.where(all_pad, fixed, mask)
    return mask < 0.5


# --------------------------------------------------------------------------
# V2 blocks: QK-Norm + Grouped-Query Attention, additive only.
#
# These are NEW classes, not modifications to the ones above. Mini's
# training run (in flight on GCP as this is written) built its model from
# EncoderStack/DecoderStack exactly as defined above; changing those
# classes -- even conditionally -- would change the parameter names/shapes
# `ReliefFMMini(mini_config())` produces and break `load_state_dict` on
# that checkpoint the moment training finishes. Flash opts into these via
# new MiniConfig fields (`use_qk_norm`, `n_kv_heads`) that default to
# values reproducing Mini's exact current behavior; see
# `ml/relieffm/mini/*.py` for where each module picks V1 vs V2 based on
# those flags.
# --------------------------------------------------------------------------

class GroupedSelfAttention(nn.Module):
    """Like SelfAttention, plus optional QK-Norm and optional grouped-query
    attention (n_kv_heads < n_heads, Llama-3/Mistral style)."""

    def __init__(
        self, hidden_dim: int, n_heads: int, n_kv_heads: int | None = None,
        dropout: float = 0.0, use_rope: bool = True, max_seq_len: int = 4096, use_qk_norm: bool = True,
    ):
        super().__init__()
        self.n_heads = n_heads
        self.n_kv_heads = n_kv_heads or n_heads
        assert n_heads % self.n_kv_heads == 0, "n_heads must be divisible by n_kv_heads"
        self.n_rep = n_heads // self.n_kv_heads
        self.head_dim = hidden_dim // n_heads
        self.q_proj = nn.Linear(hidden_dim, n_heads * self.head_dim, bias=False)
        self.k_proj = nn.Linear(hidden_dim, self.n_kv_heads * self.head_dim, bias=False)
        self.v_proj = nn.Linear(hidden_dim, self.n_kv_heads * self.head_dim, bias=False)
        self.out = nn.Linear(hidden_dim, hidden_dim, bias=False)
        self.dropout = dropout
        self.use_rope = use_rope
        if use_rope:
            self.rope = RotaryEmbedding(self.head_dim, max_seq_len)
        self.use_qk_norm = use_qk_norm
        if use_qk_norm:
            self.q_norm = RMSNorm(self.head_dim)
            self.k_norm = RMSNorm(self.head_dim)

    def forward(self, x: torch.Tensor, key_padding_mask: torch.Tensor | None = None) -> torch.Tensor:
        B, T, H = x.shape
        q = self.q_proj(x).view(B, T, self.n_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(x).view(B, T, self.n_kv_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(x).view(B, T, self.n_kv_heads, self.head_dim).transpose(1, 2)
        if self.use_qk_norm:
            q, k = self.q_norm(q), self.k_norm(k)
        if self.use_rope:
            cos, sin = self.rope(T, x.device, x.dtype)
            q, k = apply_rotary(q, k, cos, sin)
        bias = _padding_bias(key_padding_mask, B, T, T, x.device, x.dtype)
        out = F.scaled_dot_product_attention(
            q, k, v,
            attn_mask=bias,
            dropout_p=self.dropout if self.training else 0.0,
            enable_gqa=self.n_rep > 1,
        )
        out = out.transpose(1, 2).reshape(B, T, H)
        return self.out(out)


class GroupedCrossAttention(nn.Module):
    def __init__(self, hidden_dim: int, n_heads: int, n_kv_heads: int | None = None, dropout: float = 0.0, use_qk_norm: bool = True):
        super().__init__()
        self.n_heads = n_heads
        self.n_kv_heads = n_kv_heads or n_heads
        assert n_heads % self.n_kv_heads == 0, "n_heads must be divisible by n_kv_heads"
        self.n_rep = n_heads // self.n_kv_heads
        self.head_dim = hidden_dim // n_heads
        self.q_proj = nn.Linear(hidden_dim, n_heads * self.head_dim, bias=False)
        self.k_proj = nn.Linear(hidden_dim, self.n_kv_heads * self.head_dim, bias=False)
        self.v_proj = nn.Linear(hidden_dim, self.n_kv_heads * self.head_dim, bias=False)
        self.out = nn.Linear(hidden_dim, hidden_dim, bias=False)
        self.dropout = dropout
        self.use_qk_norm = use_qk_norm
        if use_qk_norm:
            self.q_norm = RMSNorm(self.head_dim)
            self.k_norm = RMSNorm(self.head_dim)

    def forward(self, x: torch.Tensor, memory: torch.Tensor, memory_key_padding_mask: torch.Tensor | None = None) -> torch.Tensor:
        B, Tq, H = x.shape
        Tk = memory.shape[1]
        q = self.q_proj(x).view(B, Tq, self.n_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(memory).view(B, Tk, self.n_kv_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(memory).view(B, Tk, self.n_kv_heads, self.head_dim).transpose(1, 2)
        if self.use_qk_norm:
            q, k = self.q_norm(q), self.k_norm(k)
        bias = _padding_bias(memory_key_padding_mask, B, Tq, Tk, x.device, x.dtype)
        out = F.scaled_dot_product_attention(
            q, k, v,
            attn_mask=bias,
            dropout_p=self.dropout if self.training else 0.0,
            enable_gqa=self.n_rep > 1,
        )
        out = out.transpose(1, 2).reshape(B, Tq, H)
        return self.out(out)


class EncoderBlockV2(nn.Module):
    def __init__(self, hidden_dim: int, n_heads: int, ff_dim: int, dropout: float, n_kv_heads: int | None = None, max_seq_len: int = 4096, use_qk_norm: bool = True):
        super().__init__()
        self.norm1 = RMSNorm(hidden_dim)
        self.attn = GroupedSelfAttention(hidden_dim, n_heads, n_kv_heads, dropout, use_rope=True, max_seq_len=max_seq_len, use_qk_norm=use_qk_norm)
        self.norm2 = RMSNorm(hidden_dim)
        self.ff = SwiGLU(hidden_dim, ff_dim, dropout)

    def forward(self, x: torch.Tensor, key_padding_mask: torch.Tensor | None = None) -> torch.Tensor:
        x = x + self.attn(self.norm1(x), key_padding_mask)
        x = x + self.ff(self.norm2(x))
        return x


class EncoderStackV2(nn.Module):
    def __init__(self, hidden_dim: int, n_heads: int, ff_dim: int, n_layers: int, dropout: float, n_kv_heads: int | None = None, max_seq_len: int = 4096, use_qk_norm: bool = True, activation_checkpointing: bool = False):
        super().__init__()
        self.layers = nn.ModuleList(
            [EncoderBlockV2(hidden_dim, n_heads, ff_dim, dropout, n_kv_heads, max_seq_len, use_qk_norm) for _ in range(n_layers)]
        )
        self.final_norm = RMSNorm(hidden_dim)
        self.activation_checkpointing = activation_checkpointing

    def forward(self, x: torch.Tensor, key_padding_mask: torch.Tensor | None = None) -> torch.Tensor:
        for layer in self.layers:
            if self.activation_checkpointing and self.training and torch.is_grad_enabled():
                x = checkpoint(layer, x, key_padding_mask, use_reentrant=False)
            else:
                x = layer(x, key_padding_mask)
        return self.final_norm(x)


class DecoderBlockV2(nn.Module):
    def __init__(self, hidden_dim: int, n_heads: int, ff_dim: int, dropout: float, n_kv_heads: int | None = None, use_qk_norm: bool = True):
        super().__init__()
        self.norm1 = RMSNorm(hidden_dim)
        self.self_attn = GroupedSelfAttention(hidden_dim, n_heads, n_kv_heads, dropout, use_rope=False, use_qk_norm=use_qk_norm)
        self.norm2 = RMSNorm(hidden_dim)
        self.cross_attn = GroupedCrossAttention(hidden_dim, n_heads, n_kv_heads, dropout, use_qk_norm=use_qk_norm)
        self.norm3 = RMSNorm(hidden_dim)
        self.ff = SwiGLU(hidden_dim, ff_dim, dropout)

    def forward(self, x: torch.Tensor, memory: torch.Tensor, memory_key_padding_mask: torch.Tensor | None = None) -> torch.Tensor:
        x = x + self.self_attn(self.norm1(x))
        x = x + self.cross_attn(self.norm2(x), memory, memory_key_padding_mask)
        x = x + self.ff(self.norm3(x))
        return x


class DecoderStackV2(nn.Module):
    def __init__(self, hidden_dim: int, n_heads: int, ff_dim: int, n_layers: int, dropout: float, n_kv_heads: int | None = None, use_qk_norm: bool = True, activation_checkpointing: bool = False):
        super().__init__()
        self.layers = nn.ModuleList(
            [DecoderBlockV2(hidden_dim, n_heads, ff_dim, dropout, n_kv_heads, use_qk_norm) for _ in range(n_layers)]
        )
        self.final_norm = RMSNorm(hidden_dim)
        self.activation_checkpointing = activation_checkpointing

    def forward(self, x: torch.Tensor, memory: torch.Tensor, memory_key_padding_mask: torch.Tensor | None = None) -> torch.Tensor:
        for layer in self.layers:
            if self.activation_checkpointing and self.training and torch.is_grad_enabled():
                x = checkpoint(layer, x, memory, memory_key_padding_mask, use_reentrant=False)
            else:
                x = layer(x, memory, memory_key_padding_mask)
        return self.final_norm(x)
