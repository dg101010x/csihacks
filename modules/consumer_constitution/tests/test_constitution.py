from __future__ import annotations

import json
from pathlib import Path

import pytest
from relief_consumer_constitution import (
    InMemoryConstitutionRuleStore,
    SqlConstitutionRuleStore,
    parse_constitution_rule,
    simulate_constitution_rule,
)
from relief_consumer_constitution.store import Base
from relief_contracts import HouseholdSnapshotV1
from relief_interventions import generate_intervention_packages
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

SHOCK_PATH = (
    Path(__file__).resolve().parents[3] / "packages" / "test_fixtures" / "fixtures" / "sarah_income_shock.json"
)


def test_parse_extracts_scope_and_permitted_actions():
    rule = parse_constitution_rule("Please split payments and pause subscriptions for medical expenses.")
    assert "medicine" in rule.scope
    assert "split_payment" in rule.permitted_actions
    assert "pause_subscription" in rule.permitted_actions
    assert rule.confidence > 0.6


def test_parse_extracts_prohibited_actions_and_amount():
    rule = parse_constitution_rule("Never delay rent, and never add interest above $50.")
    assert "delay_rent_without_confirmation" in rule.prohibited_actions
    assert "term_extension_with_interest" in rule.prohibited_actions
    assert rule.maximum_monetary_impact_cents == 5000


def test_parse_defaults_to_always_ask_when_confirm_requested():
    rule = parse_constitution_rule("Always ask me before touching my credit card.")
    assert rule.approval_requirement.value == "always_ask"


def test_parse_with_no_recognizable_scope_defaults_to_all():
    rule = parse_constitution_rule("do whatever makes sense")
    assert rule.scope == ["all"]
    assert rule.trigger == "Any candidate intervention."


def test_simulate_blocks_packages_touching_prohibited_actions():
    snapshot = HouseholdSnapshotV1(**json.loads(SHOCK_PATH.read_text())["household_snapshot"])
    packages = generate_intervention_packages(snapshot, horizon_days=14)
    rule = parse_constitution_rule("Never split my auto loan payment.")
    rule = rule.model_copy(update={"prohibited_actions": ["split_payment"]})

    result = simulate_constitution_rule(rule, packages)
    blocked_action_types = {
        a.action_type for pkg in packages if pkg.package_id in result.blocked_package_ids for a in pkg.actions
    }
    if any("split_payment" in {a.action_type for a in p.actions} for p in packages):
        assert "split_payment" in blocked_action_types


def test_simulate_detects_conflict_with_existing_rule():
    rule_a = parse_constitution_rule("split payments are fine").model_copy(
        update={"rule_id": "rule_a", "permitted_actions": ["split_payment"], "prohibited_actions": []}
    )
    rule_b = parse_constitution_rule("never split payments").model_copy(
        update={"rule_id": "rule_b", "permitted_actions": [], "prohibited_actions": ["split_payment"]}
    )
    result = simulate_constitution_rule(rule_a, packages=[], existing_rules=[rule_b])
    assert len(result.conflicts) == 1
    assert result.conflicts[0].with_rule_id == "rule_b"


@pytest.mark.parametrize("backend", ["memory", "sql"])
def test_store_upsert_activate_and_list(backend):
    if backend == "memory":
        store = InMemoryConstitutionRuleStore()
    else:
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        store = SqlConstitutionRuleStore(sessionmaker(bind=engine)())

    rule = parse_constitution_rule("protect groceries")
    store.upsert("hh_01", rule)
    assert store.get(rule.rule_id).status.value == "draft"

    activated = store.activate("hh_01", rule.rule_id)
    assert activated.status.value == "active"
    assert store.get(rule.rule_id).status.value == "active"
    assert [r.rule_id for r in store.list_for_household("hh_01", status="active")] == [rule.rule_id]
    assert store.list_for_household("hh_01", status="draft") == []
