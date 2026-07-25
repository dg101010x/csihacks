from __future__ import annotations

from datetime import datetime, timedelta, timezone

from relief_contracts import FinancialEventV1
from relief_recurring_detection import detect_recurring_patterns


def make_event(event_id: str, days_ago: int, amount_cents: int, **overrides) -> FinancialEventV1:
    when = datetime(2026, 7, 25, 9, tzinfo=timezone.utc) - timedelta(days=days_ago)
    base = dict(
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
        amount_cents=amount_cents,
        currency="USD",
        direction="outflow",
        merchant_name="Meridian Realty",
        merchant_category="rent",
        obligation_id=None,
        is_recurring=True,
        is_pending=False,
        metadata={},
    )
    base.update(overrides)
    return FinancialEventV1(**base)


def test_detects_monthly_rent_with_high_confidence():
    events = [
        make_event("evt_1", 90, 145000),
        make_event("evt_2", 60, 145000),
        make_event("evt_3", 30, 145000),
        make_event("evt_4", 0, 145000),
    ]
    patterns = detect_recurring_patterns(events)
    assert len(patterns) == 1
    pattern = patterns[0]
    assert pattern.recurrence_rule == "FREQ=MONTHLY"
    assert pattern.confidence > 0.8
    assert pattern.average_amount_cents == 145000
    assert pattern.next_predicted_at is not None


def test_single_occurrence_is_not_a_pattern():
    events = [make_event("evt_1", 0, 5000, merchant_name="One Time Shop", merchant_category="retail")]
    assert detect_recurring_patterns(events) == []


def test_irregular_amounts_and_timing_lower_confidence():
    regular = detect_recurring_patterns(
        [
            make_event("evt_1", 90, 145000),
            make_event("evt_2", 60, 145000),
            make_event("evt_3", 30, 145000),
        ]
    )[0]
    irregular = detect_recurring_patterns(
        [
            make_event("evt_4", 95, 40000, merchant_name="Variable Merchant", merchant_category="misc"),
            make_event("evt_5", 51, 90000, merchant_name="Variable Merchant", merchant_category="misc"),
            make_event("evt_6", 3, 15000, merchant_name="Variable Merchant", merchant_category="misc"),
        ]
    )[0]
    assert irregular.confidence < regular.confidence


def test_scheduled_events_are_ignored():
    events = [
        make_event("evt_1", 90, 145000),
        make_event("evt_2", 60, 145000, event_status="scheduled"),
    ]
    assert detect_recurring_patterns(events) == []
