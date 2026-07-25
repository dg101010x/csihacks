from __future__ import annotations

import hashlib
from datetime import timedelta
from typing import Optional

from relief_contracts.shared import ObligationV1
from relief_elasticity import ObligationElasticityV1
from relief_recurring_detection import FREQ_PERIOD_DAYS

from .models import ApprovalStatus, ExecutionMode, InterventionActionV1, ProviderApprovalStatus

# Essentiality above which an obligation with *no* available elasticity
# action still gets a draft-only hardship inquiry — better to hand the
# consumer something to act on manually than to offer nothing for the
# obligation most likely to be causing the risk (Section 61).
_HARDSHIP_ESSENTIALITY_THRESHOLD = 0.85


def _action_id(obligation_id: str, action_type: str) -> str:
    digest = hashlib.sha1(f"{obligation_id}:{action_type}".encode()).hexdigest()[:8]
    return f"action_{action_type}_{digest}"


def _capability_id(obligation: ObligationV1, action_type: str) -> Optional[str]:
    return f"{obligation.provider_id}:{action_type}" if obligation.provider_id else None


def build_atomic_actions(
    obligation: ObligationV1, elasticity: ObligationElasticityV1
) -> list[InterventionActionV1]:
    """One candidate InterventionActionV1 per feasible action type on this
    obligation — the intervention optimizer then combines these into
    packages rather than generating packages directly, so ranking always
    operates on the same atomic units."""
    actions: list[InterventionActionV1] = []
    due = obligation.next_due_at

    if "split_payment" in elasticity.available_actions and due is not None:
        first = round(obligation.scheduled_amount_cents / 2)
        second = obligation.scheduled_amount_cents - first
        second_date = due + timedelta(days=min(10, max(1, elasticity.delay_tolerance_days)))
        actions.append(
            InterventionActionV1(
                action_id=_action_id(obligation.obligation_id, "split_payment"),
                action_type="split_payment",
                obligation_id=obligation.obligation_id,
                display_name=f"Split the {obligation.display_name} payment",
                parameters={
                    "first_payment_cents": first,
                    "second_payment_cents": second,
                    "second_payment_date": second_date.date().isoformat(),
                },
                execution_mode=ExecutionMode.simulated,
                provider_capability_id=_capability_id(obligation, "split_payment"),
                consumer_status=ApprovalStatus.pending,
                provider_status=ProviderApprovalStatus.pending,
            )
        )

    if "delay_payment" in elasticity.available_actions and due is not None:
        delayed_to = due + timedelta(days=elasticity.delay_tolerance_days)
        actions.append(
            InterventionActionV1(
                action_id=_action_id(obligation.obligation_id, "delay_payment"),
                action_type="delay_payment",
                obligation_id=obligation.obligation_id,
                display_name=f"Delay the {obligation.display_name} payment",
                parameters={"delayed_to": delayed_to.date().isoformat()},
                execution_mode=ExecutionMode.simulated,
                provider_capability_id=_capability_id(obligation, "delay_payment"),
                consumer_status=ApprovalStatus.pending,
                provider_status=ProviderApprovalStatus.pending,
            )
        )

    if "pause_subscription" in elasticity.available_actions:
        period_days = FREQ_PERIOD_DAYS.get(obligation.recurrence_rule or "", 30.0)
        resume_at = (due or obligation.next_due_at) + timedelta(days=period_days) if due else None
        actions.append(
            InterventionActionV1(
                action_id=_action_id(obligation.obligation_id, "pause_subscription"),
                action_type="pause_subscription",
                obligation_id=obligation.obligation_id,
                display_name=f"Pause {obligation.display_name} this cycle",
                parameters={"resume_at": resume_at.date().isoformat()} if resume_at else {},
                execution_mode=ExecutionMode.consumer_executable,
                provider_capability_id=None,
                consumer_status=ApprovalStatus.pending,
                provider_status=ProviderApprovalStatus.not_required,
            )
        )

    if not actions and obligation.essentiality_score >= _HARDSHIP_ESSENTIALITY_THRESHOLD:
        actions.append(
            InterventionActionV1(
                action_id=_action_id(obligation.obligation_id, "hardship_request"),
                action_type="hardship_request",
                obligation_id=obligation.obligation_id,
                display_name=f"Draft a hardship inquiry to {obligation.provider_id or 'the provider'}",
                parameters={"message_template": f"{obligation.obligation_type}_hardship_inquiry"},
                execution_mode=ExecutionMode.draft_only,
                provider_capability_id=None,
                consumer_status=ApprovalStatus.pending,
                provider_status=ProviderApprovalStatus.not_required,
            )
        )

    return actions
