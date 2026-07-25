from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Optional

from relief_contracts import FinancialEventV1
from relief_contracts.shared import AccountV1

from .plaid_client import PlaidClient
from .provider import AccountProvider


def _map_account(raw: dict, *, is_simulated: bool) -> AccountV1:
    balances = raw.get("balances", {})
    current = balances.get("current")
    available = balances.get("available")
    return AccountV1(
        account_id=raw["account_id"],
        provider="plaid",
        account_type=raw.get("type", "unknown"),
        account_subtype=raw.get("subtype"),
        display_name=raw.get("official_name") or raw.get("name", "Account"),
        current_balance_cents=round((current or 0) * 100),
        available_balance_cents=round(available * 100) if available is not None else None,
        balance_updated_at=datetime.now(timezone.utc),
        data_status="current",
        is_simulated=is_simulated,
    )


def _map_transaction(raw: dict, *, household_id: str, contract_version: str = "1.0.0") -> FinancialEventV1:
    # Plaid's sign convention is the inverse of Relief's: a positive amount is
    # money leaving the account (a debit), negative is money coming in.
    amount = raw["amount"]
    direction = "outflow" if amount > 0 else "inflow"
    when = datetime.fromisoformat(raw["date"]).replace(tzinfo=timezone.utc)
    category = (raw.get("personal_finance_category") or {}).get("primary")

    return FinancialEventV1(
        contract_version=contract_version,
        event_id=f"plaid_{raw['transaction_id']}",
        household_id=household_id,
        account_id=raw["account_id"],
        source="plaid",
        source_event_id=raw["transaction_id"],
        event_type=(category or "transaction").lower(),
        event_status="pending" if raw.get("pending") else "posted",
        occurred_at=when,
        effective_at=when,
        amount_cents=round(abs(amount) * 100),
        currency=raw.get("iso_currency_code") or "USD",
        direction=direction,
        merchant_name=raw.get("merchant_name") or raw.get("name"),
        merchant_category=category,
        obligation_id=None,  # matched later by modules/recurring_detection + modules/obligations
        is_recurring=False,
        is_pending=bool(raw.get("pending")),
        metadata={"plaid_category": raw.get("category") or []},
    )


class PlaidAdapter(AccountProvider):
    """Section 15: the same AccountProvider interface
    SyntheticWellsFargoAdapter implements, backed by a real Plaid Item.
    `get_access_token` resolves a household to its stored Plaid access
    token — token persistence itself belongs to apps/api, not this module.
    """

    provider_id = "plaid"

    def __init__(self, client: PlaidClient, get_access_token: Callable[[str], Optional[str]]) -> None:
        self._client = client
        self._get_access_token = get_access_token

    def list_accounts(self, household_id: str) -> list[AccountV1]:
        access_token = self._get_access_token(household_id)
        if access_token is None:
            return []
        is_simulated = self._client.env != "production"
        return [_map_account(a, is_simulated=is_simulated) for a in self._client.get_accounts(access_token)]

    def list_events(self, household_id: str, *, since: datetime) -> list[FinancialEventV1]:
        access_token = self._get_access_token(household_id)
        if access_token is None:
            return []

        events: list[FinancialEventV1] = []
        cursor: Optional[str] = None
        while True:
            page = self._client.sync_transactions(access_token, cursor=cursor)
            for raw in page.get("added", []) + page.get("modified", []):
                event = _map_transaction(raw, household_id=household_id)
                if event.effective_at >= since:
                    events.append(event)
            cursor = page.get("next_cursor")
            if not page.get("has_more"):
                break
        return events
