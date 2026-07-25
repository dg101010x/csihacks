from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ExecutionMode(str, Enum):
    recommendation_only = "recommendation_only"
    draft_only = "draft_only"
    simulated = "simulated"
    consumer_executable = "consumer_executable"
    provider_executable = "provider_executable"


class ApprovalStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class ProviderApprovalStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    not_required = "not_required"


class Reversibility(str, Enum):
    fully_reversible = "fully_reversible"
    partially_reversible = "partially_reversible"
    irreversible = "irreversible"


class UserEffort(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class InterventionActionV1(BaseModel):
    """Plan-Two-internal (Section 60) — python twin of
    packages/test_fixtures/src/types.ts' InterventionActionV1."""

    model_config = ConfigDict(extra="forbid")

    action_id: str
    action_type: str
    obligation_id: str
    display_name: str
    parameters: dict
    execution_mode: ExecutionMode
    provider_capability_id: Optional[str]
    consumer_status: ApprovalStatus
    provider_status: ProviderApprovalStatus


class RemainingRisk(BaseModel):
    model_config = ConfigDict(extra="forbid")

    negative_balance: bool
    essential_reserve_violation: bool


class InterventionCandidateV1(BaseModel):
    """Plan-Two-internal (Section 61) — python twin of
    packages/test_fixtures/src/types.ts' InterventionCandidateV1."""

    model_config = ConfigDict(extra="forbid")

    package_id: str
    label: str
    description: str
    actions: list[InterventionActionV1]
    added_cost_cents: int
    new_minimum_balance_cents: int
    remaining_risk: RemainingRisk
    required_approvals: list[str]
    user_effort: UserEffort
    provider_acceptance_probability: Optional[float] = Field(default=None, ge=0, le=1)
    reversibility: Reversibility
    constitution_compatible: bool
    confidence: float = Field(ge=0, le=1)
    ranking_reason: str
