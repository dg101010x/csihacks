"""Shared sub-models embedded in the five core Relief contracts.

Field names are snake_case to mirror the JSON wire format exactly (see
CONTRACTS.md) — this file is the Python twin of ``src/shared.ts``.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


def validate_contract_version(value: str) -> str:
    if not _SEMVER_RE.match(value):
        raise ValueError("contract_version must be a semantic version, e.g. 1.0.0")
    return value


class DataStatus(str, Enum):
    current = "current"
    stale = "stale"
    unavailable = "unavailable"


class ObligationStatus(str, Enum):
    active = "active"
    paused = "paused"
    closed = "closed"


class EvidenceSource(str, Enum):
    provider_structured_policy = "provider_structured_policy"
    provider_published_policy_document = "provider_published_policy_document"
    confirmed_product_contract = "confirmed_product_contract"
    consumer_supplied_contract_information = "consumer_supplied_contract_information"
    simulated_demonstration_policy = "simulated_demonstration_policy"
    unknown = "unknown"


class AccountV1(BaseModel):
    """Mirrors the ``accounts`` table (Section 32.4)."""

    model_config = ConfigDict(extra="forbid")

    account_id: str
    provider: str
    account_type: str
    account_subtype: Optional[str]
    display_name: str
    current_balance_cents: int
    available_balance_cents: Optional[int]
    balance_updated_at: datetime
    data_status: DataStatus
    is_simulated: bool


class ObligationV1(BaseModel):
    """Mirrors the ``obligations`` table (Section 32.6) / obligation model (Section 36)."""

    model_config = ConfigDict(extra="forbid")

    obligation_id: str
    provider_id: Optional[str]
    obligation_type: str
    display_name: str
    principal_balance_cents: Optional[int]
    scheduled_amount_cents: int
    next_due_at: Optional[datetime]
    recurrence_rule: Optional[str]
    essentiality_score: float = Field(ge=0, le=1)
    status: ObligationStatus
    source_confidence: float = Field(ge=0, le=1)
    consumer_confirmed: bool


class ProviderCapabilityV1(BaseModel):
    """Mirrors the ``provider_capabilities`` table (Section 32.7)."""

    model_config = ConfigDict(extra="forbid")

    provider_id: str
    product_type: str
    action_type: str
    eligibility_rule: Optional[str]
    cost_rule: Optional[str]
    timing_rule: Optional[str]
    evidence_source: EvidenceSource
    effective_from: Optional[datetime]
    effective_until: Optional[datetime]
    is_simulated: bool


class ConsumerConstitutionV1(BaseModel):
    """The confirmed, structured consumer rule set (Section 71)."""

    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=0)
    protected_categories: list[str]
    allow_term_extension: bool
    maximum_added_interest_cents: int
    require_confirmation_for_subscriptions: bool


class DailySummaryEntryV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_date: date
    median_ending_balance_cents: int
    lower_ending_balance_cents: int
    upper_ending_balance_cents: int
    reserve_violation_probability: float = Field(ge=0, le=1)


class TrajectoryPointV1(BaseModel):
    """Mirrors the ``forecast_trajectories`` table (Section 32.9)."""

    model_config = ConfigDict(extra="forbid")

    scenario_index: int = Field(ge=0)
    event_date: date
    starting_balance_cents: int
    inflow_cents: int
    outflow_cents: int
    ending_balance_cents: int
    essential_reserve_cents: int


class ReasonFactorV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    factor: str
    weight: float = Field(ge=0, le=1)
    description: str
