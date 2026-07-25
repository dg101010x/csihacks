"""HouseholdSnapshotV1 (Section 10).

Owner: Plan Two. Version: 1.0.0. The complete, self-contained input to every
forecast provider — the model team must never query Plan Two's production
database directly. Python twin of ``src/household_snapshot.ts``.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from .financial_event import FinancialEventV1
from .shared import (
    AccountV1,
    ConsumerConstitutionV1,
    ObligationV1,
    ProviderCapabilityV1,
    validate_contract_version,
)


class HouseholdSnapshotV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: str
    snapshot_id: str
    household_id: str
    generated_at: datetime
    timezone: str
    currency: str
    accounts: list[AccountV1]
    obligations: list[ObligationV1]
    recent_events: list[FinancialEventV1]
    known_future_events: list[FinancialEventV1]
    consumer_constitution: ConsumerConstitutionV1
    provider_capabilities: list[ProviderCapabilityV1]

    @field_validator("contract_version")
    @classmethod
    def _validate_contract_version(cls, v: str) -> str:
        return validate_contract_version(v)
