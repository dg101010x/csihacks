"""Section 20.5 — Context Fusion Layer.

Combines household state, historical event state, and known-future state
into the single reusable household embedding (section 4's first output).
Nano has no intervention state to fuse (that's Mini-scope, section 29).
"""
from __future__ import annotations

import torch
from torch import nn

from .config import NanoConfig


class ContextFusionLayer(nn.Module):
    def __init__(self, config: NanoConfig):
        super().__init__()
        H = config.hidden_dimension
        self.mlp = nn.Sequential(
            nn.Linear(3 * H, config.feedforward_dimension),
            nn.GELU(),
            nn.Dropout(config.dropout),
            nn.Linear(config.feedforward_dimension, H),
        )
        self.norm = nn.LayerNorm(H)

    def forward(self, context_vec: torch.Tensor, historical_vec: torch.Tensor, known_future_vec: torch.Tensor) -> torch.Tensor:
        fused = self.mlp(torch.cat([context_vec, historical_vec, known_future_vec], dim=-1))
        return self.norm(fused + context_vec)
