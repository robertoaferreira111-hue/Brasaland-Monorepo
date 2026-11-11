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


def test_trigger_enqueues_and_a_live_lease_conflicts(monkeypatch) -> None:
    called: dict = {}

    def _enqueue(week_start, trigger_type):
        called["week_start"] = week_start
        called["trigger_type"] = trigger_type
        return "a1b2c3d4-e5f6-7890-abcd-ef1234567890"

    monkeypatch.setattr(reporting, "live_lease_run_id", lambda: None)
    monkeypatch.setattr(reporting, "_enqueue_weekly_pipeline", _enqueue)
    accepted = client.post(
        "/reporting/pipeline-runs",
        json={"week_start": "2026-10-12", "trigger_type": "backfill"},
    )
    assert accepted.status_code == 202
    assert accepted.json() == {"task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"}
    assert called == {"week_start": date(2026, 10, 12), "trigger_type": "backfill"}

    monkeypatch.setattr(
        reporting,
        "live_lease_run_id",
        lambda: "8bb7302d-cbe7-49fc-ae56-3dddb12739a4",
    )
    conflict = client.post("/reporting/pipeline-runs", json={"trigger_type": "manual"})
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["active_run_id"] == "8bb7302d-cbe7-49fc-ae56-3dddb12739a4"


def test_trigger_returns_503_when_the_broker_is_down(monkeypatch) -> None:
    def _down(week_start, trigger_type):
        del week_start, trigger_type
        raise reporting.QueueUnavailable("Redis is unreachable")

    monkeypatch.setattr(reporting, "live_lease_run_id", lambda: None)
    monkeypatch.setattr(reporting, "_enqueue_weekly_pipeline", _down)
    response = client.post("/reporting/pipeline-runs", json={"trigger_type": "manual"})
    assert response.status_code == 503
    assert response.json()["detail"] == "Queue unavailable"


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
    assert set(body) == {"week_start", "locations"}
    assert body["week_start"] == "2026-10-12"
    location = body["locations"][0]
    assert set(location) == {
        "location_id",
        "country",
        "total_purchase_cost",
        "total_waste_cost",
        "waste_ratio",
        "stockout_events_count",
        "price_alert_events_count",
        "currency",
    }
    assert location["total_purchase_cost"] == 400
    assert location["currency"] == "COP"


def test_non_monday_week_is_rejected() -> None:
    response = client.get(
        "/reporting/weekly-location-performance",
        params={"week_start": "2026-10-13"},
    )
    assert response.status_code == 422
