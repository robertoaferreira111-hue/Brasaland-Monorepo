"""Pipeline behavior that does not need a live database."""

from __future__ import annotations

import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

_PIPELINES = Path(__file__).resolve().parents[3] / "data" / "pipelines"
sys.path.insert(0, str(_PIPELINES))

import pipeline  # noqa: E402


def _event(event_id: str, event_type: str, tags: dict, timestamp: str = "2026-10-13T15:00:00Z") -> dict:
    return {
        "id": event_id,
        "timestamp": timestamp,
        "event_type": event_type,
        "tags": tags,
    }


def _purchase(**extra) -> dict:
    tags = {
        "location_id": "loc_co_01",
        "country": "CO",
        "quantity": 4,
        "unit_cost": 100,
        "currency": "COP",
    }
    tags.update(extra)
    return tags


def test_tasks_declare_retries_cache_and_return_state() -> None:
    assert pipeline.extract_telemetry_events.retries == 3
    assert pipeline.load_weekly_location_performance.retries == 3
    assert pipeline.transform_weekly_location_performance.cache_key_fn is not None
    assert pipeline.transform_weekly_location_performance.cache_expiration is not None
    source = Path(pipeline.__file__).read_text(encoding="utf-8")
    assert "return_state=True" in source
    assert "on conflict (location_id, week_start) do update" in pipeline.UPSERT_SQL.lower()
    assert "+" not in pipeline.UPSERT_SQL.split("do update", 1)[1]


def test_transform_replaces_kpis_and_keeps_a_zero_purchase_ratio() -> None:
    events = [
        _event("11111111-1111-1111-1111-111111111111", "inbound_order_created", _purchase()),
        _event(
            "22222222-2222-2222-2222-222222222222",
            "stock_waste_registered",
            _purchase(quantity=1, unit_cost=50),
        ),
        _event(
            "33333333-3333-3333-3333-333333333333",
            "stock_waste_registered",
            _purchase(location_id="loc_co_03", quantity=2, unit_cost=10),
        ),
        _event(
            "44444444-4444-4444-4444-444444444444",
            "stock_threshold_triggered",
            {"location_id": "loc_co_01", "country": "CO", "currency": "COP"},
        ),
        _event(
            "55555555-5555-5555-5555-555555555555",
            "ingredient_price_variance_detected",
            {"location_id": "loc_us_01", "country": "US", "currency": "USD"},
        ),
    ]
    result = pipeline.transform_events(events)
    by_location = {row["location_id"]: row for row in result["rows"]}
    assert by_location["loc_co_01"]["total_purchase_cost"] == Decimal("400")
    assert by_location["loc_co_01"]["total_waste_cost"] == Decimal("50")
    assert by_location["loc_co_01"]["waste_ratio"] == Decimal("50") / Decimal("400")
    assert by_location["loc_co_01"]["stockout_events_count"] == 1
    assert by_location["loc_co_03"]["total_purchase_cost"] == Decimal("0")
    assert by_location["loc_co_03"]["waste_ratio"] == Decimal("0")
    assert by_location["loc_us_01"]["price_alert_events_count"] == 1
    assert by_location["loc_us_01"]["currency"] == "USD"


def test_duplicate_event_is_counted_once_and_a_conflict_fails() -> None:
    tags = _purchase()
    event = _event("11111111-1111-1111-1111-111111111111", "inbound_order_created", tags)
    result = pipeline.transform_events([event, dict(event)])
    assert result["rows_skipped_duplicate"] == 1
    assert result["rows"][0]["total_purchase_cost"] == Decimal("400")
    changed = _event(
        "11111111-1111-1111-1111-111111111111",
        "inbound_order_created",
        _purchase(quantity=9),
    )
    with pytest.raises(pipeline.TransformError, match="conflicting payload"):
        pipeline.transform_events([event, changed])


def test_country_currency_mismatch_and_missing_cost_are_rejected() -> None:
    mismatch = _event(
        "11111111-1111-1111-1111-111111111111",
        "inbound_order_created",
        _purchase(currency="USD"),
    )
    with pytest.raises(pipeline.TransformError, match="country/currency"):
        pipeline.transform_events([mismatch])
    missing = _event(
        "22222222-2222-2222-2222-222222222222",
        "stock_waste_registered",
        {"location_id": "loc_co_01", "country": "CO", "quantity": 1, "currency": "COP"},
    )
    with pytest.raises(pipeline.TransformError, match="unit_cost"):
        pipeline.transform_events([missing])


def test_completed_week_is_the_previous_utc_monday() -> None:
    assert pipeline.last_completed_week_start(date(2026, 11, 5)) == date(2026, 10, 26)
    start, end, requested, weeks = pipeline.source_window(date(2026, 10, 12), "manual")
    assert requested == date(2026, 10, 12)
    assert weeks == [date(2026, 10, 12)]
    assert start == datetime(2026, 10, 12, tzinfo=timezone.utc)
    assert end == datetime(2026, 10, 19, tzinfo=timezone.utc)
    with pytest.raises(ValueError):
        pipeline.source_window(date(2026, 10, 13), "manual")
