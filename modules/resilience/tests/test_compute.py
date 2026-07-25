from __future__ import annotations

import json
from pathlib import Path

import pytest
from relief_contracts import HouseholdSnapshotV1
from relief_deterministic_forecast import generate_forecast
from relief_resilience import compute_resilience_score

FIXTURE_PATH = (
    Path(__file__).resolve().parents[3] / "packages" / "test_fixtures" / "fixtures" / "sarah_baseline.json"
)


@pytest.fixture
def sarah_snapshot() -> HouseholdSnapshotV1:
    data = json.loads(FIXTURE_PATH.read_text())["household_snapshot"]
    return HouseholdSnapshotV1(**data)


def test_component_weights_sum_to_one(sarah_snapshot):
    forecast = generate_forecast(sarah_snapshot, horizon_days=14)
    score = compute_resilience_score(sarah_snapshot, forecast)
    assert round(sum(c.weight for c in score.components), 6) == 1.0


def test_healthy_baseline_scores_reasonably_high(sarah_snapshot):
    forecast = generate_forecast(sarah_snapshot, horizon_days=14)
    score = compute_resilience_score(sarah_snapshot, forecast)
    assert score.overall >= 60
    assert score.primary_stabilizing_factor is not None


def test_draining_the_account_lowers_the_score(sarah_snapshot):
    forecast = generate_forecast(sarah_snapshot, horizon_days=14)
    healthy = compute_resilience_score(sarah_snapshot, forecast)

    drained_account = sarah_snapshot.accounts[0].model_copy(update={"current_balance_cents": 10_000})
    drained_snapshot = sarah_snapshot.model_copy(update={"accounts": [drained_account]})
    drained_forecast = generate_forecast(drained_snapshot, horizon_days=14)
    drained = compute_resilience_score(drained_snapshot, drained_forecast)

    assert drained.overall < healthy.overall
    assert drained.primary_weakness is not None


def test_trend_reflects_previous_score(sarah_snapshot):
    forecast = generate_forecast(sarah_snapshot, horizon_days=14)
    improving = compute_resilience_score(sarah_snapshot, forecast, previous_overall=10)
    declining = compute_resilience_score(sarah_snapshot, forecast, previous_overall=99)
    stable = compute_resilience_score(sarah_snapshot, forecast, previous_overall=forecast.confidence * 0 + improving.overall)
    assert improving.trend.value == "improving"
    assert declining.trend.value == "declining"
    assert stable.trend.value == "stable"


def test_no_recurring_income_detected_lowers_confidence(sarah_snapshot):
    forecast = generate_forecast(sarah_snapshot, horizon_days=14)
    no_income_snapshot = sarah_snapshot.model_copy(update={"recent_events": []})
    no_income_forecast = generate_forecast(no_income_snapshot, horizon_days=14)
    with_income = compute_resilience_score(sarah_snapshot, forecast)
    without_income = compute_resilience_score(no_income_snapshot, no_income_forecast)
    income_component = next(c for c in without_income.components if c.key == "income_stability")
    assert income_component.confidence < 0.5
