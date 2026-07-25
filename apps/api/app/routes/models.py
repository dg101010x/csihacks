from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from relief_contracts import ForecastProviderName
from relief_model_gateway import ModelServiceUnavailableError, ReliefFMClient
from relief_model_gateway import generate_forecast as gateway_generate_forecast
from sqlalchemy.orm import Session

from ..db import get_db
from ..dependencies import get_household_id, get_request_id
from ..envelope import envelope
from ..snapshot import assemble_household_snapshot

router = APIRouter(prefix="/v1/models", tags=["models"])


def model_registry() -> list[dict]:
    return [
        {
            "id": "deterministic",
            "name": "Deterministic safety forecast",
            "status": "active",
            "selectable": True,
            "lifecycle": "active",
            "version": "1.0.0",
        },
        ReliefFMClient(model="mini", timeout=2.0).status(),
        ReliefFMClient(model="flash", timeout=2.0).status(),
    ]


@router.get("")
def list_models(request_id: str = Depends(get_request_id)):
    return envelope(request_id, model_registry())


@router.post("/preview")
def preview_model(
    model: Literal["mini", "flash"] = Query(...),
    session: Session = Depends(get_db),
    household_id: str = Depends(get_household_id),
    request_id: str = Depends(get_request_id),
):
    """Run a customer-visible ReliefFM preview without changing the
    deterministic forecast used by interventions or workflow execution."""
    snapshot = assemble_household_snapshot(session, household_id)
    try:
        forecast = gateway_generate_forecast(
            snapshot,
            horizon_days=30,
            provider=ForecastProviderName.relieffm,
            request_id=request_id,
            client=ReliefFMClient(model=model),
        )
    except ModelServiceUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return envelope(
        request_id,
        forecast.model_dump(mode="json"),
        warnings=[
            f"ReliefFM {model.title()} is in shadow mode; deterministic forecasts continue to drive financial actions."
        ],
    )
