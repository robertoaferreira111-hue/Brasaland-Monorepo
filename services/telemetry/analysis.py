"""Phase 1 operational metrics over Supabase `telemetry_events`.

Pipeline per metric: LOAD (SQL) → REFINE → CONVERT → GROUP → AGGREGATE → SERVE.

Error classification uses the stored `level` column produced by capture
(`error` for technical failures, `info` for successful business events).
HTTP status codes inside tags are not treated as a universal error definition.

`events_by_dimension` defaults to tag key `route`, which is populated on the
verified technical events from the catalogue (`protected_route_unauthenticated`,
`request_validation_rejected`, `storage_unavailable`).

`auth_failure_rate` uses verified catalogue auth events only:
- failed attempts: `staff_login_failed`
- successful attempts: none are defined in the approved catalogue / capture
  (no `staff_login_succeeded`). The denominator is therefore
  failed + succeeded among *recorded* auth attempt events. Until a success
  event exists in capture, days with failures report rate 1.0.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Callable

import pandas as pd

try:
    from repository import fetch_events
except ImportError:  # package-style import when loaded under services.telemetry
    from .repository import fetch_events

FetchFn = Callable[..., list[dict[str, Any]]]

# Verified auth attempt event types from docs/telemetry (catalogue).
AUTH_FAILED_EVENT_TYPES = ("staff_login_failed",)
# No login-success event exists in the approved catalogue; keep the tuple for
# SQL IN (...) compatibility if one is added later without inventing types now.
AUTH_SUCCEEDED_EVENT_TYPES: tuple[str, ...] = ()
AUTH_ATTEMPT_EVENT_TYPES = AUTH_FAILED_EVENT_TYPES + AUTH_SUCCEEDED_EVENT_TYPES


def _records_to_frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(
            columns=["id", "timestamp", "event_type", "level", "tags"]
        )
    return pd.DataFrame.from_records(rows)


def _normalize_tags(value: Any) -> dict[str, Any]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _prepare_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Refine + convert timestamps (UTC) before any temporal groupby."""
    if df.empty:
        return df.copy()

    out = df.copy()
    if "tags" not in out.columns:
        out["tags"] = [{} for _ in range(len(out))]
    else:
        out["tags"] = out["tags"].map(_normalize_tags)
    # ISO8601 handles mixed fractional-second lengths from Supabase timestamptz.
    out["timestamp"] = pd.to_datetime(
        out["timestamp"], utc=True, format="ISO8601", errors="coerce"
    )
    out = out.dropna(subset=["timestamp"])
    out["date"] = out["timestamp"].dt.strftime("%Y-%m-%d")
    out["is_error"] = out["level"].astype(str).str.lower().eq("error")
    return out


def _as_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df.empty:
        return []
    # Convert pandas/numpy scalars to plain Python for JSON safety.
    return json.loads(df.to_json(orient="records", date_format="iso"))


def events_per_day(
    start_date: datetime,
    end_date: datetime,
    *,
    fetch: FetchFn = fetch_events,
) -> list[dict[str, Any]]:
    """How many telemetry events occurred each day?"""
    rows = fetch(
        start_date=start_date,
        end_date=end_date,
        columns=("id", "timestamp", "event_type", "level", "tags"),
    )
    df = _prepare_frame(_records_to_frame(rows))
    if df.empty:
        return []

    result = (
        df.groupby("date", sort=True)["id"]
        .count()
        .reset_index()
        .rename(columns={"id": "count"})
    )
    return _as_records(result)


def error_rate_by_type(
    start_date: datetime,
    end_date: datetime,
    *,
    fetch: FetchFn = fetch_events,
) -> list[dict[str, Any]]:
    """What share of events are errors for each event_type?"""
    rows = fetch(
        start_date=start_date,
        end_date=end_date,
        columns=("id", "timestamp", "event_type", "level", "tags"),
    )
    df = _prepare_frame(_records_to_frame(rows))
    if df.empty:
        return []

    grouped = (
        df.groupby("event_type", sort=True)
        .agg(
            total_events=("id", "count"),
            error_events=("is_error", "sum"),
        )
        .reset_index()
    )
    grouped["error_events"] = grouped["error_events"].astype(int)
    rates = (100.0 * grouped["error_events"] / grouped["total_events"]).where(
        grouped["total_events"] > 0, 0.0
    )
    grouped["error_rate"] = rates.round(4)
    return _as_records(grouped)


def events_by_dimension(
    start_date: datetime,
    end_date: datetime,
    *,
    dimension: str = "route",
    fetch: FetchFn = fetch_events,
) -> list[dict[str, Any]]:
    """How are events distributed across a verified tags dimension?

    Default dimension is `route` (present on technical catalogue events).
    Missing/null dimension values are retained as null in the output.
    """
    if not dimension or not isinstance(dimension, str):
        raise ValueError("dimension must be a non-empty tag key")

    rows = fetch(
        start_date=start_date,
        end_date=end_date,
        columns=("id", "timestamp", "event_type", "level", "tags"),
    )
    df = _prepare_frame(_records_to_frame(rows))
    if df.empty:
        return []

    df[dimension] = df["tags"].map(
        lambda tags: tags.get(dimension) if isinstance(tags, dict) else None
    )
    result = (
        df.groupby(dimension, sort=True, dropna=False)["id"]
        .count()
        .reset_index()
        .rename(columns={"id": "count", dimension: "dimension_value"})
    )
    result.insert(0, "dimension", dimension)
    return _as_records(result)


def auth_failure_rate(
    start_date: datetime,
    end_date: datetime,
    *,
    fetch: FetchFn = fetch_events,
) -> list[dict[str, Any]]:
    """Daily staff login failure rate among recorded auth attempt events.

    rate = failed / (failed + succeeded), values in [0.0, 1.0].
    Days with zero recorded attempts are omitted (no division by zero).
    """
    if not AUTH_ATTEMPT_EVENT_TYPES:
        return []

    rows = fetch(
        start_date=start_date,
        end_date=end_date,
        event_types=list(AUTH_ATTEMPT_EVENT_TYPES),
        columns=("id", "timestamp", "event_type", "level", "tags"),
    )
    df = _prepare_frame(_records_to_frame(rows))
    if df.empty:
        return []

    failed_set = set(AUTH_FAILED_EVENT_TYPES)
    succeeded_set = set(AUTH_SUCCEEDED_EVENT_TYPES)
    df["is_failed_auth"] = df["event_type"].isin(failed_set)
    df["is_succeeded_auth"] = df["event_type"].isin(succeeded_set)

    grouped = (
        df.groupby("date", sort=True)
        .agg(
            failed_attempts=("is_failed_auth", "sum"),
            succeeded_attempts=("is_succeeded_auth", "sum"),
        )
        .reset_index()
    )
    grouped["failed_attempts"] = grouped["failed_attempts"].astype(int)
    grouped["succeeded_attempts"] = grouped["succeeded_attempts"].astype(int)
    grouped["total_attempts"] = (
        grouped["failed_attempts"] + grouped["succeeded_attempts"]
    )
    grouped = grouped[grouped["total_attempts"] > 0]
    if grouped.empty:
        return []

    grouped["auth_failure_rate"] = (
        grouped["failed_attempts"] / grouped["total_attempts"]
    ).round(6)
    return _as_records(
        grouped[
            [
                "date",
                "failed_attempts",
                "succeeded_attempts",
                "total_attempts",
                "auth_failure_rate",
            ]
        ]
    )
