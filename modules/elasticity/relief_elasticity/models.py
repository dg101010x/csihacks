from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class Reversibility(str, Enum):
    fully_reversible = "fully_reversible"
    partially_reversible = "partially_reversible"
    irreversible = "irreversible"


class ObligationElasticityV1(BaseModel):
    """How much give one obligation has (Section 40) — the input the
    intervention optimizer (modules/interventions) ranks candidate actions
    against. Plan-Two-internal; not part of @relief/contracts."""

    model_config = ConfigDict(extra="forbid")

    obligation_id: str
    obligation_type: str
    delay_tolerance_days: int = Field(ge=0)
    amount_flexibility_ratio: float = Field(ge=0, le=1)
    cost_of_delay_cents_per_day: int = Field(ge=0)
    available_actions: list[str]
    reversibility: Reversibility
    confidence: float = Field(ge=0, le=1)
