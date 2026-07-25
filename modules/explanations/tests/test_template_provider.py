from __future__ import annotations

import json
from pathlib import Path

import pytest
from relief_contracts import HouseholdSnapshotV1
from relief_deterministic_forecast import generate_forecast
from relief_explanations import get_default_explanation_provider
from relief_interventions import generate_intervention_packages
from relief_resilience import compute_resilience_score

BASELINE_PATH = (
    Path(__file__).resolve().parents[3] / "packages" / "test_fixtures" / "fixtures" / "sarah_baseline.json"
)
SHOCK_PATH = (
    Path(__file__).resolve().parents[3] / "packages" / "test_fixtures" / "fixtures" / "sarah_income_shock.json"
)


def load_snapshot(path: Path) -> HouseholdSnapshotV1:
    return HouseholdSnapshotV1(**json.loads(path.read_text())["household_snapshot"])


@pytest.fixture
def provider():
    return get_default_explanation_provider()


def test_healthy_forecast_gets_a_reassuring_headline(provider):
    forecast = generate_forecast(load_snapshot(BASELINE_PATH), horizon_days=14)
    explanation = provider.explain_forecast_risk(forecast)
    assert "no near-term" in explanation.headline.lower()
    assert explanation.supporting_points == []


def test_risky_forecast_cites_a_real_reason_factor(provider):
    forecast = generate_forecast(load_snapshot(SHOCK_PATH), horizon_days=14)
    explanation = provider.explain_forecast_risk(forecast)
    assert "%" in explanation.headline
    if forecast.reason_factors:
        assert explanation.summary == sorted(forecast.reason_factors, key=lambda f: f.weight, reverse=True)[0].description


def test_resilience_explanation_names_strongest_and_weakest(provider):
    snapshot = load_snapshot(SHOCK_PATH)
    forecast = generate_forecast(snapshot, horizon_days=14)
    score = compute_resilience_score(snapshot, forecast)
    explanation = provider.explain_resilience_score(score)
    assert str(round(score.overall)) in explanation.headline
    assert len(explanation.supporting_points) == len(score.components)


def test_intervention_explanation_reuses_ranking_reason(provider):
    snapshot = load_snapshot(SHOCK_PATH)
    packages = generate_intervention_packages(snapshot, horizon_days=14)
    if not packages:
        pytest.skip("no packages generated for this fixture horizon")
    explanation = provider.explain_intervention_package(packages[0])
    assert explanation.summary == packages[0].ranking_reason
    assert explanation.headline == packages[0].label


def test_every_explanation_carries_a_disclosure(provider):
    forecast = generate_forecast(load_snapshot(BASELINE_PATH), horizon_days=14)
    explanation = provider.explain_forecast_risk(forecast)
    assert explanation.disclosure
    assert explanation.generated_by == "template"
