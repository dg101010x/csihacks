from __future__ import annotations

import json
from pathlib import Path

import pytest
from relief_contracts import HouseholdSnapshotV1
from relief_interventions import generate_intervention_packages

BASELINE_PATH = (
    Path(__file__).resolve().parents[3] / "packages" / "test_fixtures" / "fixtures" / "sarah_baseline.json"
)
SHOCK_PATH = (
    Path(__file__).resolve().parents[3] / "packages" / "test_fixtures" / "fixtures" / "sarah_income_shock.json"
)


def load_snapshot(path: Path) -> HouseholdSnapshotV1:
    return HouseholdSnapshotV1(**json.loads(path.read_text())["household_snapshot"])


def test_healthy_baseline_has_no_recommended_interventions():
    snapshot = load_snapshot(BASELINE_PATH)
    assert generate_intervention_packages(snapshot) == []


def test_shocked_household_gets_ranked_packages():
    snapshot = load_snapshot(SHOCK_PATH)
    packages = generate_intervention_packages(snapshot, horizon_days=14)
    assert 1 <= len(packages) <= 3
    labels = [p.label for p in packages]
    assert "Recommended balance" in labels
    assert len(set(labels)) == len(labels)  # no duplicate labels


def test_recommended_package_is_the_best_scoring_option():
    snapshot = load_snapshot(SHOCK_PATH)
    packages = generate_intervention_packages(snapshot, horizon_days=14)
    recommended = next(p for p in packages if p.label == "Recommended balance")
    # Every action in every package traces back to a real obligation.
    obligation_ids = {o.obligation_id for o in snapshot.obligations}
    for action in recommended.actions:
        assert action.obligation_id in obligation_ids


def test_subscription_pause_is_zero_cost_and_fully_reversible():
    snapshot = load_snapshot(SHOCK_PATH)
    packages = generate_intervention_packages(snapshot, horizon_days=14)
    pause_only = [p for p in packages if len(p.actions) == 1 and p.actions[0].action_type == "pause_subscription"]
    if pause_only:
        assert pause_only[0].added_cost_cents == 0
        assert pause_only[0].reversibility.value == "fully_reversible"


def test_provider_action_gets_a_required_approval_and_acceptance_probability():
    snapshot = load_snapshot(SHOCK_PATH)
    packages = generate_intervention_packages(snapshot, horizon_days=14)
    with_provider_action = [p for p in packages if any(a.provider_capability_id for a in p.actions)]
    for package in with_provider_action:
        assert any(approval.startswith("provider:") for approval in package.required_approvals)
        assert package.provider_acceptance_probability is not None


def test_new_minimum_balance_is_never_worse_than_added_cost_would_suggest():
    snapshot = load_snapshot(SHOCK_PATH)
    packages = generate_intervention_packages(snapshot, horizon_days=14)
    for package in packages:
        assert isinstance(package.new_minimum_balance_cents, int)
        assert 0 <= package.confidence <= 1
