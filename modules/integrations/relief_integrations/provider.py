from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from relief_contracts import FinancialEventV1
from relief_contracts.shared import AccountV1


class AccountProvider(ABC):
    """One interface every account/transaction source implements (Section
    15-16) — Plaid, the synthetic Wells Fargo reference adapter, and any
    future provider. apps/api's ledger ingestion never branches on which
    provider it's talking to; it only calls these two methods."""

    provider_id: str

    @abstractmethod
    def list_accounts(self, household_id: str) -> list[AccountV1]: ...

    @abstractmethod
    def list_events(self, household_id: str, *, since: datetime) -> list[FinancialEventV1]: ...
