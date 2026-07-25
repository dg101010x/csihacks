from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from relief_consumer_constitution import ConstitutionRuleV1
from relief_consumer_constitution.store import SqlConstitutionRuleStore
from relief_contracts.shared import AccountV1, ConsumerConstitutionV1, ProviderCapabilityV1
from relief_integrations import SyntheticWellsFargoAdapter
from relief_ledger import SqlLedgerStore
from relief_obligations.store import SqlObligationStore
from sqlalchemy.orm import Session

from .dependencies import DEMO_HOUSEHOLD_ID

_FIXTURES_DIR = Path(__file__).resolve().parents[3] / "packages" / "test_fixtures" / "fixtures"
_BASELINE_PATH = _FIXTURES_DIR / "sarah_baseline.json"
_CONSTITUTION_PATH = _FIXTURES_DIR / "sarah_constitution.json"
_PROVIDER_STATUS_PATH = _FIXTURES_DIR / "sarah_provider_status.json"
_DATA_TRUST_PATH = _FIXTURES_DIR / "sarah_data_trust.json"

_EPOCH = datetime(2000, 1, 1, tzinfo=timezone.utc)

# accounts, provider_capabilities, and consumer_constitution have no owning
# module yet — modules/accounts and modules/provider_policies are still
# `.gitkeep` placeholders per the README's build order — so these live here
# as the honest, undisguised stand-in until those modules exist. Every
# route reaches them only through the getters below, so swapping in a real
# store later touches this file alone.
_accounts_by_household: dict[str, list[AccountV1]] = {}
_capabilities_by_household: dict[str, list[ProviderCapabilityV1]] = {}
_constitution_by_household: dict[str, ConsumerConstitutionV1] = {}


def seed_demo_household(session: Session) -> None:
    """Loads the Sarah persona fixture into the real, SQL-backed stores so
    apps/api serves consistent data through actual business logic instead
    of MSW/fixture playback. Idempotent — the ledger dedupes on (source,
    source_event_id, account_id); obligations and constitution rules
    upsert by id."""
    adapter = SyntheticWellsFargoAdapter(_BASELINE_PATH)
    raw_snapshot = json.loads(_BASELINE_PATH.read_text())["household_snapshot"]

    ledger = SqlLedgerStore(session)
    for event in adapter.list_events(DEMO_HOUSEHOLD_ID, since=_EPOCH):
        ledger.append(event)

    obligations = SqlObligationStore(session)
    for obligation in raw_snapshot["obligations"]:
        from relief_contracts.shared import ObligationV1

        obligations.upsert(ObligationV1(**obligation), household_id=DEMO_HOUSEHOLD_ID)

    constitution = SqlConstitutionRuleStore(session)
    constitution_data = json.loads(_CONSTITUTION_PATH.read_text())
    for rule in [*constitution_data["rules"], *constitution_data["starter_rules"]]:
        constitution.upsert(DEMO_HOUSEHOLD_ID, ConstitutionRuleV1(**rule))

    _accounts_by_household[DEMO_HOUSEHOLD_ID] = adapter.list_accounts(DEMO_HOUSEHOLD_ID)
    _capabilities_by_household[DEMO_HOUSEHOLD_ID] = [
        ProviderCapabilityV1(**c) for c in raw_snapshot["provider_capabilities"]
    ]
    _constitution_by_household[DEMO_HOUSEHOLD_ID] = ConsumerConstitutionV1(**raw_snapshot["consumer_constitution"])

    session.commit()


def get_seeded_accounts(household_id: str) -> list[AccountV1]:
    return _accounts_by_household.get(household_id, [])


def get_seeded_provider_capabilities(household_id: str) -> list[ProviderCapabilityV1]:
    return _capabilities_by_household.get(household_id, [])


def get_consumer_constitution(household_id: str) -> ConsumerConstitutionV1:
    return _constitution_by_household.get(
        household_id,
        ConsumerConstitutionV1(
            version=0, protected_categories=[], allow_term_extension=True,
            maximum_added_interest_cents=0, require_confirmation_for_subscriptions=False,
        ),
    )


def get_provider_status_fixture() -> list[dict]:
    return json.loads(_PROVIDER_STATUS_PATH.read_text())["providers"]


def get_data_trust_fixture() -> list[dict]:
    return json.loads(_DATA_TRUST_PATH.read_text())["sources"]
