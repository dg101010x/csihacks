"""FinancialEventV1 (Section 9).

Owner: Plan Two. Version: 1.0.0.
See CONTRACTS.md for required/optional fields and versioning rules. This is
the Python twin of ``src/financial_event.ts`` — keep both in sync.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .shared import validate_contract_version


class EventStatus(str, Enum):
    scheduled = "scheduled"
    pending = "pending"
    posted = "posted"
    cancelled = "cancelled"
    corrected = "corrected"


class Direction(str, Enum):
    inflow = "inflow"
    outflow = "outflow"


class FinancialEventV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: str
    event_id: str
    household_id: str
    account_id: str
    source: str
    source_event_id: str
    event_type: str
    event_status: EventStatus
    occurred_at: datetime
    effective_at: datetime
    amount_cents: int = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)
    direction: Direction
    merchant_name: Optional[str]
    merchant_category: Optional[str]
    obligation_id: Optional[str]
    is_recurring: bool
    is_pending: bool
    metadata: dict

    @field_validator("contract_version")
    @classmethod
    def _validate_contract_version(cls, v: str) -> str:
        return validate_contract_version(v)
