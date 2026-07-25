"""Section 20.3 — Historical Event Encoder.

Bidirectional attention over the observed event sequence: "all historical
events are known at forecast time" (section 20.3), so there's no causal
masking here — that's reserved for autoregressive baselines, not Nano.
Takes the largest share of the encoder_layers budget since this is the
main representation-learning workhorse (section 3's research contribution
rests on this stream jointly with the known-future stream, not on it
alone).
"""
from __future__ import annotations

import torch
from torch import nn

from . import vocab
from .config import NanoConfig
from .field_encoder import SEGMENT_HISTORICAL, TokenEmbedder
from .nn_utils import key_padding_mask, make_encoder, masked_mean_pool

_HISTORICAL_ENCODER_LAYERS = 2


class HistoricalEventEncoder(nn.Module):
    def __init__(self, config: NanoConfig):
        super().__init__()
        H = config.hidden_dimension
        self.embedder = TokenEmbedder(
            vocab_sizes=[
                len(vocab.EVENT_TYPE), len(vocab.EVENT_STATUS), len(vocab.DIRECTION),
                len(vocab.RECURRENCE_STATE), len(vocab.SOURCE_TYPE), len(vocab.ACCOUNT_TYPE),
                len(vocab.MERCHANT_CATEGORY),
            ],
            numeric_dim=config.event_numeric_dim,
            hidden_dim=H,
            segment_id=SEGMENT_HISTORICAL,
        )
        self.encoder = make_encoder(
            H, config.attention_heads, config.feedforward_dimension, _HISTORICAL_ENCODER_LAYERS, config.dropout
        )

    def forward(self, batch: dict[str, torch.Tensor]) -> tuple[torch.Tensor, torch.Tensor]:
        tokens = self.embedder(batch["event_cat"], batch["event_numeric"])  # (B, T, H)
        mask = batch["event_mask"]
        encoded = self.encoder(tokens, src_key_padding_mask=key_padding_mask(mask))
        pooled = masked_mean_pool(encoded, mask)
        return encoded, pooled
