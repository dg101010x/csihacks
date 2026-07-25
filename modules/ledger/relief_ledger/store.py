from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from relief_contracts import FinancialEventV1


class LedgerStore(ABC):
    """Append-only store of FinancialEventV1 records (Section 9, Section 32.5).

    Every method that would mutate history is deliberately absent — the only
    way to change the ledger's view of the world is to append a new
    ``corrected`` or ``cancelled`` event referencing the original, never to
    edit or delete a prior row.
    """

    @abstractmethod
    def append(self, event: FinancialEventV1) -> FinancialEventV1:
        """Append one event. Idempotent on (source, source_event_id, account_id):
        appending an identical duplicate is a no-op that returns the stored
        event; appending a same-key event with different content raises
        DuplicateEventError."""

    def append_many(self, events: list[FinancialEventV1]) -> list[FinancialEventV1]:
        return [self.append(event) for event in events]

    @abstractmethod
    def get(self, event_id: str) -> Optional[FinancialEventV1]:
        ...

    @abstractmethod
    def list_events(
        self,
        household_id: str,
        *,
        account_id: Optional[str] = None,
        effective_from: Optional[datetime] = None,
        effective_until: Optional[datetime] = None,
        statuses: Optional[list[str]] = None,
    ) -> list[FinancialEventV1]:
        """Return events for a household ordered by effective_at ascending."""

    def recent_events(self, household_id: str, as_of: datetime) -> list[FinancialEventV1]:
        """Posted events with effective_at <= as_of (Section 10)."""
        return [
            e
            for e in self.list_events(household_id, effective_until=as_of, statuses=["posted"])
        ]

    def known_future_events(self, household_id: str, as_of: datetime) -> list[FinancialEventV1]:
        """Scheduled/pending events with effective_at > as_of (Section 10)."""
        events = self.list_events(household_id, effective_from=as_of, statuses=["scheduled", "pending"])
        return [e for e in events if e.effective_at > as_of]

    def balance_as_of(self, household_id: str, account_id: str, as_of: datetime, opening_balance_cents: int = 0) -> int:
        """Replay posted events up to `as_of` to derive a balance (Section 45)."""
        balance = opening_balance_cents
        for event in self.list_events(household_id, account_id=account_id, effective_until=as_of, statuses=["posted"]):
            balance += event.amount_cents if event.direction == "inflow" else -event.amount_cents
        return balance
