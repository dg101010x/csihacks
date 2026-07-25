from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class RuleStatus(str, Enum):
    draft = "draft"
    active = "active"


class ApprovalRequirement(str, Enum):
    none = "none"
    consumer_confirmation = "consumer_confirmation"
    always_ask = "always_ask"


class ConstitutionRuleV1(BaseModel):
    """Section 71's structured interpretation of a consumer's natural-
    language policy statement. Plan-Two-internal; python twin of
    packages/test_fixtures/src/types.ts' ConstitutionRuleV1."""

    model_config = ConfigDict(extra="forbid")

    rule_id: str
    status: RuleStatus
    raw_text: str
    trigger: str
    scope: list[str]
    permitted_actions: list[str]
    prohibited_actions: list[str]
    approval_requirement: ApprovalRequirement
    maximum_monetary_impact_cents: Optional[int]
    expiration: Optional[str]
    priority: int
    exceptions: list[str]
    confidence: float = Field(ge=0, le=1)
    created_at: datetime


class RuleConflict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    with_rule_id: str
    description: str


class ConstitutionSimulationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule: ConstitutionRuleV1
    allowed_package_ids: list[str]
    blocked_package_ids: list[str]
    conflicts: list[RuleConflict]
