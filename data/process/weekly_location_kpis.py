"""Pure Weekly Location Cost & Waste calculations.

No database access and no Prefect. The pipeline imports these functions and
publishes the rows they return.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

EVENT_TYPES = (
    "inbound_order_created",
    "outbound_order_created",
    "stock_waste_registered",
    "stock_threshold_triggered",
    "ingredient_price_variance_detected",
)
KPI_EVENT_TYPES = frozenset(EVENT_TYPES) - {"outbound_order_created"}
CURRENCY_FOR_COUNTRY = {"CO": "COP", "US": "USD"}
_REQUIRED = {
    "inbound_order_created": ("location_id", "country", "quantity", "unit_cost", "currency"),
    "outbound_order_created": ("location_id", "country", "quantity", "currency"),
    "stock_waste_registered": ("location_id", "country", "quantity", "unit_cost", "currency"),
    "stock_threshold_triggered": ("location_id", "country", "currency"),
    "ingredient_price_variance_detected": ("location_id", "country", "currency"),
}


class TransformError(RuntimeError):
    """A KPI-bearing source row cannot be published."""


def require_tags_object(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    raise TransformError("tags must be an object")


def line_cost(quantity: Any, unit_cost: Any) -> Decimal:
    if isinstance(quantity, bool) or isinstance(unit_cost, bool):
        raise TransformError("quantity and unit_cost must be numbers")
    try:
        amount = Decimal(str(quantity)) * Decimal(str(unit_cost))
    except Exception as exc:
        raise TransformError("quantity and unit_cost must be numbers") from exc
    if amount <= 0:
        raise TransformError("cost events require a positive quantity and unit_cost")
    return amount


def iso_monday(timestamp: Any) -> date:
    if isinstance(timestamp, str):
        timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    if not isinstance(timestamp, datetime) or timestamp.tzinfo is None:
        raise TransformError("timestamp must be timezone-aware")
    day = timestamp.astimezone(timezone.utc).date()
    return day - timedelta(days=day.weekday())


def aggregate_weekly_location_kpis(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Validate source rows and recompute one row per location and ISO week."""
    seen: dict[str, dict[str, Any]] = {}
    rejected = 0
    skipped = 0
    rejections: list[dict[str, str]] = []
    usable: list[dict[str, Any]] = []
    for event in events:
        event_type = event.get("event_type")
        if event_type not in EVENT_TYPES:
            rejected += 1
            rejections.append(
                {
                    "id": str(event.get("id")),
                    "event_type": str(event_type),
                    "reason": "unsupported event type",
                }
            )
            continue
        try:
            tags = require_tags_object(event.get("tags"))
            missing = [key for key in _REQUIRED[event_type] if key not in tags]
            if missing:
                raise TransformError("missing " + ", ".join(missing))
            country = tags["country"]
            currency = tags["currency"]
            if CURRENCY_FOR_COUNTRY.get(country) != currency:
                raise TransformError("country/currency mismatch")
            identity = str(event["id"])
            payload = {"event_type": event_type, "timestamp": str(event["timestamp"]), "tags": tags}
            if identity in seen and seen[identity] != payload:
                raise TransformError("conflicting payload for one id")
            if identity in seen:
                skipped += 1
                continue
            seen[identity] = payload
            usable.append(
                {
                    "id": identity,
                    "event_type": event_type,
                    "week": iso_monday(event["timestamp"]),
                    "tags": tags,
                }
            )
        except TransformError as exc:
            if event_type == "outbound_order_created":
                rejected += 1
                rejections.append(
                    {
                        "id": str(event.get("id")),
                        "event_type": str(event_type),
                        "reason": str(exc),
                    }
                )
                continue
            raise
    buckets: dict[tuple[str, str, date, str], dict[str, Any]] = {}
    location_pairs: dict[tuple[str, date], set[tuple[str, str]]] = {}
    for event in usable:
        if event["event_type"] not in KPI_EVENT_TYPES:
            continue
        tags = event["tags"]
        key = (tags["location_id"], tags["country"], event["week"], tags["currency"])
        location_pairs.setdefault((tags["location_id"], event["week"]), set()).add(
            (tags["country"], tags["currency"])
        )
        bucket = buckets.setdefault(
            key,
            {
                "location_id": tags["location_id"],
                "country": tags["country"],
                "week_start": event["week"],
                "currency": tags["currency"],
                "total_purchase_cost": Decimal("0"),
                "total_waste_cost": Decimal("0"),
                "stockout_ids": set(),
                "price_ids": set(),
            },
        )
        if event["event_type"] == "inbound_order_created":
            bucket["total_purchase_cost"] += line_cost(tags["quantity"], tags["unit_cost"])
        elif event["event_type"] == "stock_waste_registered":
            bucket["total_waste_cost"] += line_cost(tags["quantity"], tags["unit_cost"])
        elif event["event_type"] == "stock_threshold_triggered":
            bucket["stockout_ids"].add(event["id"])
        elif event["event_type"] == "ingredient_price_variance_detected":
            bucket["price_ids"].add(event["id"])
    for pairs in location_pairs.values():
        if len(pairs) > 1:
            raise TransformError("country/currency conflict for one location-week")
    rows = []
    for bucket in buckets.values():
        purchase = bucket["total_purchase_cost"]
        waste = bucket["total_waste_cost"]
        ratio = Decimal("0") if purchase == 0 else waste / purchase
        rows.append(
            {
                "location_id": bucket["location_id"],
                "country": bucket["country"],
                "week_start": bucket["week_start"],
                "total_purchase_cost": purchase,
                "total_waste_cost": waste,
                "waste_ratio": ratio,
                "stockout_events_count": len(bucket["stockout_ids"]),
                "price_alert_events_count": len(bucket["price_ids"]),
                "currency": bucket["currency"],
            }
        )
    rows.sort(key=lambda row: (row["week_start"], row["country"], row["location_id"]))
    return {
        "rows": rows,
        "rows_rejected": rejected,
        "rows_skipped_duplicate": skipped,
        "rejections": rejections,
    }
