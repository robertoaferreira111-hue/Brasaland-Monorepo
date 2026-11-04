"""Best-effort telemetry capture into Supabase `telemetry_events`.

Failures here must never change HTTP responses or recurse into more telemetry.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import httpx

from app.config import _load_env_files

logger = logging.getLogger("brasaland.api.telemetry")

SERVICE_NAME = "api"
PROTECTED_ROUTE_DETAILS = frozenset(
    {"Not authenticated", "Session expired", "Invalid token"}
)
LOGIN_FAILURE_DETAIL = "Incorrect email or password"
STORAGE_DETAIL = "Storage unavailable"


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _supabase_config() -> tuple[str, str] | None:
    """Read URL + service role from process env (after dotenv load)."""
    _load_env_files()
    url = (os.getenv("SUPABASE_URL") or "").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or ""
    if not url or not key:
        return None
    return url, key


def persist_telemetry_event(
    *,
    event_type: str,
    level: str,
    tags: dict[str, Any],
    message: str | None = None,
    value: float | None = None,
) -> None:
    """POST one eight-column row. Never raises to callers."""
    try:
        config = _supabase_config()
        if config is None:
            logger.warning("telemetry skipped: SUPABASE_URL/SERVICE_ROLE_KEY unset")
            return
        url, key = config
        row: dict[str, Any] = {
            "id": str(uuid4()),
            "timestamp": _utcnow_iso(),
            "service": SERVICE_NAME,
            "event_type": event_type,
            "level": level,
            "tags": tags,
        }
        if message is not None:
            row["message"] = message
        if value is not None:
            row["value"] = value
        endpoint = f"{url}/rest/v1/telemetry_events"
        headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        }
        with httpx.Client(timeout=5.0) as client:
            response = client.post(endpoint, headers=headers, json=row)
            if response.status_code >= 400:
                logger.warning(
                    "telemetry write failed event_type=%s status=%s",
                    event_type,
                    response.status_code,
                )
    except Exception:
        logger.exception("telemetry write error event_type=%s", event_type)


def emit_staff_login_failed() -> None:
    persist_telemetry_event(
        event_type="staff_login_failed",
        level="error",
        message="Staff login rejected",
        tags={"outcome": "invalid_credentials"},
    )


def emit_protected_route_unauthenticated(*, route: str, detail: str) -> None:
    if detail not in PROTECTED_ROUTE_DETAILS:
        return
    persist_telemetry_event(
        event_type="protected_route_unauthenticated",
        level="error",
        message="Protected route rejected unauthenticated request",
        tags={"route": route, "status_code": 401, "detail": detail},
    )


def emit_request_validation_rejected(*, route: str, error_count: int) -> None:
    persist_telemetry_event(
        event_type="request_validation_rejected",
        level="error",
        message="Request validation rejected",
        tags={
            "route": route,
            "status_code": 422,
            "error_count": max(1, int(error_count)),
        },
    )


def emit_storage_unavailable(*, route: str) -> None:
    persist_telemetry_event(
        event_type="storage_unavailable",
        level="error",
        message="Storage unavailable",
        tags={"route": route, "status_code": 500, "detail": STORAGE_DETAIL},
    )


def emit_supplier_created(
    *,
    supplier_id: int,
    country: str,
    currency: str,
    categories: list[str],
    status: str,
) -> None:
    persist_telemetry_event(
        event_type="supplier_created",
        level="info",
        message="Supplier created",
        tags={
            "supplier_id": str(supplier_id),
            "country": country,
            "currency": currency,
            "categories": list(categories),
            "status": status,
        },
    )


def emit_supplier_rate_changed(
    *,
    supplier_id: int,
    country: str,
    currency: str,
    categories: list[str],
    previous_rate: float,
    new_rate: float,
) -> None:
    if previous_rate == new_rate:
        return
    persist_telemetry_event(
        event_type="supplier_rate_changed",
        level="info",
        message="Supplier rate changed",
        tags={
            "supplier_id": str(supplier_id),
            "country": country,
            "currency": currency,
            "categories": list(categories),
            "previous_rate": previous_rate,
            "new_rate": new_rate,
        },
    )


def emit_supplier_status_changed(
    *,
    supplier_id: int,
    country: str,
    previous_status: str,
    new_status: str,
) -> None:
    if previous_status == new_status:
        return
    persist_telemetry_event(
        event_type="supplier_status_changed",
        level="info",
        message="Supplier status changed",
        tags={
            "supplier_id": str(supplier_id),
            "country": country,
            "previous_status": previous_status,
            "new_status": new_status,
        },
    )
