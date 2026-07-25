from __future__ import annotations

import torch
from torch import nn


def masked_mean_pool(x: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    """x: (B, T, H), mask: (B, T) with 1=valid/0=pad -> (B, H).

    Households with zero valid tokens in a stream (e.g. no known-future
    events) fall back to a zero vector rather than dividing by zero.
    """
    mask = mask.unsqueeze(-1)  # (B, T, 1)
    summed = (x * mask).sum(dim=1)
    count = mask.sum(dim=1).clamp(min=1.0)
    return summed / count


def safe_mask(mask: torch.Tensor) -> torch.Tensor:
    """Guarantee at least one valid token per row. An all-pad row (e.g. a
    household with zero known-future events, section 90's missing-data
    case) would otherwise make self-attention softmax over all -inf and
    return NaN. The forced-valid slot is a zero-value pad token, so this
    degrades to a harmless small bias rather than corrupting real data."""
    all_pad = mask.sum(dim=1, keepdim=True) < 0.5
    fix = torch.zeros_like(mask)
    fix[:, 0] = 1.0
    return torch.where(all_pad, fix, mask)


def key_padding_mask(mask: torch.Tensor) -> torch.Tensor:
    """1=valid/0=pad -> bool tensor with True=pad, as `nn.TransformerEncoder` expects."""
    return safe_mask(mask) < 0.5


def make_encoder(hidden_dim: int, heads: int, ff_dim: int, layers: int, dropout: float) -> nn.TransformerEncoder:
    layer = nn.TransformerEncoderLayer(
        d_model=hidden_dim,
        nhead=heads,
        dim_feedforward=ff_dim,
        dropout=dropout,
        batch_first=True,
        activation="gelu",
    )
    # enable_nested_tensor's fast path hits unimplemented ops on MPS and
    # buys nothing at Nano's sequence lengths, so it's off unconditionally.
    return nn.TransformerEncoder(layer, num_layers=layers, enable_nested_tensor=False)
