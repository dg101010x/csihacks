"""Section 20.4 — Known Future Encoder.

Processes authoritative scheduled events (confirmed paychecks, scheduled
obligation payments) in their own encoder, separate from the uncertain
historical stream — "prevents the model from treating a contractual
obligation as merely another uncertain prediction" (section 20.4). Its
pooled output feeds the fusion layer for representation purposes; the
actual known-event *values* bypass the model entirely at inference via
deterministic clamping (section 23), not through this encoder.
"""
from __future__ import annotations

import torch
from torch import nn

from . import vocab
from .config import NanoConfig
from .field_encoder import SEGMENT_KNOWN_FUTURE, TokenEmbedder
from .nn_utils import key_padding_mask, make_encoder, masked_mean_pool

_KNOWN_FUTURE_ENCODER_LAYERS = 1


class KnownFutureEncoder(nn.Module):
    def __init__(self, config: NanoConfig):
        super().__init__()
        H = config.hidden_dimension
        self.embedder = TokenEmbedder(
            vocab_sizes=[len(vocab.EVENT_TYPE), len(vocab.DIRECTION), len(vocab.ACCOUNT_TYPE), len(vocab.KNOWN_FUTURE_SOURCE)],
            numeric_dim=config.known_future_numeric_dim,
            hidden_dim=H,
            segment_id=SEGMENT_KNOWN_FUTURE,
        )
        self.encoder = make_encoder(
            H, config.attention_heads, config.feedforward_dimension, _KNOWN_FUTURE_ENCODER_LAYERS, config.dropout
        )

    def forward(self, batch: dict[str, torch.Tensor]) -> tuple[torch.Tensor, torch.Tensor]:
        tokens = self.embedder(batch["known_cat"], batch["known_numeric"])
        mask = batch["known_mask"]
        encoded = self.encoder(tokens, src_key_padding_mask=key_padding_mask(mask))
        pooled = masked_mean_pool(encoded, mask)
        return encoded, pooled
