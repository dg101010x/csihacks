"""Section 20's intervention encoder / section 12.6's intervention token.

Deliberately self-contained rather than reusing `field_encoder.TokenEmbedder`'s
shared segment-embedding table: that table's size (`NUM_SEGMENTS`) is baked
into the already-trained Nano checkpoint's `state_dict`, and bumping it to
fit a sixth (intervention) segment would break `load_state_dict` on that
checkpoint. Intervention only ever appears as a single always-present-or-
absent token, so it doesn't need to share a table with anything.
"""
from __future__ import annotations

import torch
from torch import nn

from .. import vocab
from ..config import MiniConfig


class InterventionEncoder(nn.Module):
    def __init__(self, config: MiniConfig):
        super().__init__()
        H = config.hidden_dimension
        self.action_embedding = nn.Embedding(len(vocab.INTERVENTION_ACTION_TYPE), H, padding_idx=0)
        self.numeric_projection = nn.Linear(config.intervention_numeric_dim, H)
        self.segment_bias = nn.Parameter(torch.zeros(H))

    def forward(self, action_type_idx: torch.Tensor, numeric: torch.Tensor) -> torch.Tensor:
        """action_type_idx: (B,) long, numeric: (B, intervention_numeric_dim) -> (B, H)."""
        return self.action_embedding(action_type_idx) + self.numeric_projection(numeric) + self.segment_bias
