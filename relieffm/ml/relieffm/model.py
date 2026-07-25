"""Top-level ReliefFM Nano (section 19.1). Composes the seven architecture
modules from section 20, minus the ones Mini/Base-only: no intervention
encoder (section 29), no horizon event-set decoder (section 21) — Nano
predicts aggregate daily quantile series instead (section 19.1's own
output list).
"""
from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import nn

from .config import NanoConfig
from .context_encoder import HouseholdContextEncoder
from .distress_heads import DistressHeads
from .fusion import ContextFusionLayer
from .historical_encoder import HistoricalEventEncoder
from .known_future_encoder import KnownFutureEncoder
from .reason_factors import ReasonFactorHead
from .trajectory_heads import TrajectoryHeads


@dataclass
class ReliefFMOutput:
    household_embedding: torch.Tensor
    inflow_quantiles: torch.Tensor
    essential_outflow_quantiles: torch.Tensor
    discretionary_outflow_quantiles: torch.Tensor
    balance_residual_quantiles: torch.Tensor
    distress_probabilities: torch.Tensor  # (B, n_horizons, 3)
    reason_factors: torch.Tensor  # (B, n_factors)


class ReliefFMNano(nn.Module):
    def __init__(self, config: NanoConfig | None = None):
        super().__init__()
        self.config = config or NanoConfig()

        self.context_encoder = HouseholdContextEncoder(self.config)
        self.historical_encoder = HistoricalEventEncoder(self.config)
        self.known_future_encoder = KnownFutureEncoder(self.config)
        self.fusion = ContextFusionLayer(self.config)
        self.trajectory_heads = TrajectoryHeads(self.config)
        self.distress_heads = DistressHeads(self.config)
        self.reason_factor_head = ReasonFactorHead(self.config)

    def forward(self, batch: dict[str, torch.Tensor]) -> ReliefFMOutput:
        context_vec = self.context_encoder(batch)
        historical_encoded, historical_pooled = self.historical_encoder(batch)
        known_future_encoded, known_future_pooled = self.known_future_encoder(batch)

        household_embedding = self.fusion(context_vec, historical_pooled, known_future_pooled)

        trajectory = self.trajectory_heads(
            household_embedding,
            historical_encoded, batch["event_mask"],
            known_future_encoded, batch["known_mask"],
        )
        distress = self.distress_heads(household_embedding)
        reason_factors = self.reason_factor_head(household_embedding)

        return ReliefFMOutput(
            household_embedding=household_embedding,
            distress_probabilities=distress,
            reason_factors=reason_factors,
            **trajectory,
        )

    def num_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters())
