from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from relief_contracts import ForecastProviderName, ForecastResponseV1, HouseholdSnapshotV1
from relief_deterministic_forecast import generate_forecast as generate_deterministic_forecast
from relief_deterministic_forecast import generate_mock_forecast

from .client import ReliefFMClient
from .errors import ModelServiceUnavailableError


def _assemble_relieffm_response(
    snapshot: HouseholdSnapshotV1, inference: dict, *, request_id: str
) -> ForecastResponseV1:
    generated_at = snapshot.generated_at
    return ForecastResponseV1(
        contract_version="1.0.0",
        request_id=request_id,
        forecast_id=f"forecast_{uuid.uuid4().hex[:12]}",
        provider=ForecastProviderName.relieffm,
        provider_version=inference.get("model_version", "unknown"),
        generated_at=generated_at,
        valid_until=generated_at + timedelta(hours=1),
        confidence=inference["confidence"],
        is_stale=False,
        warnings=inference.get("warnings", []),
        daily_summary=inference["daily_summary"],
        trajectories=inference["trajectories"],
        distress_probabilities=inference["distress_probabilities"],
        reason_factors=inference["reason_factors"],
        model_metadata={
            "model_version": inference.get("model_version", "unknown"),
            "calibration_version": inference.get("calibration_version"),
            "inference_latency_ms": inference.get("inference_latency_ms", 0.0),
        },
    )


def generate_forecast(
    snapshot: HouseholdSnapshotV1,
    *,
    horizon_days: int = 30,
    provider: ForecastProviderName = ForecastProviderName.deterministic,
    request_id: Optional[str] = None,
    client: Optional[ReliefFMClient] = None,
) -> ForecastResponseV1:
    """The one function every caller (apps/api, workflow_worker, anything
    else needing a forecast) should call instead of reaching into
    relief_deterministic_forecast or a ReliefFM client directly — this is
    the seam Section 19 describes: swapping which provider produced a
    ForecastResponseV1 never changes the shape a caller receives.

    Does not fall back on ModelServiceUnavailableError itself — the platform
    must work before ReliefFM is connected (the README's core architectural
    rule), but *how* to react to ReliefFM being unreachable (retry, fall
    back to deterministic, surface an error) is a caller decision, not this
    function's to make silently.
    """
    if provider == ForecastProviderName.mock:
        return generate_mock_forecast(snapshot, horizon_days=horizon_days, request_id=request_id)
    if provider == ForecastProviderName.deterministic:
        return generate_deterministic_forecast(snapshot, horizon_days=horizon_days, request_id=request_id)

    # provider == relieffm
    resolved_client = client or ReliefFMClient()
    inference = resolved_client.infer(snapshot, horizon_days=horizon_days)
    return _assemble_relieffm_response(
        snapshot, inference, request_id=request_id or f"req_{uuid.uuid4().hex[:12]}"
    )
