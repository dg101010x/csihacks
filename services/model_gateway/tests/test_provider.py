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
    monkeypatch.delenv("RELIEFFM_MINI_URL", raising=False)
    with pytest.raises(ModelServiceUnavailableError):
        generate_forecast(snapshot, horizon_days=14, provider=ForecastProviderName.relieffm)


def test_relieffm_raises_on_a_failed_call(snapshot):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    client = ReliefFMClient(base_url="https://model-inference.internal", transport=httpx.MockTransport(handler))
    with pytest.raises(ModelServiceUnavailableError):
        generate_forecast(snapshot, horizon_days=14, provider=ForecastProviderName.relieffm, client=client)


def test_relieffm_response_is_assembled_into_a_valid_forecast_once_the_seam_is_live(snapshot):
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/model/v1/metadata":
            return httpx.Response(
                200,
                json={
                    "model_version": "mini-20260725",
                    "calibration_version": "cal-2026-07",
                    "supported_horizons": [60],
                    "maximum_scenarios": 8,
                },
            )
        assert request.url.path == "/model/v1/forecast"
        return httpx.Response(
            200,
            json={
                "provider_version": "relieffm_mini_mini-20260725",
                "confidence": 0.93,
                "daily_summary": [
                    {
                        "date": "2026-07-26T16:00:00Z",
                        "balance_p10_cents": 75000,
                        "balance_p50_cents": 80000,
                        "balance_p90_cents": 85000,
                        "inflow_p50_cents": 0,
                        "outflow_p50_cents": 168000,
                    }
                ],
                "trajectories": [
                    {
                        "scenario_id": 0,
                        "daily_balances_cents": [80000],
                        "accounting_valid": True,
                    }
                ],
                "distress_probabilities": {
                    "negative_balance": 0.01,
                    "essential_reserve_violation": 0.05,
                    "missed_obligation": 0.01,
                },
                "reason_factors": [{"name": "liquidity", "contribution": 0.7}],
                "warnings": [],
                "model_metadata": {
                    "model_version": "mini-20260725",
                    "calibration_version": "cal-2026-07",
                },
            },
        )

    client = ReliefFMClient(base_url="https://model-inference.internal", transport=httpx.MockTransport(handler))
    forecast = generate_forecast(snapshot, horizon_days=1, provider=ForecastProviderName.relieffm, client=client)

    assert forecast.provider.value == "relieffm"
    assert forecast.model_metadata is not None
    assert forecast.model_metadata.model_version == "relieffm_mini_mini-20260725"
    assert forecast.model_metadata.inference_latency_ms >= 0
    assert forecast.confidence == 0.93
    assert forecast.trajectories[0].starting_balance_cents == 248000
    assert forecast.trajectories[0].ending_balance_cents == 80000
    assert forecast.trajectories[0].outflow_cents == 168000
    assert forecast.reason_factors[0].factor == "liquidity"

    payload = json.loads(requests[-1].content)
    assert payload["horizon_days"] == 60
    assert payload["scenario_count"] == 8
    assert payload["snapshot"]["household_state"]["total_liquid_balance_cents"] == 248000
    assert payload["snapshot"]["obligations"][1]["obligation_type"] == "auto_loan"
    assert payload["snapshot"]["known_future_events"][0]["event_type"] == "auto_loan_payment"


def test_model_status_reports_connected_mini(snapshot):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/model/v1/health"
        return httpx.Response(
            200,
            json={
                "status": "ok",
                "model_version": "mini-20260725",
                "lifecycle_status": "shadow",
            },
        )

    client = ReliefFMClient(base_url="https://model-inference.internal", transport=httpx.MockTransport(handler))
    assert client.status() == {
        "id": "mini",
        "name": "ReliefFM Mini",
        "status": "available",
        "selectable": True,
        "lifecycle": "shadow",
        "version": "mini-20260725",
    }
