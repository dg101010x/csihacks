from __future__ import annotations

import uuid

from fastapi import Request

# Single seeded demo household/tenant (matches the "Sarah" persona the
# frontend's MSW fixtures already demonstrate against) — real multi-
# household routing is an auth concern (Section 14 hardening pass), not
# invented ad hoc here.
DEMO_HOUSEHOLD_ID = "hh_01"


def get_request_id(request: Request) -> str:
    """Set by RequestIdMiddleware; falls back to a fresh id for anything
    invoked outside the middleware (e.g. direct unit tests)."""
    existing = getattr(request.state, "request_id", None)
    return existing or f"req_{uuid.uuid4().hex[:12]}"


def get_household_id() -> str:
    return DEMO_HOUSEHOLD_ID
