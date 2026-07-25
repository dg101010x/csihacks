from __future__ import annotations

from datetime import datetime, timezone

import pytest
from relief_audit import ActorType, InMemoryAuditStore, SqlAuditStore, record_event, replay_decision
from relief_audit.store import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture(params=["memory", "sql"])
def store(request):
    if request.param == "memory":
        return InMemoryAuditStore()
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return SqlAuditStore(sessionmaker(bind=engine)())


def test_record_event_computes_a_consistent_hash(store):
    event = record_event(
        store,
        decision_id="dec_1",
        event_type="package_confirmed",
        actor_type=ActorType.consumer,
        actor_id="hh_01",
        request_id="req_1",
        summary="Consumer confirmed the recommended package.",
        reason="User clicked confirm.",
        before_state="review",
        after_state="confirmed",
    )
    result = replay_decision(store, "dec_1")
    assert result.verified is True
    assert result.events == [event]


def test_replay_orders_events_chronologically(store):
    from datetime import datetime, timedelta, timezone

    base = datetime(2026, 7, 25, tzinfo=timezone.utc)
    record_event(
        store, decision_id="dec_2", event_type="submitted", actor_type=ActorType.consumer, actor_id="hh_01",
        request_id="req_2", summary="submitted", reason="r", before_state="confirmed", after_state="submitted",
        occurred_at=base + timedelta(minutes=5),
    )
    record_event(
        store, decision_id="dec_2", event_type="confirmed", actor_type=ActorType.consumer, actor_id="hh_01",
        request_id="req_1", summary="confirmed", reason="r", before_state="review", after_state="confirmed",
        occurred_at=base,
    )
    result = replay_decision(store, "dec_2")
    assert [e.event_type for e in result.events] == ["confirmed", "submitted"]


def test_replay_detects_tampering(store):
    event = record_event(
        store, decision_id="dec_3", event_type="approved", actor_type=ActorType.provider, actor_id="prov_1",
        request_id="req_3", summary="approved", reason="r", before_state="pending_provider", after_state="accepted",
    )
    # Simulate a row altered after the fact: the stored hash still reflects
    # the original after_state, but the state itself has been changed.
    if isinstance(store, InMemoryAuditStore):
        store._events[event.event_id] = event.model_copy(update={"after_state": "rejected"})
    else:
        from relief_audit.store import AuditEventRow

        row = store._session.get(AuditEventRow, event.event_id)
        row.after_state = "rejected"
        store._session.flush()

    result = replay_decision(store, "dec_3")
    assert result.verified is False
    assert result.broken_at_event_id == event.event_id


def test_list_recent_returns_newest_first(store):
    older = record_event(
        store,
        decision_id="dec_old",
        event_type="created",
        actor_type=ActorType.system,
        actor_id="system",
        request_id="req_old",
        summary="Older",
        reason="test",
        occurred_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    newer = record_event(
        store,
        decision_id="dec_new",
        event_type="created",
        actor_type=ActorType.system,
        actor_id="system",
        request_id="req_new",
        summary="Newer",
        reason="test",
        occurred_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )
    assert [event.event_id for event in store.list_recent(limit=1)] == [newer.event_id]
    assert older.event_id != newer.event_id


def test_list_for_decision_is_scoped_per_decision(store):
    record_event(
        store, decision_id="dec_a", event_type="x", actor_type=ActorType.system, actor_id="system",
        request_id="req_a", summary="s", reason="r",
    )
    record_event(
        store, decision_id="dec_b", event_type="y", actor_type=ActorType.system, actor_id="system",
        request_id="req_b", summary="s", reason="r",
    )
    assert len(store.list_for_decision("dec_a")) == 1
    assert len(store.list_for_decision("dec_b")) == 1
