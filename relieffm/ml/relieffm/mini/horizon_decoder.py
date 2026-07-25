"""Sections 21-22: the shared horizon decoder. Day-level trajectory queries
and event-slot queries are processed by *one* decoder stack (efficient
reuse of the decoder_layers budget) that cross-attends into the encoder
memory. A global trajectory latent `z` (section 22) is sampled per
scenario and added to every query token for that scenario, so a single
decoder stack — run once per (household, scenario) — produces internally
consistent, correlated day-level and event-level predictions for that
scenario rather than independent per-day noise.

Coupled sampling (section 31) means calling `forward` twice with the same
`z` tensor: once with the baseline memory, once with intervention-
augmented memory (see `mini/model.py`).
"""
from __future__ import annotations

import torch
from torch import nn

from ..config import MiniConfig
from .stack_factory import build_decoder_stack


class HorizonDecoder(nn.Module):
    def __init__(self, config: MiniConfig):
        super().__init__()
        H = config.hidden_dimension
        self.horizon_days = config.forecast_horizon_days
        self.max_event_slots = config.max_event_slots

        self.day_queries = nn.Embedding(config.forecast_horizon_days, H)
        self.event_slot_queries = nn.Embedding(config.max_event_slots, H)
        self.latent_proj = nn.Linear(config.latent_dim, H)
        self.latent_dim = config.latent_dim

        self.decoder = build_decoder_stack(config, config.decoder_layers)

    def sample_latent(self, batch_size: int, n_scenarios: int, device, dtype) -> torch.Tensor:
        return torch.randn(batch_size, n_scenarios, self.latent_dim, device=device, dtype=dtype)

    def forward(
        self,
        memory: torch.Tensor,
        memory_mask: torch.Tensor,
        z: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """memory: (B, T_mem, H), memory_mask: (B, T_mem) 1=valid, z: (B, K, latent_dim).

        Returns (day_hidden, event_hidden), each shaped (B, K, n_queries, H).
        """
        B, K, _ = z.shape
        T_mem = memory.shape[1]
        H = memory.shape[-1]

        memory_rep = memory.unsqueeze(1).expand(B, K, T_mem, H).reshape(B * K, T_mem, H)
        mask_rep = memory_mask.unsqueeze(1).expand(B, K, T_mem).reshape(B * K, T_mem)
        from ..blocks import safe_key_padding_mask

        kpm = safe_key_padding_mask(mask_rep)

        z_bias = self.latent_proj(z).reshape(B * K, 1, H)  # (B*K, 1, H)

        day_q = self.day_queries.weight.unsqueeze(0).expand(B * K, -1, -1) + z_bias
        event_q = self.event_slot_queries.weight.unsqueeze(0).expand(B * K, -1, -1) + z_bias

        combined_q = torch.cat([day_q, event_q], dim=1)
        decoded = self.decoder(combined_q, memory_rep, kpm)

        day_hidden = decoded[:, : self.horizon_days, :].reshape(B, K, self.horizon_days, H)
        event_hidden = decoded[:, self.horizon_days :, :].reshape(B, K, self.max_event_slots, H)
        return day_hidden, event_hidden
