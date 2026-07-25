from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ActorType(str, Enum):
    consumer = "consumer"
    provider = "provider"
    system = "system"


class AuditEventV1(BaseModel):
    """Mirrors the audit_events table (Section 32.12) — append only. Python
    twin of packages/test_fixtures/src/types.ts' AuditEventV1."""

    model_config = ConfigDict(extra="forbid")

    event_id: str
    decision_id: str
    event_type: str
    actor_type: ActorType
    actor_id: str
    request_id: str
    occurred_at: datetime
    payload_hash: str
    summary: str
    reason: str
    evidence: list[str]
    before_state: Optional[str]
    after_state: Optional[str]
    related_model_version: Optional[str]
    related_data_sources: list[str]
    related_constitution_rule_id: Optional[str]


class ReplayResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision_id: str
    events: list[AuditEventV1]
    verified: bool
    broken_at_event_id: Optional[str] = None
