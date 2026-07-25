"""Shared Model Contracts (AGENTS_FM.md Part One, sections 7-11).

Plan Two owns the canonical copy of this package. This copy is what Plan
One (ReliefFM) builds and tests against. Keep both in sync by contract
version, not by import.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SUPPORTED_CONTRACT_VERSIONS = {"1.0.0"}
SUPPORTED_CURRENCIES = {"USD"}


class ContractError(ValueError):
    """Raised when a request/response violates section 11's reject list."""


# --------------------------------------------------------------------------
# Enums (section 12 token classes)
# --------------------------------------------------------------------------

class EventType(str, Enum):
    PAYCHECK = "paycheck"
    RENT_PAYMENT = "rent_payment"
    MORTGAGE_PAYMENT = "mortgage_payment"
    AUTO_LOAN_PAYMENT = "auto_loan_payment"
    PERSONAL_LOAN_PAYMENT = "personal_loan_payment"
    CREDIT_CARD_PAYMENT = "credit_card_payment"
    INSURANCE_PREMIUM = "insurance_premium"
    UTILITY_BILL = "utility_bill"
    SUBSCRIPTION = "subscription"
    BNPL_PAYMENT = "bnpl_payment"
    MEDICAL_PAYMENT = "medical_payment"
    TRANSFER = "transfer"
    FEE = "fee"
    REFUND = "refund"
    PURCHASE = "purchase"
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    SHOCK_EXPENSE = "shock_expense"
    OTHER = "other"


class EventStatus(str, Enum):
    POSTED = "posted"
    PENDING = "pending"
    SCHEDULED = "scheduled"
    CANCELLED = "cancelled"
    FAILED = "failed"


class Direction(str, Enum):
    INFLOW = "inflow"
    OUTFLOW = "outflow"


class RecurrenceState(str, Enum):
    NONE = "none"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    SEMIMONTHLY = "semimonthly"
    MONTHLY = "monthly"
    IRREGULAR = "irregular"


class SourceType(str, Enum):
    BANK_FEED = "bank_feed"
    CARD_FEED = "card_feed"
    MANUAL = "manual"
    SIMULATED = "simulated"
    PROVIDER_CONFIRMED = "provider_confirmed"


class AccountType(str, Enum):
    CHECKING = "checking"
    SAVINGS = "savings"
    CREDIT_CARD = "credit_card"
    LOAN = "loan"
    BROKERAGE = "brokerage"


class ObligationType(str, Enum):
    RENT = "rent"
    MORTGAGE = "mortgage"
    AUTO_LOAN = "auto_loan"
    PERSONAL_LOAN = "personal_loan"
    CREDIT_CARD_MINIMUM = "credit_card_minimum"
    INSURANCE_PREMIUM = "insurance_premium"
    UTILITY = "utility"
    SUBSCRIPTION = "subscription"
    BNPL = "bnpl"
    MEDICAL_PAYMENT_PLAN = "medical_payment_plan"


class EssentialityCategory(str, Enum):
    ESSENTIAL = "essential"
    DISCRETIONARY = "discretionary"


class PaymentStatus(str, Enum):
    CURRENT = "current"
    LATE = "late"
    MISSED = "missed"
    IN_HARDSHIP_PROGRAM = "in_hardship_program"


class KnownFutureEventSource(str, Enum):
    CONFIRMED_PAYCHECK = "confirmed_paycheck"
    SCHEDULED_LOAN_PAYMENT = "scheduled_loan_payment"
    CONFIRMED_RENT_PAYMENT = "confirmed_rent_payment"
    CONFIRMED_INSURANCE_PREMIUM = "confirmed_insurance_premium"
    APPROVED_INTERVENTION_EVENT = "approved_intervention_event"


class InterventionActionType(str, Enum):
    SPLIT_PAYMENT = "split_payment"
    DELAY_PAYMENT = "delay_payment"
    WAIVE_FEE = "waive_fee"
    PAUSE_SUBSCRIPTION = "pause_subscription"
    HARDSHIP_PROGRAM = "hardship_program"
    REDUCE_PAYMENT = "reduce_payment"
    REFINANCE = "refinance"


SUPPORTED_INTERVENTION_TYPES = {t.value for t in InterventionActionType}


class ModelLifecycleState(str, Enum):
    EXPERIMENTAL = "experimental"
    CANDIDATE = "candidate"
    SHADOW = "shadow"
    LIMITED = "limited"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


# --------------------------------------------------------------------------
# Token-class records (section 12)
# --------------------------------------------------------------------------

class HouseholdState(BaseModel):
    """12.1 Household state token."""

    model_config = ConfigDict(extra="forbid")

    total_liquid_balance_cents: int
    available_balance_cents: int
    num_accounts: int = Field(ge=0)
    num_obligations: int = Field(ge=0)
    essential_reserve_cents: int = Field(ge=0)
    data_freshness_hours: float = Field(ge=0)
    snapshot_completeness: float = Field(ge=0.0, le=1.0)


class AccountState(BaseModel):
    """12.2 Account state token."""

    model_config = ConfigDict(extra="forbid")

    account_id: str
    account_type: AccountType
    account_subtype: str = ""
    current_balance_cents: int
    available_balance_cents: int
    credit_limit_cents: Optional[int] = None
    data_freshness_hours: float = Field(ge=0)
    institution_ref: Optional[str] = None  # dropped during training per section 12.2


class HistoricalEvent(BaseModel):
    """12.3 Observed financial event token."""

    model_config = ConfigDict(extra="forbid")

    event_id: str
    event_type: EventType
    event_status: EventStatus
    amount_cents: int
    direction: Direction
    account_id: str
    merchant_category: str = "unknown"
    recurrence_state: RecurrenceState = RecurrenceState.NONE
    transaction_confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source_type: SourceType = SourceType.SIMULATED
    occurrence_time: datetime
    effective_time: datetime


class Obligation(BaseModel):
    """12.4 Obligation token. Not a prediction target — a constraint."""

    model_config = ConfigDict(extra="forbid")

    obligation_id: str
    obligation_type: ObligationType
    scheduled_amount_cents: int = Field(gt=0)
    due_date: datetime
    recurrence: RecurrenceState
    remaining_principal_cents: Optional[int] = None
    essentiality_category: EssentialityCategory
    payment_status: PaymentStatus = PaymentStatus.CURRENT
    provider_capability_known: bool = False
    account_id: str


class KnownFutureEvent(BaseModel):
    """12.5 Known future event token. Constraint, not a prediction target."""

    model_config = ConfigDict(extra="forbid")

    event_id: str
    event_type: EventType
    amount_cents: int
    direction: Direction
    account_id: str
    effective_time: datetime
    source: KnownFutureEventSource
    obligation_id: Optional[str] = None


class InterventionToken(BaseModel):
    """12.6 Intervention token."""

    model_config = ConfigDict(extra="forbid")

    action_type: InterventionActionType
    obligation_id: str
    original_amount_cents: Optional[int] = None
    modified_amount_cents: Optional[int] = None
    original_date: Optional[datetime] = None
    modified_date: Optional[datetime] = None
    added_cost_cents: int = 0
    duration_days: Optional[int] = None
    execution_assumption: str = "approved_and_executed_exactly_as_described"


# --------------------------------------------------------------------------
# HouseholdSnapshotV1 — constructed and validated by Plan Two
# --------------------------------------------------------------------------

class HouseholdSnapshotV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    household_id: str
    currency: str
    as_of: datetime
    household_state: HouseholdState
    accounts: list[AccountState] = Field(default_factory=list)
    obligations: list[Obligation] = Field(default_factory=list)
    historical_events: list[HistoricalEvent] = Field(default_factory=list)
    known_future_events: list[KnownFutureEvent] = Field(default_factory=list)

    @field_validator("household_id")
    @classmethod
    def _household_id_present(cls, v: str) -> str:
        if not v or not v.strip():
            raise ContractError("missing household identifier")
        return v

    @field_validator("currency")
    @classmethod
    def _currency_supported(cls, v: str) -> str:
        if v not in SUPPORTED_CURRENCIES:
            raise ContractError(f"unsupported currency: {v}")
        return v

    @model_validator(mode="after")
    def _balances_and_timestamps(self) -> "HouseholdSnapshotV1":
        if self.household_state.total_liquid_balance_cents < -10_000_000_00:
            raise ContractError("invalid balance: implausibly negative")
        for acct in self.accounts:
            if acct.account_type != AccountType.CREDIT_CARD and acct.current_balance_cents < -10_000_000_00:
                raise ContractError(f"invalid balance on account {acct.account_id}")
        for ev in self.historical_events:
            if ev.effective_time < ev.occurrence_time - _MAX_CLOCK_SKEW:
                raise ContractError(f"impossible timestamp on event {ev.event_id}")
            if ev.occurrence_time > self.as_of:
                raise ContractError(f"future-dated historical event {ev.event_id}")
        for obl in self.obligations:
            if obl.scheduled_amount_cents <= 0:
                raise ContractError(f"malformed obligation {obl.obligation_id}: non-positive amount")
        return self


from datetime import timedelta  # noqa: E402

_MAX_CLOCK_SKEW = timedelta(days=1)


# --------------------------------------------------------------------------
# Section 8-9: Forecast request/response
# --------------------------------------------------------------------------

REQUESTED_OUTPUTS = {
    "daily_balance_trajectories",
    "distress_probabilities",
    "income_distribution",
    "variable_spending_distribution",
    "household_embedding",
}


class ForecastRequestV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: str
    request_id: str
    snapshot: HouseholdSnapshotV1
    horizon_days: int = Field(gt=0, le=180)
    scenario_count: int = Field(ge=0, le=256)
    requested_outputs: list[str] = Field(default_factory=list)

    @field_validator("contract_version")
    @classmethod
    def _known_contract_version(cls, v: str) -> str:
        if v not in SUPPORTED_CONTRACT_VERSIONS:
            raise ContractError(f"unknown contract version: {v}")
        return v

    @field_validator("scenario_count")
    @classmethod
    def _nonnegative_scenarios(cls, v: int) -> int:
        if v < 0:
            raise ContractError("negative scenario count")
        return v

    @field_validator("requested_outputs")
    @classmethod
    def _known_outputs(cls, v: list[str]) -> list[str]:
        unknown = set(v) - REQUESTED_OUTPUTS
        if unknown:
            raise ContractError(f"unsupported requested_outputs: {unknown}")
        return v


class DailySummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: datetime
    balance_p10_cents: int
    balance_p50_cents: int
    balance_p90_cents: int
    inflow_p50_cents: int
    outflow_p50_cents: int


class ScenarioTrajectory(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_id: int
    daily_balances_cents: list[int]
    accounting_valid: bool = True


class DistressProbabilities(BaseModel):
    model_config = ConfigDict(extra="forbid")

    negative_balance: float = Field(ge=0.0, le=1.0)
    essential_reserve_violation: float = Field(ge=0.0, le=1.0)
    missed_obligation: float = Field(ge=0.0, le=1.0)


class ReasonFactor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    contribution: float = Field(ge=0.0, le=1.0)


class ModelMetadataV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_family: str = "relieffm"
    model_name: str
    model_version: str
    contract_versions: list[str] = Field(default_factory=lambda: sorted(SUPPORTED_CONTRACT_VERSIONS))
    training_data_version: str
    calibration_version: str
    supported_horizons: list[int] = Field(default_factory=lambda: [7, 14, 30])
    maximum_scenarios: int = 32
    status: ModelLifecycleState = ModelLifecycleState.EXPERIMENTAL
    intended_use: str = "household cash flow trajectory forecasting"
    prohibited_use: list[str] = Field(
        default_factory=lambda: [
            "credit approval",
            "financial execution",
            "autonomous contract modification",
        ]
    )
    # Kept here for response embedding (section 9's nested model_metadata is a subset)
    model_size: str = "nano"


class ForecastResponseV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: str
    request_id: str
    forecast_id: str
    provider: str = "relieffm"
    provider_version: str
    generated_at: datetime
    valid_until: datetime
    confidence: float = Field(ge=0.0, le=1.0)
    is_stale: bool = False
    warnings: list[str] = Field(default_factory=list)
    daily_summary: list[DailySummary] = Field(default_factory=list)
    trajectories: list[ScenarioTrajectory] = Field(default_factory=list)
    distress_probabilities: DistressProbabilities
    reason_factors: list[ReasonFactor] = Field(default_factory=list)
    model_metadata: ModelMetadataV1


# --------------------------------------------------------------------------
# Section 10: Intervention simulation request
# --------------------------------------------------------------------------

class Intervention(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_type: str
    obligation_id: str
    parameters: dict = Field(default_factory=dict)

    @field_validator("action_type")
    @classmethod
    def _known_action_type(cls, v: str) -> str:
        if v not in SUPPORTED_INTERVENTION_TYPES:
            raise ContractError(f"unsupported intervention type: {v}")
        return v


class InterventionSimulationRequestV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: str
    request_id: str
    snapshot: HouseholdSnapshotV1
    base_forecast_id: Optional[str] = None
    intervention: Intervention
    horizon_days: int = Field(gt=0, le=180)
    scenario_count: int = Field(ge=0, le=256)

    @field_validator("contract_version")
    @classmethod
    def _known_contract_version(cls, v: str) -> str:
        if v not in SUPPORTED_CONTRACT_VERSIONS:
            raise ContractError(f"unknown contract version: {v}")
        return v
