from __future__ import annotations

import os

from fastapi import APIRouter, Depends
from relief_contracts import ForecastProviderName
from relief_model_gateway import ModelServiceUnavailableError
from relief_model_gateway import generate_forecast as gateway_generate_forecast
from sqlalchemy.orm import Session

from ..dependencies import get_household_id, get_request_id
from ..db import get_db
from ..envelope import envelope
from ..snapshot import assemble_household_snapshot

router = APIRouter(prefix="/v1/forecasts", tags=["forecasts"])


@router.post("")
def create_forecast(
    session: Session = Depends(get_db),
    household_id: str = Depends(get_household_id),
    request_id: str = Depends(get_request_id),
):
    """The README's core architectural rule: three providers (mock,
    deterministic, relieffm) behind one ForecastResponseV1 shape, selected
    via FORECAST_PROVIDER — no page, table, optimizer, or workflow may know
    which one produced a result. Defaults to deterministic since ReliefFM
    isn't connected in this environment (services/model_inference is Plan
    One's, not built in this repo); if FORECAST_PROVIDER=relieffm is set
    but unreachable, falls back to deterministic explicitly with a warning
    rather than failing the request."""
    requested = ForecastProviderName(os.environ.get("FORECAST_PROVIDER", "deterministic"))
    snapshot = assemble_household_snapshot(session, household_id)
    warnings: list[str] = []

    try:
        forecast = gateway_generate_forecast(snapshot, horizon_days=30, provider=requested)
    except ModelServiceUnavailableError:
        forecast = gateway_generate_forecast(snapshot, horizon_days=30, provider=ForecastProviderName.deterministic)
        warnings.append(f"Requested forecast provider '{requested.value}' was unavailable; used deterministic instead.")

    return envelope(request_id, forecast.model_dump(mode="json"), warnings=warnings + list(forecast.warnings))
