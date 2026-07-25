"""Mini's Historical Event Encoder (section 20.3) — bidirectional, modern
blocks, the largest layer share of the encoder budget (section 3's
research surface lives here and in the known-future encoder jointly).

Optional masked event reconstruction (section 49, Objective One): when
`config.use_masked_pretraining` is set (Flash only — Mini's already-
trained checkpoint was built without it, see `config.py`'s docstring), a
random subset of valid historical-event positions gets replaced with a
learned mask embedding before encoding, and two small heads predict the
masked positions' true event type and direction from the encoded output.
This is a training-time-only auxiliary signal (`self.training` gated) —
inference never masks real history, matching section 20.3's premise that
"all historical events are known at forecast time."
"""
from __future__ import annotations

import torch
from torch import nn

from .. import vocab
from ..blocks import masked_mean_pool, safe_key_padding_mask
from ..config import MiniConfig
from ..field_encoder import SEGMENT_HISTORICAL, TokenEmbedder
from .stack_factory import build_encoder_stack


class HistoricalEventEncoder(nn.Module):
    def __init__(self, config: MiniConfig):
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
        self.encoder = build_encoder_stack(config, config.historical_encoder_layers, config.context_events)

        self.use_masked_pretraining = config.use_masked_pretraining
        if self.use_masked_pretraining:
            self.mask_ratio = config.mask_ratio
            self.mask_embedding = nn.Parameter(torch.zeros(H))
            self.masked_categorical_heads = nn.ModuleList(
                nn.Linear(H, size)
                for size in (
                    len(vocab.EVENT_TYPE),
                    len(vocab.EVENT_STATUS),
                    len(vocab.DIRECTION),
                    len(vocab.RECURRENCE_STATE),
                    len(vocab.SOURCE_TYPE),
                    len(vocab.ACCOUNT_TYPE),
                    len(vocab.MERCHANT_CATEGORY),
                )
            )
            self.masked_numeric_head = nn.Linear(H, config.event_numeric_dim)

    def forward(self, batch: dict[str, torch.Tensor]) -> tuple[torch.Tensor, torch.Tensor, dict[str, torch.Tensor] | None]:
        tokens = self.embedder(batch["event_cat"], batch["event_numeric"])
        mask = batch["event_mask"]

        mlm_out = None
        if self.use_masked_pretraining and self.training:
            B, T, H = tokens.shape
            maskable = (mask.bool()) & (torch.rand(B, T, device=tokens.device) < self.mask_ratio)
            tokens = torch.where(maskable.unsqueeze(-1), self.mask_embedding.to(tokens.dtype), tokens)
            if maskable.any():
                mlm_out = {"mask": maskable}

        encoded = self.encoder(tokens, safe_key_padding_mask(mask))
        pooled = masked_mean_pool(encoded, mask)

        if mlm_out is not None:
            mlm_out["categorical_logits"] = [head(encoded) for head in self.masked_categorical_heads]
            mlm_out["numeric_prediction"] = self.masked_numeric_head(encoded)

        return encoded, pooled, mlm_out
