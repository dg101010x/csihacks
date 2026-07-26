from __future__ import annotations

from fastapi import APIRouter, Depends
from relief_workflow_worker.store import PackageStateRow, ProviderCaseRow
from sqlalchemy.orm import Session

from .. import demo_state
from ..dependencies import get_household_id, get_request_id
from ..db import get_db
from ..envelope import envelope
from ..snapshot import assemble_household_snapshot
from .interventions import clear_household_packages

router = APIRouter(prefix="/v1/demo", tags=["demo"])


@router.post("/shock")
def trigger_shock(
    session: Session = Depends(get_db),
    household_id: str = Depends(get_household_id),
    request_id: str = Depends(get_request_id),
):
    """Section 16.3's shock simulator — demo-only, not part of the
    production API surface. Reduces the next paycheck the same way
    sarah_income_shock.json's trigger_event does; everything downstream
    (forecast, resilience, interventions) recomputes for real against it."""
    demo_state.trigger_shock(household_id)
    snapshot = assemble_household_snapshot(session, household_id)
    return envelope(request_id, snapshot.model_dump(mode="json"))


@router.post("/reset")
def reset_demo(
    session: Session = Depends(get_db),
    household_id: str = Depends(get_household_id),
    request_id: str = Depends(get_request_id),
):
    demo_state.reset_demo(household_id)

    # Intervention package IDs are re-derived deterministically from the
    # live snapshot, so a repeat /generate call reuses the same IDs the
    # previous test/demo run already advanced through the approval
    # workflow. Without clearing the persisted state here, the next
    # approve() call 409s on an invalid stage transition (single-household
    # demo, so a full clear is correct — see clear_household_packages).
    clear_household_packages(household_id)
    session.query(PackageStateRow).delete()
    session.query(ProviderCaseRow).delete()
    session.commit()

    snapshot = assemble_household_snapshot(session, household_id)
    return envelope(request_id, snapshot.model_dump(mode="json"))
