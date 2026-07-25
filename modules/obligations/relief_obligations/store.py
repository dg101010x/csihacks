from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from relief_contracts.shared import ObligationV1
from sqlalchemy import JSON, String
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class ObligationStore(ABC):
    """Obligations are mutable (Section 36) — unlike the ledger, a consumer
    can confirm, pause, or close one, and detection re-runs must upsert
    without clobbering those confirmations (see classify.pattern_to_obligation)."""

    @abstractmethod
    def upsert(self, obligation: ObligationV1) -> ObligationV1: ...

    @abstractmethod
    def get(self, obligation_id: str) -> Optional[ObligationV1]: ...

    @abstractmethod
    def list_for_household(self, household_id: str) -> list[ObligationV1]: ...


class InMemoryObligationStore(ObligationStore):
    def __init__(self) -> None:
        self._by_household: dict[str, dict[str, ObligationV1]] = {}

    def upsert(self, obligation: ObligationV1, household_id: str = "") -> ObligationV1:
        bucket = self._by_household.setdefault(household_id, {})
        bucket[obligation.obligation_id] = obligation
        return obligation

    def get(self, obligation_id: str) -> Optional[ObligationV1]:
        for bucket in self._by_household.values():
            if obligation_id in bucket:
                return bucket[obligation_id]
        return None

    def list_for_household(self, household_id: str) -> list[ObligationV1]:
        return list(self._by_household.get(household_id, {}).values())


class Base(DeclarativeBase):
    pass


class ObligationRow(Base):
    __tablename__ = "obligations"

    obligation_id: Mapped[str] = mapped_column(String, primary_key=True)
    household_id: Mapped[str] = mapped_column(String, index=True)
    provider_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    obligation_type: Mapped[str] = mapped_column(String)
    display_name: Mapped[str] = mapped_column(String)
    principal_balance_cents: Mapped[Optional[int]] = mapped_column(nullable=True)
    scheduled_amount_cents: Mapped[int] = mapped_column()
    next_due_at: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    recurrence_rule: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    essentiality_score: Mapped[float] = mapped_column()
    status: Mapped[str] = mapped_column(String)
    source_confidence: Mapped[float] = mapped_column()
    consumer_confirmed: Mapped[bool] = mapped_column()


def _row_to_obligation(row: ObligationRow) -> ObligationV1:
    return ObligationV1(
        obligation_id=row.obligation_id,
        provider_id=row.provider_id,
        obligation_type=row.obligation_type,
        display_name=row.display_name,
        principal_balance_cents=row.principal_balance_cents,
        scheduled_amount_cents=row.scheduled_amount_cents,
        next_due_at=row.next_due_at,
        recurrence_rule=row.recurrence_rule,
        essentiality_score=row.essentiality_score,
        status=row.status,
        source_confidence=row.source_confidence,
        consumer_confirmed=row.consumer_confirmed,
    )


class SqlObligationStore(ObligationStore):
    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert(self, obligation: ObligationV1, household_id: str = "") -> ObligationV1:
        row = self._session.get(ObligationRow, obligation.obligation_id)
        next_due_at = obligation.next_due_at.isoformat() if obligation.next_due_at else None
        if row is None:
            row = ObligationRow(obligation_id=obligation.obligation_id, household_id=household_id)
            self._session.add(row)
        row.household_id = household_id or row.household_id
        row.provider_id = obligation.provider_id
        row.obligation_type = obligation.obligation_type
        row.display_name = obligation.display_name
        row.principal_balance_cents = obligation.principal_balance_cents
        row.scheduled_amount_cents = obligation.scheduled_amount_cents
        row.next_due_at = next_due_at
        row.recurrence_rule = obligation.recurrence_rule
        row.essentiality_score = obligation.essentiality_score
        row.status = obligation.status.value if hasattr(obligation.status, "value") else obligation.status
        row.source_confidence = obligation.source_confidence
        row.consumer_confirmed = obligation.consumer_confirmed
        self._session.flush()
        return obligation

    def get(self, obligation_id: str) -> Optional[ObligationV1]:
        row = self._session.get(ObligationRow, obligation_id)
        return _row_to_obligation(row) if row is not None else None

    def list_for_household(self, household_id: str) -> list[ObligationV1]:
        from sqlalchemy import select

        stmt = select(ObligationRow).where(ObligationRow.household_id == household_id)
        return [_row_to_obligation(row) for row in self._session.scalars(stmt)]
