"""Unit tests for Phase 1 analysis metrics (mocked repository; no Supabase writes)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import pytest

import analysis
import repository


START = datetime(2026, 11, 2, 0, 0, tzinfo=timezone.utc)
END = datetime(2026, 11, 5, 0, 0, tzinfo=timezone.utc)


def _row(
    *,
    event_id: str,
    ts: str,
    event_type: str,
    level: str,
    tags: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": event_id,
        "timestamp": ts,
        "event_type": event_type,
        "level": level,
        "tags": tags if tags is not None else {},
    }


FIXTURE_ROWS = [
    _row(
        event_id="1",
        ts="2026-11-02T22:00:00+00:00",
        event_type="staff_login_failed",
        level="error",
        tags={"outcome": "invalid_credentials"},
    ),
    _row(
        event_id="2",
        ts="2026-11-03T10:00:00Z",
        event_type="staff_login_failed",
        level="error",
        tags={"outcome": "invalid_credentials"},
    ),
    _row(
        event_id="3",
        ts="2026-11-03T12:00:00+00:00",
        event_type="supplier_created",
        level="info",
        tags={"supplier_id": "1", "country": "Colombia"},
    ),
    _row(
        event_id="4",
        ts="2026-11-03T15:00:00+00:00",
        event_type="protected_route_unauthenticated",
        level="error",
        tags={"route": "/suppliers", "status_code": 401, "detail": "Not authenticated"},
    ),
    _row(
        event_id="5",
        ts="2026-11-04T01:30:00+00:00",
        event_type="request_validation_rejected",
        level="error",
        tags={"route": "/auth/login", "status_code": 422, "error_count": 2},
    ),
    _row(
        event_id="6",
        ts="2026-11-04T02:00:00+00:00",
        event_type="storage_unavailable",
        level="error",
        tags={"route": "/suppliers", "status_code": 500, "detail": "Storage unavailable"},
    ),
    _row(
        event_id="7",
        ts="not-a-timestamp",
        event_type="supplier_created",
        level="info",
        tags={"supplier_id": "2"},
    ),
]


@pytest.fixture()
def fetch_fixture():
    calls: list[dict[str, Any]] = []

    def _fetch(**kwargs: Any) -> list[dict[str, Any]]:
        calls.append(kwargs)
        start = kwargs["start_date"]
        end = kwargs["end_date"]
        assert start.tzinfo is not None and end.tzinfo is not None
        # Simulate SQL window: inclusive start, exclusive end on parsed timestamps.
        out: list[dict[str, Any]] = []
        for row in FIXTURE_ROWS:
            try:
                ts = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
            except ValueError:
                # Repository would still return the row; analysis drops invalid ts.
                out.append(row)
                continue
            if start <= ts < end:
                out.append(row)
        event_types = kwargs.get("event_types")
        if event_types:
            out = [r for r in out if r["event_type"] in set(event_types)]
        columns = kwargs.get("columns")
        if columns:
            out = [{k: r[k] for k in columns if k in r} for r in out]
        return out

    _fetch.calls = calls  # type: ignore[attr-defined]
    return _fetch


def test_events_per_day_groups_and_orders(fetch_fixture) -> None:
    result = analysis.events_per_day(START, END, fetch=fetch_fixture)
    assert result == [
        {"date": "2026-11-02", "count": 1},
        {"date": "2026-11-03", "count": 3},
        {"date": "2026-11-04", "count": 2},
    ]
    json.dumps(result)


def test_events_per_day_empty(fetch_fixture) -> None:
    empty_start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    empty_end = datetime(2026, 1, 2, tzinfo=timezone.utc)
    assert analysis.events_per_day(empty_start, empty_end, fetch=fetch_fixture) == []


def test_events_per_day_same_day_multiple(fetch_fixture) -> None:
    day = datetime(2026, 11, 3, tzinfo=timezone.utc)
    nxt = datetime(2026, 11, 4, tzinfo=timezone.utc)
    result = analysis.events_per_day(day, nxt, fetch=fetch_fixture)
    assert result == [{"date": "2026-11-03", "count": 3}]


def test_error_rate_by_type(fetch_fixture) -> None:
    result = analysis.error_rate_by_type(START, END, fetch=fetch_fixture)
    by_type = {row["event_type"]: row for row in result}
    assert by_type["staff_login_failed"]["total_events"] == 2
    assert by_type["staff_login_failed"]["error_events"] == 2
    assert by_type["staff_login_failed"]["error_rate"] == 100.0
    assert by_type["supplier_created"]["total_events"] == 1
    assert by_type["supplier_created"]["error_events"] == 0
    assert by_type["supplier_created"]["error_rate"] == 0.0
    json.dumps(result)


def test_error_rate_empty(fetch_fixture) -> None:
    empty_start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    empty_end = datetime(2026, 1, 2, tzinfo=timezone.utc)
    assert analysis.error_rate_by_type(empty_start, empty_end, fetch=fetch_fixture) == []


def test_events_by_dimension_route(fetch_fixture) -> None:
    result = analysis.events_by_dimension(START, END, dimension="route", fetch=fetch_fixture)
    by_value = {row["dimension_value"]: row["count"] for row in result}
    assert by_value["/suppliers"] == 2
    assert by_value["/auth/login"] == 1
    assert None in by_value  # business/login-failed rows without route
    assert all(row["dimension"] == "route" for row in result)
    json.dumps(result)


def test_events_by_dimension_missing_tags(fetch_fixture) -> None:
    def fetch_null_tags(**kwargs: Any) -> list[dict[str, Any]]:
        del kwargs
        return [
            _row(
                event_id="a",
                ts="2026-11-03T00:00:00Z",
                event_type="supplier_created",
                level="info",
                tags=None,
            )
        ]

    result = analysis.events_by_dimension(START, END, dimension="route", fetch=fetch_null_tags)
    assert result == [
        {"dimension": "route", "dimension_value": None, "count": 1}
    ]


def test_events_by_dimension_rejects_blank() -> None:
    with pytest.raises(ValueError):
        analysis.events_by_dimension(START, END, dimension="")


def test_utc_conversion_across_offsets(fetch_fixture) -> None:
    def fetch_offsets(**kwargs: Any) -> list[dict[str, Any]]:
        del kwargs
        return [
            _row(
                event_id="x",
                ts="2026-11-03T23:30:00-05:00",  # → 2026-11-04 04:30 UTC
                event_type="staff_login_failed",
                level="error",
                tags={},
            ),
            _row(
                event_id="y",
                ts="2026-11-04T00:31:21.41679+00:00",  # mixed fractional seconds
                event_type="supplier_created",
                level="info",
                tags={"supplier_id": "9"},
            ),
        ]

    result = analysis.events_per_day(START, END, fetch=fetch_offsets)
    assert result == [{"date": "2026-11-04", "count": 2}]


def test_independent_calls_share_window(fetch_fixture) -> None:
    analysis.events_per_day(START, END, fetch=fetch_fixture)
    analysis.error_rate_by_type(START, END, fetch=fetch_fixture)
    analysis.events_by_dimension(START, END, fetch=fetch_fixture)
    assert len(fetch_fixture.calls) == 3
    for call in fetch_fixture.calls:
        assert call["start_date"] == START
        assert call["end_date"] == END


def test_repository_rejects_naive_datetimes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-key")
    with pytest.raises(repository.TelemetryRepositoryError):
        repository.fetch_events(
            start_date=datetime(2026, 11, 1),
            end_date=datetime(2026, 11, 2, tzinfo=timezone.utc),
        )


def test_repository_builds_filters(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    class _Resp:
        status_code = 200

        def json(self) -> list:
            return []

    class _Client:
        def __init__(self, *args: object, **kwargs: object) -> None:
            del args, kwargs

        def __enter__(self) -> "_Client":
            return self

        def __exit__(self, *args: object) -> None:
            del args

        def get(self, endpoint: str, headers: dict, params: list) -> _Resp:
            captured["endpoint"] = endpoint
            captured["params"] = params
            captured["headers_have_key"] = "Authorization" in headers
            return _Resp()

    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-key")
    monkeypatch.setattr(repository.httpx, "Client", _Client)

    rows = repository.fetch_events(
        start_date=START,
        end_date=END,
        event_types=["staff_login_failed", "supplier_created"],
        columns=("id", "timestamp", "event_type"),
    )
    assert rows == []
    params = dict(captured["params"])
    # list of tuples may have duplicate timestamp keys — inspect raw list
    raw = captured["params"]
    assert ("select", "id,timestamp,event_type") in raw
    assert ("timestamp", f"gte.{START.isoformat().replace('+00:00', 'Z')}") in raw
    assert ("timestamp", f"lt.{END.isoformat().replace('+00:00', 'Z')}") in raw
    assert ("event_type", "in.(staff_login_failed,supplier_created)") in raw
    assert captured["headers_have_key"] is True


def test_repository_empty_window_short_circuits(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*args: object, **kwargs: object) -> object:
        raise AssertionError("should not call httpx")

    monkeypatch.setattr(repository.httpx, "Client", boom)
    assert (
        repository.fetch_events(
            start_date=END,
            end_date=START,
        )
        == []
    )


def test_auth_failure_rate_failures_only(fetch_fixture) -> None:
    result = analysis.auth_failure_rate(START, END, fetch=fetch_fixture)
    # Fixture has staff_login_failed on 2026-11-02 (1) and 2026-11-03 (1).
    by_date = {row["date"]: row for row in result}
    assert by_date["2026-11-02"]["failed_attempts"] == 1
    assert by_date["2026-11-02"]["succeeded_attempts"] == 0
    assert by_date["2026-11-02"]["total_attempts"] == 1
    assert by_date["2026-11-02"]["auth_failure_rate"] == 1.0
    assert by_date["2026-11-03"]["failed_attempts"] == 1
    assert by_date["2026-11-03"]["auth_failure_rate"] == 1.0
    json.dumps(result)


def test_auth_failure_rate_with_successes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        analysis,
        "AUTH_FAILED_EVENT_TYPES",
        ("staff_login_failed",),
    )
    monkeypatch.setattr(
        analysis,
        "AUTH_SUCCEEDED_EVENT_TYPES",
        ("staff_login_succeeded",),
    )
    monkeypatch.setattr(
        analysis,
        "AUTH_ATTEMPT_EVENT_TYPES",
        ("staff_login_failed", "staff_login_succeeded"),
    )

    def fetch(**kwargs: Any) -> list[dict[str, Any]]:
        del kwargs
        return [
            _row(
                event_id="f1",
                ts="2026-11-03T10:00:00Z",
                event_type="staff_login_failed",
                level="error",
                tags={"outcome": "invalid_credentials"},
            ),
            _row(
                event_id="s1",
                ts="2026-11-03T11:00:00Z",
                event_type="staff_login_succeeded",
                level="info",
                tags={"outcome": "ok"},
            ),
            _row(
                event_id="s2",
                ts="2026-11-03T12:00:00Z",
                event_type="staff_login_succeeded",
                level="info",
                tags={"outcome": "ok"},
            ),
        ]

    result = analysis.auth_failure_rate(START, END, fetch=fetch)
    assert len(result) == 1
    assert result[0]["date"] == "2026-11-03"
    assert result[0]["failed_attempts"] == 1
    assert result[0]["succeeded_attempts"] == 2
    assert result[0]["total_attempts"] == 3
    assert result[0]["auth_failure_rate"] == pytest.approx(1 / 3)
    json.dumps(result)


def test_auth_failure_rate_empty(fetch_fixture) -> None:
    empty_start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    empty_end = datetime(2026, 1, 2, tzinfo=timezone.utc)
    assert analysis.auth_failure_rate(empty_start, empty_end, fetch=fetch_fixture) == []


def test_repository_propagates_http_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Resp:
        status_code = 500

        def json(self) -> list:
            return []

    class _Client:
        def __init__(self, *args: object, **kwargs: object) -> None:
            del args, kwargs

        def __enter__(self) -> "_Client":
            return self

        def __exit__(self, *args: object) -> None:
            del args

        def get(self, *args: object, **kwargs: object) -> _Resp:
            del args, kwargs
            return _Resp()

    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-key")
    monkeypatch.setattr(repository.httpx, "Client", _Client)
    with pytest.raises(repository.TelemetryRepositoryError):
        repository.fetch_events(start_date=START, end_date=END)
