"""Section 20.2 — Household Context Encoder.

Processes account state, obligation state, and current liquidity state
(the household-state token) jointly through a shallow Transformer encoder,
then mask-aware mean-pools to a single context vector.
"""
from __future__ import annotations

import torch
from torch import nn

from . import vocab
from .config import NanoConfig
from .field_encoder import HouseholdStateEmbedder, SEGMENT_ACCOUNT, SEGMENT_OBLIGATION, TokenEmbedder
from .nn_utils import key_padding_mask, make_encoder, masked_mean_pool

_CONTEXT_ENCODER_LAYERS = 1  # small slice of the encoder_layers budget (section 19.1)


class HouseholdContextEncoder(nn.Module):
    def __init__(self, config: NanoConfig):
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
        self.encoder = make_encoder(H, config.attention_heads, config.feedforward_dimension, _CONTEXT_ENCODER_LAYERS, config.dropout)

    def forward(self, batch: dict[str, torch.Tensor]) -> torch.Tensor:
        household_tok = self.household_embedder(batch["household_numeric"]).unsqueeze(1)  # (B,1,H)
        account_tok = self.account_embedder(batch["account_cat"], batch["account_numeric"])  # (B,A,H)
        obligation_tok = self.obligation_embedder(batch["obligation_cat"], batch["obligation_numeric"])  # (B,O,H)

        tokens = torch.cat([household_tok, account_tok, obligation_tok], dim=1)
        household_mask = torch.ones(household_tok.shape[:2], device=household_tok.device)
        mask = torch.cat([household_mask, batch["account_mask"], batch["obligation_mask"]], dim=1)

        encoded = self.encoder(tokens, src_key_padding_mask=key_padding_mask(mask))
        return masked_mean_pool(encoded, mask)
