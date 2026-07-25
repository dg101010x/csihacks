"""Section 41 — intervention pair generation.

For every obligation with known provider capability, sample one valid
synthetic intervention, apply it to a *copy* of the future event stream
(all other events — income, spending, shocks, other obligations — stay
identical, coupling the comparison per section 31's intent), replay the
ledger for both baseline and intervention scenarios, and store the exact
outcome difference. Label is `simulated` throughout (section 41).

This produces Milestone Two's required intervention-pair data. ReliefFM
Nano does not consume it this session (intervention-conditioned
forecasting is Mini-scope, section 19.2) — it's generated so the data
exists for that future work.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import timedelta

import numpy as np

from . import providers
from .ledger import daily_balances
from .types import HouseholdRecord, SimEvent

_DEFAULT_SPLIT_GAP_DAYS = 14
_DEFAULT_DELAY_DAYS = 10
_DEFAULT_PAUSE_DAYS = 30
_HARDSHIP_REDUCTION = 0.5
_REDUCE_PAYMENT_PCT = 0.3
_REFINANCE_PCT = 0.2
_WAIVE_FEE_CENTS = 2_500


@dataclass
class InterventionPair:
    household_id: str
    obligation_id: str
    action_type: str
    added_cost_cents: int
    baseline_daily_balances_cents: list[int]
    intervention_daily_balances_cents: list[int]
    delta_min_balance_cents: int
    delta_end_balance_cents: int
    baseline_negative_balance: bool
    intervention_negative_balance: bool
    provider_capability_label: str = "simulated"


def generate_intervention_pairs(record: HouseholdRecord, rng: np.random.Generator) -> list[InterventionPair]:
    checking_id = record.accounts[0].account_id
    start_balance = record.account_starting_balances_cents[checking_id]
    baseline_events = [e for e in record.events if e.account_id == checking_id]
    baseline_balances = daily_balances(
        baseline_events, start_balance, record.history_start, record.horizon_end, checking_id
    )

    pairs: list[InterventionPair] = []
    for obl in record.obligations:
        actions = providers.available_actions(obl.obligation_type)
        if not actions or obl.account_id != checking_id:
            continue
        action_type = str(rng.choice(sorted(actions)))
        modified_events, added_cost = _apply_intervention(
            baseline_events, obl.obligation_id, action_type, record.as_of, rng
        )
        intervention_balances = daily_balances(
            modified_events, start_balance, record.history_start, record.horizon_end, checking_id
        )

        pairs.append(
            InterventionPair(
                household_id=record.params.household_id,
                obligation_id=obl.obligation_id,
                action_type=action_type,
                added_cost_cents=added_cost,
                baseline_daily_balances_cents=baseline_balances,
                intervention_daily_balances_cents=intervention_balances,
                delta_min_balance_cents=min(intervention_balances) - min(baseline_balances),
                delta_end_balance_cents=intervention_balances[-1] - baseline_balances[-1],
                baseline_negative_balance=min(baseline_balances) < 0,
                intervention_negative_balance=min(intervention_balances) < 0,
            )
        )
    return pairs


def _apply_intervention(
    events: list[SimEvent],
    obligation_id: str,
    action_type: str,
    as_of,
    rng: np.random.Generator,
) -> tuple[list[SimEvent], int]:
    events = copy.deepcopy(events)
    future_for_obl = sorted(
        (e for e in events if e.obligation_id == obligation_id and e.occurrence_time > as_of),
        key=lambda e: e.occurrence_time,
    )
    added_cost = providers.modification_cost_cents(action_type)
    if not future_for_obl:
        return events, 0

    if action_type == "split_payment":
        target = future_for_obl[0]
        events.remove(target)
        half = target.amount_cents // 2
        first = copy.deepcopy(target)
        first.amount_cents = half
        first.event_id = target.event_id + "_split_a"
        second = copy.deepcopy(target)
        second.amount_cents = target.amount_cents - half
        second.event_id = target.event_id + "_split_b"
        second.occurrence_time = target.occurrence_time + timedelta(days=_DEFAULT_SPLIT_GAP_DAYS)
        second.effective_time = second.occurrence_time
        events.extend([first, second])

    elif action_type == "delay_payment":
        target = future_for_obl[0]
        target.occurrence_time += timedelta(days=_DEFAULT_DELAY_DAYS)
        target.effective_time = target.occurrence_time

    elif action_type == "waive_fee":
        target = future_for_obl[0]
        target.amount_cents = max(target.amount_cents - _WAIVE_FEE_CENTS, 0)
        added_cost = 0

    elif action_type == "pause_subscription":
        cutoff = as_of + timedelta(days=_DEFAULT_PAUSE_DAYS)
        for e in future_for_obl:
            if e.occurrence_time <= cutoff:
                events.remove(e)
        added_cost = 0

    elif action_type == "hardship_program":
        for e in future_for_obl:
            e.amount_cents = int(e.amount_cents * (1.0 - _HARDSHIP_REDUCTION))
        added_cost = 0

    elif action_type == "reduce_payment":
        for e in future_for_obl:
            e.amount_cents = int(e.amount_cents * (1.0 - _REDUCE_PAYMENT_PCT))
        added_cost = 0

    elif action_type == "refinance":
        for e in future_for_obl:
            e.amount_cents = int(e.amount_cents * (1.0 - _REFINANCE_PCT))

    return events, added_cost
