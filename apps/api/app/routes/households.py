from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..dependencies import get_household_id, get_request_id
from ..db import get_db
from ..envelope import envelope
from ..snapshot import assemble_household_snapshot

router = APIRouter(prefix="/v1/households", tags=["households"])


@router.get("/current/snapshot")
def get_current_snapshot(
    session: Session = Depends(get_db),
    household_id: str = Depends(get_household_id),
    request_id: str = Depends(get_request_id),
):
    snapshot = assemble_household_snapshot(session, household_id)
    return envelope(request_id, snapshot.model_dump(mode="json"))
