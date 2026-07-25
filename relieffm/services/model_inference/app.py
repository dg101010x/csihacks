"""Section 7 — the four required endpoints. Dispatches between Nano and
Mini checkpoints automatically based on `checkpoint_meta.json`'s
`model_name` field, so one service binary serves either. Run with:

    RELIEFFM_CHECKPOINT_DIR=runs/mini_v1/checkpoint uvicorn services.model_inference.app:app --port 8080

Section 118's default activation gate is not met for either model (no
shadow deployment, no calibration/robustness/fairness approval), so every
response reports `status: shadow` and this service must never be pointed
to as Plan Two's default provider — only its deterministic fallback
should be default.
"""
from __future__ import annotations

import json
import os
import threading
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from relief_contracts.schemas import ForecastRequestV1, InterventionSimulationRequestV1

from . import inference, inference_mini
from .intervention import InterventionError, apply_intervention

app = FastAPI(title="ReliefFM model_inference", version="0.1.0")

_loaded = None
_loaded_kind: str | None = None  # "nano" | "mini"
_load_lock = threading.Lock()


def get_model():
    global _loaded, _loaded_kind
    if _loaded is not None:
        return _loaded, _loaded_kind
    with _load_lock:
        if _loaded is not None:
            return _loaded, _loaded_kind
        checkpoint_dir = os.environ.get("RELIEFFM_CHECKPOINT_DIR")
        if not checkpoint_dir:
            raise HTTPException(status_code=503, detail="RELIEFFM_CHECKPOINT_DIR not configured")
        meta_path = Path(checkpoint_dir) / "checkpoint_meta.json"
        if not meta_path.exists():
            raise HTTPException(status_code=503, detail=f"no checkpoint_meta.json in {checkpoint_dir}")
        try:
            model_name = json.loads(meta_path.read_text()).get("model_name", "")
            if model_name in ("relieffm_mini", "relieffm_flash"):
                _loaded = inference_mini.LoadedMiniModel(checkpoint_dir)
                _loaded_kind = "mini"
            else:
                _loaded = inference.LoadedModel(checkpoint_dir)
                _loaded_kind = "nano"
        except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
            raise HTTPException(
                status_code=503,
                detail=f"checkpoint failed to load: {type(exc).__name__}",
            ) from exc
    return _loaded, _loaded_kind


@app.get("/model/v1/health")
def health():
    try:
        loaded, kind = get_model()
        return {
            "status": "ok",
            "model_name": loaded.meta["model_name"],
            "model_version": loaded.meta["model_version"],
            "kind": kind,
            "device": str(loaded.device),
            "lifecycle_status": "shadow",
        }
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"status": "unavailable", "detail": e.detail})


@app.get("/model/v1/metadata")
def metadata():
    loaded, _ = get_model()
    return loaded.metadata().model_dump(mode="json")


@app.post("/model/v1/forecast")
def forecast(request: ForecastRequestV1):
    loaded, kind = get_model()
    try:
        if kind == "mini":
            response = inference_mini.run_forecast_mini(
                loaded, snapshot=request.snapshot, horizon_days=request.horizon_days,
                scenario_count=request.scenario_count, request_id=request.request_id,
                forecast_id=f"forecast_{uuid.uuid4().hex[:12]}",
            )
        else:
            response = inference.run_forecast(
                loaded, snapshot=request.snapshot, horizon_days=request.horizon_days,
                scenario_count=request.scenario_count, request_id=request.request_id,
                forecast_id=f"forecast_{uuid.uuid4().hex[:12]}",
            )
    except (inference.ForecastError, inference_mini.ForecastError) as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    return response.model_dump(mode="json")


@app.post("/model/v1/simulate_intervention")
def simulate_intervention(request: InterventionSimulationRequestV1):
    loaded, kind = get_model()
    try:
        if kind == "mini":
            response = inference_mini.run_forecast_mini(
                loaded, snapshot=request.snapshot, horizon_days=request.horizon_days,
                scenario_count=request.scenario_count, request_id=request.request_id,
                forecast_id=f"intervention_{uuid.uuid4().hex[:12]}",
                intervention=request.intervention,
            )
        else:
            modified_snapshot, added_cost_cents = apply_intervention(request.snapshot, request.intervention)
            response = inference.run_forecast(
                loaded, snapshot=modified_snapshot, horizon_days=request.horizon_days,
                scenario_count=request.scenario_count, request_id=request.request_id,
                forecast_id=f"intervention_{uuid.uuid4().hex[:12]}",
                extra_warnings=[
                    "intervention_conditioning_not_modeled: only the deterministic known-event "
                    "component reflects the proposed intervention; the uncertain-component "
                    "forecast is unconditioned (intervention-conditioned forecasting is Mini-scope, "
                    "section 19.2, not implemented by relieffm_nano)",
                    f"added_cost_cents={added_cost_cents}",
                ],
            )
    except (inference.ForecastError, inference_mini.ForecastError) as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    except InterventionError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return response.model_dump(mode="json")
