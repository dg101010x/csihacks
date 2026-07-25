"""Deterministic ledger replay — the one place daily balances get computed
from an event list. Shared by the intervention pair generator and by the
dataset compiler's label construction (section 24's balance recurrence,
implemented exactly, not learned).
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta

from .types import SimEvent


def day_bucket(occurrence_time: datetime, start_date: datetime) -> int:
    """Which zero-indexed day-bucket `occurrence_time` falls into relative to
    `start_date`, using the same day_end = start_date + (idx+1) days cutoff
    that `daily_balances` uses. Callers that aggregate per-day targets
    outside this module MUST use this instead of `.date()` arithmetic, or
    bucketing will silently drift whenever start_date's time-of-day isn't
    midnight (assert `daily_balances`'s per-day totals stay reconcilable)."""
    delta_days = (occurrence_time - start_date).total_seconds() / 86400.0
    return math.ceil(delta_days) - 1


def daily_balances(
    events: list[SimEvent],
    start_balance_cents: int,
    start_date: datetime,
    end_date: datetime,
    account_id: str,
) -> list[int]:
    """End-of-day balance for each day strictly after start_date up to and
    including end_date — (end_date - start_date).days values total."""
    relevant = sorted(
        (e for e in events if e.account_id == account_id and start_date < e.occurrence_time <= end_date),
        key=lambda e: e.occurrence_time,
    )
    n_days = (end_date.date() - start_date.date()).days
    balances = [0] * n_days
    balance = start_balance_cents
    ei = 0
    for day_idx in range(n_days):
        day_end = start_date + timedelta(days=day_idx + 1)
        while ei < len(relevant) and relevant[ei].occurrence_time <= day_end:
            e = relevant[ei]
            balance += e.amount_cents if e.direction == "inflow" else -e.amount_cents
            ei += 1
        balances[day_idx] = balance
    return balances
