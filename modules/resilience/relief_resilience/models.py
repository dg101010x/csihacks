from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from relief_contracts.shared import DataStatus


class Trend(str, Enum):
    improving = "improving"
    stable = "stable"
    declining = "declining"


class ResilienceComponentV1(BaseModel):
    """Plan-Two-internal shape (Section 22) — not part of @relief/contracts,
    which covers only the Plan One/Two forecasting boundary. Python twin of
    packages/test_fixtures/src/types.ts' ResilienceComponentV1."""

    model_config = ConfigDict(extra="forbid")

    key: str
    label: str
    weight: float = Field(ge=0, le=1)
    score: float = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)


class ResilienceScoreV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str
    overall: float = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    trend: Trend
    components: list[ResilienceComponentV1]
    primary_weakness: Optional[str]
    primary_stabilizing_factor: Optional[str]
    data_freshness: DataStatus
    disclosure: str
