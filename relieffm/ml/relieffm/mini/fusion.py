"""Mini's Context Fusion Layer (section 20.5), SwiGLU/RMSNorm version."""
from __future__ import annotations

import torch
from torch import nn

from ..blocks import RMSNorm, SwiGLU
from ..config import MiniConfig


class ContextFusionLayer(nn.Module):
    def __init__(self, config: MiniConfig):
        super().__init__()
        H = config.hidden_dimension
        self.proj_in = nn.Linear(3 * H, H, bias=False)
        self.norm = RMSNorm(H)
        self.ff = SwiGLU(H, config.feedforward_dimension, config.dropout)
        self.final_norm = RMSNorm(H)

    def forward(self, context_vec: torch.Tensor, historical_vec: torch.Tensor, known_future_vec: torch.Tensor) -> torch.Tensor:
        x = context_vec + self.proj_in(torch.cat([context_vec, historical_vec, known_future_vec], dim=-1))
        x = x + self.ff(self.norm(x))
        return self.final_norm(x)
