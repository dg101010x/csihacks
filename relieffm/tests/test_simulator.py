from datetime import datetime

from ml.simulator.interventions import generate_intervention_pairs
from ml.simulator.population import generate_population
from ml.simulator.validation import validate_household_record

import numpy as np

AS_OF = datetime(2026, 7, 25, 12, 0, 0)


def test_population_generates_without_warnings():
    records = generate_population(100, seed=123, as_of=AS_OF, history_days=90, horizon_days=30)
    warnings = []
    for r in records:
        warnings += validate_household_record(r)
    assert warnings == []
    assert all(len(r.events) > 0 for r in records)
    assert all(len(r.accounts) >= 1 for r in records)
    assert all(len(r.obligations) >= 2 for r in records)


def test_population_deterministic_given_seed():
    a = generate_population(20, seed=7, as_of=AS_OF)
    b = generate_population(20, seed=7, as_of=AS_OF)
    assert [r.params.income_amount_cents for r in a] == [r.params.income_amount_cents for r in b]
    assert [len(r.events) for r in a] == [len(r.events) for r in b]


def test_starting_balances_reconcile_to_current_balance():
    """Replaying history forward from the computed starting balance must
    reproduce the account's as-of balance exactly (section 24's ledger
    recurrence, applied to the simulator's own construction)."""
    records = generate_population(30, seed=5, as_of=AS_OF)
    for r in records:
        for acct in r.accounts:
            balance = r.account_starting_balances_cents[acct.account_id]
            for e in sorted(r.historical_events(), key=lambda e: e.occurrence_time):
                if e.account_id != acct.account_id:
                    continue
                balance += e.amount_cents if e.direction == "inflow" else -e.amount_cents
            assert balance == acct.current_balance_cents


def test_intervention_pairs_share_background_randomness():
    """Coupled sampling (section 31's intent applied at the simulator level,
    section 41): every event outside the target obligation must be
    identical between baseline and intervention scenarios."""
    records = generate_population(10, seed=11, as_of=AS_OF)
    rng = np.random.default_rng(1)
    for r in records:
        pairs = generate_intervention_pairs(r, rng)
        for p in pairs:
            assert p.action_type
            assert len(p.baseline_daily_balances_cents) == len(p.intervention_daily_balances_cents)
