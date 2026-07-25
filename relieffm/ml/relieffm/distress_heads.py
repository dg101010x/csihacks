"""Section 26 — distress hazard heads.

Each risk stays a separate sigmoid probability at each configured horizon
("do not collapse all risks into one hidden distress score" — section 26)
"""
from __future__ import annotations

import torch
from torch import nn

from .config import NanoConfig

RISK_NAMES = ("negative_balance", "essential_reserve_violation", "missed_obligation")


class DistressHeads(nn.Module):
    def __init__(self, config: NanoConfig):
        super().__init__()
        H = config.hidden_dimension
        self.n_horizons = len(config.distress_horizons)
        self.mlp = nn.Sequential(
            nn.Linear(H, H),
            nn.GELU(),
            nn.Dropout(config.dropout),
            nn.Linear(H, self.n_horizons * len(RISK_NAMES)),
        )

    def forward(self, household_embedding: torch.Tensor) -> torch.Tensor:
        logits = self.mlp(household_embedding)
        logits = logits.view(-1, self.n_horizons, len(RISK_NAMES))
        return torch.sigmoid(logits)
