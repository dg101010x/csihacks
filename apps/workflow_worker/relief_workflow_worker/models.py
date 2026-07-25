from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class PackageStage(str, Enum):
    """Mirrors the frontend's InterventionActionStage
    (apps/web/src/domain/types.ts) — the staged approval flow an
    intervention package moves through."""

    review = "review"
    confirmed = "confirmed"
    submitted = "submitted"
    pending_provider = "pending_provider"
    accepted = "accepted"
    rejected = "rejected"
    executed = "executed"


class ProviderCaseStatus(str, Enum):
    pending_review = "pending_review"
    approved = "approved"
    rejected = "rejected"
    information_requested = "information_requested"


class PolicyReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str
    passage_id: str
    effective_date: str
    confidence: float = Field(ge=0, le=1)
    is_simulated: bool


class ProviderCaseV1(BaseModel):
    """Plan-Two-internal (Section 85) — python twin of
    packages/test_fixtures/src/types.ts' ProviderCaseV1."""

    model_config = ConfigDict(extra="forbid")

    case_id: str
    provider_id: str
    action_id: str
    status: ProviderCaseStatus
    consumer_impact_summary: str
    provider_impact_summary: str
    policy_reference: Optional[PolicyReference]


class PackageApprovalState(BaseModel):
    """The mutable half of an intervention package's lifecycle — the
    optimizer's InterventionCandidateV1 output is a ranking, immutable once
    computed; this tracks where a specific package_id currently sits in the
    staged approval flow, separate from that ranking."""

    model_config = ConfigDict(extra="forbid")

    package_id: str
    stage: PackageStage
    case_id: Optional[str] = None
    history: list[str] = Field(default_factory=list)
