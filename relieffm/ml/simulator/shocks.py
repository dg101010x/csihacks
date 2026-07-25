"""Section 40 — shock library.

Two families:
  * expense shocks: inject a one-time (or short recurring) uncertain
    outflow event (vehicle repair, medical expense, duplicate charge, ...).
  * income shocks: perturb existing paycheck events in place (delayed
    paycheck, reduced work hours) so income timing/amount uncertainty
    correlates with the same household-level shock process rather than
    being independent of the expense side (section 40: "correlated event
    effects").

All shock-affected events are `known=False` — a shock is by definition
something Plan Two did not already schedule.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np

from .types import HouseholdParams, SimEvent

_EXPENSE_SHOCK_TYPES = [
    "vehicle_repair",
    "medical_expense",
    "duplicate_charge",
    "utility_spike",
    "unplanned_family_expense",
    "emergency_travel",
]

_BASE_SEVERITY_CENTS = {
    "vehicle_repair": 45_000,
    "medical_expense": 60_000,
    "duplicate_charge": 8_000,
    "utility_spike": 6_000,
    "unplanned_family_expense": 20_000,
    "emergency_travel": 35_000,
}


def apply_shocks(
    params: HouseholdParams,
    events: list[SimEvent],
    checking_account_id: str,
    rng: np.random.Generator,
    history_start: datetime,
    horizon_end: datetime,
) -> list[SimEvent]:
    window_days = (horizon_end - history_start).days + 1
    expected_shocks = params.shock_frequency / 365.0 * window_days
    n_shocks = int(rng.poisson(lam=max(expected_shocks, 0.0)))

    new_events: list[SimEvent] = []
    income_events = [e for e in events if e.event_type == "paycheck"]

    for i in range(n_shocks):
        shock_type = str(rng.choice(_EXPENSE_SHOCK_TYPES + ["reduced_work_hours", "delayed_paycheck"]))
        start = history_start + timedelta(days=int(rng.integers(0, window_days)))

        if shock_type == "reduced_work_hours" and income_events:
            target = _nearest_future_event(income_events, start)
            if target is not None:
                reduction = 1.0 - float(np.clip(params.shock_severity * rng.uniform(0.3, 1.0), 0.05, 0.7))
                target.amount_cents = max(int(target.amount_cents * reduction), 1)
                target.transaction_confidence = min(target.transaction_confidence, 0.5)
            continue

        if shock_type == "delayed_paycheck" and income_events:
            target = _nearest_future_event(income_events, start)
            if target is not None:
                delay_days = int(np.clip(rng.gamma(2.0, 2.0), 1, 14))
                target.occurrence_time = target.occurrence_time + timedelta(days=delay_days)
                target.effective_time = target.effective_time + timedelta(days=delay_days)
                target.known = False
                target.known_source = None
                target.transaction_confidence = min(target.transaction_confidence, 0.4)
            continue

        base = _BASE_SEVERITY_CENTS[shock_type]
        amount = int(np.clip(base * (0.4 + 1.6 * params.shock_severity) * float(rng.lognormal(0.0, 0.35)), 500, 5_000_00))
        new_events.append(
            SimEvent(
                event_id=f"{params.household_id}_shock_{shock_type}_{i}",
                event_type="shock_expense",
                event_status="posted" if start <= history_start else "scheduled",
                amount_cents=amount,
                direction="outflow",
                account_id=checking_account_id,
                merchant_category=shock_type,
                recurrence_state="none",
                source_type="simulated",
                occurrence_time=start,
                effective_time=start,
                known=False,
                transaction_confidence=float(rng.uniform(0.6, 0.95)),
            )
        )

    return events + new_events


def _nearest_future_event(income_events: list[SimEvent], anchor: datetime) -> SimEvent | None:
    candidates = [e for e in income_events if e.occurrence_time >= anchor]
    if not candidates:
        return None
    return min(candidates, key=lambda e: e.occurrence_time)
