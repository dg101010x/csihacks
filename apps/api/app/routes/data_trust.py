from __future__ import annotations

from fastapi import APIRouter, Depends

from ..dependencies import get_request_id
from ..envelope import envelope
from .models import model_registry
from ..seed import get_data_trust_fixture

router = APIRouter(prefix="/v1/data", tags=["data"])


@router.get("/trust")
def get_data_trust(request_id: str = Depends(get_request_id)):
    trust = get_data_trust_fixture()
    mini = next(model for model in model_registry() if model["id"] == "mini")
    for source in trust:
        source["forecast_provider"] = "deterministic (actions) + ReliefFM Mini (shadow preview)"
        source["relieffm_version"] = mini["version"]
        source["calibration_summary"] = (
            "ReliefFM Mini is connected in shadow mode. Its balance trajectories beat the seasonal baseline, "
            "but its distress estimates remain uncalibrated and cannot drive financial actions."
            if mini["status"] == "available"
            else "ReliefFM Mini is not connected; deterministic forecasting remains fully available."
        )
        source["known_limitations"] = [
            *source["known_limitations"],
            "ReliefFM previews do not drive intervention ranking or financial execution.",
        ]
    return envelope(request_id, trust)
