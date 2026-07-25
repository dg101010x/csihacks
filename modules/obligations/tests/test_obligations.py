from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from relief_contracts import FinancialEventV1
from relief_obligations.classify import detect_obligations
from relief_obligations.store import Base, InMemoryObligationStore, SqlObligationStore
from relief_recurring_detection import detect_recurring_patterns
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def rent_event(event_id: str, days_ago: int) -> FinancialEventV1:
    when = datetime(2026, 7, 25, 9, tzinfo=timezone.utc) - timedelta(days=days_ago)
    return FinancialEventV1(
        contract_version="1.0.0",
        event_id=event_id,
        household_id="hh_01",
        account_id="acct_01",
        source="synthetic_wells_fargo",
        source_event_id=event_id,
        event_type="scheduled_payment",
        event_status="posted",
        occurred_at=when,
        effective_at=when,
        amount_cents=145000,
        currency="USD",
        direction="outflow",
        merchant_name="Meridian Realty",
        merchant_category="rent",
        obligation_id=None,
        is_recurring=True,
        is_pending=False,
        metadata={},
    )


def test_detect_obligations_scores_rent_as_highly_essential():
    events = [rent_event("evt_1", 90), rent_event("evt_2", 60), rent_event("evt_3", 30)]
    patterns = detect_recurring_patterns(events)
    obligations = detect_obligations("hh_01", patterns)
    assert len(obligations) == 1
    obligation = obligations[0]
    assert obligation.obligation_type == "rent"
    assert obligation.essentiality_score == 0.95
    assert obligation.consumer_confirmed is False
    assert obligation.scheduled_amount_cents == 145000


def test_redetection_preserves_consumer_confirmation():
    events = [rent_event("evt_1", 90), rent_event("evt_2", 60), rent_event("evt_3", 30)]
    patterns = detect_recurring_patterns(events)
    first_pass = detect_obligations("hh_01", patterns)
    confirmed = first_pass[0].model_copy(update={"consumer_confirmed": True, "status": "active"})

    events.append(rent_event("evt_4", 0))
    new_patterns = detect_recurring_patterns(events)
    second_pass = detect_obligations("hh_01", new_patterns, existing_obligations=[confirmed])

    assert len(second_pass) == 1
    assert second_pass[0].obligation_id == confirmed.obligation_id
    assert second_pass[0].consumer_confirmed is True


@pytest.mark.parametrize("backend", ["memory", "sql"])
def test_store_upsert_and_list(backend):
    obligation = detect_obligations(
        "hh_01", detect_recurring_patterns([rent_event("evt_1", 90), rent_event("evt_2", 60), rent_event("evt_3", 30)])
    )[0]

    if backend == "memory":
        store = InMemoryObligationStore()
    else:
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        store = SqlObligationStore(sessionmaker(bind=engine)())

    store.upsert(obligation, household_id="hh_01")
    fetched = store.get(obligation.obligation_id)
    assert fetched.obligation_id == obligation.obligation_id
    assert [o.obligation_id for o in store.list_for_household("hh_01")] == [obligation.obligation_id]
