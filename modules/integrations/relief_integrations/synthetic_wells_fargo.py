from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from relief_contracts import FinancialEventV1
from relief_contracts.shared import AccountV1

from .provider import AccountProvider


class SyntheticWellsFargoAdapter(AccountProvider):
    """The Wells Fargo reference adapter (Section 16) — same AccountProvider
    interface a real Plaid-backed provider implements, backed by a fixture
    file instead of a live bank connection. This is what lets apps/api seed
    and demo the whole platform before any real institution is connected:
    swap this for PlaidAdapter and nothing upstream of the ledger changes.
    """

    provider_id = "synthetic_wells_fargo"

    def __init__(self, fixture_path: Path) -> None:
        self._snapshot = json.loads(Path(fixture_path).read_text())["household_snapshot"]

    def list_accounts(self, household_id: str) -> list[AccountV1]:
        if self._snapshot["household_id"] != household_id:
            return []
        return [AccountV1(**a) for a in self._snapshot["accounts"]]

    def list_events(self, household_id: str, *, since: datetime) -> list[FinancialEventV1]:
        if self._snapshot["household_id"] != household_id:
            return []
        raw_events = [*self._snapshot["recent_events"], *self._snapshot["known_future_events"]]
        events = [FinancialEventV1(**e) for e in raw_events]
        return [e for e in events if e.effective_at >= since]
