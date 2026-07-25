"""Tier One deterministic unit fixtures (AGENTS_FM.md section 34).

Used for contract testing, accounting testing, and model input testing.
Kept as code (not static JSON) so they can't silently drift from the schema.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from relief_contracts.schemas import (
    AccountState,
    AccountType,
    Direction,
    EssentialityCategory,
    EventStatus,
    EventType,
    HistoricalEvent,
    HouseholdSnapshotV1,
    HouseholdState,
    Intervention,
    InterventionSimulationRequestV1,
    KnownFutureEvent,
    KnownFutureEventSource,
    ForecastRequestV1,
    Obligation,
    ObligationType,
    PaymentStatus,
    RecurrenceState,
    SourceType,
)

AS_OF = datetime(2026, 7, 25, 12, 0, 0)


def minimal_household_snapshot(household_id: str = "hh_fixture_01") -> HouseholdSnapshotV1:
    """One checking account, one rent obligation, one paycheck history, one known future paycheck."""
    account = AccountState(
        account_id="acct_checking_01",
        account_type=AccountType.CHECKING,
        account_subtype="checking",
        current_balance_cents=150_000,
        available_balance_cents=150_000,
        data_freshness_hours=2.0,
    )
    obligation = Obligation(
        obligation_id="obl_rent_01",
        obligation_type=ObligationType.RENT,
        scheduled_amount_cents=180_000,
        due_date=AS_OF + timedelta(days=6),
        recurrence=RecurrenceState.MONTHLY,
        essentiality_category=EssentialityCategory.ESSENTIAL,
        payment_status=PaymentStatus.CURRENT,
        account_id=account.account_id,
    )
    history = [
        HistoricalEvent(
            event_id="ev_paycheck_prev",
            event_type=EventType.PAYCHECK,
            event_status=EventStatus.POSTED,
            amount_cents=320_000,
            direction=Direction.INFLOW,
            account_id=account.account_id,
            merchant_category="payroll",
            recurrence_state=RecurrenceState.BIWEEKLY,
            transaction_confidence=1.0,
            source_type=SourceType.SIMULATED,
            occurrence_time=AS_OF - timedelta(days=11),
            effective_time=AS_OF - timedelta(days=11),
        ),
        HistoricalEvent(
            event_id="ev_rent_prev",
            event_type=EventType.RENT_PAYMENT,
            event_status=EventStatus.POSTED,
            amount_cents=180_000,
            direction=Direction.OUTFLOW,
            account_id=account.account_id,
            merchant_category="housing",
            recurrence_state=RecurrenceState.MONTHLY,
            source_type=SourceType.SIMULATED,
            occurrence_time=AS_OF - timedelta(days=25),
            effective_time=AS_OF - timedelta(days=25),
        ),
    ]
    known_future = [
        KnownFutureEvent(
            event_id="kfe_paycheck_next",
            event_type=EventType.PAYCHECK,
            amount_cents=320_000,
            direction=Direction.INFLOW,
            account_id=account.account_id,
            effective_time=AS_OF + timedelta(days=3),
            source=KnownFutureEventSource.CONFIRMED_PAYCHECK,
        ),
        KnownFutureEvent(
            event_id="kfe_rent_next",
            event_type=EventType.RENT_PAYMENT,
            amount_cents=180_000,
            direction=Direction.OUTFLOW,
            account_id=account.account_id,
            effective_time=obligation.due_date,
            source=KnownFutureEventSource.CONFIRMED_RENT_PAYMENT,
            obligation_id=obligation.obligation_id,
        ),
    ]
    state = HouseholdState(
        total_liquid_balance_cents=account.current_balance_cents,
        available_balance_cents=account.available_balance_cents,
        num_accounts=1,
        num_obligations=1,
        essential_reserve_cents=50_000,
        data_freshness_hours=2.0,
        snapshot_completeness=1.0,
    )
    return HouseholdSnapshotV1(
        household_id=household_id,
        currency="USD",
        as_of=AS_OF,
        household_state=state,
        accounts=[account],
        obligations=[obligation],
        historical_events=history,
        known_future_events=known_future,
    )


def minimal_forecast_request() -> ForecastRequestV1:
    return ForecastRequestV1(
        contract_version="1.0.0",
        request_id="forecast_req_fixture_01",
        snapshot=minimal_household_snapshot(),
        horizon_days=30,
        scenario_count=8,
        requested_outputs=[
            "daily_balance_trajectories",
            "distress_probabilities",
            "income_distribution",
            "variable_spending_distribution",
        ],
    )


def minimal_intervention_request() -> InterventionSimulationRequestV1:
    snapshot = minimal_household_snapshot()
    return InterventionSimulationRequestV1(
        contract_version="1.0.0",
        request_id="intervention_req_fixture_01",
        snapshot=snapshot,
        base_forecast_id="forecast_fixture_01",
        intervention=Intervention(
            action_type="split_payment",
            obligation_id=snapshot.obligations[0].obligation_id,
            parameters={
                "first_payment_cents": 90_000,
                "second_payment_cents": 90_000,
                "second_payment_date": (AS_OF + timedelta(days=13)).isoformat(),
            },
        ),
        horizon_days=30,
        scenario_count=8,
    )
