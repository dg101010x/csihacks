"""Section 20.1 — Financial Field Encoder.

Implements equation from section 13: e_i = sum of categorical field
embeddings + a learned projection of the numeric feature vector. One
`TokenEmbedder` instance is shared by every token class that needs it
(accounts, obligations, historical events, known-future events) — each
gets its own instance because vocab sets and numeric widths differ, but
the mechanism (sum embeddings, add a numeric projection, add a segment
embedding) is identical across all six token classes in section 12.
"""
from __future__ import annotations

import torch
from torch import nn

# Segment ids distinguishing token classes when they're pooled together
# (section 17: "explicit segment embeddings to distinguish... Historical
# events / Current state / Known future events / Proposed intervention /
# Forecast queries"). Nano has no intervention token.
SEGMENT_HOUSEHOLD = 0
SEGMENT_ACCOUNT = 1
SEGMENT_OBLIGATION = 2
SEGMENT_HISTORICAL = 3
SEGMENT_KNOWN_FUTURE = 4
NUM_SEGMENTS = 5


class TokenEmbedder(nn.Module):
    def __init__(self, vocab_sizes: list[int], numeric_dim: int, hidden_dim: int, segment_id: int):
        super().__init__()
        self.categorical_embeddings = nn.ModuleList(
            [nn.Embedding(vocab_size, hidden_dim, padding_idx=0) for vocab_size in vocab_sizes]
        )
        self.numeric_projection = nn.Linear(numeric_dim, hidden_dim)
        self.segment_id = segment_id
        self.segment_embedding = nn.Embedding(NUM_SEGMENTS, hidden_dim)

    def forward(self, categorical: torch.Tensor, numeric: torch.Tensor) -> torch.Tensor:
        """categorical: (..., n_fields) long, numeric: (..., numeric_dim) float -> (..., hidden_dim)."""
        embedded = sum(emb(categorical[..., i]) for i, emb in enumerate(self.categorical_embeddings))
        embedded = embedded + self.numeric_projection(numeric)
        segment = self.segment_embedding.weight[self.segment_id]
        return embedded + segment


class HouseholdStateEmbedder(nn.Module):
    """No categorical fields — section 12.1 is purely numeric/scalar."""

    def __init__(self, numeric_dim: int, hidden_dim: int):
        super().__init__()
        self.numeric_projection = nn.Linear(numeric_dim, hidden_dim)
        self.segment_embedding = nn.Embedding(NUM_SEGMENTS, hidden_dim)

    def forward(self, numeric: torch.Tensor) -> torch.Tensor:
        return self.numeric_projection(numeric) + self.segment_embedding.weight[SEGMENT_HOUSEHOLD]
