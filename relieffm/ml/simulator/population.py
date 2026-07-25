"""Orchestrates one household's full generation: params -> accounts ->
obligations -> income/spending/shock events -> reconciled starting
balances -> HouseholdRecord.

Simplification (documented in the data card): all cash-flow events settle
against the single checking account. Savings/credit-card/loan accounts are
generated with a plausible as-of balance and appear as context tokens, but
are not part of the dynamic ledger in this Nano-scale simulator.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np

from .accounts import generate_accounts
from .households import sample_household_params
from .income import generate_income_events
from .obligations import generate_obligation_events, generate_obligations
from .shocks import apply_shocks
from .spending import generate_spending_events
from .types import HouseholdRecord


def generate_household(
    household_id: str,
    seed: int,
    as_of: datetime,
    history_days: int = 90,
    horizon_days: int = 30,
) -> HouseholdRecord:
    rng = np.random.default_rng(seed)

    history_start = as_of - timedelta(days=history_days)
    horizon_end = as_of + timedelta(days=horizon_days)

    params = sample_household_params(household_id, rng)
    accounts, as_of_balances, roles = generate_accounts(params, rng)
    obligations = generate_obligations(params, roles, rng, as_of)

    events = []
    events += generate_income_events(params, roles["checking"], rng, history_start, as_of, horizon_end)
    events += generate_spending_events(params, roles["checking"], rng, history_start, horizon_end)
    events += generate_obligation_events(obligations, rng, history_start, as_of, horizon_end)
    events = apply_shocks(params, events, roles["checking"], rng, history_start, horizon_end)
    events.sort(key=lambda e: e.occurrence_time)

    # Reconcile: as-of balance is given: back out each account's starting
    # (history_start) balance so replaying history forward reproduces it.
    starting_balances: dict[str, int] = {}
    for acct in accounts:
        net_history_flow = sum(
            (e.amount_cents if e.direction == "inflow" else -e.amount_cents)
            for e in events
            if e.account_id == acct.account_id and e.occurrence_time <= as_of
        )
        starting_balances[acct.account_id] = as_of_balances[acct.account_id] - net_history_flow

    return HouseholdRecord(
        params=params,
        as_of=as_of,
        history_start=history_start,
        horizon_end=horizon_end,
        accounts=accounts,
        obligations=obligations,
        events=events,
        account_starting_balances_cents=starting_balances,
    )


def generate_population(
    n_households: int,
    seed: int,
    as_of: datetime,
    history_days: int = 90,
    horizon_days: int = 30,
) -> list[HouseholdRecord]:
    records = []
    for i in range(n_households):
        household_id = f"sim_hh_{seed}_{i:07d}"
        records.append(
            generate_household(household_id, seed=seed * 1_000_003 + i, as_of=as_of, history_days=history_days, horizon_days=horizon_days)
        )
    return records
