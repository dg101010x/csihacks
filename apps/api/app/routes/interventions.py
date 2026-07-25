from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from relief_audit import ActorType, record_event
from relief_audit.store import SqlAuditStore
from relief_interventions import InterventionCandidateV1, generate_intervention_packages
from relief_workflow_worker import InvalidTransitionError, PackageStage
from relief_workflow_worker.store import SqlWorkflowStore
from relief_workflow_worker.workflow import confirm as workflow_confirm
from relief_workflow_worker.workflow import submit as workflow_submit
from sqlalchemy.orm import Session

from ..dependencies import get_household_id, get_request_id
from ..db import get_db
from ..envelope import envelope
from ..seed import get_seeded_provider_capabilities
from ..snapshot import assemble_household_snapshot

router = APIRouter(prefix="/v1/interventions", tags=["interventions"])

# No dedicated intervention_cases persistence yet — packages are re-derived
# from the live snapshot on every /generate call, matching the same
# pragmatic in-process pattern as apps/api/app/seed.py's accounts/
# capabilities. _case_to_package lets the provider-case route find its way
# back to the originating package without a reverse-index table.
_packages_by_household: dict[str, dict[str, InterventionCandidateV1]] = {}
_case_to_package: dict[str, str] = {}


@router.post("/generate")
def generate_interventions(
    session: Session = Depends(get_db),
    household_id: str = Depends(get_household_id),
    request_id: str = Depends(get_request_id),
):
    snapshot = assemble_household_snapshot(session, household_id)
    packages = generate_intervention_packages(snapshot, horizon_days=30)
    _packages_by_household[household_id] = {p.package_id: p for p in packages}
    return envelope(request_id, [p.model_dump(mode="json") for p in packages])


def _get_package(household_id: str, package_id: str) -> InterventionCandidateV1:
    package = _packages_by_household.get(household_id, {}).get(package_id)
    if package is None:
        raise HTTPException(status_code=404, detail="Intervention package not found — call /generate first.")
    return package


@router.post("/{intervention_id}/approve")
def approve_intervention(
    intervention_id: str,
    session: Session = Depends(get_db),
    household_id: str = Depends(get_household_id),
    request_id: str = Depends(get_request_id),
):
    """Collapses review -> confirmed -> submitted into one call, matching
    the frontend's single 'approve' action rather than exposing the staged
    state machine as separate clicks."""
    package = _get_package(household_id, intervention_id)
    workflow_store = SqlWorkflowStore(session)
    audit_store = SqlAuditStore(session)

    state = workflow_store.get_package_state(intervention_id)
    before_stage = state.stage.value if state else PackageStage.review.value
    if state is None:
        from relief_workflow_worker.workflow import start

        state = start(intervention_id)

    try:
        if state.stage == PackageStage.review:
            state = workflow_confirm(state)
        state, case = workflow_submit(state, package, get_seeded_provider_capabilities(household_id))
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    workflow_store.upsert_package_state(state)
    if case is not None:
        workflow_store.upsert_case(case)
        _case_to_package[case.case_id] = intervention_id

    record_event(
        audit_store,
        decision_id=intervention_id,
        event_type="intervention_submitted",
        actor_type=ActorType.consumer,
        actor_id=household_id,
        request_id=request_id,
        summary=f"Consumer submitted package '{package.label}' for approval.",
        reason="Consumer approved the recommended intervention package.",
        evidence=[a.action_id for a in package.actions],
        before_state=before_stage,
        after_state=state.stage.value,
    )
    session.commit()

    return envelope(request_id, {"provider_case": case.model_dump(mode="json") if case else None})
