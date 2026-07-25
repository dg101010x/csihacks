from __future__ import annotations

import hashlib
from typing import Optional

from relief_contracts.shared import ObligationV1
from relief_recurring_detection import RecurringPattern

from .essentiality import classify_essentiality


def _stable_obligation_id(household_id: str, account_id: str, label: str) -> str:
    digest = hashlib.sha1(f"{household_id}:{account_id}:{label.lower()}".encode()).hexdigest()[:10]
    return f"obl_{digest}"


def pattern_to_obligation(
    household_id: str,
    pattern: RecurringPattern,
    *,
    existing: Optional[ObligationV1] = None,
) -> ObligationV1:
    """Turns one detected RecurringPattern into an ObligationV1. If `existing`
    is passed (a previously stored obligation matching this pattern), its
    consumer-confirmed fields (consumer_confirmed, status, obligation_type
    override) are preserved rather than overwritten by re-detection — a
    consumer's confirmation must never be silently reverted by the detector.
    """
    obligation_type, essentiality = classify_essentiality(pattern.merchant_category, pattern.event_type)
    obligation_id = existing.obligation_id if existing else _stable_obligation_id(
        household_id, pattern.account_id, pattern.display_key
    )

    return ObligationV1(
        obligation_id=obligation_id,
        provider_id=existing.provider_id if existing else None,
        obligation_type=existing.obligation_type if existing else obligation_type,
        display_name=existing.display_name if existing else pattern.display_key,
        principal_balance_cents=existing.principal_balance_cents if existing else None,
        scheduled_amount_cents=pattern.average_amount_cents,
        next_due_at=pattern.next_predicted_at,
        recurrence_rule=pattern.recurrence_rule,
        essentiality_score=existing.essentiality_score if existing else essentiality,
        status=existing.status if existing else "active",
        source_confidence=pattern.confidence,
        consumer_confirmed=existing.consumer_confirmed if existing else False,
    )


def detect_obligations(
    household_id: str,
    patterns: list[RecurringPattern],
    *,
    existing_obligations: Optional[list[ObligationV1]] = None,
) -> list[ObligationV1]:
    by_id = {o.obligation_id: o for o in (existing_obligations or [])}
    obligations = []
    for pattern in patterns:
        if pattern.recurrence_rule is None:
            continue  # irregular timing isn't a confirmable recurring obligation yet
        candidate_id = _stable_obligation_id(household_id, pattern.account_id, pattern.display_key)
        obligations.append(pattern_to_obligation(household_id, pattern, existing=by_id.get(candidate_id)))
    return obligations
