from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from .hashing import compute_payload_hash
from .models import ActorType, AuditEventV1
from .store import AuditStore


def record_event(
    store: AuditStore,
    *,
    decision_id: str,
    event_type: str,
    actor_type: ActorType,
    actor_id: str,
    request_id: str,
    summary: str,
    reason: str,
    evidence: list[str] = (),
    before_state: Optional[str] = None,
    after_state: Optional[str] = None,
    related_model_version: Optional[str] = None,
    related_data_sources: list[str] = (),
    related_constitution_rule_id: Optional[str] = None,
    occurred_at: Optional[datetime] = None,
) -> AuditEventV1:
    """Every module that mutates state (workflow transitions, constitution
    rule activation, obligation confirmation) calls this rather than writing
    to the audit table directly, so payload_hash is never forgotten or
    computed inconsistently."""
    event = AuditEventV1(
        event_id=f"audit_{uuid.uuid4().hex[:12]}",
        decision_id=decision_id,
        event_type=event_type,
        actor_type=actor_type,
        actor_id=actor_id,
        request_id=request_id,
        occurred_at=occurred_at or datetime.now(timezone.utc),
        payload_hash=compute_payload_hash(before_state, after_state),
        summary=summary,
        reason=reason,
        evidence=list(evidence),
        before_state=before_state,
        after_state=after_state,
        related_model_version=related_model_version,
        related_data_sources=list(related_data_sources),
        related_constitution_rule_id=related_constitution_rule_id,
    )
    return store.append(event)
