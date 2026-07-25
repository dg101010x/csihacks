"""ForecastResponseV1 (Section 12). Owner: Plan One + Plan Two. Version: 1.0.0.

The single response shape returned by every forecast provider (mock,
deterministic, relieffm). Python twin of ``src/forecast_response.ts``.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .shared import DailySummaryEntryV1, ReasonFactorV1, TrajectoryPointV1, validate_contract_version


class ForecastProviderName(str, Enum):
    mock = "mock"
    deterministic = "deterministic"
    relieffm = "relieffm"


class DistressProbabilities(BaseModel):
    model_config = ConfigDict(extra="forbid")

    negative_balance: float = Field(ge=0, le=1)
    essential_reserve_violation: float = Field(ge=0, le=1)
    missed_obligation: float = Field(ge=0, le=1)


class ModelMetadataV1(BaseModel):
    """Populated only when provider == relieffm; deterministic sets this to None."""

    model_config = ConfigDict(extra="forbid")

    model_version: str
    calibration_version: Optional[str]
    inference_latency_ms: float = Field(ge=0)


class ForecastResponseV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: str
    request_id: str
    forecast_id: str
    provider: ForecastProviderName
    provider_version: str
    generated_at: datetime
    valid_until: datetime
    confidence: float = Field(ge=0, le=1)
    is_stale: bool
    warnings: list[str]
    daily_summary: list[DailySummaryEntryV1]
    trajectories: list[TrajectoryPointV1]
    distress_probabilities: DistressProbabilities
    reason_factors: list[ReasonFactorV1]
    model_metadata: Optional[ModelMetadataV1]

    @field_validator("contract_version")
    @classmethod
    def _validate_contract_version(cls, v: str) -> str:
        return validate_contract_version(v)

    @model_validator(mode="after")
    def _model_metadata_only_for_relieffm(self) -> "ForecastResponseV1":
        if self.provider != ForecastProviderName.relieffm and self.model_metadata is not None:
            raise ValueError("model_metadata must be null unless provider is relieffm")
        return self
