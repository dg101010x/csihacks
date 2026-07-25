"""Picks V1 (Mini's original, already-trained-against) vs V2 (QK-Norm +
GQA) encoder/decoder stacks based on `MiniConfig.use_qk_norm` /
`n_kv_heads`. Centralized here so every module that builds a stack
branches identically -- see `blocks.py`'s V2-blocks docstring for why the
V1 path must stay byte-for-byte unchanged.
"""
from __future__ import annotations

from ..blocks import DecoderStack, DecoderStackV2, EncoderStack, EncoderStackV2
from ..config import MiniConfig


def build_encoder_stack(config: MiniConfig, n_layers: int, max_seq_len: int):
    H = config.hidden_dimension
    if config.use_qk_norm or config.n_kv_heads is not None:
        return EncoderStackV2(
            H, config.attention_heads, config.feedforward_dimension, n_layers, config.dropout,
            n_kv_heads=config.n_kv_heads, max_seq_len=max_seq_len, use_qk_norm=config.use_qk_norm,
            activation_checkpointing=config.use_activation_checkpointing,
        )
    return EncoderStack(H, config.attention_heads, config.feedforward_dimension, n_layers, config.dropout, max_seq_len=max_seq_len)


def build_decoder_stack(config: MiniConfig, n_layers: int):
    H = config.hidden_dimension
    if config.use_qk_norm or config.n_kv_heads is not None:
        return DecoderStackV2(
            H, config.attention_heads, config.feedforward_dimension, n_layers, config.dropout,
            n_kv_heads=config.n_kv_heads, use_qk_norm=config.use_qk_norm,
            activation_checkpointing=config.use_activation_checkpointing,
        )
    return DecoderStack(H, config.attention_heads, config.feedforward_dimension, n_layers, config.dropout)
