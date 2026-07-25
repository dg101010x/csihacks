from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from sqlalchemy import JSON, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from .models import ConstitutionRuleV1, RuleStatus


class ConstitutionRuleStore(ABC):
    @abstractmethod
    def upsert(self, household_id: str, rule: ConstitutionRuleV1) -> ConstitutionRuleV1: ...

    @abstractmethod
    def get(self, rule_id: str) -> Optional[ConstitutionRuleV1]: ...

    @abstractmethod
    def list_for_household(self, household_id: str, *, status: Optional[str] = None) -> list[ConstitutionRuleV1]: ...

    def activate(self, household_id: str, rule_id: str) -> Optional[ConstitutionRuleV1]:
        rule = self.get(rule_id)
        if rule is None:
            return None
        # model_copy(update=...) does not re-validate/coerce, so this must be
        # the enum member itself, not the string "active".
        activated = rule.model_copy(update={"status": RuleStatus.active})
        return self.upsert(household_id, activated)


class InMemoryConstitutionRuleStore(ConstitutionRuleStore):
    def __init__(self) -> None:
        self._by_household: dict[str, dict[str, ConstitutionRuleV1]] = {}

    def upsert(self, household_id: str, rule: ConstitutionRuleV1) -> ConstitutionRuleV1:
        self._by_household.setdefault(household_id, {})[rule.rule_id] = rule
        return rule

    def get(self, rule_id: str) -> Optional[ConstitutionRuleV1]:
        for bucket in self._by_household.values():
            if rule_id in bucket:
                return bucket[rule_id]
        return None

    def list_for_household(self, household_id: str, *, status: Optional[str] = None) -> list[ConstitutionRuleV1]:
        rules = list(self._by_household.get(household_id, {}).values())
        if status is not None:
            rules = [r for r in rules if r.status.value == status]
        return rules


class Base(DeclarativeBase):
    pass


class ConstitutionRuleRow(Base):
    __tablename__ = "constitution_rules"

    rule_id: Mapped[str] = mapped_column(String, primary_key=True)
    household_id: Mapped[str] = mapped_column(String, index=True)
    status: Mapped[str] = mapped_column(String)
    raw_text: Mapped[str] = mapped_column(String)
    trigger: Mapped[str] = mapped_column(String)
    scope: Mapped[list] = mapped_column(JSON)
    permitted_actions: Mapped[list] = mapped_column(JSON)
    prohibited_actions: Mapped[list] = mapped_column(JSON)
    approval_requirement: Mapped[str] = mapped_column(String)
    maximum_monetary_impact_cents: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    expiration: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    priority: Mapped[int] = mapped_column(Integer)
    exceptions: Mapped[list] = mapped_column(JSON)
    confidence: Mapped[float] = mapped_column()
    created_at: Mapped[str] = mapped_column(String)


def _row_to_rule(row: ConstitutionRuleRow) -> ConstitutionRuleV1:
    return ConstitutionRuleV1(
        rule_id=row.rule_id,
        status=row.status,
        raw_text=row.raw_text,
        trigger=row.trigger,
        scope=row.scope,
        permitted_actions=row.permitted_actions,
        prohibited_actions=row.prohibited_actions,
        approval_requirement=row.approval_requirement,
        maximum_monetary_impact_cents=row.maximum_monetary_impact_cents,
        expiration=row.expiration,
        priority=row.priority,
        exceptions=row.exceptions,
        confidence=row.confidence,
        created_at=row.created_at,
    )


class SqlConstitutionRuleStore(ConstitutionRuleStore):
    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert(self, household_id: str, rule: ConstitutionRuleV1) -> ConstitutionRuleV1:
        row = self._session.get(ConstitutionRuleRow, rule.rule_id)
        if row is None:
            row = ConstitutionRuleRow(rule_id=rule.rule_id, household_id=household_id)
            self._session.add(row)
        row.household_id = household_id
        row.status = rule.status.value
        row.raw_text = rule.raw_text
        row.trigger = rule.trigger
        row.scope = rule.scope
        row.permitted_actions = rule.permitted_actions
        row.prohibited_actions = rule.prohibited_actions
        row.approval_requirement = rule.approval_requirement.value
        row.maximum_monetary_impact_cents = rule.maximum_monetary_impact_cents
        row.expiration = rule.expiration
        row.priority = rule.priority
        row.exceptions = rule.exceptions
        row.confidence = rule.confidence
        row.created_at = rule.created_at.isoformat()
        self._session.flush()
        return rule

    def get(self, rule_id: str) -> Optional[ConstitutionRuleV1]:
        row = self._session.get(ConstitutionRuleRow, rule_id)
        return _row_to_rule(row) if row is not None else None

    def list_for_household(self, household_id: str, *, status: Optional[str] = None) -> list[ConstitutionRuleV1]:
        from sqlalchemy import select

        stmt = select(ConstitutionRuleRow).where(ConstitutionRuleRow.household_id == household_id)
        if status is not None:
            stmt = stmt.where(ConstitutionRuleRow.status == status)
        return [_row_to_rule(row) for row in self._session.scalars(stmt)]
