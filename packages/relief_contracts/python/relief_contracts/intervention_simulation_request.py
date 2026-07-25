"""InterventionSimulationRequestV1 (Section 13). Owner: Plan Two. Version: 1.0.0.

Python twin of ``src/intervention_simulation_request.ts``.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .shared import validate_contract_version


class InterventionActionInputV1(BaseModel):
    """``parameters`` is intentionally open — each action_type (Section 56)
    defines its own shape, validated by the interventions module."""

    model_config = ConfigDict(extra="forbid")

    action_type: str
    obligation_id: str
    parameters: dict


class InterventionSimulationRequestV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: str
    simulation_id: str
    base_forecast_id: str
    household_snapshot_id: str
    interventions: list[InterventionActionInputV1] = Field(min_length=1)

    @field_validator("contract_version")
    @classmethod
    def _validate_contract_version(cls, v: str) -> str:
        return validate_contract_version(v)
