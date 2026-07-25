from __future__ import annotations

import logging
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger("relief_api")


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Every request gets a stable request_id propagated into the response
    envelope and audit events — accepts an inbound X-Request-Id for client-
    side correlation, or mints one.

    Also the one place that converts an unhandled exception into a generic
    500 (Section 18 hardening): FastAPI's `@app.exception_handler(Exception)`
    does not reliably fire for errors raised inside routes when
    BaseHTTPMiddleware-based middleware sits in front of them (a known
    Starlette limitation — the exception propagates through call_next
    instead of being routed to the app-level handler), so the safety net
    has to live here instead.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("x-request-id") or f"req_{uuid.uuid4().hex[:12]}"
        request.state.request_id = request_id

        try:
            response = await call_next(request)
        except Exception:
            logger.exception("Unhandled exception for request %s", request_id)
            response = JSONResponse(
                status_code=500, content={"detail": "Internal server error.", "request_id": request_id}
            )

        response.headers["x-request-id"] = request_id
        return response
