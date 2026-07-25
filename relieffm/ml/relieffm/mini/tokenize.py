"""Mini's tokenizer. Reuses Nano's `encode_snapshot`/`encode_targets`
unmodified — `MiniConfig` shares every attribute name those functions read
(`household_numeric_dim`, `max_accounts`, `forecast_horizon_days`,
`distress_horizons`, ...), so they work via duck typing without
Mini-specific copies. This file adds exactly the three things Mini has
that Nano doesn't: engineered distress features, event-set targets, and
an (optional) intervention token + its delta target.
"""
from __future__ import annotations

import numpy as np

from relief_contracts.schemas import HouseholdSnapshotV1

from .. import vocab
from ..config import MiniConfig
from ..engineered_features import compute_engineered_features
from ..features import amount_transform, relative_to_balance, relative_to_income, time_offset_days
from ..tokenize import encode_snapshot, encode_targets

try:
    from ml.datasets.compile import EventSetTargets, InterventionExample, NanoTargets
except ImportError:  # pragma: no cover
    EventSetTargets = InterventionExample = NanoTargets = None  # type: ignore


def encode_mini_snapshot(snapshot: HouseholdSnapshotV1, config: MiniConfig) -> dict[str, np.ndarray]:
    out = encode_snapshot(snapshot, config)
    out["engineered_features"] = compute_engineered_features(snapshot)
    return out


def encode_mini_targets(targets: "NanoTargets", config: MiniConfig) -> dict[str, np.ndarray]:
    return encode_targets(targets, config)


def encode_event_set_targets(targets: "EventSetTargets", config: MiniConfig) -> dict[str, np.ndarray]:
    return {
        "event_set_type_idx": np.array(targets.event_type_idx, dtype=np.int64),
        "event_set_time_fraction": np.array(targets.time_fraction, dtype=np.float32),
        "event_set_amount": np.array(targets.amount_transformed, dtype=np.float32),
        "event_set_direction_idx": np.array(targets.direction_idx, dtype=np.int64),
        "event_set_account_idx": np.array(targets.account_idx, dtype=np.int64),
        "event_set_recurrence_idx": np.array(targets.recurrence_idx, dtype=np.int64),
        "event_set_obligation_linked": np.array(targets.obligation_linked, dtype=np.float32),
        "event_set_valid_mask": np.array(targets.valid_mask, dtype=np.float32),
    }


def encode_intervention_example(example: "InterventionExample", snapshot: HouseholdSnapshotV1, config: MiniConfig) -> dict[str, np.ndarray]:
    income_estimate = _estimate_income(snapshot)
    balance_estimate = snapshot.household_state.total_liquid_balance_cents

    action_idx = vocab.index_of(vocab.INTERVENTION_ACTION_TYPE, example.action_type) if example.has_intervention else 0
    numeric = np.array(
        [
            amount_transform(example.original_amount_cents),
            amount_transform(example.modified_amount_cents),
            amount_transform(example.modified_amount_cents - example.original_amount_cents),
            float(np.clip(example.original_date_offset_days / 30.0, -3.0, 3.0)),
            float(np.clip(example.modified_date_offset_days / 30.0, -3.0, 3.0)),
            float(np.log1p(example.added_cost_cents / 100.0)),
        ],
        dtype=np.float32,
    )
    return {
        "intervention_action_idx": np.array(action_idx, dtype=np.int64),
        "intervention_numeric": numeric,
        "has_intervention": np.array(1.0 if example.has_intervention else 0.0, dtype=np.float32),
        "intervention_delta_balance_cents": np.array(example.delta_daily_balance_cents, dtype=np.float32),
    }


def _estimate_income(snapshot: HouseholdSnapshotV1) -> float:
    paychecks = [e.amount_cents for e in snapshot.historical_events if e.event_type.value == "paycheck"]
    return float(np.mean(paychecks)) if paychecks else 100_000.0
