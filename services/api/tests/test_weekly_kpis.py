"""Pure KPI functions have no database and no Prefect."""

from __future__ import annotations

import ast
import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

_PROCESS = Path(__file__).resolve().parents[3] / "data" / "process"
sys.path.insert(0, str(_PROCESS))

import weekly_location_kpis as kpis  # noqa: E402


def _event(event_id: str, event_type: str, tags: dict, timestamp: str = "2026-10-13T15:00:00Z") -> dict:
    return {"id": event_id, "timestamp": timestamp, "event_type": event_type, "tags": tags}


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


def test_module_does_not_import_the_database_or_prefect() -> None:
    source = Path(kpis.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module.split(".")[0])
    assert "prefect" not in imported
    assert "psycopg" not in imported
    assert "db" not in imported


def test_line_cost_iso_monday_and_currency_pair() -> None:
    assert kpis.line_cost(4, 100) == Decimal("400")
    assert kpis.iso_monday("2026-10-13T15:00:00Z") == date(2026, 10, 12)
    assert kpis.iso_monday(datetime(2026, 10, 18, 23, tzinfo=timezone.utc)) == date(2026, 10, 12)
    with pytest.raises(kpis.TransformError, match="positive"):
        kpis.line_cost(0, 10)
    with pytest.raises(kpis.TransformError, match="timezone-aware"):
        kpis.iso_monday(datetime(2026, 10, 13, 15))


def test_aggregate_matches_the_pipeline_contract() -> None:
    events = [
        _event("11111111-1111-1111-1111-111111111111", "inbound_order_created", _purchase()),
        _event(
            "22222222-2222-2222-2222-222222222222",
            "stock_waste_registered",
            _purchase(quantity=1, unit_cost=50),
        ),
        _event(
            "33333333-3333-3333-3333-333333333333",
            "outbound_order_created",
            {"location_id": "loc_co_01"},
        ),
        _event(
            "44444444-4444-4444-4444-444444444444",
            "inbound_order_created",
            _purchase(),
        ),
    ]
    events.append(dict(events[0]))
    result = kpis.aggregate_weekly_location_kpis(events)
    row = result["rows"][0]
    assert row["total_purchase_cost"] == Decimal("800")
    assert row["total_waste_cost"] == Decimal("50")
    assert row["waste_ratio"] == Decimal("50") / Decimal("800")
    assert result["rows_skipped_duplicate"] == 1
    assert result["rows_rejected"] == 1
    assert result["rejections"][0]["event_type"] == "outbound_order_created"
