from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from relief_contracts.fixtures import minimal_forecast_request, minimal_household_snapshot, minimal_intervention_request
from relief_contracts.schemas import (
    AccountState,
    AccountType,
    Direction,
    EssentialityCategory,
    EventStatus,
    EventType,
    ForecastRequestV1,
    HistoricalEvent,
    HouseholdSnapshotV1,
    HouseholdState,
    Intervention,
    InterventionSimulationRequestV1,
    Obligation,
    ObligationType,
    PaymentStatus,
    RecurrenceState,
    SourceType,
)

AS_OF = datetime(2026, 7, 25, 12, 0, 0)


def _base_state() -> HouseholdState:
    return HouseholdState(
        total_liquid_balance_cents=100_000,
        available_balance_cents=100_000,
        num_accounts=1,
        num_obligations=0,
        essential_reserve_cents=10_000,
        data_freshness_hours=1.0,
        snapshot_completeness=1.0,
    )


def _base_account() -> AccountState:
    return AccountState(
        account_id="acct_01",
        account_type=AccountType.CHECKING,
        current_balance_cents=100_000,
        available_balance_cents=100_000,
        data_freshness_hours=1.0,
    )


def test_fixtures_round_trip():
    snapshot = minimal_household_snapshot()
    dumped = snapshot.model_dump_json()
    restored = HouseholdSnapshotV1.model_validate_json(dumped)
    assert restored == snapshot

    req = minimal_forecast_request()
    assert req.model_validate_json(req.model_dump_json()) == req

    intervention_req = minimal_intervention_request()
    assert intervention_req.model_validate_json(intervention_req.model_dump_json()) == intervention_req


def test_rejects_missing_household_id():
    with pytest.raises(ValidationError):
        HouseholdSnapshotV1(
            household_id="",
            currency="USD",
            as_of=AS_OF,
            household_state=_base_state(),
            accounts=[_base_account()],
        )


def test_rejects_unsupported_currency():
    with pytest.raises(ValidationError):
        HouseholdSnapshotV1(
            household_id="hh_01",
            currency="XYZ",
            as_of=AS_OF,
            household_state=_base_state(),
            accounts=[_base_account()],
        )


def test_rejects_impossible_timestamp():
    bad_event = HistoricalEvent(
        event_id="ev_bad",
        event_type=EventType.PURCHASE,
        event_status=EventStatus.POSTED,
        amount_cents=1_000,
        direction=Direction.OUTFLOW,
        account_id="acct_01",
        source_type=SourceType.SIMULATED,
        occurrence_time=AS_OF,
        effective_time=AS_OF - timedelta(days=10),  # effective before occurrence, beyond skew tolerance
    )
    with pytest.raises(ValidationError):
        HouseholdSnapshotV1(
            household_id="hh_01",
            currency="USD",
            as_of=AS_OF,
            household_state=_base_state(),
            accounts=[_base_account()],
            historical_events=[bad_event],
        )


def test_rejects_malformed_obligation_amount():
    with pytest.raises(ValidationError):
        Obligation(
            obligation_id="obl_bad",
            obligation_type=ObligationType.RENT,
            scheduled_amount_cents=0,
            due_date=AS_OF + timedelta(days=5),
            recurrence=RecurrenceState.MONTHLY,
            essentiality_category=EssentialityCategory.ESSENTIAL,
            payment_status=PaymentStatus.CURRENT,
            account_id="acct_01",
        )


def test_rejects_negative_scenario_count():
    with pytest.raises(ValidationError):
        ForecastRequestV1(
            contract_version="1.0.0",
            request_id="req_01",
            snapshot=minimal_household_snapshot(),
            horizon_days=30,
            scenario_count=-1,
        )


def test_rejects_unknown_contract_version():
    with pytest.raises(ValidationError):
        ForecastRequestV1(
            contract_version="9.9.9",
            request_id="req_01",
            snapshot=minimal_household_snapshot(),
            horizon_days=30,
            scenario_count=8,
        )


def test_rejects_unsupported_intervention_type():
    with pytest.raises(ValidationError):
        Intervention(action_type="do_something_illegal", obligation_id="obl_01", parameters={})


def test_intervention_request_fixture_valid():
    req = minimal_intervention_request()
    assert req.intervention.action_type == "split_payment"
