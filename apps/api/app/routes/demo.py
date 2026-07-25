from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import demo_state
from ..dependencies import get_household_id, get_request_id
from ..db import get_db
from ..envelope import envelope
from ..snapshot import assemble_household_snapshot

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
    snapshot = assemble_household_snapshot(session, household_id)
    return envelope(request_id, snapshot.model_dump(mode="json"))
