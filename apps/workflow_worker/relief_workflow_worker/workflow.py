from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from relief_contracts.shared import ProviderCapabilityV1
from relief_interventions import InterventionCandidateV1

from .models import PackageApprovalState, PackageStage, PolicyReference, ProviderCaseStatus, ProviderCaseV1
from .transitions import validate_transition


def _record(state: PackageApprovalState, target: PackageStage) -> PackageApprovalState:
    validate_transition(state.stage, target)
    entry = f"{datetime.now(timezone.utc).isoformat()}: {state.stage.value} -> {target.value}"
    return state.model_copy(update={"stage": target, "history": [*state.history, entry]})


def start(package_id: str) -> PackageApprovalState:
    return PackageApprovalState(package_id=package_id, stage=PackageStage.review, history=[])


def confirm(state: PackageApprovalState) -> PackageApprovalState:
    """Consumer confirms they want to proceed with this package."""
    return _record(state, PackageStage.confirmed)


def _policy_reference_for(
    action_provider_capability_id: Optional[str], capabilities: list[ProviderCapabilityV1]
) -> Optional[PolicyReference]:
    if action_provider_capability_id is None:
        return None
    provider_id, action_type = action_provider_capability_id.split(":", 1)
    capability = next(
        (c for c in capabilities if c.provider_id == provider_id and c.action_type == action_type), None
    )
    if capability is None:
        return None
    return PolicyReference(
        document_id=f"{provider_id}:{capability.product_type}",
        passage_id=capability.action_type,
        effective_date=(capability.effective_from or datetime.now(timezone.utc)).date().isoformat(),
        confidence=0.75 if capability.is_simulated else 0.9,
        is_simulated=capability.is_simulated,
    )


def submit(
    state: PackageApprovalState,
    package: InterventionCandidateV1,
    provider_capabilities: list[ProviderCapabilityV1] = (),
) -> tuple[PackageApprovalState, Optional[ProviderCaseV1]]:
    """Consumer submits the confirmed package. If any action needs provider
    approval (Section 85), opens a ProviderCaseV1 and moves to
    pending_provider; otherwise the package needs no provider and clears
    straight to accepted."""
    submitted_state = _record(state, PackageStage.submitted)
    provider_action = next((a for a in package.actions if a.provider_capability_id is not None), None)

    if provider_action is None:
        return _record(submitted_state, PackageStage.accepted), None

    new_state = _record(submitted_state, PackageStage.pending_provider)
    case = ProviderCaseV1(
        case_id=f"case_{uuid.uuid4().hex[:10]}",
        provider_id=provider_action.provider_capability_id.split(":", 1)[0],
        action_id=provider_action.action_id,
        status=ProviderCaseStatus.pending_review,
        consumer_impact_summary=package.description,
        provider_impact_summary=f"Consumer requests: {provider_action.display_name}.",
        policy_reference=_policy_reference_for(provider_action.provider_capability_id, provider_capabilities),
    )
    return new_state.model_copy(update={"case_id": case.case_id}), case


def provider_approve(state: PackageApprovalState, case: ProviderCaseV1) -> tuple[PackageApprovalState, ProviderCaseV1]:
    return _record(state, PackageStage.accepted), case.model_copy(update={"status": ProviderCaseStatus.approved})


def provider_reject(state: PackageApprovalState, case: ProviderCaseV1) -> tuple[PackageApprovalState, ProviderCaseV1]:
    return _record(state, PackageStage.rejected), case.model_copy(update={"status": ProviderCaseStatus.rejected})


def execute(state: PackageApprovalState) -> PackageApprovalState:
    """The real cash-flow-affecting execution happens outside this module
    (the actual provider/bank integration) — this only records that
    execution has occurred once whatever executed it reports success."""
    return _record(state, PackageStage.executed)
