"""Section 20.6 (Nano's aggregate variant of the Horizon Decoder) + section
20.7 / section 25's direct trajectory head.

Nano skips the full horizon *event-set* decoder (section 21 — that's
Mini-scope: individual event existence/type/amount slots). Instead it uses
a parallel (non-autoregressive) decoder with one learned query per forecast
day — avoiding the recursive-generation degradation section 21 warns
about — that cross-attends to the historical and known-future streams and
predicts four **uncertain-component** daily quantile series directly
(section 25): inflow, essential outflow, discretionary outflow, and a
balance-residual series. All four are quantile heads (p10/p50/p90) with a
monotonicity constraint built in, since nothing else enforces p10 <= p50
<= p90 downstream.
"""
from __future__ import annotations

import torch
from torch import nn

from .config import NanoConfig


class _QuantileHead(nn.Module):
    def __init__(self, hidden_dim: int):
        super().__init__()
        self.median = nn.Linear(hidden_dim, 1)
        self.spread = nn.Linear(hidden_dim, 2)  # softplus'd -> [lower_gap, upper_gap]

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        median = self.median(x)
        gaps = torch.nn.functional.softplus(self.spread(x))
        p10 = median - gaps[..., 0:1]
        p90 = median + gaps[..., 1:2]
        return torch.cat([p10, median, p90], dim=-1)  # (..., 3)


class TrajectoryHeads(nn.Module):
    def __init__(self, config: NanoConfig):
        super().__init__()
        H = config.hidden_dimension
        self.horizon_days = config.forecast_horizon_days
        self.day_queries = nn.Embedding(config.forecast_horizon_days, H)
        self.household_token_proj = nn.Identity()

        decoder_layer = nn.TransformerDecoderLayer(
            d_model=H,
            nhead=config.attention_heads,
            dim_feedforward=config.feedforward_dimension,
            dropout=config.dropout,
            batch_first=True,
            activation="gelu",
        )
        self.decoder = nn.TransformerDecoder(decoder_layer, num_layers=config.decoder_layers)

        self.inflow_head = _QuantileHead(H)
        self.essential_outflow_head = _QuantileHead(H)
        self.discretionary_outflow_head = _QuantileHead(H)
        self.balance_residual_head = _QuantileHead(H)

    def forward(
        self,
        household_embedding: torch.Tensor,
        historical_encoded: torch.Tensor,
        historical_mask: torch.Tensor,
        known_future_encoded: torch.Tensor,
        known_future_mask: torch.Tensor,
    ) -> dict[str, torch.Tensor]:
        B = household_embedding.shape[0]
        device = household_embedding.device

        memory = torch.cat([historical_encoded, known_future_encoded, household_embedding.unsqueeze(1)], dim=1)
        memory_mask = torch.cat(
            [historical_mask, known_future_mask, torch.ones(B, 1, device=device)], dim=1
        )
        from .nn_utils import key_padding_mask

        tgt = self.day_queries.weight.unsqueeze(0).expand(B, -1, -1)  # (B, horizon_days, H)
        decoded = self.decoder(tgt, memory, memory_key_padding_mask=key_padding_mask(memory_mask))

        return {
            "inflow_quantiles": self.inflow_head(decoded),
            "essential_outflow_quantiles": self.essential_outflow_head(decoded),
            "discretionary_outflow_quantiles": self.discretionary_outflow_head(decoded),
            "balance_residual_quantiles": self.balance_residual_head(decoded),
        }
