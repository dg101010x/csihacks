from __future__ import annotations

import os
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

_DEFAULT_LIMIT = 120
_WINDOW_SECONDS = 60.0


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Section 18 hardening: a fixed-window limiter per client IP, in-
    process (fine for the single-process demo deployment this repo targets
    today; a real multi-instance deployment would move this to a shared
    store like Redis — infrastructure/deployment's job, not this one).
    Limit is configurable via RELIEF_RATE_LIMIT_PER_MINUTE so tests and
    ops can tune it without a code change."""

    def __init__(self, app, limit: int | None = None) -> None:
        super().__init__(app)
        self._limit = limit or int(os.environ.get("RELIEF_RATE_LIMIT_PER_MINUTE", _DEFAULT_LIMIT))
        self._windows: dict[str, tuple[float, int]] = {}

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path == "/health":
            return await call_next(request)

        client_id = request.client.host if request.client else "unknown"
        now = time.monotonic()
        window_start, count = self._windows.get(client_id, (now, 0))

        if now - window_start >= _WINDOW_SECONDS:
            window_start, count = now, 0

        count += 1
        self._windows[client_id] = (window_start, count)

        if count > self._limit:
            retry_after = max(0, int(_WINDOW_SECONDS - (now - window_start)))
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded."},
                headers={"Retry-After": str(retry_after)},
            )

        return await call_next(request)
