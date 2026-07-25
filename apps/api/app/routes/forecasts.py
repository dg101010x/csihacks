from __future__ import annotations

from fastapi import APIRouter, Depends
from relief_deterministic_forecast import generate_forecast
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
    """Section 11: the deterministic provider today. ReliefFM
    (services/model_gateway) is a drop-in replacement behind the same
    ForecastResponseV1 shape once Plan One ships it — this route doesn't
    change, only which function it calls."""
    snapshot = assemble_household_snapshot(session, household_id)
    forecast = generate_forecast(snapshot, horizon_days=30)
    return envelope(request_id, forecast.model_dump(mode="json"), warnings=list(forecast.warnings))
