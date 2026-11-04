"""Map a validated TelemetryEvent onto one telemetry_events row.

Column names and types come from the Storage reference solution.

- `timestamp` ← `event.timestamp`
- `event_type` ← `event.event_type`
- `service` ← constant `api` (this FastAPI writer)
- `level` ← `error` for catalogue failure events, otherwise `info`
- `value` ← `properties.quantity` or `properties.error_count` when present
- `message` ← `entity_action`
- `id` ← `event.eventId` (required UUID). A repeat of that id does not
  insert a second row.
- `tags` ← `event.properties` only (plan allowlists; `location_id` / `country`
  stay here for later rollups)

Envelope fields `sessionId`, `userId`, `schemaVersion`, and `requestId` are
not copied into `tags`. `eventId` is stored as `id`, not inside `tags`.
"""

from __future__ import annotations

from typing import Any

from app.telemetry_event import TelemetryEvent

SERVICE_NAME = "api"

_ERROR_EVENT_TYPES = frozenset(
    {
        "direct_stock_edit_rejected",
        "inbound_currency_mismatch_rejected",
        "waste_reason_rejected",
        "supplier_document_unreadable",
        "staff_login_failed",
        "protected_route_unauthenticated",
        "request_validation_rejected",
        "storage_unavailable",
    }
)
_VALUE_KEYS = ("quantity", "error_count")


def _metric_value(properties: dict[str, Any]) -> int | float | None:
    for key in _VALUE_KEYS:
        if key not in properties:
            continue
        raw = properties[key]
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            continue
        return raw
    return None


def map_event_to_row(event: TelemetryEvent) -> dict[str, Any]:
    """One row. `id` is the producer `eventId`."""
    properties = dict(event.properties)
    level = "error" if event.event_type in _ERROR_EVENT_TYPES else "info"
    return {
        "id": event.eventId,
        "timestamp": event.timestamp,
        "service": SERVICE_NAME,
        "event_type": event.event_type,
        "level": level,
        "value": _metric_value(properties),
        "message": event.entity_action,
        "tags": properties,
    }
