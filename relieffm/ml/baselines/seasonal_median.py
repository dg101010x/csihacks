"""Section 78 — statistical baseline (seasonal median / last-cycle
repetition, combined). Section 77's deterministic baseline already gets
full credit for known events; this baseline is ReliefFM's actual
competitor — it predicts the *uncertain* residual using nothing but the
household's own historical median daily net flow, so any gain Nano shows
over it is gain from modeling the event sequence, not from knowing
obligations exist.
"""
from __future__ import annotations

import numpy as np

from ml.simulator.types import HouseholdRecord


def predict_uncertain_daily_net_flow(record: HouseholdRecord) -> float:
    """Median historical daily net flow from events Plan Two would NOT have
    already scheduled (i.e. excluding obligation-driven, known-tagged
    events) — the seasonal/no-model prediction for each future day's
    uncertain contribution."""
    checking_id = record.accounts[0].account_id
    daily_flow: dict = {}
    for e in record.historical_events():
        if e.account_id != checking_id or e.known:
            continue
        day = e.occurrence_time.date()
        signed = e.amount_cents if e.direction == "inflow" else -e.amount_cents
        daily_flow[day] = daily_flow.get(day, 0) + signed

    history_days = (record.as_of.date() - record.history_start.date()).days
    all_days = [record.history_start.date().fromordinal(record.history_start.date().toordinal() + i) for i in range(history_days)]
    flows = np.array([daily_flow.get(d, 0) for d in all_days], dtype=np.float64)
    return float(np.median(flows)) if len(flows) else 0.0


def predict_daily_balance(record: HouseholdRecord, known_daily_balance_cents: list[int]) -> list[float]:
    median_flow = predict_uncertain_daily_net_flow(record)
    horizon_days = len(known_daily_balance_cents)
    cumulative = np.cumsum(np.full(horizon_days, median_flow))
    return [known_daily_balance_cents[i] + cumulative[i] for i in range(horizon_days)]
