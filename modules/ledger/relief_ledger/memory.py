from __future__ import annotations

from datetime import datetime
from typing import Optional

from relief_contracts import FinancialEventV1

from .errors import DuplicateEventError
from .store import LedgerStore


class InMemoryLedgerStore(LedgerStore):
    """Dict-backed ledger for tests and the demo seed path. Not for production
    persistence — see SqlLedgerStore for that."""

    def __init__(self) -> None:
        self._by_id: dict[str, FinancialEventV1] = {}
        self._dedupe_index: dict[tuple[str, str, str], str] = {}

    def append(self, event: FinancialEventV1) -> FinancialEventV1:
        dedupe_key = (event.source, event.source_event_id, event.account_id)
        existing_id = self._dedupe_index.get(dedupe_key)
        if existing_id is not None:
            existing = self._by_id[existing_id]
            if existing.model_dump() == event.model_dump():
                return existing
            raise DuplicateEventError(
                f"({dedupe_key}) already recorded as {existing_id} with different content"
            )
        self._by_id[event.event_id] = event
        self._dedupe_index[dedupe_key] = event.event_id
        return event

    def get(self, event_id: str) -> Optional[FinancialEventV1]:
        return self._by_id.get(event_id)

    def list_events(
        self,
        household_id: str,
        *,
        account_id: Optional[str] = None,
        effective_from: Optional[datetime] = None,
        effective_until: Optional[datetime] = None,
        statuses: Optional[list[str]] = None,
    ) -> list[FinancialEventV1]:
        events = [e for e in self._by_id.values() if e.household_id == household_id]
        if account_id is not None:
            events = [e for e in events if e.account_id == account_id]
        if effective_from is not None:
            events = [e for e in events if e.effective_at >= effective_from]
        if effective_until is not None:
            events = [e for e in events if e.effective_at <= effective_until]
        if statuses is not None:
            events = [e for e in events if e.event_status.value in statuses]
        return sorted(events, key=lambda e: e.effective_at)
