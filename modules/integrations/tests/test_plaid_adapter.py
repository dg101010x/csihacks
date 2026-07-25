from __future__ import annotations

from datetime import datetime, timezone

from relief_integrations import PlaidAdapter


class FakePlaidClient:
    """Stands in for relief_integrations.PlaidClient so the adapter's
    mapping logic (sign-convention flip, pagination, account shape) can be
    tested without an HTTP layer at all."""

    env = "sandbox"

    def __init__(self, accounts, pages):
        self._accounts = accounts
        self._pages = pages
        self._calls = 0

    def get_accounts(self, access_token):
        return self._accounts

    def sync_transactions(self, access_token, *, cursor=None):
        page = self._pages[self._calls]
        self._calls += 1
        return page


def test_list_accounts_maps_balances_to_cents():
    client = FakePlaidClient(
        accounts=[
            {
                "account_id": "plaid_acc_1",
                "name": "Plaid Checking",
                "official_name": None,
                "type": "depository",
                "subtype": "checking",
                "balances": {"current": 1234.56, "available": 1200.00, "iso_currency_code": "USD"},
            }
        ],
        pages=[],
    )
    adapter = PlaidAdapter(client, get_access_token=lambda hh: "token-abc")
    accounts = adapter.list_accounts("hh_01")
    assert accounts[0].current_balance_cents == 123456
    assert accounts[0].available_balance_cents == 120000
    assert accounts[0].provider == "plaid"


def test_list_accounts_returns_empty_without_a_stored_access_token():
    client = FakePlaidClient(accounts=[], pages=[])
    adapter = PlaidAdapter(client, get_access_token=lambda hh: None)
    assert adapter.list_accounts("hh_01") == []


def test_list_events_flips_plaid_sign_convention_to_relief_direction():
    client = FakePlaidClient(
        accounts=[],
        pages=[
            {
                "added": [
                    {
                        "transaction_id": "txn_1",
                        "account_id": "plaid_acc_1",
                        "amount": 45.00,  # Plaid: positive = money out
                        "iso_currency_code": "USD",
                        "date": "2026-07-27",
                        "name": "Coffee Shop",
                        "merchant_name": "Coffee Shop",
                        "personal_finance_category": {"primary": "FOOD_AND_DRINK"},
                        "pending": False,
                    },
                    {
                        "transaction_id": "txn_2",
                        "account_id": "plaid_acc_1",
                        "amount": -2100.00,  # Plaid: negative = money in
                        "iso_currency_code": "USD",
                        "date": "2026-07-24",
                        "name": "Payroll",
                        "merchant_name": "Riverstone Logistics Payroll",
                        "personal_finance_category": {"primary": "INCOME"},
                        "pending": False,
                    },
                ],
                "modified": [],
                "removed": [],
                "next_cursor": "cursor-1",
                "has_more": False,
            }
        ],
    )
    adapter = PlaidAdapter(client, get_access_token=lambda hh: "token-abc")
    events = adapter.list_events("hh_01", since=datetime(2026, 1, 1, tzinfo=timezone.utc))

    outflow = next(e for e in events if e.event_id == "plaid_txn_1")
    inflow = next(e for e in events if e.event_id == "plaid_txn_2")
    assert outflow.direction.value == "outflow"
    assert outflow.amount_cents == 4500
    assert inflow.direction.value == "inflow"
    assert inflow.amount_cents == 210000


def test_list_events_paginates_until_has_more_is_false():
    client = FakePlaidClient(
        accounts=[],
        pages=[
            {
                "added": [
                    {
                        "transaction_id": "txn_page1",
                        "account_id": "plaid_acc_1",
                        "amount": 10.00,
                        "iso_currency_code": "USD",
                        "date": "2026-07-20",
                        "name": "A",
                        "pending": False,
                    }
                ],
                "modified": [],
                "removed": [],
                "next_cursor": "cursor-1",
                "has_more": True,
            },
            {
                "added": [
                    {
                        "transaction_id": "txn_page2",
                        "account_id": "plaid_acc_1",
                        "amount": 20.00,
                        "iso_currency_code": "USD",
                        "date": "2026-07-21",
                        "name": "B",
                        "pending": False,
                    }
                ],
                "modified": [],
                "removed": [],
                "next_cursor": "cursor-2",
                "has_more": False,
            },
        ],
    )
    adapter = PlaidAdapter(client, get_access_token=lambda hh: "token-abc")
    events = adapter.list_events("hh_01", since=datetime(2026, 1, 1, tzinfo=timezone.utc))
    assert {e.event_id for e in events} == {"plaid_txn_page1", "plaid_txn_page2"}
