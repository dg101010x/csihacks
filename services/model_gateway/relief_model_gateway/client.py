from __future__ import annotations

import os
from typing import Optional

import httpx
from relief_contracts import HouseholdSnapshotV1

from .errors import ModelServiceUnavailableError


class ReliefFMClient:
    """The Plan-Two side of the ReliefFM boundary. Calls
    services/model_inference's `/v1/infer` — Plan One's side, which does not
    exist in this repository yet (ml/ and services/model_inference are
    outside Plan Two's ownership per docs/architecture/relief_plan_two.md).

    Expected response shape from `/v1/infer` (the interface Plan One's
    service should implement — this is the contract, not an assumption
    about code that already exists):
        {
          "trajectories": [TrajectoryPointV1, ...],
          "daily_summary": [DailySummaryEntryV1, ...],
          "distress_probabilities": {"negative_balance": float, "essential_reserve_violation": float, "missed_obligation": float},
          "reason_factors": [ReasonFactorV1, ...],
          "confidence": float,
          "model_version": str,
          "calibration_version": str | null,
          "inference_latency_ms": float
        }
    Only the model-specific fields — everything ForecastResponseV1 also
    needs (request_id, forecast_id, provider, timestamps) is assembled by
    provider.py, the same as it is for the deterministic path.
    """

    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        timeout: float = 10.0,
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        self.base_url = base_url if base_url is not None else os.environ.get("RELIEFFM_INFERENCE_URL")
        self._timeout = timeout
        self._transport = transport

    def infer(self, snapshot: HouseholdSnapshotV1, *, horizon_days: int) -> dict:
        if not self.base_url:
            raise ModelServiceUnavailableError(
                "RELIEFFM_INFERENCE_URL is not configured — ReliefFM is not connected in this environment."
            )
        try:
            with httpx.Client(base_url=self.base_url, transport=self._transport, timeout=self._timeout) as client:
                response = client.post(
                    "/v1/infer",
                    json={"household_snapshot": snapshot.model_dump(mode="json"), "horizon_days": horizon_days},
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as exc:
            raise ModelServiceUnavailableError(f"ReliefFM inference call failed: {exc}") from exc
