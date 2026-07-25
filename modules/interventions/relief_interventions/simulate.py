from __future__ import annotations

from datetime import date, timedelta

from relief_contracts import ForecastResponseV1, HouseholdSnapshotV1
from relief_deterministic_forecast import generate_forecast

from .models import InterventionActionV1


def _apply_action(snapshot: HouseholdSnapshotV1, action: InterventionActionV1) -> HouseholdSnapshotV1:
    """Approximates one action's cash-flow effect by editing the target
    obligation, then lets the forecast engine's own projection regenerate
    events from it — this is a ranking-time simulation, not the real
    executor (that's apps/workflow_worker's job once a package is approved).
    """
    obligations = []
    for obligation in snapshot.obligations:
        if obligation.obligation_id != action.obligation_id:
            obligations.append(obligation)
            continue

        if action.action_type == "split_payment":
            # This cycle's due amount drops to the first installment; the
            # second installment isn't separately modeled at ranking time.
            obligations.append(
                obligation.model_copy(update={"scheduled_amount_cents": action.parameters["first_payment_cents"]})
            )
        elif action.action_type == "delay_payment":
            delayed_date = date.fromisoformat(action.parameters["delayed_to"])
            delayed_to = obligation.next_due_at + timedelta(days=(delayed_date - obligation.next_due_at.date()).days)
            obligations.append(obligation.model_copy(update={"next_due_at": delayed_to}))
        elif action.action_type in ("pause_subscription", "cancel_subscription"):
            obligations.append(obligation.model_copy(update={"status": "paused"}))
        else:
            # hardship_request and any other draft-only/no-cash-flow-effect
            # action type: no change to the obligation.
            obligations.append(obligation)

    return snapshot.model_copy(update={"obligations": obligations})


def simulate_package(
    snapshot: HouseholdSnapshotV1, actions: list[InterventionActionV1], *, horizon_days: int
) -> ForecastResponseV1:
    modified = snapshot
    for action in actions:
        modified = _apply_action(modified, action)
    return generate_forecast(modified, horizon_days=horizon_days, as_of=snapshot.generated_at)
