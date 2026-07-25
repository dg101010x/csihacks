from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from relief_contracts import ForecastProviderName, HouseholdSnapshotV1
from relief_model_gateway import ModelServiceUnavailableError, ReliefFMClient, generate_forecast

BASELINE_PATH = (
    Path(__file__).resolve().parents[3] / "packages" / "test_fixtures" / "fixtures" / "sarah_baseline.json"
)


@pytest.fixture
def snapshot() -> HouseholdSnapshotV1:
    return HouseholdSnapshotV1(**json.loads(BASELINE_PATH.read_text())["household_snapshot"])


def test_default_provider_is_deterministic_and_reconciles(snapshot):
    forecast = generate_forecast(snapshot, horizon_days=14)
    assert forecast.provider.value == "deterministic"
    assert forecast.model_metadata is None


def test_mock_provider_dispatches_to_the_trivial_engine(snapshot):
    forecast = generate_forecast(snapshot, horizon_days=14, provider=ForecastProviderName.mock)
    assert forecast.provider.value == "mock"


def test_relieffm_raises_when_not_configured(snapshot, monkeypatch):
    monkeypatch.delenv("RELIEFFM_INFERENCE_URL", raising=False)
    with pytest.raises(ModelServiceUnavailableError):
        generate_forecast(snapshot, horizon_days=14, provider=ForecastProviderName.relieffm)


def test_relieffm_raises_on_a_failed_call(snapshot):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    client = ReliefFMClient(base_url="https://model-inference.internal", transport=httpx.MockTransport(handler))
    with pytest.raises(ModelServiceUnavailableError):
        generate_forecast(snapshot, horizon_days=14, provider=ForecastProviderName.relieffm, client=client)


def test_relieffm_response_is_assembled_into_a_valid_forecast_once_the_seam_is_live(snapshot):
    """Proves the seam's mapping logic is correct even though
    services/model_inference doesn't exist in this repo yet — once Plan One
    ships it and points RELIEFFM_INFERENCE_URL at it, this is exactly the
    shape the gateway will receive and assemble."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "model_version": "reliefm-0.1.0",
                "calibration_version": "cal-2026-07",
                "inference_latency_ms": 42.5,
                "confidence": 0.93,
                "daily_summary": [
                    {
                        "event_date": "2026-07-27",
                        "median_ending_balance_cents": 80000,
                        "lower_ending_balance_cents": 75000,
                        "upper_ending_balance_cents": 85000,
                        "reserve_violation_probability": 0.05,
                    }
                ],
                "trajectories": [
                    {
                        "scenario_index": 0,
                        "event_date": "2026-07-27",
                        "starting_balance_cents": 248000,
                        "inflow_cents": 0,
                        "outflow_cents": 168000,
                        "ending_balance_cents": 80000,
                        "essential_reserve_cents": 50000,
                    }
                ],
                "distress_probabilities": {
                    "negative_balance": 0.01,
                    "essential_reserve_violation": 0.05,
                    "missed_obligation": 0.01,
                },
                "reason_factors": [],
            },
        )

    client = ReliefFMClient(base_url="https://model-inference.internal", transport=httpx.MockTransport(handler))
    forecast = generate_forecast(snapshot, horizon_days=14, provider=ForecastProviderName.relieffm, client=client)

    assert forecast.provider.value == "relieffm"
    assert forecast.model_metadata is not None
    assert forecast.model_metadata.model_version == "reliefm-0.1.0"
    assert forecast.model_metadata.inference_latency_ms == 42.5
    assert forecast.confidence == 0.93
