from __future__ import annotations

from datetime import datetime, timezone

import pytest
from relief_contracts import FinancialEventV1
from relief_ledger import DuplicateEventError, InMemoryLedgerStore, SqlLedgerStore
from relief_ledger.sql import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def make_event(**overrides) -> FinancialEventV1:
    base = dict(
        contract_version="1.0.0",
        event_id="evt_1",
        household_id="hh_01",
        account_id="acct_01",
        source="synthetic_wells_fargo",
        source_event_id="src_1",
        event_type="paycheck",
        event_status="posted",
        occurred_at=datetime(2026, 7, 24, 8, tzinfo=timezone.utc),
        effective_at=datetime(2026, 7, 24, 8, tzinfo=timezone.utc),
        amount_cents=210000,
        currency="USD",
        direction="inflow",
        merchant_name="Payroll",
        merchant_category="payroll",
        obligation_id=None,
        is_recurring=True,
        is_pending=False,
        metadata={},
    )
    base.update(overrides)
    return FinancialEventV1(**base)


@pytest.fixture(params=["memory", "sql"])
def store(request):
    if request.param == "memory":
        yield InMemoryLedgerStore()
    else:
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        session = sessionmaker(bind=engine)()
        yield SqlLedgerStore(session)
        session.close()


def test_append_and_get(store):
    event = make_event()
    store.append(event)
    assert store.get("evt_1") == event


def test_append_is_idempotent_for_identical_duplicate(store):
    event = make_event()
    store.append(event)
    store.append(event)  # no-op, not an error
    assert len(store.list_events("hh_01")) == 1


def test_append_rejects_conflicting_duplicate(store):
    store.append(make_event())
    conflicting = make_event(amount_cents=1)
    with pytest.raises(DuplicateEventError):
        store.append(conflicting)


def test_list_events_filters_by_status_and_window(store):
    store.append(make_event(event_id="evt_posted", event_status="posted"))
    store.append(
        make_event(
            event_id="evt_future",
            source_event_id="src_2",
            event_status="scheduled",
            occurred_at=datetime(2026, 7, 31, 8, tzinfo=timezone.utc),
            effective_at=datetime(2026, 7, 31, 8, tzinfo=timezone.utc),
        )
    )
    as_of = datetime(2026, 7, 25, tzinfo=timezone.utc)
    recent = store.recent_events("hh_01", as_of)
    future = store.known_future_events("hh_01", as_of)
    assert [e.event_id for e in recent] == ["evt_posted"]
    assert [e.event_id for e in future] == ["evt_future"]


def test_balance_as_of_replays_posted_events(store):
    store.append(make_event(event_id="evt_in", amount_cents=100000, direction="inflow"))
    store.append(
        make_event(
            event_id="evt_out",
            source_event_id="src_2",
            amount_cents=30000,
            direction="outflow",
            event_type="scheduled_payment",
        )
    )
    balance = store.balance_as_of("hh_01", "acct_01", datetime(2026, 7, 25, tzinfo=timezone.utc))
    assert balance == 70000
