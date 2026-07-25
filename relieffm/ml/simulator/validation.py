"""Section 43 — synthetic realism validation (subset).

Two layers:
  * per-household sanity checks (structural — should never fail)
  * population-level aggregate statistics (distributional — used to sanity
    check the generator, not a formal realism benchmark against real data,
    since we have none to compare against yet)
"""
from __future__ import annotations

from collections import Counter

import numpy as np

from .types import HouseholdRecord


def validate_household_record(record: HouseholdRecord) -> list[str]:
    warnings: list[str] = []
    if not record.accounts:
        warnings.append(f"{record.params.household_id}: no accounts generated")
    if not record.events:
        warnings.append(f"{record.params.household_id}: no events generated")
    account_ids = {a.account_id for a in record.accounts}
    for e in record.events:
        if e.account_id not in account_ids:
            warnings.append(f"{record.params.household_id}: event {e.event_id} references unknown account {e.account_id}")
        if e.effective_time < e.occurrence_time - _MAX_SKEW:
            warnings.append(f"{record.params.household_id}: event {e.event_id} has impossible timestamps")
    for obl in record.obligations:
        if obl.account_id not in account_ids:
            warnings.append(f"{record.params.household_id}: obligation {obl.obligation_id} references unknown account")
    return warnings


from datetime import timedelta  # noqa: E402

_MAX_SKEW = timedelta(days=1)


def population_realism_report(records: list[HouseholdRecord]) -> dict:
    """Aggregate distributions per section 43's checklist (subset)."""
    event_counts = [len(r.events) for r in records]
    amounts = np.array([e.amount_cents for r in records for e in r.events], dtype=np.float64)
    merchant_categories = Counter(e.merchant_category for r in records for e in r.events)

    interevent_days: list[float] = []
    for r in records:
        times = sorted(e.occurrence_time for e in r.events)
        for a, b in zip(times, times[1:]):
            interevent_days.append((b - a).total_seconds() / 86400.0)

    as_of_balances = np.array(
        [r.account_starting_balances_cents.get(a.account_id, 0) for r in records for a in r.accounts],
        dtype=np.float64,
    )
    negative_balance_frac = float(np.mean(np.array([a.current_balance_cents for r in records for a in r.accounts]) < 0))

    return {
        "n_households": len(records),
        "total_events": int(sum(event_counts)),
        "events_per_household": _summary(np.array(event_counts, dtype=np.float64)),
        "amount_cents": _summary(amounts),
        "interevent_days": _summary(np.array(interevent_days, dtype=np.float64)) if interevent_days else {},
        "top_merchant_categories": merchant_categories.most_common(10),
        "negative_balance_fraction": negative_balance_frac,
    }


def _summary(x: np.ndarray) -> dict:
    if x.size == 0:
        return {}
    return {
        "mean": float(np.mean(x)),
        "std": float(np.std(x)),
        "p10": float(np.percentile(x, 10)),
        "p50": float(np.percentile(x, 50)),
        "p90": float(np.percentile(x, 90)),
        "min": float(np.min(x)),
        "max": float(np.max(x)),
    }
