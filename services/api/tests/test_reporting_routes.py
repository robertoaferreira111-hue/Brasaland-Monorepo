"""Reporting routes call the pipeline module and keep the staff auth contract."""

from __future__ import annotations

import sys
from datetime import date, datetime, timezone

from fastapi.testclient import TestClient

from app.deps import current_user_email
from app.main import app

reporting = sys.modules["brasaland_reporting_router"]
client = TestClient(app)


def setup_function() -> None:
    app.dependency_overrides[current_user_email] = lambda: "staff@example.com"


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_reporting_requires_a_staff_token() -> None:
    app.dependency_overrides.clear()
    response = client.get("/reporting/pipeline-runs/latest")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_latest_run_reports_stored_metadata(monkeypatch) -> None:
    monkeypatch.setattr(
        reporting,
        "get_latest_pipeline_run",
        lambda: {
            "run_id": "8bb7302d-cbe7-49fc-ae56-3dddb12739a4",
            "status": "success",
            "started_at": datetime(2026, 11, 2, tzinfo=timezone.utc),
            "finished_at": datetime(2026, 11, 2, 0, 1, tzinfo=timezone.utc),
            "records_processed": 60,
            "error_summary": None,
        },
    )
    response = client.get("/reporting/pipeline-runs/latest")
    assert response.status_code == 200
    body = response.json()
    assert body["records_processed"] == 60
    assert body["status"] == "success"
    assert body["error_summary"] is None


def test_trigger_calls_the_flow_and_a_live_lease_conflicts(monkeypatch) -> None:
    called: dict = {}

    def _run(week_start, trigger_type):
        called["week_start"] = week_start
        called["trigger_type"] = trigger_type
        return {"run_id": "8bb7302d-cbe7-49fc-ae56-3dddb12739a4", "status": "success"}

    _run.fn = _run
    monkeypatch.setattr(reporting, "business_performance_etl_flow", _run)
    accepted = client.post(
        "/reporting/pipeline-runs",
        json={"week_start": "2026-10-12", "trigger_type": "manual"},
    )
    assert accepted.status_code == 202
    assert called == {"week_start": date(2026, 10, 12), "trigger_type": "manual"}

    def _busy(week_start, trigger_type):
        del week_start, trigger_type
        raise reporting.PipelineLeaseHeld("8bb7302d-cbe7-49fc-ae56-3dddb12739a4")

    _busy.fn = _busy
    monkeypatch.setattr(reporting, "business_performance_etl_flow", _busy)
    conflict = client.post("/reporting/pipeline-runs", json={"trigger_type": "manual"})
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["active_run_id"] == "8bb7302d-cbe7-49fc-ae56-3dddb12739a4"


def test_weekly_performance_uses_pipeline_rows(monkeypatch) -> None:
    monkeypatch.setattr(
        reporting,
        "get_weekly_location_performance",
        lambda week_start, week_end, location_id, country: [
            {
                "location_id": "loc_co_01",
                "country": "CO",
                "week_start": date(2026, 10, 12),
                "total_purchase_cost": 400,
                "total_waste_cost": 50,
                "waste_ratio": 0.125,
                "stockout_events_count": 1,
                "price_alert_events_count": 0,
                "currency": "COP",
                "computed_at": datetime(2026, 10, 19, tzinfo=timezone.utc),
            }
        ],
    )
    response = client.get(
        "/reporting/weekly-location-performance",
        params={"week_start": "2026-10-12", "country": "CO"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["coverage"] == "observed_locations_only"
    assert body["locations"][0]["total_purchase_cost"] == 400
    assert body["locations"][0]["currency"] == "COP"


def test_non_monday_week_is_rejected() -> None:
    response = client.get(
        "/reporting/weekly-location-performance",
        params={"week_start": "2026-10-13"},
    )
    assert response.status_code == 422
