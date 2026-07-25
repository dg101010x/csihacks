from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from relief_contracts import (
    AccountV1,
    ConsumerConstitutionV1,
    FinancialEventV1,
    HouseholdSnapshotV1,
    ObligationV1,
)
from relief_deterministic_forecast import compute_essential_reserve_cents, generate_forecast, generate_mock_forecast

FIXTURE_PATH = (
    Path(__file__).resolve().parents[3] / "packages" / "test_fixtures" / "fixtures" / "sarah_baseline.json"
)


@pytest.fixture
def sarah_snapshot() -> HouseholdSnapshotV1:
    data = json.loads(FIXTURE_PATH.read_text())["household_snapshot"]
    return HouseholdSnapshotV1(**data)


def test_reserve_reflects_essential_obligations(sarah_snapshot):
    reserve = compute_essential_reserve_cents(sarah_snapshot.obligations)
    # Rent ($1450/mo) + auto loan ($240/mo) prorated to a daily rate * 7 days,
    # well above the flat floor.
    assert reserve > 20_000


def test_generate_forecast_reconciles_every_trajectory_row(sarah_snapshot):
    forecast = generate_forecast(sarah_snapshot, horizon_days=14)
    assert forecast.provider.value == "deterministic"
    assert forecast.model_metadata is None
    for point in forecast.trajectories:
        assert point.starting_balance_cents + point.inflow_cents - point.outflow_cents == point.ending_balance_cents


def test_generate_forecast_starts_from_total_account_balance(sarah_snapshot):
    forecast = generate_forecast(sarah_snapshot, horizon_days=14)
    total_balance = sum(a.current_balance_cents for a in sarah_snapshot.accounts)
    assert forecast.trajectories[0].starting_balance_cents == total_balance


def test_forecast_projects_beyond_explicit_known_future_events(sarah_snapshot):
    explicit_dates = {e.effective_at.date() for e in sarah_snapshot.known_future_events}
    forecast = generate_forecast(sarah_snapshot, horizon_days=60)
    projected_dates = {p.event_date for p in forecast.trajectories}
    # Rent/auto-loan/streaming/paycheck recur monthly — a 60 day horizon must
    # surface a second occurrence beyond the ones the fixture enumerates.
    assert projected_dates - explicit_dates


def test_healthy_baseline_has_no_reason_factors(sarah_snapshot):
    forecast = generate_forecast(sarah_snapshot, horizon_days=14)
    assert forecast.distress_probabilities.essential_reserve_violation < 0.15
    assert forecast.reason_factors == []


def test_confidence_drops_when_data_is_stale(sarah_snapshot):
    baseline = generate_forecast(sarah_snapshot, horizon_days=14)
    stale_account = sarah_snapshot.accounts[0].model_copy(update={"data_status": "stale"})
    stale_snapshot = sarah_snapshot.model_copy(update={"accounts": [stale_account]})
    stale_forecast = generate_forecast(stale_snapshot, horizon_days=14)
    assert stale_forecast.confidence < baseline.confidence
    assert stale_forecast.is_stale is True
    assert any("stale" in w for w in stale_forecast.warnings)


def test_a_shock_that_drains_the_account_raises_reserve_violation_probability(sarah_snapshot):
    shocked_account = sarah_snapshot.accounts[0].model_copy(update={"current_balance_cents": 60_000})
    shocked = sarah_snapshot.model_copy(update={"accounts": [shocked_account]})
    forecast = generate_forecast(shocked, horizon_days=14)
    assert forecast.distress_probabilities.essential_reserve_violation > 0.15
    assert len(forecast.reason_factors) > 0
    assert all(0 <= f.weight <= 1 for f in forecast.reason_factors)


def test_mock_provider_only_uses_explicit_events_with_no_uncertainty(sarah_snapshot):
    forecast = generate_mock_forecast(sarah_snapshot, horizon_days=60)
    assert forecast.provider.value == "mock"
    explicit_dates = {e.effective_at.date() for e in sarah_snapshot.known_future_events}
    assert {p.event_date for p in forecast.trajectories} == explicit_dates
    for entry in forecast.daily_summary:
        assert entry.lower_ending_balance_cents == entry.median_ending_balance_cents == entry.upper_ending_balance_cents
