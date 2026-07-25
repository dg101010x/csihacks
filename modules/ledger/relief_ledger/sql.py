from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from relief_contracts import FinancialEventV1
from sqlalchemy import JSON, Boolean, DateTime, Index, String, UniqueConstraint, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from .errors import DuplicateEventError
from .store import LedgerStore


class Base(DeclarativeBase):
    pass


class FinancialEventRow(Base):
    """Mirrors the `financial_events` table (Section 32.5). Append-only: no
    code path in this module issues an UPDATE or DELETE against this table."""

    __tablename__ = "financial_events"
    __table_args__ = (
        UniqueConstraint("source", "source_event_id", "account_id", name="uq_financial_event_source"),
        Index("ix_financial_events_household_effective", "household_id", "effective_at"),
    )

    event_id: Mapped[str] = mapped_column(String, primary_key=True)
    contract_version: Mapped[str] = mapped_column(String)
    household_id: Mapped[str] = mapped_column(String)
    account_id: Mapped[str] = mapped_column(String)
    source: Mapped[str] = mapped_column(String)
    source_event_id: Mapped[str] = mapped_column(String)
    event_type: Mapped[str] = mapped_column(String)
    event_status: Mapped[str] = mapped_column(String)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    amount_cents: Mapped[int] = mapped_column()
    currency: Mapped[str] = mapped_column(String)
    direction: Mapped[str] = mapped_column(String)
    merchant_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    merchant_category: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    obligation_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_recurring: Mapped[bool] = mapped_column(Boolean)
    is_pending: Mapped[bool] = mapped_column(Boolean)
    event_metadata: Mapped[dict] = mapped_column(JSON)


def _as_utc(value: datetime) -> datetime:
    """SQLite's DateTime column drops tzinfo on round-trip (unlike Postgres) —
    normalize here so callers get consistent aware datetimes regardless of
    which engine apps/api is pointed at."""
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _row_to_event(row: FinancialEventRow) -> FinancialEventV1:
    return FinancialEventV1(
        contract_version=row.contract_version,
        event_id=row.event_id,
        household_id=row.household_id,
        account_id=row.account_id,
        source=row.source,
        source_event_id=row.source_event_id,
        event_type=row.event_type,
        event_status=row.event_status,
        occurred_at=_as_utc(row.occurred_at),
        effective_at=_as_utc(row.effective_at),
        amount_cents=row.amount_cents,
        currency=row.currency,
        direction=row.direction,
        merchant_name=row.merchant_name,
        merchant_category=row.merchant_category,
        obligation_id=row.obligation_id,
        is_recurring=row.is_recurring,
        is_pending=row.is_pending,
        metadata=row.event_metadata,
    )


def _event_to_row(event: FinancialEventV1) -> FinancialEventRow:
    return FinancialEventRow(
        event_id=event.event_id,
        contract_version=event.contract_version,
        household_id=event.household_id,
        account_id=event.account_id,
        source=event.source,
        source_event_id=event.source_event_id,
        event_type=event.event_type,
        event_status=event.event_status.value,
        occurred_at=event.occurred_at.astimezone(timezone.utc),
        effective_at=event.effective_at.astimezone(timezone.utc),
        amount_cents=event.amount_cents,
        currency=event.currency,
        direction=event.direction.value,
        merchant_name=event.merchant_name,
        merchant_category=event.merchant_category,
        obligation_id=event.obligation_id,
        is_recurring=event.is_recurring,
        is_pending=event.is_pending,
        event_metadata=event.metadata,
    )


class SqlLedgerStore(LedgerStore):
    """Session-scoped ledger store — one instance per request/unit of work,
    matching apps/api's `get_db` dependency lifecycle."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def append(self, event: FinancialEventV1) -> FinancialEventV1:
        existing = self._session.scalar(
            select(FinancialEventRow).where(
                FinancialEventRow.source == event.source,
                FinancialEventRow.source_event_id == event.source_event_id,
                FinancialEventRow.account_id == event.account_id,
            )
        )
        if existing is not None:
            if _row_to_event(existing).model_dump() == event.model_dump():
                return event
            raise DuplicateEventError(
                f"({event.source}, {event.source_event_id}, {event.account_id}) "
                "already recorded with different content"
            )
        self._session.add(_event_to_row(event))
        self._session.flush()
        return event

    def get(self, event_id: str) -> Optional[FinancialEventV1]:
        row = self._session.get(FinancialEventRow, event_id)
        return _row_to_event(row) if row is not None else None

    def list_events(
        self,
        household_id: str,
        *,
        account_id: Optional[str] = None,
        effective_from: Optional[datetime] = None,
        effective_until: Optional[datetime] = None,
        statuses: Optional[list[str]] = None,
    ) -> list[FinancialEventV1]:
        stmt = select(FinancialEventRow).where(FinancialEventRow.household_id == household_id)
        if account_id is not None:
            stmt = stmt.where(FinancialEventRow.account_id == account_id)
        if effective_from is not None:
            stmt = stmt.where(FinancialEventRow.effective_at >= effective_from)
        if effective_until is not None:
            stmt = stmt.where(FinancialEventRow.effective_at <= effective_until)
        if statuses is not None:
            stmt = stmt.where(FinancialEventRow.event_status.in_(statuses))
        stmt = stmt.order_by(FinancialEventRow.effective_at.asc())
        return [_row_to_event(row) for row in self._session.scalars(stmt)]
