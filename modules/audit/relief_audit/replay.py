from __future__ import annotations

from .hashing import compute_payload_hash
from .models import ReplayResult
from .store import AuditStore


def replay_decision(store: AuditStore, decision_id: str) -> ReplayResult:
    """Section 17: reconstructs a decision's full event timeline and
    verifies integrity by recomputing each event's payload_hash from its own
    before/after state. A mismatch means that row's state was altered after
    it was written — the hash is derived from the state, not stored
    independently of it, so there's no way to edit one without the other
    going out of sync."""
    events = store.list_for_decision(decision_id)
    for event in events:
        expected = compute_payload_hash(event.before_state, event.after_state)
        if expected != event.payload_hash:
            return ReplayResult(decision_id=decision_id, events=events, verified=False, broken_at_event_id=event.event_id)
    return ReplayResult(decision_id=decision_id, events=events, verified=True, broken_at_event_id=None)
