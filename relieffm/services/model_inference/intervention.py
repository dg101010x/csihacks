"""Applies a proposed `Intervention` to a copy of the snapshot's known
future events. Mirrors `ml/simulator/interventions.py`'s action semantics
exactly (same seven action types, section 39/41) but operates on real
`relief_contracts` objects instead of the simulator's internal SimEvent,
since this runs against whatever HouseholdSnapshotV1 Plan Two sends.
"""
from __future__ import annotations

import copy
from datetime import datetime, timedelta

from relief_contracts.schemas import HouseholdSnapshotV1, Intervention

_DEFAULT_SPLIT_GAP_DAYS = 14
_DEFAULT_DELAY_DAYS = 10
_DEFAULT_PAUSE_DAYS = 30
_HARDSHIP_REDUCTION = 0.5
_REDUCE_PAYMENT_PCT = 0.3
_REFINANCE_PCT = 0.2
_WAIVE_FEE_CENTS = 2_500


class InterventionError(ValueError):
    pass


def _bounded_fraction(parameters: dict, key: str, default: float) -> float:
    value = float(parameters.get(key, default))
    if not 0.0 <= value <= 1.0:
        raise InterventionError(f"{key} must be between 0 and 1")
    return value


def _positive_days(parameters: dict, key: str, default: int) -> int:
    value = int(parameters.get(key, default))
    if value < 1:
        raise InterventionError(f"{key} must be at least 1")
    return value


def _optional_datetime(parameters: dict, key: str) -> datetime | None:
    value = parameters.get(key)
    if value is None:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise InterventionError(f"{key} must be an ISO-8601 timestamp") from exc


def apply_intervention(snapshot: HouseholdSnapshotV1, intervention: Intervention) -> tuple[HouseholdSnapshotV1, int]:
    """Returns (modified_snapshot, added_cost_cents). Only known_future_events
    tied to the target obligation are touched; everything else (historical
    events, other obligations, account state) is untouched, which is what
    keeps this a *conditional* forecast rather than a full re-simulation
    (section 28: "what trajectories are likely if this action is approved
    and executed", not a new household)."""
    snapshot = snapshot.model_copy(deep=True)
    action = intervention.action_type
    obligation_id = intervention.obligation_id

    future = sorted(
        (e for e in snapshot.known_future_events if e.obligation_id == obligation_id),
        key=lambda e: e.effective_time,
    )
    if not future:
        return snapshot, 0

    added_cost = 0
    if action == "split_payment":
        target = future[0]
        snapshot.known_future_events.remove(target)
        params = intervention.parameters
        first_amt = int(params.get("first_payment_cents", target.amount_cents // 2))
        second_amt = int(params.get("second_payment_cents", target.amount_cents - first_amt))
        if first_amt < 0 or second_amt < 0 or first_amt + second_amt != target.amount_cents:
            raise InterventionError(
                "split payment amounts must be non-negative and preserve the original total"
            )
        first_date = _optional_datetime(params, "first_payment_date") or target.effective_time
        second_date = _optional_datetime(params, "second_payment_date") or (
            target.effective_time + timedelta(days=_DEFAULT_SPLIT_GAP_DAYS)
        )
        if second_date < first_date:
            raise InterventionError("second_payment_date must not precede first_payment_date")
        first = target.model_copy(
            update={
                "amount_cents": first_amt,
                "event_id": target.event_id + "_split_a",
                "effective_time": first_date,
            }
        )
        second = target.model_copy(
            update={
                "amount_cents": second_amt,
                "event_id": target.event_id + "_split_b",
                "effective_time": second_date,
            }
        )
        snapshot.known_future_events.extend([first, second])

    elif action == "delay_payment":
        target = future[0]
        params = intervention.parameters
        delayed_until = _optional_datetime(params, "new_payment_date") or (
            target.effective_time
            + timedelta(
                days=_positive_days(params, "delay_days", _DEFAULT_DELAY_DAYS)
            )
        )
        if delayed_until <= target.effective_time:
            raise InterventionError("delayed payment must move to a later date")
        idx = snapshot.known_future_events.index(target)
        snapshot.known_future_events[idx] = target.model_copy(
            update={"effective_time": delayed_until}
        )
        added_cost = int(params.get("added_cost_cents", 500))

    elif action == "waive_fee":
        target = future[0]
        waived = int(intervention.parameters.get("waive_amount_cents", _WAIVE_FEE_CENTS))
        if waived < 0:
            raise InterventionError("waive_amount_cents must be non-negative")
        idx = snapshot.known_future_events.index(target)
        snapshot.known_future_events[idx] = target.model_copy(
            update={"amount_cents": max(target.amount_cents - waived, 0)}
        )

    elif action == "pause_subscription":
        duration_days = _positive_days(
            intervention.parameters, "duration_days", _DEFAULT_PAUSE_DAYS
        )
        cutoff = snapshot.as_of + timedelta(days=duration_days)
        snapshot.known_future_events = [
            e for e in snapshot.known_future_events
            if not (e.obligation_id == obligation_id and e.effective_time <= cutoff)
        ]

    elif action == "hardship_program":
        reduction = _bounded_fraction(
            intervention.parameters, "reduction_fraction", _HARDSHIP_REDUCTION
        )
        snapshot.known_future_events = [
            e.model_copy(update={"amount_cents": int(e.amount_cents * (1 - reduction))})
            if e.obligation_id == obligation_id else e
            for e in snapshot.known_future_events
        ]

    elif action == "reduce_payment":
        reduction = _bounded_fraction(
            intervention.parameters, "reduction_fraction", _REDUCE_PAYMENT_PCT
        )
        snapshot.known_future_events = [
            e.model_copy(update={"amount_cents": int(e.amount_cents * (1 - reduction))})
            if e.obligation_id == obligation_id else e
            for e in snapshot.known_future_events
        ]

    elif action == "refinance":
        reduction = _bounded_fraction(
            intervention.parameters, "reduction_fraction", _REFINANCE_PCT
        )
        snapshot.known_future_events = [
            e.model_copy(update={"amount_cents": int(e.amount_cents * (1 - reduction))})
            if e.obligation_id == obligation_id else e
            for e in snapshot.known_future_events
        ]
        added_cost = int(intervention.parameters.get("added_cost_cents", 2_500))

    return snapshot, added_cost
