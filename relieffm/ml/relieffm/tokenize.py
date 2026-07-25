"""Milestone Three — input compiler.

Turns a `HouseholdSnapshotV1` (+ optional `NanoTargets`) into fixed-shape
numpy arrays: household/account/obligation/historical-event/known-future-
event tokens (section 12's six classes minus intervention, which Nano
doesn't consume), each with a categorical-index array, a numeric-feature
array, and a validity mask (section 17-18: segment separation, dynamic
length handling via truncate-to-most-recent + padding).

Deliberately numpy-only (no torch import) so it can run standalone during
dataset preparation; `ml/training` stacks and converts to tensors.
"""
from __future__ import annotations

import numpy as np

from relief_contracts.schemas import HouseholdSnapshotV1

from . import vocab
from .config import NanoConfig
from .features import (
    amount_transform,
    calendar_features,
    relative_to_balance,
    relative_to_income,
    time_offset_days,
)

try:
    from ml.datasets.compile import NanoTargets
except ImportError:  # pragma: no cover - compile.py depends on this module's siblings, not this file
    NanoTargets = None  # type: ignore


def _estimate_income_cents(snapshot: HouseholdSnapshotV1) -> float:
    paychecks = [e.amount_cents for e in snapshot.historical_events if e.event_type.value == "paycheck"]
    if paychecks:
        return float(np.mean(paychecks))
    return 100_000.0  # fallback: $1,000, keeps ratios finite for income-sparse snapshots


def encode_snapshot(snapshot: HouseholdSnapshotV1, config: NanoConfig) -> dict[str, np.ndarray]:
    account_type_by_id = {a.account_id: a.account_type for a in snapshot.accounts}
    income_estimate = _estimate_income_cents(snapshot)
    balance_estimate = snapshot.household_state.total_liquid_balance_cents

    out: dict[str, np.ndarray] = {}

    out["household_numeric"] = np.array(
        [
            _signed_log(snapshot.household_state.total_liquid_balance_cents),
            _signed_log(snapshot.household_state.available_balance_cents),
            snapshot.household_state.num_accounts / 5.0,
            snapshot.household_state.num_obligations / 10.0,
            np.log1p(snapshot.household_state.essential_reserve_cents / 100.0),
            snapshot.household_state.data_freshness_hours / 24.0,
            snapshot.household_state.snapshot_completeness,
        ],
        dtype=np.float32,
    )

    out["account_cat"], out["account_numeric"], out["account_mask"] = _encode_accounts(snapshot, config)
    out["obligation_cat"], out["obligation_numeric"], out["obligation_mask"] = _encode_obligations(
        snapshot, config
    )
    out["event_cat"], out["event_numeric"], out["event_mask"] = _encode_historical_events(
        snapshot, config, account_type_by_id, income_estimate, balance_estimate
    )
    out["known_cat"], out["known_numeric"], out["known_mask"] = _encode_known_future_events(
        snapshot, config, account_type_by_id, income_estimate, balance_estimate
    )
    return out


def encode_targets(targets: "NanoTargets", config: NanoConfig) -> dict[str, np.ndarray]:
    h = config.forecast_horizon_days
    assert targets.horizon_days == h, f"target horizon {targets.horizon_days} != config horizon {h}"

    out = {
        "target_uncertain_inflow_cents": np.array(targets.uncertain_daily_inflow_cents, dtype=np.float32),
        "target_uncertain_essential_outflow_cents": np.array(
            targets.uncertain_daily_essential_outflow_cents, dtype=np.float32
        ),
        "target_uncertain_discretionary_outflow_cents": np.array(
            targets.uncertain_daily_discretionary_outflow_cents, dtype=np.float32
        ),
        "target_known_balance_cents": np.array(targets.known_daily_balance_cents, dtype=np.float32),
        "target_full_balance_cents": np.array(targets.daily_balance_cents, dtype=np.float32),
    }

    distress = np.zeros((len(config.distress_horizons), 3), dtype=np.float32)
    for i, hz in enumerate(config.distress_horizons):
        distress[i, 0] = float(targets.distress_negative_balance.get(hz, False))
        distress[i, 1] = float(targets.distress_reserve_violation.get(hz, False))
        distress[i, 2] = float(targets.distress_missed_obligation.get(hz, False))
    out["target_distress"] = distress
    return out


def _signed_log(cents: float) -> float:
    return amount_transform(cents)


def _encode_accounts(snapshot: HouseholdSnapshotV1, config: NanoConfig):
    n = config.max_accounts
    cat = np.zeros((n, 1), dtype=np.int64)
    num = np.zeros((n, config.account_numeric_dim), dtype=np.float32)
    mask = np.zeros((n,), dtype=np.float32)
    for i, a in enumerate(snapshot.accounts[:n]):
        cat[i, 0] = vocab.index_of(vocab.ACCOUNT_TYPE, a.account_type)
        num[i] = [
            _signed_log(a.current_balance_cents),
            _signed_log(a.available_balance_cents),
            np.log1p((a.credit_limit_cents or 0) / 100.0),
            a.data_freshness_hours / 24.0,
        ]
        mask[i] = 1.0
    return cat, num, mask


def _encode_obligations(snapshot: HouseholdSnapshotV1, config: NanoConfig):
    n = config.max_obligations
    cat = np.zeros((n, 4), dtype=np.int64)
    num = np.zeros((n, config.obligation_numeric_dim), dtype=np.float32)
    mask = np.zeros((n,), dtype=np.float32)
    for i, o in enumerate(snapshot.obligations[:n]):
        cat[i] = [
            vocab.index_of(vocab.OBLIGATION_TYPE, o.obligation_type),
            vocab.index_of(vocab.RECURRENCE_STATE, o.recurrence),
            vocab.index_of(vocab.ESSENTIALITY, o.essentiality_category),
            vocab.index_of(vocab.PAYMENT_STATUS, o.payment_status),
        ]
        days_until_due = time_offset_days(o.due_date, snapshot.as_of)
        num[i] = [
            np.log1p(o.scheduled_amount_cents / 100.0),
            float(np.clip(days_until_due / 30.0, -2.0, 2.0)),
            np.log1p((o.remaining_principal_cents or 0) / 100.0),
        ]
        mask[i] = 1.0
    return cat, num, mask


def _encode_historical_events(snapshot, config: NanoConfig, account_type_by_id, income_estimate, balance_estimate):
    n = config.context_events
    events = sorted(snapshot.historical_events, key=lambda e: e.occurrence_time)
    events = events[-n:]  # section 18: recent event preservation

    cat = np.zeros((n, 7), dtype=np.int64)
    num = np.zeros((n, config.event_numeric_dim), dtype=np.float32)
    mask = np.zeros((n,), dtype=np.float32)

    pad = n - len(events)
    for j, e in enumerate(events):
        i = pad + j
        signed_amount = e.amount_cents if e.direction.value == "inflow" else -e.amount_cents
        account_type = account_type_by_id.get(e.account_id)
        cat[i] = [
            vocab.index_of(vocab.EVENT_TYPE, e.event_type),
            vocab.index_of(vocab.EVENT_STATUS, e.event_status),
            vocab.index_of(vocab.DIRECTION, e.direction),
            vocab.index_of(vocab.RECURRENCE_STATE, e.recurrence_state),
            vocab.index_of(vocab.SOURCE_TYPE, e.source_type),
            vocab.index_of(vocab.ACCOUNT_TYPE, account_type) if account_type else 0,
            vocab.index_of(vocab.MERCHANT_CATEGORY, e.merchant_category),
        ]
        dow_s, dow_c, dom_s, dom_c = calendar_features(e.occurrence_time)
        num[i] = [
            amount_transform(signed_amount),
            relative_to_income(signed_amount, income_estimate),
            relative_to_balance(signed_amount, balance_estimate),
            time_offset_days(e.occurrence_time, snapshot.as_of) / 30.0,
            dow_s, dow_c, dom_s, dom_c,
            e.transaction_confidence,
        ]
        mask[i] = 1.0
    return cat, num, mask


def _encode_known_future_events(snapshot, config: NanoConfig, account_type_by_id, income_estimate, balance_estimate):
    n = config.max_known_future_events
    events = sorted(snapshot.known_future_events, key=lambda e: e.effective_time)[:n]

    cat = np.zeros((n, 4), dtype=np.int64)
    num = np.zeros((n, config.known_future_numeric_dim), dtype=np.float32)
    mask = np.zeros((n,), dtype=np.float32)

    for i, e in enumerate(events):
        signed_amount = e.amount_cents if e.direction.value == "inflow" else -e.amount_cents
        account_type = account_type_by_id.get(e.account_id)
        cat[i] = [
            vocab.index_of(vocab.EVENT_TYPE, e.event_type),
            vocab.index_of(vocab.DIRECTION, e.direction),
            vocab.index_of(vocab.ACCOUNT_TYPE, account_type) if account_type else 0,
            vocab.index_of(vocab.KNOWN_FUTURE_SOURCE, e.source),
        ]
        dow_s, dow_c, dom_s, dom_c = calendar_features(e.effective_time)
        num[i] = [
            amount_transform(signed_amount),
            relative_to_income(signed_amount, income_estimate),
            relative_to_balance(signed_amount, balance_estimate),
            time_offset_days(e.effective_time, snapshot.as_of) / 30.0,
            dow_s, dow_c, dom_s, dom_c,
        ]
        mask[i] = 1.0
    return cat, num, mask
