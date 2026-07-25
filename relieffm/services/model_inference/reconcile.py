"""Section 23-24, standalone: replays a `HouseholdSnapshotV1`'s
known_future_events deterministically to produce the known-only daily
balance/inflow/outflow series the model's predicted residual gets added
to. Depends only on relief_contracts + ml.simulator.ledger's day-bucketing
helper (Plan One owns both), never on ml.simulator's internal SimEvent
type — this is the boundary a real Plan Two snapshot crosses.
"""
from __future__ import annotations

from dataclasses import dataclass

from relief_contracts.schemas import HouseholdSnapshotV1
from ml.simulator.ledger import day_bucket


@dataclass
class KnownProjection:
    daily_balance_cents: list[int]
    daily_inflow_cents: list[int]
    daily_outflow_cents: list[int]


def project_known_events(snapshot: HouseholdSnapshotV1, horizon_days: int) -> KnownProjection:
    account_id = snapshot.accounts[0].account_id
    start_balance = next(
        (a.current_balance_cents for a in snapshot.accounts if a.account_id == account_id),
        snapshot.household_state.total_liquid_balance_cents,
    )

    inflow = [0] * horizon_days
    outflow = [0] * horizon_days
    for e in snapshot.known_future_events:
        if e.account_id != account_id:
            continue
        idx = day_bucket(e.effective_time, snapshot.as_of)
        if not (0 <= idx < horizon_days):
            continue
        if e.direction.value == "inflow":
            inflow[idx] += e.amount_cents
        else:
            outflow[idx] += e.amount_cents

    balances = [0] * horizon_days
    balance = start_balance
    for d in range(horizon_days):
        balance += inflow[d] - outflow[d]
        balances[d] = balance

    return KnownProjection(daily_balance_cents=balances, daily_inflow_cents=inflow, daily_outflow_cents=outflow)
