"""Mini's Known Future Encoder (section 20.4) — modern blocks. As with
Nano, the encoded known-future values never reach the trajectory output
directly (section 23's deterministic clamping happens outside the model);
this encoder only shapes the household embedding and decoder memory.
"""
from __future__ import annotations

import torch
from torch import nn

from .. import vocab
from ..blocks import masked_mean_pool, safe_key_padding_mask
from ..config import MiniConfig
from ..field_encoder import SEGMENT_KNOWN_FUTURE, TokenEmbedder
from .stack_factory import build_encoder_stack


class KnownFutureEncoder(nn.Module):
    def __init__(self, config: MiniConfig):
        super().__init__()
        H = config.hidden_dimension
        self.embedder = TokenEmbedder(
            vocab_sizes=[len(vocab.EVENT_TYPE), len(vocab.DIRECTION), len(vocab.ACCOUNT_TYPE), len(vocab.KNOWN_FUTURE_SOURCE)],
            numeric_dim=config.known_future_numeric_dim,
            hidden_dim=H,
            segment_id=SEGMENT_KNOWN_FUTURE,
        )
        self.encoder = build_encoder_stack(config, config.known_future_encoder_layers, config.max_known_future_events)

    def forward(self, batch: dict[str, torch.Tensor]) -> tuple[torch.Tensor, torch.Tensor]:
        tokens = self.embedder(batch["known_cat"], batch["known_numeric"])
        mask = batch["known_mask"]
        encoded = self.encoder(tokens, safe_key_padding_mask(mask))
        pooled = masked_mean_pool(encoded, mask)
        return encoded, pooled
