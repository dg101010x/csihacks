"""Top-level ReliefFM Mini. Composes: three modern-block encoders + fusion
(sections 20.2-20.5), a shared horizon decoder producing both day-level
and event-slot hidden states from one latent-conditioned pass per
scenario (sections 21-22), trajectory + event-set output heads, distress
heads with legitimate engineered features, the diagnostic reason-factor
head (reused from Nano unmodified), and coupled baseline/intervention
decoding for intervention-conditioned forecasting (sections 29-31).

Unlike Nano, everything here is new/untrained code this session — see
`ml/model_cards/relieffm_mini.md` for what's verified vs. what's a
reasonable-effort design choice under time pressure.
"""
from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import nn

from ..config import MiniConfig
from ..reason_factors import FACTOR_NAMES, ReasonFactorHead
from .context_encoder import HouseholdContextEncoder
from .distress_heads import DistressHeads
from .fusion import ContextFusionLayer
from .historical_encoder import HistoricalEventEncoder
from .horizon_decoder import HorizonDecoder
from .horizon_event_decoder import EventSetHeads
from .intervention_encoder import InterventionEncoder
from .known_future_encoder import KnownFutureEncoder
from .trajectory_heads import TrajectoryHeads


@dataclass
class MiniOutput:
    household_embedding: torch.Tensor
    distress_logits: torch.Tensor
    distress_probabilities: torch.Tensor
    reason_factors: torch.Tensor
    baseline_trajectory: dict[str, torch.Tensor]
    baseline_event_set: dict[str, torch.Tensor]
    intervention_trajectory: dict[str, torch.Tensor] | None
    masked_reconstruction: dict[str, torch.Tensor] | None = None


class ReliefFMMini(nn.Module):
    def __init__(self, config: MiniConfig | None = None):
        super().__init__()
        self.config = config or MiniConfig()

        self.context_encoder = HouseholdContextEncoder(self.config)
        self.historical_encoder = HistoricalEventEncoder(self.config)
        self.known_future_encoder = KnownFutureEncoder(self.config)
        self.fusion = ContextFusionLayer(self.config)

        self.horizon_decoder = HorizonDecoder(self.config)
        self.trajectory_heads = TrajectoryHeads(self.config)
        self.event_set_heads = EventSetHeads(self.config)

        self.intervention_encoder = InterventionEncoder(self.config)

        self.distress_heads = DistressHeads(self.config)
        self.reason_factor_head = ReasonFactorHead(self.config)

    def encode(self, batch: dict[str, torch.Tensor]):
        """Returns (household_embedding, memory, memory_mask, context_vec, mlm_out)."""
        context_vec = self.context_encoder(batch)
        historical_encoded, historical_pooled, mlm_out = self.historical_encoder(batch)
        known_future_encoded, known_future_pooled = self.known_future_encoder(batch)
        household_embedding = self.fusion(context_vec, historical_pooled, known_future_pooled)

        memory = torch.cat(
            [historical_encoded, known_future_encoded, household_embedding.unsqueeze(1), context_vec.unsqueeze(1)], dim=1
        )
        B = context_vec.shape[0]
        device = context_vec.device
        memory_mask = torch.cat(
            [batch["event_mask"], batch["known_mask"], torch.ones(B, 2, device=device)], dim=1
        )
        return household_embedding, memory, memory_mask, context_vec, mlm_out

    def forward(self, batch: dict[str, torch.Tensor], n_scenarios: int, include_intervention: bool = True) -> MiniOutput:
        household_embedding, memory, memory_mask, context_vec, mlm_out = self.encode(batch)

        distress_logits = self.distress_heads(household_embedding, batch["engineered_features"])
        distress = torch.sigmoid(distress_logits)
        reason_factors = self.reason_factor_head(household_embedding)

        B = household_embedding.shape[0]
        z = self.horizon_decoder.sample_latent(B, n_scenarios, household_embedding.device, household_embedding.dtype)

        day_hidden, event_hidden = self.horizon_decoder(memory, memory_mask, z)
        baseline_trajectory = self.trajectory_heads(day_hidden)
        baseline_event_set = self.event_set_heads(event_hidden)

        intervention_trajectory = None
        if include_intervention:
            intervention_vec = self.intervention_encoder(batch["intervention_action_idx"], batch["intervention_numeric"])
            memory_i = torch.cat([memory, intervention_vec.unsqueeze(1)], dim=1)
            mask_i = torch.cat([memory_mask, torch.ones(B, 1, device=memory_mask.device)], dim=1)
            day_hidden_i, _event_hidden_i = self.horizon_decoder(memory_i, mask_i, z)
            intervention_trajectory = self.trajectory_heads(day_hidden_i)

        return MiniOutput(
            household_embedding=household_embedding,
            distress_logits=distress_logits,
            distress_probabilities=distress,
            reason_factors=reason_factors,
            baseline_trajectory=baseline_trajectory,
            baseline_event_set=baseline_event_set,
            intervention_trajectory=intervention_trajectory,
            masked_reconstruction=mlm_out,
        )

    def num_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters())
