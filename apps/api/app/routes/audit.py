from __future__ import annotations

from fastapi import APIRouter, Depends
from relief_audit.store import SqlAuditStore
from sqlalchemy.orm import Session

from ..dependencies import get_request_id
from ..db import get_db
from ..envelope import envelope

router = APIRouter(prefix="/v1/audit", tags=["audit"])


@router.get("")
def get_recent_audit_events(
    session: Session = Depends(get_db),
    request_id: str = Depends(get_request_id),
):
    events = SqlAuditStore(session).list_recent()
    return envelope(request_id, [event.model_dump(mode="json") for event in events])


@router.get("/{decision_id}")
def get_audit_trail(
    decision_id: str,
    session: Session = Depends(get_db),
    request_id: str = Depends(get_request_id),
):
    store = SqlAuditStore(session)
    events = store.list_for_decision(decision_id)
    return envelope(request_id, [e.model_dump(mode="json") for e in events])
