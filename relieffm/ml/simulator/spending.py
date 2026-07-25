"""Section 38 — spending models.

Handles the *variable* transaction stream (essential + discretionary
purchases, fees, refunds). Fixed recurring items (rent, subscriptions,
insurance, debt service) are obligation-driven and live in obligations.py.

Categories are driven by a shared AR(1) "spending pressure" latent per day
so essential and discretionary spending move together rather than varying
independently (section 38: "use correlated spending factors").
"""
from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np

from .types import HouseholdParams, SimEvent

_ESSENTIAL_CATEGORIES = ["groceries", "fuel", "pharmacy", "utilities_variable"]
_DISCRETIONARY_CATEGORIES = ["dining", "entertainment", "shopping", "travel"]


def generate_spending_events(
    params: HouseholdParams,
    checking_account_id: str,
    rng: np.random.Generator,
    history_start: datetime,
    horizon_end: datetime,
) -> list[SimEvent]:
    events: list[SimEvent] = []
    num_days = (horizon_end - history_start).days + 1

    pressure = 0.0
    idx = 0
    for day_idx in range(num_days):
        day = history_start + timedelta(days=day_idx)
        pressure = 0.7 * pressure + float(rng.normal(0.0, 1.0))
        pressure_mult = float(np.clip(1.0 + 0.15 * pressure, 0.4, 2.2))

        n_essential = rng.poisson(lam=0.6)
        for _ in range(n_essential):
            amt = params.essential_spending_level * pressure_mult * float(
                np.clip(rng.gamma(shape=2.0, scale=params.spending_volatility), 0.1, 4.0)
            )
            events.append(_purchase_event(params, checking_account_id, day, rng, amt, essential=True, idx=idx))
            idx += 1

        n_discretionary = rng.poisson(lam=0.35 * pressure_mult)
        for _ in range(n_discretionary):
            amt = params.discretionary_spending_level * pressure_mult * float(
                np.clip(rng.gamma(shape=1.6, scale=params.spending_volatility * 1.3), 0.1, 5.0)
            )
            events.append(_purchase_event(params, checking_account_id, day, rng, amt, essential=False, idx=idx))
            idx += 1

        if rng.random() < 0.015:
            fee_amt = int(np.clip(rng.gamma(2.0, 12_00), 1_00, 75_00))
            events.append(
                SimEvent(
                    event_id=f"{params.household_id}_fee_{idx}",
                    event_type="fee",
                    event_status="posted" if day <= history_start else "scheduled",
                    amount_cents=fee_amt,
                    direction="outflow",
                    account_id=checking_account_id,
                    merchant_category="bank_fee",
                    recurrence_state="none",
                    source_type="simulated",
                    occurrence_time=_with_time(day, rng),
                    effective_time=_with_time(day, rng),
                    known=False,
                    transaction_confidence=0.5,
                )
            )
            idx += 1

        if rng.random() < 0.008:
            refund_amt = int(np.clip(rng.gamma(2.0, 20_00), 1_00, 150_00))
            events.append(
                SimEvent(
                    event_id=f"{params.household_id}_refund_{idx}",
                    event_type="refund",
                    event_status="posted" if day <= history_start else "scheduled",
                    amount_cents=refund_amt,
                    direction="inflow",
                    account_id=checking_account_id,
                    merchant_category="refund",
                    recurrence_state="none",
                    source_type="simulated",
                    occurrence_time=_with_time(day, rng),
                    effective_time=_with_time(day, rng),
                    known=False,
                    transaction_confidence=0.5,
                )
            )
            idx += 1

    return events


def _purchase_event(
    params: HouseholdParams,
    account_id: str,
    day: datetime,
    rng: np.random.Generator,
    amount_float: float,
    essential: bool,
    idx: int,
) -> SimEvent:
    category = rng.choice(_ESSENTIAL_CATEGORIES if essential else _DISCRETIONARY_CATEGORIES)
    amount_cents = max(int(amount_float), 50)
    t = _with_time(day, rng)
    return SimEvent(
        event_id=f"{params.household_id}_purchase_{idx}",
        event_type="purchase",
        event_status="posted",
        amount_cents=amount_cents,
        direction="outflow",
        account_id=account_id,
        merchant_category=str(category),
        recurrence_state="none",
        source_type="simulated",
        occurrence_time=t,
        effective_time=t,
        known=False,
        transaction_confidence=float(rng.uniform(0.85, 1.0)),
    )


def _with_time(day: datetime, rng: np.random.Generator) -> datetime:
    return day.replace(hour=int(rng.integers(6, 22)), minute=int(rng.integers(0, 60)))
