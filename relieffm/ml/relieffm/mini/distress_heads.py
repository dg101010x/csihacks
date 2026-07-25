"""Section 26 — distress hazard heads, Mini version.

Nano's distress head lost decisively to a gradient-boosted-trees baseline
(see `ml/model_cards/relieffm_nano.md`) even after fixing that baseline's
feature leakage. The fix here is two-part: (1) give the head more capacity
(deeper MLP, its own hidden layer instead of one shared linear projection)
and (2) feed it the *same legitimate, snapshot-derivable* engineered
features the corrected GBM baseline uses (`ml/baselines/gradient_boosted.py`
`FEATURE_NAMES`) concatenated with the learned household embedding — since
those features demonstrably carry strong signal for this specific target,
there's no reason to make the network rediscover them from raw tokens
under a shared multi-task representation when they're cheap to compute
and legitimate to use.
"""
from __future__ import annotations

import torch
from torch import nn

from ..blocks import RMSNorm
from ..config import MiniConfig

RISK_NAMES = ("negative_balance", "essential_reserve_violation", "missed_obligation")


class DistressHeads(nn.Module):
    def __init__(self, config: MiniConfig):
        super().__init__()
        H = config.hidden_dimension
        self.n_horizons = len(config.distress_horizons)
        self.engineered_proj = nn.Linear(config.distress_engineered_dim, H)
        self.norm = RMSNorm(H)
        self.mlp = nn.Sequential(
            nn.Linear(2 * H, H),
            nn.GELU(),
            nn.Dropout(config.dropout),
            nn.Linear(H, H // 2),
            nn.GELU(),
            nn.Linear(H // 2, self.n_horizons * len(RISK_NAMES)),
        )

    def forward(self, household_embedding: torch.Tensor, engineered_features: torch.Tensor) -> torch.Tensor:
        eng = self.norm(self.engineered_proj(engineered_features))
        x = torch.cat([household_embedding, eng], dim=-1)
        return self.mlp(x).view(-1, self.n_horizons, len(RISK_NAMES))
