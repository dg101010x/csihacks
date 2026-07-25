"""Section 25's direct trajectory head, Mini version: point predictions per
scenario (not per-day quantile triples like Nano) — diversity comes from
the scenario latent `z`, and daily quantiles for the contract response are
computed empirically across the `scenario_count` generated trajectories
at inference time (`services/model_inference`), which is closer to what
section 22's "complete trajectory ensembles" actually means than Nano's
parametric per-day quantile heads.
"""
from __future__ import annotations

import torch
from torch import nn

from ..config import MiniConfig


class TrajectoryHeads(nn.Module):
    def __init__(self, config: MiniConfig):
        super().__init__()
        H = config.hidden_dimension
        self.inflow_head = nn.Linear(H, 1)
        self.essential_outflow_head = nn.Linear(H, 1)
        self.discretionary_outflow_head = nn.Linear(H, 1)
        self.balance_residual_head = nn.Linear(H, 1)

    def forward(self, day_hidden: torch.Tensor) -> dict[str, torch.Tensor]:
        """day_hidden: (B, K, horizon_days, H) -> each output (B, K, horizon_days)."""
        return {
            "inflow": self.inflow_head(day_hidden).squeeze(-1),
            "essential_outflow": self.essential_outflow_head(day_hidden).squeeze(-1),
            "discretionary_outflow": self.discretionary_outflow_head(day_hidden).squeeze(-1),
            "balance_residual": self.balance_residual_head(day_hidden).squeeze(-1),
        }
