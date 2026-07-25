"""Section 39 — obligation models.

Generates the household's recurring contractual obligations and their
payment event stream. Every future occurrence of an obligation payment is
a *known* future event (section 12.5) — Plan Two treats obligations as
authoritative, not as something ReliefFM predicts.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np

from relief_contracts.schemas import EssentialityCategory, ObligationType, Obligation, PaymentStatus

from . import providers
from .households import _PAY_PERIOD_DAYS
from .types import HouseholdParams, SimEvent

_RECURRENCE_DAYS = {
    "monthly": 30,
    "biweekly": 14,
    "weekly": 7,
}

_ESSENTIAL_TYPES = {
    ObligationType.RENT,
    ObligationType.MORTGAGE,
    ObligationType.UTILITY,
    ObligationType.INSURANCE_PREMIUM,
}


def generate_obligations(
    params: HouseholdParams,
    roles: dict[str, str],
    rng: np.random.Generator,
    as_of: datetime,
) -> list[Obligation]:
    checking_id = roles["checking"]
    obligations: list[Obligation] = []

    # income_amount_cents is a per-*pay-period* figure (section 37's several
    # frequencies), not monthly -- normalize before sizing a monthly
    # obligation, or weekly/biweekly earners get implausibly cheap rent and
    # monthly earners get implausibly expensive rent (section 43 realism
    # check caught ~60% of households going distressed within a week).
    monthly_income_cents = params.income_amount_cents / _PAY_PERIOD_DAYS[params.income_frequency] * 30.0
    housing_type = ObligationType.MORTGAGE if rng.random() < 0.35 else ObligationType.RENT
    housing_amount = int(monthly_income_cents * params.fixed_expense_ratio * 0.6)
    obligations.append(
        _make_obligation(
            params, f"{params.household_id}_obl_housing", housing_type, max(housing_amount, 30_000),
            _next_due(as_of, rng, 30), "monthly", checking_id, rng,
        )
    )

    obligations.append(
        _make_obligation(
            params, f"{params.household_id}_obl_utility", ObligationType.UTILITY,
            int(np.clip(rng.lognormal(4.8, 0.4), 3_000, 40_000)),
            _next_due(as_of, rng, 30), "monthly", checking_id, rng,
        )
    )

    if "credit_card" in roles:
        obligations.append(
            _make_obligation(
                params, f"{params.household_id}_obl_cc_min", ObligationType.CREDIT_CARD_MINIMUM,
                int(np.clip(rng.lognormal(4.5, 0.5), 2_500, 60_000)),
                _next_due(as_of, rng, 30), "monthly", checking_id, rng,
                remaining_principal_cents=None,
            )
        )

    if "loan" in roles:
        obligations.append(
            _make_obligation(
                params, f"{params.household_id}_obl_auto_loan", ObligationType.AUTO_LOAN,
                int(np.clip(rng.lognormal(5.9, 0.35), 15_000, 90_000)),
                _next_due(as_of, rng, 30), "monthly", checking_id, rng,
                remaining_principal_cents=abs(int(rng.uniform(200_000, 3_000_000))),
            )
        )

    if rng.random() < 0.5:
        obligations.append(
            _make_obligation(
                params, f"{params.household_id}_obl_insurance", ObligationType.INSURANCE_PREMIUM,
                int(np.clip(rng.lognormal(4.3, 0.4), 2_000, 30_000)),
                _next_due(as_of, rng, 30), "monthly", checking_id, rng,
            )
        )

    if rng.random() < 0.6:
        obligations.append(
            _make_obligation(
                params, f"{params.household_id}_obl_subscription", ObligationType.SUBSCRIPTION,
                int(np.clip(rng.lognormal(2.6, 0.5), 500, 6_000)),
                _next_due(as_of, rng, 30), "monthly", checking_id, rng,
            )
        )

    if rng.random() < 0.15:
        obligations.append(
            _make_obligation(
                params, f"{params.household_id}_obl_bnpl", ObligationType.BNPL,
                int(np.clip(rng.lognormal(3.8, 0.4), 1_500, 20_000)),
                _next_due(as_of, rng, 14), "biweekly", checking_id, rng,
            )
        )

    return obligations[: max(params.obligation_count, 2)]


def generate_obligation_events(
    obligations: list[Obligation],
    rng: np.random.Generator,
    history_start: datetime,
    as_of: datetime,
    horizon_end: datetime,
) -> list[SimEvent]:
    events: list[SimEvent] = []
    for obl in obligations:
        period_days = _RECURRENCE_DAYS.get(obl.recurrence.value, 30)
        t = obl.due_date
        while t > history_start:
            t -= timedelta(days=period_days)
        idx = 0
        while t <= horizon_end:
            is_future = t > as_of
            status = "scheduled" if is_future else "posted"
            late = (not is_future) and rng.random() < 0.04
            amount = obl.scheduled_amount_cents
            events.append(
                SimEvent(
                    event_id=f"{obl.obligation_id}_pmt_{idx}",
                    event_type=_event_type_for(obl.obligation_type),
                    event_status=status,
                    amount_cents=amount,
                    direction="outflow",
                    account_id=obl.account_id,
                    merchant_category=obl.obligation_type.value,
                    recurrence_state=obl.recurrence.value,
                    source_type="simulated",
                    occurrence_time=t + (timedelta(days=2) if late else timedelta()),
                    effective_time=t + (timedelta(days=2) if late else timedelta()),
                    known=is_future,
                    known_source=_known_source_for(obl.obligation_type) if is_future else None,
                    obligation_id=obl.obligation_id,
                    transaction_confidence=1.0 if not is_future else 0.98,
                )
            )
            idx += 1
            t += timedelta(days=period_days)
    return events


def _event_type_for(obligation_type: ObligationType) -> str:
    return {
        ObligationType.RENT: "rent_payment",
        ObligationType.MORTGAGE: "mortgage_payment",
        ObligationType.AUTO_LOAN: "auto_loan_payment",
        ObligationType.PERSONAL_LOAN: "personal_loan_payment",
        ObligationType.CREDIT_CARD_MINIMUM: "credit_card_payment",
        ObligationType.INSURANCE_PREMIUM: "insurance_premium",
        ObligationType.UTILITY: "utility_bill",
        ObligationType.SUBSCRIPTION: "subscription",
        ObligationType.BNPL: "bnpl_payment",
        ObligationType.MEDICAL_PAYMENT_PLAN: "medical_payment",
    }[obligation_type]


def _known_source_for(obligation_type: ObligationType) -> str:
    if obligation_type == ObligationType.RENT:
        return "confirmed_rent_payment"
    if obligation_type == ObligationType.INSURANCE_PREMIUM:
        return "confirmed_insurance_premium"
    if obligation_type in (ObligationType.AUTO_LOAN, ObligationType.PERSONAL_LOAN, ObligationType.MORTGAGE):
        return "scheduled_loan_payment"
    return "scheduled_loan_payment"


def _next_due(as_of: datetime, rng: np.random.Generator, period_days: int) -> datetime:
    return as_of + timedelta(days=int(rng.integers(1, period_days + 1)))


def _make_obligation(
    params: HouseholdParams,
    obligation_id: str,
    obligation_type: ObligationType,
    amount_cents: int,
    due_date: datetime,
    recurrence: str,
    account_id: str,
    rng: np.random.Generator,
    remaining_principal_cents: int | None = None,
) -> Obligation:
    from relief_contracts.schemas import RecurrenceState

    capable = bool(providers.available_actions(obligation_type))
    return Obligation(
        obligation_id=obligation_id,
        obligation_type=obligation_type,
        scheduled_amount_cents=amount_cents,
        due_date=due_date,
        recurrence=RecurrenceState(recurrence),
        remaining_principal_cents=remaining_principal_cents,
        essentiality_category=(
            EssentialityCategory.ESSENTIAL if obligation_type in _ESSENTIAL_TYPES else EssentialityCategory.DISCRETIONARY
        ),
        payment_status=PaymentStatus.LATE if rng.random() < 0.03 else PaymentStatus.CURRENT,
        provider_capability_known=capable,
        account_id=account_id,
    )
