"""Mini's Household Context Encoder (section 20.2) — same token embedders
as Nano (`ml/relieffm/field_encoder.py`'s `TokenEmbedder` is dimension-
generic, reused unmodified) but processed through the modern
`EncoderStack` (RMSNorm/SwiGLU/RoPE/SDPA, `ml/relieffm/blocks.py`).
"""
from __future__ import annotations

import torch
from torch import nn

from .. import vocab
from ..blocks import masked_mean_pool, safe_key_padding_mask
from ..config import MiniConfig
from ..field_encoder import SEGMENT_ACCOUNT, SEGMENT_OBLIGATION, HouseholdStateEmbedder, TokenEmbedder
from .stack_factory import build_encoder_stack


class HouseholdContextEncoder(nn.Module):
    def __init__(self, config: MiniConfig):
        super().__init__()
        H = config.hidden_dimension
        self.household_embedder = HouseholdStateEmbedder(config.household_numeric_dim, H)
        self.account_embedder = TokenEmbedder(
            vocab_sizes=[len(vocab.ACCOUNT_TYPE)],
            numeric_dim=config.account_numeric_dim,
            hidden_dim=H,
            segment_id=SEGMENT_ACCOUNT,
        )
        self.obligation_embedder = TokenEmbedder(
            vocab_sizes=[len(vocab.OBLIGATION_TYPE), len(vocab.RECURRENCE_STATE), len(vocab.ESSENTIALITY), len(vocab.PAYMENT_STATUS)],
            numeric_dim=config.obligation_numeric_dim,
            hidden_dim=H,
            segment_id=SEGMENT_OBLIGATION,
        )
        max_seq = 1 + config.max_accounts + config.max_obligations
        self.encoder = build_encoder_stack(config, config.context_encoder_layers, max_seq)

    def forward(self, batch: dict[str, torch.Tensor]) -> torch.Tensor:
        household_tok = self.household_embedder(batch["household_numeric"]).unsqueeze(1)
        account_tok = self.account_embedder(batch["account_cat"], batch["account_numeric"])
        obligation_tok = self.obligation_embedder(batch["obligation_cat"], batch["obligation_numeric"])

        tokens = torch.cat([household_tok, account_tok, obligation_tok], dim=1)
        household_mask = torch.ones(household_tok.shape[:2], device=household_tok.device)
        mask = torch.cat([household_mask, batch["account_mask"], batch["obligation_mask"]], dim=1)

        encoded = self.encoder(tokens, safe_key_padding_mask(mask))
        return masked_mean_pool(encoded, mask)
