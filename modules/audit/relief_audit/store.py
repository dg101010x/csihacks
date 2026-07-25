from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import JSON, DateTime, String, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from .models import AuditEventV1


class AuditStore(ABC):
    """Append-only (Section 32.12) — like modules/ledger, there is no update
    or delete here. Correcting a prior audit event means appending a new one
    that references it, never rewriting history."""

    @abstractmethod
    def append(self, event: AuditEventV1) -> AuditEventV1: ...

    @abstractmethod
    def list_for_decision(self, decision_id: str) -> list[AuditEventV1]: ...


class InMemoryAuditStore(AuditStore):
    def __init__(self) -> None:
        self._events: dict[str, AuditEventV1] = {}

    def append(self, event: AuditEventV1) -> AuditEventV1:
        self._events[event.event_id] = event
        return event

    def list_for_decision(self, decision_id: str) -> list[AuditEventV1]:
        matches = [e for e in self._events.values() if e.decision_id == decision_id]
        return sorted(matches, key=lambda e: e.occurred_at)


class Base(DeclarativeBase):
    pass


class AuditEventRow(Base):
    __tablename__ = "audit_events"

    event_id: Mapped[str] = mapped_column(String, primary_key=True)
    decision_id: Mapped[str] = mapped_column(String, index=True)
    event_type: Mapped[str] = mapped_column(String)
    actor_type: Mapped[str] = mapped_column(String)
    actor_id: Mapped[str] = mapped_column(String)
    request_id: Mapped[str] = mapped_column(String)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    payload_hash: Mapped[str] = mapped_column(String)
    summary: Mapped[str] = mapped_column(String)
    reason: Mapped[str] = mapped_column(String)
    evidence: Mapped[list] = mapped_column(JSON)
    before_state: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    after_state: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    related_model_version: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    related_data_sources: Mapped[list] = mapped_column(JSON)
    related_constitution_rule_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _row_to_event(row: AuditEventRow) -> AuditEventV1:
    return AuditEventV1(
        event_id=row.event_id,
        decision_id=row.decision_id,
        event_type=row.event_type,
        actor_type=row.actor_type,
        actor_id=row.actor_id,
        request_id=row.request_id,
        occurred_at=_as_utc(row.occurred_at),
        payload_hash=row.payload_hash,
        summary=row.summary,
        reason=row.reason,
        evidence=row.evidence,
        before_state=row.before_state,
        after_state=row.after_state,
        related_model_version=row.related_model_version,
        related_data_sources=row.related_data_sources,
        related_constitution_rule_id=row.related_constitution_rule_id,
    )


class SqlAuditStore(AuditStore):
    def __init__(self, session: Session) -> None:
        self._session = session

    def append(self, event: AuditEventV1) -> AuditEventV1:
        row = AuditEventRow(
            event_id=event.event_id,
            decision_id=event.decision_id,
            event_type=event.event_type,
            actor_type=event.actor_type.value,
            actor_id=event.actor_id,
            request_id=event.request_id,
            occurred_at=event.occurred_at.astimezone(timezone.utc),
            payload_hash=event.payload_hash,
            summary=event.summary,
            reason=event.reason,
            evidence=event.evidence,
            before_state=event.before_state,
            after_state=event.after_state,
            related_model_version=event.related_model_version,
            related_data_sources=event.related_data_sources,
            related_constitution_rule_id=event.related_constitution_rule_id,
        )
        self._session.add(row)
        self._session.flush()
        return event

    def list_for_decision(self, decision_id: str) -> list[AuditEventV1]:
        stmt = (
            select(AuditEventRow)
            .where(AuditEventRow.decision_id == decision_id)
            .order_by(AuditEventRow.occurred_at.asc())
        )
        return [_row_to_event(row) for row in self._session.scalars(stmt)]
