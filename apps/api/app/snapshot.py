from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from relief_contracts import HouseholdSnapshotV1
from relief_ledger import SqlLedgerStore
from relief_obligations.store import SqlObligationStore
from sqlalchemy.orm import Session

from . import demo_state
from .seed import get_consumer_constitution, get_seeded_accounts, get_seeded_provider_capabilities


def assemble_household_snapshot(
    session: Session, household_id: str, *, as_of: Optional[datetime] = None
) -> HouseholdSnapshotV1:
    """Section 10: the one self-contained input every forecast provider (and
    everything downstream of a forecast — resilience, elasticity,
    interventions) reads. Built fresh from the ledger/obligation stores on
    every call rather than cached, so a shock/reset toggle is reflected
    immediately without any invalidation logic."""
    as_of = as_of or datetime.now(timezone.utc)

    ledger = SqlLedgerStore(session)
    obligations = SqlObligationStore(session)

    snapshot = HouseholdSnapshotV1(
        contract_version="1.0.0",
        snapshot_id=f"snap_{uuid.uuid4().hex[:12]}",
        household_id=household_id,
        generated_at=as_of,
        timezone="America/Los_Angeles",
        currency="USD",
        accounts=get_seeded_accounts(household_id),
        obligations=obligations.list_for_household(household_id),
        recent_events=ledger.recent_events(household_id, as_of),
        known_future_events=ledger.known_future_events(household_id, as_of),
        consumer_constitution=get_consumer_constitution(household_id),
        provider_capabilities=get_seeded_provider_capabilities(household_id),
    )
    return demo_state.apply_scenario(snapshot, household_id)
