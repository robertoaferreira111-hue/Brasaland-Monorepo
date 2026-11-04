"""Phase 2: GET /telemetry/report + 60s cache."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from cache import ReportCache
from report_period import fill_zero_event_days, resolve_period
from router import configure_report_runtime, reset_report_runtime


@pytest.fixture(autouse=True)
def _reset_report_hooks():
    reset_report_runtime()
    yield
    reset_report_runtime()


def _metric_stubs() -> dict[str, Any]:
    calls: dict[str, list[tuple[datetime, datetime]]] = {
        "events_per_day": [],
        "error_rate_by_type": [],
        "events_by_dimension": [],
        "auth_failure_rate": [],
    }

    def events_per_day(start: datetime, end: datetime, **kwargs: Any) -> list:
        del kwargs
        calls["events_per_day"].append((start, end))
        return [{"date": "2026-11-03", "count": 2}]

    def error_rate_by_type(start: datetime, end: datetime, **kwargs: Any) -> list:
        del kwargs
        calls["error_rate_by_type"].append((start, end))
        return [
            {
                "event_type": "staff_login_failed",
                "total_events": 2,
                "error_events": 2,
                "error_rate": 100.0,
            }
        ]

    def events_by_dimension(start: datetime, end: datetime, **kwargs: Any) -> list:
        del kwargs
        calls["events_by_dimension"].append((start, end))
        return [{"dimension": "route", "dimension_value": "/suppliers", "count": 1}]

    def auth_failure_rate(start: datetime, end: datetime, **kwargs: Any) -> list:
        del kwargs
        calls["auth_failure_rate"].append((start, end))
        return [
            {
                "date": "2026-11-03",
                "failed_attempts": 2,
                "succeeded_attempts": 0,
                "total_attempts": 2,
                "auth_failure_rate": 1.0,
            }
        ]

    return {
        "calls": calls,
        "events_per_day": events_per_day,
        "error_rate_by_type": error_rate_by_type,
        "events_by_dimension": events_by_dimension,
        "auth_failure_rate": auth_failure_rate,
    }


def test_resolve_period_defaults_seven_days() -> None:
    now = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)
    start, end = resolve_period(None, None, now=now)
    assert end == now
    assert (end - start).days == 7


def test_resolve_period_rejects_inverted_range() -> None:
    with pytest.raises(Exception):
        resolve_period("2026-11-10", "2026-11-01")


def test_fill_zero_event_days() -> None:
    start = datetime(2026, 11, 1, tzinfo=timezone.utc)
    end = datetime(2026, 11, 4, tzinfo=timezone.utc)
    filled = fill_zero_event_days([{"date": "2026-11-02", "count": 5}], start, end)
    assert filled == [
        {"date": "2026-11-01", "count": 0},
        {"date": "2026-11-02", "count": 5},
        {"date": "2026-11-03", "count": 0},
    ]


def test_report_success_structure(client) -> None:
    stubs = _metric_stubs()
    configure_report_runtime(
        events_per_day=stubs["events_per_day"],
        error_rate_by_type=stubs["error_rate_by_type"],
        events_by_dimension=stubs["events_by_dimension"],
        auth_failure_rate=stubs["auth_failure_rate"],
    )
    response = client.get(
        "/telemetry/report",
        params={"start_date": "2026-11-01T00:00:00Z", "end_date": "2026-11-04T00:00:00Z"},
    )
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"period", "metrics"}
    assert body["period"]["from"].endswith("Z")
    assert body["period"]["to"].endswith("Z")
    assert set(body["metrics"]) == {
        "events_per_day",
        "error_rate_by_type",
        "events_by_dimension",
        "auth_failure_rate",
    }
    assert body["metrics"]["events_per_day"][0]["count"] == 0
    assert {"date": "2026-11-02", "count": 0} in body["metrics"]["events_per_day"]
    assert {"date": "2026-11-03", "count": 2} in body["metrics"]["events_per_day"]
    assert body["metrics"]["auth_failure_rate"][2]["auth_failure_rate"] == 1.0
    windows = [
        stubs["calls"]["events_per_day"][0],
        stubs["calls"]["error_rate_by_type"][0],
        stubs["calls"]["events_by_dimension"][0],
        stubs["calls"]["auth_failure_rate"][0],
    ]
    assert windows[0] == windows[1] == windows[2] == windows[3]


def test_report_invalid_date_422(client) -> None:
    response = client.get(
        "/telemetry/report",
        params={"start_date": "not-a-date", "end_date": "2026-11-04"},
    )
    assert response.status_code == 422
    assert "detail" in response.json()


def test_report_inverted_period_422(client) -> None:
    response = client.get(
        "/telemetry/report",
        params={"start_date": "2026-11-10", "end_date": "2026-11-01"},
    )
    assert response.status_code == 422


def test_report_cache_hit_skips_recompute(client) -> None:
    clock = {"now": 100.0}
    cache = ReportCache(ttl_seconds=60.0, clock=lambda: clock["now"])
    stubs = _metric_stubs()
    configure_report_runtime(
        cache=cache,
        events_per_day=stubs["events_per_day"],
        error_rate_by_type=stubs["error_rate_by_type"],
        events_by_dimension=stubs["events_by_dimension"],
        auth_failure_rate=stubs["auth_failure_rate"],
    )
    params = {"start_date": "2026-11-01T00:00:00Z", "end_date": "2026-11-03T00:00:00Z"}
    first = client.get("/telemetry/report", params=params)
    second = client.get("/telemetry/report", params=params)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert len(stubs["calls"]["events_per_day"]) == 1


def test_report_cache_expires(client) -> None:
    clock = {"now": 0.0}
    cache = ReportCache(ttl_seconds=60.0, clock=lambda: clock["now"])
    stubs = _metric_stubs()
    configure_report_runtime(
        cache=cache,
        events_per_day=stubs["events_per_day"],
        error_rate_by_type=stubs["error_rate_by_type"],
        events_by_dimension=stubs["events_by_dimension"],
        auth_failure_rate=stubs["auth_failure_rate"],
    )
    params = {"start_date": "2026-11-01", "end_date": "2026-11-03"}
    assert client.get("/telemetry/report", params=params).status_code == 200
    clock["now"] = 61.0
    assert client.get("/telemetry/report", params=params).status_code == 200
    assert len(stubs["calls"]["events_per_day"]) == 2


def test_report_different_windows_miss_cache(client) -> None:
    stubs = _metric_stubs()
    configure_report_runtime(
        cache=ReportCache(ttl_seconds=60.0),
        events_per_day=stubs["events_per_day"],
        error_rate_by_type=stubs["error_rate_by_type"],
        events_by_dimension=stubs["events_by_dimension"],
        auth_failure_rate=stubs["auth_failure_rate"],
    )
    assert (
        client.get(
            "/telemetry/report",
            params={"start_date": "2026-11-01", "end_date": "2026-11-03"},
        ).status_code
        == 200
    )
    assert (
        client.get(
            "/telemetry/report",
            params={"start_date": "2026-11-02", "end_date": "2026-11-04"},
        ).status_code
        == 200
    )
    assert len(stubs["calls"]["events_per_day"]) == 2


def test_report_repository_error_503(client) -> None:
    from repository import TelemetryRepositoryError

    def boom(start: datetime, end: datetime, **kwargs: Any) -> list:
        del start, end, kwargs
        raise TelemetryRepositoryError("down")

    configure_report_runtime(
        events_per_day=boom,
        error_rate_by_type=boom,
        events_by_dimension=boom,
        auth_failure_rate=boom,
    )
    response = client.get(
        "/telemetry/report",
        params={"start_date": "2026-11-01", "end_date": "2026-11-03"},
    )
    assert response.status_code == 503
    assert response.json() == {"detail": "Telemetry data temporarily unavailable"}


def test_report_empty_metrics(client) -> None:
    def empty(start: datetime, end: datetime, **kwargs: Any) -> list:
        del start, end, kwargs
        return []

    configure_report_runtime(
        events_per_day=empty,
        error_rate_by_type=empty,
        events_by_dimension=empty,
        auth_failure_rate=empty,
    )
    response = client.get(
        "/telemetry/report",
        params={"start_date": "2026-11-01", "end_date": "2026-11-03"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["metrics"]["error_rate_by_type"] == []
    assert body["metrics"]["events_by_dimension"] == []
    assert body["metrics"]["events_per_day"] == [
        {"date": "2026-11-01", "count": 0},
        {"date": "2026-11-02", "count": 0},
    ]
    assert body["metrics"]["auth_failure_rate"] == [
        {
            "date": "2026-11-01",
            "failed_attempts": 0,
            "succeeded_attempts": 0,
            "total_attempts": 0,
            "auth_failure_rate": 0.0,
        },
        {
            "date": "2026-11-02",
            "failed_attempts": 0,
            "succeeded_attempts": 0,
            "total_attempts": 0,
            "auth_failure_rate": 0.0,
        },
    ]
