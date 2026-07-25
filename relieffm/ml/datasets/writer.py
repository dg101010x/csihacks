"""Writes a compiled population to Parquet + a manifest (sections 34, 44, 75).

Tables:
  households.parquet   one row per household: household_state + params
  accounts.parquet     one row per account
  obligations.parquet  one row per obligation
  events.parquet       one row per event (historical / known-future / uncertain-future)
  targets.parquet      one row per household: Nano trajectory + distress labels
  manifest.json        dataset version, generation config, split sizes, git commit
"""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from .compile import household_record_to_snapshot, household_record_to_targets
from .splits import assign_splits
from ml.simulator.types import HouseholdRecord

DATASET_VERSION = "relief_data_0.1.0"


def write_dataset(records: list[HouseholdRecord], out_dir: str, seed: int) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    splits = assign_splits([r.params.household_id for r in records])

    household_rows, account_rows, obligation_rows, event_rows, target_rows = [], [], [], [], []

    for r in records:
        snapshot = household_record_to_snapshot(r)
        targets = household_record_to_targets(r)
        split = splits[r.params.household_id]

        household_rows.append(
            {
                "household_id": r.params.household_id,
                "split": split,
                "as_of": r.as_of.isoformat(),
                "total_liquid_balance_cents": snapshot.household_state.total_liquid_balance_cents,
                "available_balance_cents": snapshot.household_state.available_balance_cents,
                "num_accounts": snapshot.household_state.num_accounts,
                "num_obligations": snapshot.household_state.num_obligations,
                "essential_reserve_cents": snapshot.household_state.essential_reserve_cents,
                "income_amount_cents": r.params.income_amount_cents,
                "income_frequency": r.params.income_frequency,
                "income_reliability": r.params.income_reliability,
                "income_volatility": r.params.income_volatility,
                "spending_volatility": r.params.spending_volatility,
                "debt_burden": r.params.debt_burden,
                "credit_utilization": r.params.credit_utilization,
                "shock_frequency": r.params.shock_frequency,
            }
        )

        for a in snapshot.accounts:
            account_rows.append(
                {
                    "household_id": r.params.household_id,
                    "account_id": a.account_id,
                    "account_type": a.account_type.value,
                    "account_subtype": a.account_subtype,
                    "current_balance_cents": a.current_balance_cents,
                    "available_balance_cents": a.available_balance_cents,
                    "credit_limit_cents": a.credit_limit_cents,
                    "data_freshness_hours": a.data_freshness_hours,
                }
            )

        for o in snapshot.obligations:
            obligation_rows.append(
                {
                    "household_id": r.params.household_id,
                    "obligation_id": o.obligation_id,
                    "obligation_type": o.obligation_type.value,
                    "scheduled_amount_cents": o.scheduled_amount_cents,
                    "due_date": o.due_date.isoformat(),
                    "recurrence": o.recurrence.value,
                    "essentiality_category": o.essentiality_category.value,
                    "payment_status": o.payment_status.value,
                    "provider_capability_known": o.provider_capability_known,
                    "account_id": o.account_id,
                }
            )

        for e in snapshot.historical_events:
            event_rows.append(_event_row(r.params.household_id, e, "historical"))
        for e in snapshot.known_future_events:
            event_rows.append(_event_row(r.params.household_id, e, "known_future"))

        target_rows.append(
            {
                "household_id": r.params.household_id,
                "horizon_days": targets.horizon_days,
                "daily_balance_cents": targets.daily_balance_cents,
                "known_daily_balance_cents": targets.known_daily_balance_cents,
                "uncertain_daily_inflow_cents": targets.uncertain_daily_inflow_cents,
                "uncertain_daily_essential_outflow_cents": targets.uncertain_daily_essential_outflow_cents,
                "uncertain_daily_discretionary_outflow_cents": targets.uncertain_daily_discretionary_outflow_cents,
                **{
                    f"distress_negative_balance_{h}": targets.distress_negative_balance.get(h)
                    for h in (7, 14, 30)
                },
                **{
                    f"distress_reserve_violation_{h}": targets.distress_reserve_violation.get(h)
                    for h in (7, 14, 30)
                },
                **{
                    f"distress_missed_obligation_{h}": targets.distress_missed_obligation.get(h)
                    for h in (7, 14, 30)
                },
            }
        )

    pq.write_table(pa.Table.from_pylist(household_rows), out / "households.parquet")
    pq.write_table(pa.Table.from_pylist(account_rows), out / "accounts.parquet")
    pq.write_table(pa.Table.from_pylist(obligation_rows), out / "obligations.parquet")
    pq.write_table(pa.Table.from_pylist(event_rows), out / "events.parquet")
    pq.write_table(pa.Table.from_pylist(target_rows), out / "targets.parquet")

    split_counts = {name: sum(1 for s in splits.values() if s == name) for name in ("train", "val", "test")}
    manifest = {
        "dataset_version": DATASET_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "seed": seed,
        "n_households": len(records),
        "n_events": len(event_rows),
        "split_counts": split_counts,
        "git_commit": _git_commit(),
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def _event_row(household_id: str, e, kind: str) -> dict:
    return {
        "household_id": household_id,
        "kind": kind,
        "event_id": e.event_id,
        "event_type": e.event_type.value,
        "amount_cents": e.amount_cents,
        "direction": e.direction.value,
        "account_id": e.account_id,
        "occurrence_time": getattr(e, "occurrence_time", None) and e.occurrence_time.isoformat(),
        "effective_time": e.effective_time.isoformat(),
        "merchant_category": getattr(e, "merchant_category", None),
        "recurrence_state": getattr(e, "recurrence_state", None) and e.recurrence_state.value,
        "transaction_confidence": getattr(e, "transaction_confidence", None),
        "source": getattr(e, "source", None) and e.source.value,
        "obligation_id": getattr(e, "obligation_id", None),
    }


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return "unknown"
