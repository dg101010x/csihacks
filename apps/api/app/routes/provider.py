from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from relief_audit import ActorType, record_event
from relief_audit.store import SqlAuditStore
from relief_workflow_worker import InvalidTransitionError
from relief_workflow_worker.store import SqlWorkflowStore
from relief_workflow_worker.workflow import execute as workflow_execute
from relief_workflow_worker.workflow import provider_approve as workflow_provider_approve
from sqlalchemy.orm import Session

from ..dependencies import get_household_id, get_request_id
from ..db import get_db
from ..envelope import envelope
from .interventions import _case_to_package

router = APIRouter(prefix="/v1/provider/cases", tags=["provider"])


@router.post("/{case_id}/approve")
def approve_provider_case(
    case_id: str,
    session: Session = Depends(get_db),
    household_id: str = Depends(get_household_id),
    request_id: str = Depends(get_request_id),
):
    """Matches the frontend's 'simulate provider response' action: provider
    approval and execution happen together here (Section 84's
    execution_mode defaults to `simulated`), so the consumer sees the
    package move straight to executed rather than a separate manual step."""
    workflow_store = SqlWorkflowStore(session)
    audit_store = SqlAuditStore(session)

    case = workflow_store.get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Provider case not found")

    package_id = _case_to_package.get(case_id)
    state = workflow_store.get_package_state(package_id) if package_id else None
    if state is None:
        raise HTTPException(status_code=404, detail="No package is linked to this provider case")

    before_stage = state.stage.value
    try:
        state, case = workflow_provider_approve(state, case)
        state = workflow_execute(state)
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    workflow_store.upsert_package_state(state)
    workflow_store.upsert_case(case)

    record_event(
        audit_store,
        decision_id=package_id,
        event_type="provider_case_approved",
        actor_type=ActorType.provider,
        actor_id=case.provider_id,
        request_id=request_id,
        summary=f"Provider {case.provider_id} approved case {case_id}.",
        reason="Provider approval simulated for this demonstration.",
        evidence=[case.action_id],
        before_state=before_stage,
        after_state=state.stage.value,
    )
    session.commit()

    return envelope(request_id, {"case_id": case_id, "stage": state.stage.value})
