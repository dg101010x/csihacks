from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

_CONTRACT_VERSION = "1.0.0"


def envelope(
    request_id: str, data: Any, *, errors: Optional[list[str]] = None, warnings: Optional[list[str]] = None
) -> dict:
    """Every apps/api response is wrapped in this shape — matches
    packages/test_fixtures/msw/handlers.ts' `envelope()` exactly, so the
    frontend's domain layer (which already parses this shape from the MSW
    mock) needs no changes when pointed at the real API."""
    return {
        "request_id": request_id,
        "data": data,
        "errors": errors or [],
        "warnings": warnings or [],
        "metadata": {
            "contract_version": _CONTRACT_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    }
