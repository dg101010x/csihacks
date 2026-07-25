"""Section 79's hand-engineered liquidity/recurrence features — the single
source of truth used by BOTH `ml/baselines/gradient_boosted.py` (the GBM
baseline) and `ml/relieffm/mini/distress_heads.py` (fed alongside the
learned embedding). Computed only from `HouseholdSnapshotV1` fields
(`historical_events`, `accounts`, `household_state`, `obligations`) —
never from simulator-internal `HouseholdParams` — because that's exactly
the leakage bug found and fixed in the GBM baseline during the Mini
upgrade (see that module's docstring). Keeping one function used by both
consumers means that mistake can't quietly reappear in only one of them.

Historical daily balances are reconstructed by replaying
`historical_events` forward from a *derived* starting balance
(current balance minus the net of all historical flows) — not from the
simulator's true starting balance, which a real snapshot would never
expose either.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

import numpy as np

from relief_contracts.schemas import HouseholdSnapshotV1

FEATURE_NAMES = [
    "essential_reserve_cents",
    "current_liquid_balance_cents",
    "num_obligations",
    "num_accounts",
    "estimated_income_cents",
    "historical_negative_day_frac",
    "historical_daily_flow_mean",
    "historical_daily_flow_std",
    "obligation_to_income_ratio",
    "credit_utilization_observed",
]


def compute_engineered_features(snapshot: HouseholdSnapshotV1) -> np.ndarray:
    account_id = snapshot.accounts[0].account_id
    current_balance = next(a.current_balance_cents for a in snapshot.accounts if a.account_id == account_id)
    events = sorted((e for e in snapshot.historical_events if e.account_id == account_id), key=lambda e: e.occurrence_time)

    net_flow = sum((e.amount_cents if e.direction.value == "inflow" else -e.amount_cents) for e in events)
    starting_balance = current_balance - net_flow

    events_by_day = defaultdict(list)
    for e in events:
        events_by_day[e.occurrence_time.date()].append(e)

    daily_balances: list[int] = []
    if events:
        d = events[0].occurrence_time.date()
        end_date = snapshot.as_of.date()
        bal = starting_balance
        while d <= end_date:
            for e in events_by_day.get(d, []):
                signed = e.amount_cents if e.direction.value == "inflow" else -e.amount_cents
                bal += signed
            daily_balances.append(bal)
            d += timedelta(days=1)
    balances_arr = np.array(daily_balances, dtype=np.float64) if daily_balances else np.array([float(current_balance)])

    paychecks = [e.amount_cents for e in snapshot.historical_events if e.event_type.value == "paycheck"]
    estimated_income = float(np.mean(paychecks)) if paychecks else 100_000.0

    liquid_balance = sum(a.current_balance_cents for a in snapshot.accounts if a.account_type.value in ("checking", "savings"))

    daily_flow: dict = {}
    for e in events:
        day = e.occurrence_time.date()
        signed = e.amount_cents if e.direction.value == "inflow" else -e.amount_cents
        daily_flow[day] = daily_flow.get(day, 0) + signed
    flows = np.array(list(daily_flow.values()), dtype=np.float64) if daily_flow else np.array([0.0])

    obligation_total = sum(o.scheduled_amount_cents for o in snapshot.obligations)
    obligation_to_income = obligation_total / max(estimated_income, 1.0)

    credit_util = 0.0
    for a in snapshot.accounts:
        if a.account_type.value == "credit_card" and a.credit_limit_cents:
            credit_util = max(credit_util, abs(a.current_balance_cents) / max(a.credit_limit_cents, 1))

    return np.array(
        [
            snapshot.household_state.essential_reserve_cents,
            liquid_balance,
            snapshot.household_state.num_obligations,
            snapshot.household_state.num_accounts,
            estimated_income,
            float(np.mean(balances_arr < 0)),
            float(np.mean(flows)),
            float(np.std(flows)),
            obligation_to_income,
            credit_util,
        ],
        dtype=np.float32,
    )
