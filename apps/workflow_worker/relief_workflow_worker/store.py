from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from sqlalchemy import JSON, String
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from .models import PackageApprovalState, PackageStage, PolicyReference, ProviderCaseStatus, ProviderCaseV1


class WorkflowStore(ABC):
    @abstractmethod
    def upsert_package_state(self, state: PackageApprovalState) -> PackageApprovalState: ...

    @abstractmethod
    def get_package_state(self, package_id: str) -> Optional[PackageApprovalState]: ...

    @abstractmethod
    def upsert_case(self, case: ProviderCaseV1) -> ProviderCaseV1: ...

    @abstractmethod
    def get_case(self, case_id: str) -> Optional[ProviderCaseV1]: ...


class InMemoryWorkflowStore(WorkflowStore):
    def __init__(self) -> None:
        self._states: dict[str, PackageApprovalState] = {}
        self._cases: dict[str, ProviderCaseV1] = {}

    def upsert_package_state(self, state: PackageApprovalState) -> PackageApprovalState:
        self._states[state.package_id] = state
        return state

    def get_package_state(self, package_id: str) -> Optional[PackageApprovalState]:
        return self._states.get(package_id)

    def upsert_case(self, case: ProviderCaseV1) -> ProviderCaseV1:
        self._cases[case.case_id] = case
        return case

    def get_case(self, case_id: str) -> Optional[ProviderCaseV1]:
        return self._cases.get(case_id)


class Base(DeclarativeBase):
    pass


class PackageStateRow(Base):
    __tablename__ = "package_approval_states"

    package_id: Mapped[str] = mapped_column(String, primary_key=True)
    stage: Mapped[str] = mapped_column(String)
    case_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    history: Mapped[list] = mapped_column(JSON)


class ProviderCaseRow(Base):
    __tablename__ = "provider_cases"

    case_id: Mapped[str] = mapped_column(String, primary_key=True)
    provider_id: Mapped[str] = mapped_column(String)
    action_id: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    consumer_impact_summary: Mapped[str] = mapped_column(String)
    provider_impact_summary: Mapped[str] = mapped_column(String)
    policy_reference: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)


class SqlWorkflowStore(WorkflowStore):
    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert_package_state(self, state: PackageApprovalState) -> PackageApprovalState:
        row = self._session.get(PackageStateRow, state.package_id)
        if row is None:
            row = PackageStateRow(package_id=state.package_id)
            self._session.add(row)
        row.stage = state.stage.value
        row.case_id = state.case_id
        row.history = state.history
        self._session.flush()
        return state

    def get_package_state(self, package_id: str) -> Optional[PackageApprovalState]:
        row = self._session.get(PackageStateRow, package_id)
        if row is None:
            return None
        return PackageApprovalState(package_id=row.package_id, stage=row.stage, case_id=row.case_id, history=row.history)

    def upsert_case(self, case: ProviderCaseV1) -> ProviderCaseV1:
        row = self._session.get(ProviderCaseRow, case.case_id)
        if row is None:
            row = ProviderCaseRow(case_id=case.case_id)
            self._session.add(row)
        row.provider_id = case.provider_id
        row.action_id = case.action_id
        row.status = case.status.value
        row.consumer_impact_summary = case.consumer_impact_summary
        row.provider_impact_summary = case.provider_impact_summary
        row.policy_reference = case.policy_reference.model_dump() if case.policy_reference else None
        self._session.flush()
        return case

    def get_case(self, case_id: str) -> Optional[ProviderCaseV1]:
        row = self._session.get(ProviderCaseRow, case_id)
        if row is None:
            return None
        return ProviderCaseV1(
            case_id=row.case_id,
            provider_id=row.provider_id,
            action_id=row.action_id,
            status=row.status,
            consumer_impact_summary=row.consumer_impact_summary,
            provider_impact_summary=row.provider_impact_summary,
            policy_reference=PolicyReference(**row.policy_reference) if row.policy_reference else None,
        )
