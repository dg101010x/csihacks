from __future__ import annotations

import json
import logging
import os
import sys


class JsonFormatter(logging.Formatter):
    """Minimal structured formatter — stdlib only, no extra dependency for
    something this small. Every field a log aggregator (Section 20) needs to
    filter/correlate on: timestamp, level, logger, message, and request_id
    when the log call included one via `extra={"request_id": ...}`."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = getattr(record, "request_id", None)
        if request_id is not None:
            payload["request_id"] = request_id
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging() -> None:
    """LOG_FORMAT=json for production/container environments (structured,
    parseable by any log aggregator); plain text otherwise for readable
    local dev output. Called once at app startup."""
    handler = logging.StreamHandler(sys.stdout)
    if os.environ.get("LOG_FORMAT", "text") == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(os.environ.get("LOG_LEVEL", "INFO"))
