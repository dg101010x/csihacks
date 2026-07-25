from __future__ import annotations

import json
from dataclasses import asdict

import pytest
from httpx import ASGITransport, AsyncClient
from safetensors.torch import save_file

from ml.relieffm.config import MiniConfig
from ml.relieffm.mini.model import ReliefFMMini
from relief_contracts.fixtures import (
    minimal_forecast_request,
    minimal_intervention_request,
)
from services.model_inference import app as app_module


def _tiny_mini_checkpoint(tmp_path):
    config = MiniConfig(
        context_encoder_layers=1,
        historical_encoder_layers=1,
        known_future_encoder_layers=1,
        decoder_layers=1,
        hidden_dimension=32,
        attention_heads=4,
        feedforward_dimension=64,
        context_events=32,
        forecast_horizon_days=7,
        scenario_count=2,
        max_event_slots=4,
        latent_dim=8,
        max_accounts=2,
        max_obligations=4,
        max_known_future_events=8,
        distress_horizons=(7,),
        dropout=0.0,
    )
    checkpoint_dir = tmp_path / "checkpoint"
    checkpoint_dir.mkdir()
    model = ReliefFMMini(config)
    save_file(model.state_dict(), str(checkpoint_dir / "model.safetensors"))
    metadata = {
        "model_name": "relieffm_mini",
        "model_version": "0.1.0-test",
        "dataset_version": "relief_data_test",
        "calibration_version": "calibration_uncalibrated_0.0.0",
        "config": asdict(config),
    }
    (checkpoint_dir / "checkpoint_meta.json").write_text(json.dumps(metadata))
    return checkpoint_dir


def _reset_loaded_model():
    app_module._loaded = None
    app_module._loaded_kind = None


@pytest.mark.anyio
async def test_health_reports_unavailable_without_checkpoint(monkeypatch):
    monkeypatch.delenv("RELIEFFM_CHECKPOINT_DIR", raising=False)
    _reset_loaded_model()

    async with AsyncClient(
        transport=ASGITransport(app=app_module.app), base_url="http://test"
    ) as client:
        response = await client.get("/model/v1/health")

    assert response.status_code == 503
    assert response.json()["status"] == "unavailable"


@pytest.mark.anyio
async def test_mini_checkpoint_serves_forecast_and_intervention(
    tmp_path, monkeypatch
):
    checkpoint_dir = _tiny_mini_checkpoint(tmp_path)
    monkeypatch.setenv("RELIEFFM_CHECKPOINT_DIR", str(checkpoint_dir))
    monkeypatch.setenv("RELIEFFM_DEVICE", "cpu")
    _reset_loaded_model()
    async with AsyncClient(
        transport=ASGITransport(app=app_module.app), base_url="http://test"
    ) as client:
        health = await client.get("/model/v1/health")
        assert health.status_code == 200
        assert health.json() == {
            "status": "ok",
            "model_name": "relieffm_mini",
            "model_version": "0.1.0-test",
            "kind": "mini",
            "device": "cpu",
            "lifecycle_status": "shadow",
        }

        metadata = await client.get("/model/v1/metadata")
        assert metadata.status_code == 200
        assert metadata.json()["supported_horizons"] == [7]
        assert metadata.json()["maximum_scenarios"] == 2
        assert metadata.json()["status"] == "shadow"

        forecast_request = minimal_forecast_request().model_copy(
            update={"horizon_days": 7, "scenario_count": 2}
        )
        forecast = await client.post(
            "/model/v1/forecast",
            json=forecast_request.model_dump(mode="json"),
        )
        assert forecast.status_code == 200
        forecast_body = forecast.json()
        assert forecast_body["request_id"] == forecast_request.request_id
        assert len(forecast_body["daily_summary"]) == 7
        assert len(forecast_body["trajectories"]) == 2
        assert forecast_body["model_metadata"]["status"] == "shadow"

        risk_only_request = forecast_request.model_copy(update={"scenario_count": 0})
        risk_only = await client.post(
            "/model/v1/forecast",
            json=risk_only_request.model_dump(mode="json"),
        )
        assert risk_only.status_code == 200
        assert risk_only.json()["trajectories"] == []

        intervention_request = minimal_intervention_request().model_copy(
            update={"horizon_days": 7, "scenario_count": 2}
        )
        intervention = await client.post(
            "/model/v1/simulate_intervention",
            json=intervention_request.model_dump(mode="json"),
        )
        assert intervention.status_code == 200
        intervention_body = intervention.json()
        assert len(intervention_body["daily_summary"]) == 7
        assert len(intervention_body["trajectories"]) == 2
        assert any(
            warning.startswith("intervention_conditioned:")
            for warning in intervention_body["warnings"]
        )

        bad_intervention = intervention_request.model_copy(
            update={
                "intervention": intervention_request.intervention.model_copy(
                    update={"obligation_id": "obl_missing"}
                )
            }
        )
        bad_response = await client.post(
            "/model/v1/simulate_intervention",
            json=bad_intervention.model_dump(mode="json"),
        )
        assert bad_response.status_code == 422
        assert "unknown intervention obligation_id" in bad_response.json()["detail"]
