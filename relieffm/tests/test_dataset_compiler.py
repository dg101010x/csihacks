from datetime import datetime

import numpy as np

from ml.datasets.compile import household_record_to_snapshot, household_record_to_targets
from ml.simulator.population import generate_household, generate_population

AS_OF = datetime(2026, 7, 25, 12, 0, 0)


def test_snapshot_is_contract_valid():
    r = generate_household("hh_test", seed=1, as_of=AS_OF)
    snapshot = household_record_to_snapshot(r)  # raises pydantic.ValidationError if invalid
    assert snapshot.household_id == "hh_test"
    assert len(snapshot.accounts) == len(r.accounts)
    assert all(e.occurrence_time <= AS_OF for e in snapshot.historical_events)
    assert all(e.effective_time > AS_OF for e in snapshot.known_future_events)


def test_known_plus_uncertain_reconstructs_full_balance_exactly():
    """The one non-negotiable invariant in the whole pipeline (section 23):
    known_daily_balance + cumulative uncertain flow must equal the actual
    ground-truth balance, every day, for every household."""
    records = generate_population(40, seed=3, as_of=AS_OF)
    for r in records:
        t = household_record_to_targets(r)
        cumulative = 0
        for d in range(t.horizon_days):
            cumulative += (
                t.uncertain_daily_inflow_cents[d]
                - t.uncertain_daily_essential_outflow_cents[d]
                - t.uncertain_daily_discretionary_outflow_cents[d]
            )
            reconstructed = t.known_daily_balance_cents[d] + cumulative
            assert reconstructed == t.daily_balance_cents[d]


def test_distress_labels_consistent_with_balances():
    records = generate_population(40, seed=4, as_of=AS_OF)
    for r in records:
        t = household_record_to_targets(r)
        for h in (7, 14, 30):
            window = t.daily_balance_cents[:h]
            assert t.distress_negative_balance[h] == any(b < 0 for b in window)
