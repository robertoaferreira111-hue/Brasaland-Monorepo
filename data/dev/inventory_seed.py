"""Synthetic inventory events for a non-production telemetry_events table.

The business performance pipeline does not import this module. Each event is
checked against the runtime telemetry schema before it can be inserted.
Re-running the insert uses the same producer id and does not add a row.
"""

from __future__ import annotations

import json
import uuid
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any

from app.telemetry_event import TelemetryEvent
from app.telemetry_mapping import map_event_to_row

_NS = uuid.UUID("6b9c2a10-7e2d-4c1a-9f0e-1a2b3c4d5e6f")
_USER_ID = "staffdev01"
_SESSION_ID = str(uuid.uuid5(_NS, "dev-session"))

# Three complete UTC ISO weeks (Monday through the following Monday).
WEEKS = ("2026-10-12", "2026-10-19", "2026-10-26")

# Opaque dev ids. They are not a location registry.
LOCATIONS = (
    {
        "location_id": "loc_co_01",
        "country": "CO",
        "currency": "COP",
        "purchases": True,
        "waste": True,
        "stockout": True,
        "price": False,
    },
    {
        "location_id": "loc_co_02",
        "country": "CO",
        "currency": "COP",
        "purchases": True,
        "waste": True,
        "stockout": False,
        "price": True,
    },
    {
        "location_id": "loc_co_03",
        "country": "CO",
        "currency": "COP",
        "purchases": False,
        "waste": True,
        "stockout": False,
        "price": False,
    },
    {
        "location_id": "loc_us_01",
        "country": "US",
        "currency": "USD",
        "purchases": True,
        "waste": False,
        "stockout": False,
        "price": False,
    },
    {
        "location_id": "loc_us_02",
        "country": "US",
        "currency": "USD",
        "purchases": True,
        "waste": True,
        "stockout": True,
        "price": False,
    },
    {
        "location_id": "loc_us_03",
        "country": "US",
        "currency": "USD",
        "purchases": True,
        "waste": True,
        "stockout": False,
        "price": True,
    },
)

ALLOWED_PAIRS = {("CO", "COP"), ("US", "USD")}

INSERT_SQL = """
insert into public.telemetry_events (
    id, timestamp, service, event_type, level, value, message, tags
) values (
    %(id)s::uuid,
    %(timestamp)s::timestamptz,
    %(service)s,
    %(event_type)s,
    %(level)s,
    %(value)s,
    %(message)s,
    %(tags)s::jsonb
)
on conflict (id) do nothing
"""


class SeedRejected(ValueError):
    """An event must not be written by the dev seed."""


def _event_id(key: str) -> str:
    return str(uuid.uuid5(_NS, key))


def _envelope(
    key: str,
    event_type: str,
    entity_action: str,
    timestamp: str,
    properties: dict[str, Any],
) -> dict[str, Any]:
    return {
        "eventId": _event_id(key),
        "timestamp": timestamp,
        "sessionId": _SESSION_ID,
        "userId": _USER_ID,
        "event_type": event_type,
        "entity_action": entity_action,
        "schemaVersion": "1.0.0",
        "requestId": _event_id(f"request:{key}"),
        "properties": properties,
    }


def _base_props(location: dict[str, Any], product_id: str) -> dict[str, Any]:
    return {
        "location_id": location["location_id"],
        "country": location["country"],
        "product_id": product_id,
        "product_category": "protein",
        "quantity": 4,
        "unit": "kg",
        "currency": location["currency"],
    }


def _unit_cost(location: dict[str, Any]) -> float:
    return 18000 if location["currency"] == "COP" else 8.5


def week_start_of(timestamp: str) -> date:
    moment = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    day = moment.date()
    return day - timedelta(days=day.weekday())


def main_events() -> list[dict[str, Any]]:
    """Valid events for three complete weeks. Does not include the late event."""
    events: list[dict[str, Any]] = []
    for week in WEEKS:
        timestamp = f"{week}T15:00:00Z"
        for location in LOCATIONS:
            loc = location["location_id"]
            if location["purchases"]:
                props = _base_props(location, "protein_beef")
                props["supplier_id"] = "sup_dev_01"
                props["unit_cost"] = _unit_cost(location)
                events.append(
                    _envelope(
                        f"inbound:{loc}:{week}",
                        "inbound_order_created",
                        "inbound_order.created",
                        timestamp,
                        props,
                    )
                )
            outbound = _base_props(location, "protein_beef")
            outbound["quantity"] = 1
            events.append(
                _envelope(
                    f"outbound:{loc}:{week}",
                    "outbound_order_created",
                    "outbound_order.created",
                    timestamp,
                    outbound,
                )
            )
            if location["waste"]:
                waste = _base_props(location, "protein_beef")
                waste["quantity"] = 0.5
                waste["unit_cost"] = _unit_cost(location)
                waste["reason"] = "expired"
                events.append(
                    _envelope(
                        f"waste:{loc}:{week}",
                        "stock_waste_registered",
                        "stock_waste.registered",
                        timestamp,
                        waste,
                    )
                )
            if location["stockout"]:
                stock = _base_props(location, "protein_beef")
                stock["quantity"] = 0
                stock["threshold_quantity"] = 2
                events.append(
                    _envelope(
                        f"stockout:{loc}:{week}",
                        "stock_threshold_triggered",
                        "stock_threshold.triggered",
                        timestamp,
                        stock,
                    )
                )
            if location["price"]:
                price = _base_props(location, "protein_beef")
                price["supplier_id"] = "sup_dev_01"
                price["quantity"] = 1
                price["unit_cost"] = _unit_cost(location) * 1.25
                price["historical_unit_cost"] = _unit_cost(location)
                price["variance_ratio"] = 0.25
                price["threshold_ratio"] = 0.1
                events.append(
                    _envelope(
                        f"price:{loc}:{week}",
                        "ingredient_price_variance_detected",
                        "ingredient_price_variance.detected",
                        timestamp,
                        price,
                    )
                )
    return events


def late_events() -> list[dict[str, Any]]:
    """One purchase inside the earliest seeded week, loaded by a separate command."""
    location = LOCATIONS[0]
    props = _base_props(location, "protein_beef")
    props["supplier_id"] = "sup_dev_01"
    props["unit_cost"] = _unit_cost(location)
    props["quantity"] = 2
    return [
        _envelope(
            "late:inbound:loc_co_01:2026-10-12",
            "inbound_order_created",
            "inbound_order.created",
            "2026-10-18T22:00:00Z",
            props,
        )
    ]


def invalid_fixtures() -> dict[str, list[dict[str, Any]]]:
    """Samples that must never be inserted. Unit tests are their only consumer."""
    location = LOCATIONS[0]
    missing = _base_props(location, "protein_beef")
    missing["supplier_id"] = "sup_dev_01"
    mismatch = _base_props(location, "protein_beef")
    mismatch["supplier_id"] = "sup_dev_01"
    mismatch["unit_cost"] = _unit_cost(location)
    mismatch["currency"] = "USD"
    extra = _base_props(location, "protein_beef")
    extra["supplier_id"] = "sup_dev_01"
    extra["unit_cost"] = _unit_cost(location)
    extra["note"] = "not-in-the-allowlist"
    first = _envelope(
        "fixture:conflict",
        "inbound_order_created",
        "inbound_order.created",
        "2026-10-12T15:00:00Z",
        {**missing, "unit_cost": 18000, "quantity": 4},
    )
    second = _envelope(
        "fixture:conflict",
        "inbound_order_created",
        "inbound_order.created",
        "2026-10-12T15:00:00Z",
        {**missing, "unit_cost": 18000, "quantity": 9},
    )
    return {
        "missing_unit_cost": [
            _envelope(
                "fixture:missing-unit-cost",
                "inbound_order_created",
                "inbound_order.created",
                "2026-10-12T15:00:00Z",
                missing,
            )
        ],
        "country_currency_mismatch": [
            _envelope(
                "fixture:mismatch",
                "inbound_order_created",
                "inbound_order.created",
                "2026-10-12T15:00:00Z",
                mismatch,
            )
        ],
        "extra_tag": [
            _envelope(
                "fixture:extra-tag",
                "inbound_order_created",
                "inbound_order.created",
                "2026-10-12T15:00:00Z",
                extra,
            )
        ],
        "conflicting_payload": [first, second],
    }


def prepare_rows(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Validate, reject a bad country pair or a repeated id, then map rows."""
    seen: set[str] = set()
    rows: list[dict[str, Any]] = []
    for raw in events:
        event = TelemetryEvent.model_validate(raw)
        pair = (event.properties["country"], event.properties["currency"])
        if pair not in ALLOWED_PAIRS:
            raise SeedRejected("country/currency mismatch")
        if event.eventId in seen:
            raise SeedRejected("conflicting payload for one id")
        seen.add(event.eventId)
        rows.append(map_event_to_row(event))
    return rows


def insert_rows(connection: Any, events: list[dict[str, Any]]) -> int:
    """Insert validated rows. A repeated id inserts nothing and is not an error."""
    rows = prepare_rows(events)
    inserted = 0
    with connection.cursor() as cursor:
        for row in rows:
            payload = dict(row)
            payload["tags"] = json.dumps(row["tags"])
            cursor.execute(INSERT_SQL, payload)
            inserted += cursor.rowcount
    connection.commit()
    return inserted


def counts_by_type_and_week(
    events: list[dict[str, Any]],
) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for event in events:
        week = week_start_of(event["timestamp"]).isoformat()
        counts[event["event_type"]][week] += 1
    return {event_type: dict(weeks) for event_type, weeks in counts.items()}
