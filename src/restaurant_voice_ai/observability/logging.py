"""Structured JSON and readable development logging."""

import json
import logging
from datetime import UTC, datetime

from restaurant_voice_ai.observability.redaction import redact
from restaurant_voice_ai.observability.request_context import request_id_context

SAFE_EXTRA = (
    "event",
    "environment",
    "request_id",
    "conversation_id",
    "voice_session_id",
    "turn_number",
    "route",
    "method",
    "status_code",
    "latency_ms",
    "auth_identity",
    "tool_name",
    "provider",
    "fallback_used",
    "error_code",
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": redact(record.getMessage()),
            "request_id": request_id_context.get(),
        }
        for field in SAFE_EXTRA:
            if hasattr(record, field):
                payload[field] = redact(getattr(record, field))
        if record.exc_info and record.exc_info[0] is not None:
            payload["exception"] = record.exc_info[0].__name__
        return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
