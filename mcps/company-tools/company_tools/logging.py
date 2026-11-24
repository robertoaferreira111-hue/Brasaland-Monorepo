"""Structured tool-invocation logs.

This module lives inside the `company_tools` package so `import logging`
still loads the standard library.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

INVOCATION_LOGGER = "company_tools.invocation"
_HANDLER_MARK = "_company_tools_handler"
_REDACTED = "[redacted]"
_SECRET_KEYS = {
    "token",
    "access_token",
    "refresh_token",
    "password",
    "secret",
    "authorization",
    "api_key",
    "client_secret",
    "incidents_api_token",
    "description",
    "customer_id",
    "satisfaction_score",
    "reporter_id",
}


def configure_logging() -> logging.Logger:
    """Attach one stderr handler to the company_tools logger. Repeat calls do not add another."""
    logger = logging.getLogger("company_tools")
    logger.setLevel(logging.INFO)
    invocation = logging.getLogger(INVOCATION_LOGGER)
    invocation.setLevel(logging.INFO)
    if not any(getattr(handler, _HANDLER_MARK, False) for handler in logger.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        setattr(handler, _HANDLER_MARK, True)
        logger.addHandler(handler)
    return invocation


def log_invocation(
    *,
    client_id: str,
    tool: str,
    input_summary: dict[str, Any],
    result: str,
    duration_ms: int,
    error_code: str | None = None,
) -> None:
    """Write one JSON object. Tokens, secrets, and sensitive incident fields are redacted."""
    payload = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "client_id": client_id,
        "tool": tool,
        "input_summary": redact_summary(input_summary),
        "result": result,
        "error_code": error_code,
        "duration_ms": duration_ms,
    }
    logging.getLogger(INVOCATION_LOGGER).info(json.dumps(payload, separators=(",", ":")))


def redact_summary(summary: dict[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, value in summary.items():
        if _secret_key(key) or (isinstance(value, str) and _secret_value(value)):
            redacted[key] = _REDACTED
        else:
            redacted[key] = value
    return redacted


def _secret_key(key: str) -> bool:
    lowered = key.lower()
    return (
        lowered in _SECRET_KEYS
        or "token" in lowered
        or "secret" in lowered
        or "password" in lowered
    )


def _secret_value(value: str) -> bool:
    if value.lower().startswith("bearer "):
        return True
    parts = value.split(".")
    return len(parts) == 3 and all(len(part) > 10 for part in parts)
