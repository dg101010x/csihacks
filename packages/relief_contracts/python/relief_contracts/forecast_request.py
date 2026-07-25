"""ForecastRequestV1 (Section 11). Owner: Plan Two. Version: 1.0.0.

Python twin of ``src/forecast_request.ts``.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .household_snapshot import HouseholdSnapshotV1
from .shared import validate_contract_version


class RequestedForecastOutput(str, Enum):
    daily_balance_trajectories = "daily_balance_trajectories"
    distress_probabilities = "distress_probabilities"
    income_distribution = "income_distribution"
    variable_spending_distribution = "variable_spending_distribution"


class ForecastRequestV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: str
    request_id: str
    snapshot: HouseholdSnapshotV1
    horizon_days: int = Field(gt=0)
    scenario_count: int = Field(gt=0)
    requested_outputs: list[RequestedForecastOutput]

    @field_validator("contract_version")
    @classmethod
    def _validate_contract_version(cls, v: str) -> str:
        return validate_contract_version(v)
