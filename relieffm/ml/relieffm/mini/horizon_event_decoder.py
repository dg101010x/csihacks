"""Section 21's horizon event decoder output heads. Each of `max_event_slots`
learned query slots (processed by the shared `HorizonDecoder`) predicts one
candidate uncertain future event: existence probability, type, time within
horizon, amount, direction, account association, recurrence association,
and obligation association — matched against true uncertain events via a
bipartite matching loss (`ml/training/mini_losses.py`), not a fixed
assignment, per section 21's parallel (non-recursive) design.
"""
from __future__ import annotations

import torch
from torch import nn

from .. import vocab
from ..config import MiniConfig


class EventSetHeads(nn.Module):
    def __init__(self, config: MiniConfig):
        super().__init__()
        H = config.hidden_dimension
        self.existence_head = nn.Linear(H, 1)
        self.event_type_head = nn.Linear(H, len(vocab.EVENT_TYPE))
        self.time_head = nn.Linear(H, 1)  # sigmoid -> fraction of horizon
        self.amount_head = nn.Linear(H, 1)  # amount-transformed, signed
        self.direction_head = nn.Linear(H, len(vocab.DIRECTION))
        self.account_head = nn.Linear(H, len(vocab.ACCOUNT_TYPE))
        self.recurrence_head = nn.Linear(H, len(vocab.RECURRENCE_STATE))
        self.obligation_linked_head = nn.Linear(H, 1)

    def forward(self, event_hidden: torch.Tensor) -> dict[str, torch.Tensor]:
        """event_hidden: (B, K, max_event_slots, H)."""
        return {
            "existence_logit": self.existence_head(event_hidden).squeeze(-1),
            "event_type_logits": self.event_type_head(event_hidden),
            "time_fraction": torch.sigmoid(self.time_head(event_hidden)).squeeze(-1),
            "amount": self.amount_head(event_hidden).squeeze(-1),
            "direction_logits": self.direction_head(event_hidden),
            "account_logits": self.account_head(event_hidden),
            "recurrence_logits": self.recurrence_head(event_hidden),
            "obligation_linked_logit": self.obligation_linked_head(event_hidden).squeeze(-1),
        }
