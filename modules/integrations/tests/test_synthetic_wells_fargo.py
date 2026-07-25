from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from relief_integrations import SyntheticWellsFargoAdapter

FIXTURE_PATH = (
    Path(__file__).resolve().parents[3] / "packages" / "test_fixtures" / "fixtures" / "sarah_baseline.json"
)


def test_list_accounts_returns_the_fixture_household_accounts():
    adapter = SyntheticWellsFargoAdapter(FIXTURE_PATH)
    accounts = adapter.list_accounts("hh_01")
    assert len(accounts) == 1
    assert accounts[0].account_id == "acct_01"
    assert accounts[0].provider == "synthetic_wells_fargo"


def test_list_accounts_returns_empty_for_a_different_household():
    adapter = SyntheticWellsFargoAdapter(FIXTURE_PATH)
    assert adapter.list_accounts("hh_someone_else") == []


def test_list_events_combines_recent_and_future_and_filters_by_since():
    adapter = SyntheticWellsFargoAdapter(FIXTURE_PATH)
    since = datetime(2026, 7, 27, tzinfo=timezone.utc)
    events = adapter.list_events("hh_01", since=since)
    assert all(e.effective_at >= since for e in events)
    assert any(e.event_id == "evt_income_hh01_08" for e in events)
    assert not any(e.event_id == "evt_income_hh01_07" for e in events)  # occurs before `since`
