"""In-memory tests for Weekly Location Cost & Waste KPI transforms.

Fixtures match telemetry event rows (id, timestamp, event_type, tags).
No database, network, or Prefect server.
"""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import pytest

_PROCESS = Path(__file__).resolve().parents[2] / "data" / "process"
sys.path.insert(0, str(_PROCESS))

import weekly_location_kpis as kpis  # noqa: E402

_WEEK = "2026-10-13T15:00:00+00:00"


def _event(event_id: str, event_type: str, tags: dict, timestamp: str | None = _WEEK) -> dict:
    return {
        "id": event_id,
        "timestamp": timestamp,
        "event_type": event_type,
        "tags": tags,
    }


def _location_tags(location_id: str, **extra: object) -> dict:
    tags = {
        "location_id": location_id,
        "country": "CO",
        "currency": "COP",
    }
    tags.update(extra)
    return tags


def _row(events: list[dict], location_id: str) -> dict:
    result = kpis.aggregate_weekly_location_kpis(events)
    return next(row for row in result["rows"] if row["location_id"] == location_id)


def test_purchase_cost_per_location_sums_inbound_order_costs() -> None:
    events = [
        _event(
            "11111111-1111-1111-1111-111111111111",
            "inbound_order_created",
            _location_tags("loc-co-1", quantity=4, unit_cost=10),
        ),
        _event(
            "22222222-2222-2222-2222-222222222222",
            "inbound_order_created",
            _location_tags("loc-co-1", quantity=3, unit_cost=20),
        ),
        _event(
            "33333333-3333-3333-3333-333333333333",
            "outbound_order_created",
            _location_tags("loc-co-1", quantity=9),
        ),
        _event(
            "44444444-4444-4444-4444-444444444444",
            "inbound_order_created",
            _location_tags("loc-co-2", quantity=1, unit_cost=10),
        ),
    ]
    # Purchase Cost per Location is the sum of inbound costs only: (4 * 10) + (3 * 20) = 100.
    assert _row(events, "loc-co-1")["total_purchase_cost"] == Decimal("100")
    assert _row(events, "loc-co-2")["total_purchase_cost"] == Decimal("10")


def test_waste_cost_per_location_sums_stock_waste_costs() -> None:
    events = [
        _event(
            "11111111-1111-1111-1111-111111111111",
            "stock_waste_registered",
            _location_tags("loc-co-1", quantity=2, unit_cost=15),
        ),
        _event(
            "22222222-2222-2222-2222-222222222222",
            "stock_waste_registered",
            _location_tags("loc-co-1", quantity=1, unit_cost=10),
        ),
    ]
    # Waste Cost per Location: (2 * 15) + (1 * 10) = 40.
    assert _row(events, "loc-co-1")["total_waste_cost"] == Decimal("40")


def test_stockout_frequency_counts_stock_threshold_events() -> None:
    events = [
        _event(
            "11111111-1111-1111-1111-111111111111",
            "stock_threshold_triggered",
            _location_tags("loc-co-1"),
        ),
        _event(
            "22222222-2222-2222-2222-222222222222",
            "stock_threshold_triggered",
            _location_tags("loc-co-1"),
        ),
    ]
    assert _row(events, "loc-co-1")["stockout_events_count"] == 2


def test_price_alert_frequency_counts_ingredient_price_variance_events() -> None:
    events = [
        _event(
            "11111111-1111-1111-1111-111111111111",
            "ingredient_price_variance_detected",
            _location_tags("loc-us-1", country="US", currency="USD"),
        ),
    ]
    row = _row(events, "loc-us-1")
    assert row["price_alert_events_count"] == 1
    assert row["currency"] == "USD"


def test_waste_ratio_matches_briefing_for_hand_calculated_inputs() -> None:
    events = [
        _event(
            "11111111-1111-1111-1111-111111111111",
            "inbound_order_created",
            _location_tags("loc-co-1", quantity=2, unit_cost=50),
        ),
        _event(
            "22222222-2222-2222-2222-222222222222",
            "stock_waste_registered",
            _location_tags("loc-co-1", quantity=4, unit_cost=5),
        ),
        _event(
            "33333333-3333-3333-3333-333333333333",
            "stock_waste_registered",
            _location_tags("loc-co-2", quantity=3, unit_cost=10),
        ),
    ]
    # Hand-calculated from the BRIEFING Waste Ratio definition.
    # Purchase Cost = 2 * 50 = 100. Waste Cost = 4 * 5 = 20.
    # Waste Ratio = total_waste_cost / total_purchase_cost = 20 / 100 = 0.20.
    # A location with waste and no purchases that week has Waste Ratio 0.
    with_purchases = _row(events, "loc-co-1")
    assert with_purchases["total_purchase_cost"] == Decimal("100")
    assert with_purchases["total_waste_cost"] == Decimal("20")
    assert with_purchases["waste_ratio"] == Decimal("0.20")
    assert _row(events, "loc-co-2")["waste_ratio"] == Decimal("0")


def test_rejects_malformed_timestamp_and_non_numeric_cost() -> None:
    missing_timestamp = _event(
        "11111111-1111-1111-1111-111111111111",
        "stock_waste_registered",
        _location_tags("loc-co-1", quantity=1, unit_cost=10),
        timestamp=None,
    )
    with pytest.raises(kpis.TransformError):
        kpis.aggregate_weekly_location_kpis([missing_timestamp])

    wrong_type = _event(
        "22222222-2222-2222-2222-222222222222",
        "inbound_order_created",
        _location_tags("loc-co-1", quantity="many", unit_cost=10),
    )
    with pytest.raises(kpis.TransformError):
        kpis.aggregate_weekly_location_kpis([wrong_type])
