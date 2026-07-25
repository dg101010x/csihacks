"""Section 37 — income models.

Generates the paycheck event stream for one household across the full
simulated window. Only the first future paycheck after `as_of` is marked
`known` (a real payroll calendar is usually confirmed one cycle ahead);
subsequent future paychecks stay uncertain, carrying timing and amount
noise, which is exactly the uncertainty ReliefFM is meant to forecast.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np

from .types import HouseholdParams, SimEvent

_PAY_PERIOD_DAYS = {
    "weekly": 7,
    "biweekly": 14,
    "semimonthly": 15,
    "monthly": 30,
    "hourly_variable": 14,
    "freelance": 21,
}


def generate_income_events(
    params: HouseholdParams,
    checking_account_id: str,
    rng: np.random.Generator,
    history_start: datetime,
    as_of: datetime,
    horizon_end: datetime,
) -> list[SimEvent]:
    period_days = _PAY_PERIOD_DAYS[params.income_frequency]
    events: list[SimEvent] = []

    # Anchor the pay cycle at a random offset so households aren't phase-locked.
    phase_offset = int(rng.integers(0, period_days))
    t = history_start + timedelta(days=phase_offset)
    idx = 0
    first_future_marked = False

    while t <= horizon_end:
        is_future = t > as_of
        is_known = is_future and not first_future_marked
        if is_future:
            first_future_marked = True

        noise = rng.normal(0.0, params.income_volatility)
        reliability_hit = rng.random() > params.income_reliability
        amount = params.income_amount_cents * (1.0 + noise)
        if reliability_hit and not is_known:
            # Missed hours / reduced shift: partial paycheck.
            amount *= float(rng.uniform(0.4, 0.85))
        amount_cents = max(int(amount), 1)

        jitter_hours = 0 if is_known else int(rng.integers(-6, 6))
        occ = t + timedelta(hours=jitter_hours)

        events.append(
            SimEvent(
                event_id=f"{params.household_id}_income_{idx}",
                event_type="paycheck",
                event_status="posted" if occ <= as_of else "scheduled",
                amount_cents=amount_cents,
                direction="inflow",
                account_id=checking_account_id,
                merchant_category="payroll",
                recurrence_state=_recurrence_state(params.income_frequency),
                source_type="simulated",
                occurrence_time=occ,
                effective_time=occ,
                known=is_known,
                known_source="confirmed_paycheck" if is_known else None,
                transaction_confidence=1.0 if occ <= as_of else (0.95 if is_known else 0.6),
            )
        )
        idx += 1
        t += timedelta(days=period_days)

    return events


def _recurrence_state(frequency: str) -> str:
    return {
        "weekly": "weekly",
        "biweekly": "biweekly",
        "semimonthly": "semimonthly",
        "monthly": "monthly",
        "hourly_variable": "irregular",
        "freelance": "irregular",
    }[frequency]
