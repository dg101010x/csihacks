"""Shared dataclasses for ReliefSim (AGENTS_FM.md section 35)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from relief_contracts.schemas import AccountState, HistoricalEvent, KnownFutureEvent, Obligation


@dataclass
class HouseholdParams:
    """Section 36 — independent per-household parameters. No demographic personas."""

    household_id: str
    num_accounts: int
    income_amount_cents: int
    income_frequency: str
    income_reliability: float  # 0..1, probability a given paycheck arrives on time/full
    income_volatility: float  # coefficient of variation on amount
    fixed_expense_ratio: float  # share of income committed to fixed expenses
    essential_spending_level: float  # cents/day baseline
    discretionary_spending_level: float  # cents/day baseline
    spending_volatility: float
    reserve_level_cents: int
    debt_burden: float  # 0..1, share of income going to debt service
    obligation_count: int
    credit_utilization: float  # 0..1
    shock_frequency: float  # expected shocks per year
    shock_severity: float  # 0..1 multiplier
    recovery_duration_days: int


@dataclass
class SimEvent:
    """Internal event representation before being split into historical/known-future/target."""

    event_id: str
    event_type: str
    event_status: str
    amount_cents: int
    direction: str
    account_id: str
    merchant_category: str
    recurrence_state: str
    source_type: str
    occurrence_time: datetime
    effective_time: datetime
    known: bool  # True if Plan Two would treat this as an authoritative known-future event
    known_source: str | None = None
    obligation_id: str | None = None
    transaction_confidence: float = 1.0


@dataclass
class HouseholdRecord:
    """Full simulator output for one household: history + exact future ground truth."""

    params: HouseholdParams
    as_of: datetime
    history_start: datetime
    horizon_end: datetime
    accounts: list[AccountState]
    obligations: list[Obligation]
    events: list[SimEvent] = field(default_factory=list)  # spans [history_start, horizon_end]
    account_starting_balances_cents: dict[str, int] = field(default_factory=dict)  # balance at history_start

    def historical_events(self) -> list[SimEvent]:
        return [e for e in self.events if e.occurrence_time <= self.as_of]

    def future_events(self) -> list[SimEvent]:
        return [e for e in self.events if e.occurrence_time > self.as_of]

    def known_future_events(self) -> list[SimEvent]:
        return [e for e in self.future_events() if e.known]

    def uncertain_future_events(self) -> list[SimEvent]:
        """Prediction targets: future events Plan Two does NOT treat as authoritative."""
        return [e for e in self.future_events() if not e.known]
