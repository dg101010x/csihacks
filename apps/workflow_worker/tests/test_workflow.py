from __future__ import annotations

import json
from pathlib import Path

import pytest
from relief_contracts import HouseholdSnapshotV1
from relief_interventions import generate_intervention_packages
from relief_workflow_worker import (
    InMemoryWorkflowStore,
    InvalidTransitionError,
    PackageStage,
    confirm,
    execute,
    provider_approve,
    provider_reject,
    start,
    submit,
)

SHOCK_PATH = (
    Path(__file__).resolve().parents[3] / "packages" / "test_fixtures" / "fixtures" / "sarah_income_shock.json"
)


@pytest.fixture
def snapshot() -> HouseholdSnapshotV1:
    return HouseholdSnapshotV1(**json.loads(SHOCK_PATH.read_text())["household_snapshot"])


@pytest.fixture
def packages(snapshot):
    return generate_intervention_packages(snapshot, horizon_days=14)


def test_cannot_skip_straight_to_submitted():
    state = start("int_1")
    with pytest.raises(InvalidTransitionError):
        submit(state, package=None)  # still in review, must confirm first


def test_package_with_provider_action_opens_a_case(snapshot, packages):
    with_provider = next((p for p in packages if any(a.provider_capability_id for a in p.actions)), None)
    if with_provider is None:
        pytest.skip("no provider-requiring package generated for this fixture")

    state = confirm(start(with_provider.package_id))
    new_state, case = submit(state, with_provider, snapshot.provider_capabilities)

    assert new_state.stage == PackageStage.pending_provider
    assert case is not None
    assert case.status.value == "pending_review"
    assert new_state.case_id == case.case_id


def test_package_with_no_provider_action_clears_straight_to_accepted(snapshot, packages):
    consumer_only = next((p for p in packages if all(a.provider_capability_id is None for a in p.actions)), None)
    if consumer_only is None:
        pytest.skip("every generated package needed provider approval")

    state = confirm(start(consumer_only.package_id))
    new_state, case = submit(state, consumer_only)
    assert new_state.stage == PackageStage.accepted
    assert case is None


def test_provider_approval_moves_to_accepted_then_executed(snapshot, packages):
    with_provider = next((p for p in packages if any(a.provider_capability_id for a in p.actions)), None)
    if with_provider is None:
        pytest.skip("no provider-requiring package generated for this fixture")

    state = confirm(start(with_provider.package_id))
    state, case = submit(state, with_provider, snapshot.provider_capabilities)
    state, case = provider_approve(state, case)
    assert state.stage == PackageStage.accepted
    assert case.status.value == "approved"

    executed = execute(state)
    assert executed.stage == PackageStage.executed
    with pytest.raises(InvalidTransitionError):
        execute(executed)  # terminal, cannot execute twice


def test_provider_rejection_is_terminal(snapshot, packages):
    with_provider = next((p for p in packages if any(a.provider_capability_id for a in p.actions)), None)
    if with_provider is None:
        pytest.skip("no provider-requiring package generated for this fixture")

    state = confirm(start(with_provider.package_id))
    state, case = submit(state, with_provider, snapshot.provider_capabilities)
    state, case = provider_reject(state, case)
    assert state.stage == PackageStage.rejected
    assert case.status.value == "rejected"
    with pytest.raises(InvalidTransitionError):
        execute(state)


def test_store_round_trips_package_and_case_state(snapshot, packages):
    with_provider = next((p for p in packages if any(a.provider_capability_id for a in p.actions)), None)
    if with_provider is None:
        pytest.skip("no provider-requiring package generated for this fixture")

    store = InMemoryWorkflowStore()
    state = confirm(start(with_provider.package_id))
    state, case = submit(state, with_provider, snapshot.provider_capabilities)
    store.upsert_package_state(state)
    store.upsert_case(case)

    assert store.get_package_state(with_provider.package_id).stage == PackageStage.pending_provider
    assert store.get_case(case.case_id).status.value == "pending_review"
