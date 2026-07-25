from __future__ import annotations

import os
import secrets

from fastapi import Header, HTTPException

_ENV_VAR = "RELIEF_API_KEY"


def _configured_key() -> str | None:
    return os.environ.get(_ENV_VAR)


def require_api_key(x_api_key: str = Header(default="")) -> None:
    """Section 18 hardening: every /v1/* route requires X-API-Key to match
    RELIEF_API_KEY. If RELIEF_API_KEY isn't set at all, auth is left open —
    that's the local/dev/demo posture (matches the single-tenant demo
    household apps/api already runs with no real user accounts) — but any
    real deployment must set it, and main.py logs a startup warning if it
    doesn't. Uses secrets.compare_digest to avoid a timing side-channel on
    key comparison.
    """
    configured = _configured_key()
    if not configured:
        return
    if not x_api_key or not secrets.compare_digest(x_api_key, configured):
        raise HTTPException(status_code=401, detail="Missing or invalid X-API-Key.")


def auth_is_enforced() -> bool:
    return bool(_configured_key())
