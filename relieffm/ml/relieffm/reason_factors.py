"""Section 27 — structured reason factor head.

Diagnostic only: the spec does not define a supervised target for these
("Plan Two may use them as supporting evidence, but its explanation layer
must verify them against deterministic facts"), so this head is not part
of the training loss — it's exposed for inspection and for a future
verification pass, not trained end-to-end.
"""
from __future__ import annotations

import torch
from torch import nn

from .config import NanoConfig

FACTOR_NAMES = (
    "low_current_liquidity",
    "income_timing_uncertainty",
    "income_amount_uncertainty",
    "obligation_concentration",
    "spending_volatility",
    "recent_fee_activity",
    "high_debt_burden",
    "low_reserve_coverage",
    "sparse_data",
    "stale_data",
)


class ReasonFactorHead(nn.Module):
    def __init__(self, config: NanoConfig):
        super().__init__()
        H = config.hidden_dimension
        self.mlp = nn.Sequential(nn.Linear(H, H), nn.GELU(), nn.Linear(H, len(FACTOR_NAMES)))

    def forward(self, household_embedding: torch.Tensor) -> torch.Tensor:
        return torch.softmax(self.mlp(household_embedding), dim=-1)
