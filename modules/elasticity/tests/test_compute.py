from __future__ import annotations

import json
from pathlib import Path

import pytest
from relief_contracts import HouseholdSnapshotV1
from relief_elasticity import compute_elasticity_for_household

FIXTURE_PATH = (
    Path(__file__).resolve().parents[3] / "packages" / "test_fixtures" / "fixtures" / "sarah_baseline.json"
)


@pytest.fixture
def sarah_snapshot() -> HouseholdSnapshotV1:
    data = json.loads(FIXTURE_PATH.read_text())["household_snapshot"]
    return HouseholdSnapshotV1(**data)


def by_id(elasticities, obligation_id):
    return next(e for e in elasticities if e.obligation_id == obligation_id)


def test_subscription_is_fully_flexible_and_reversible(sarah_snapshot):
    elasticities = compute_elasticity_for_household(sarah_snapshot.obligations, sarah_snapshot.provider_capabilities)
    streaming = by_id(elasticities, "obl_streaming_01")
    assert streaming.amount_flexibility_ratio == 1.0
    assert streaming.reversibility.value == "fully_reversible"
    assert "pause_subscription" in streaming.available_actions
    assert "cancel_subscription" in streaming.available_actions


def test_rent_is_inflexible_and_irreversible(sarah_snapshot):
    elasticities = compute_elasticity_for_household(sarah_snapshot.obligations, sarah_snapshot.provider_capabilities)
    rent = by_id(elasticities, "obl_rent_01")
    assert rent.amount_flexibility_ratio == 0.0
    assert rent.reversibility.value == "irreversible"
    assert rent.delay_tolerance_days <= 3


def test_provider_capability_gates_provider_side_actions(sarah_snapshot):
    elasticities = compute_elasticity_for_household(sarah_snapshot.obligations, sarah_snapshot.provider_capabilities)

    auto_loan = by_id(elasticities, "obl_car_01")
    assert "split_payment" in auto_loan.available_actions  # matching ProviderCapabilityV1 exists
    assert "delay_payment" not in auto_loan.available_actions  # no capability for that action_type

    rent = by_id(elasticities, "obl_rent_01")
    assert rent.available_actions == []  # no ProviderCapabilityV1 at all for prov_meridian_realty

    credit_card = by_id(elasticities, "obl_card_01")
    assert credit_card.available_actions == []


def test_unconfirmed_obligation_has_lower_confidence(sarah_snapshot):
    unconfirmed = sarah_snapshot.obligations[0].model_copy(update={"consumer_confirmed": False})
    confirmed = sarah_snapshot.obligations[0]
    elasticities = compute_elasticity_for_household([unconfirmed, confirmed], sarah_snapshot.provider_capabilities)
    assert elasticities[0].confidence < elasticities[1].confidence


def test_closed_obligations_are_excluded(sarah_snapshot):
    closed = sarah_snapshot.obligations[0].model_copy(update={"status": "closed"})
    elasticities = compute_elasticity_for_household([closed], sarah_snapshot.provider_capabilities)
    assert elasticities == []
