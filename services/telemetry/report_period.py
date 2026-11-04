"""Reporting-period parsing, normalization, and calendar fill for Phase 2."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any


class ReportPeriodError(ValueError):
    """Invalid reporting period or unparseable ISO timestamps."""


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def parse_iso_datetime(raw: str) -> datetime:
    text = raw.strip()
    if not text:
        raise ReportPeriodError("empty timestamp")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        if len(text) == 10 and text[4] == "-" and text[7] == "-":
            day = date.fromisoformat(text)
            return datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ReportPeriodError(f"invalid ISO 8601 value: {raw}") from exc
    return _as_utc(parsed)


def default_period(*, now: datetime | None = None) -> tuple[datetime, datetime]:
    end = _as_utc(now or datetime.now(timezone.utc))
    start = end - timedelta(days=7)
    return start, end


def resolve_period(
    start_raw: str | None,
    end_raw: str | None,
    *,
    now: datetime | None = None,
) -> tuple[datetime, datetime]:
    if start_raw is None and end_raw is None:
        return default_period(now=now)
    default_start, default_end = default_period(now=now)
    start = parse_iso_datetime(start_raw) if start_raw is not None else default_start
    end = parse_iso_datetime(end_raw) if end_raw is not None else default_end
    if start >= end:
        raise ReportPeriodError("start_date must be earlier than end_date")
    return start, end


def period_payload(start: datetime, end: datetime) -> dict[str, str]:
    return {
        "from": start.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "to": end.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def _iter_utc_days(start: datetime, end: datetime):
    start_utc = _as_utc(start)
    end_utc = _as_utc(end)
    day = datetime(start_utc.year, start_utc.month, start_utc.day, tzinfo=timezone.utc)
    while day < end_utc:
        yield day.strftime("%Y-%m-%d")
        day += timedelta(days=1)


def fill_zero_event_days(
    rows: list[dict[str, Any]],
    start: datetime,
    end: datetime,
) -> list[dict[str, Any]]:
    """Ensure every UTC calendar day in [start, end) appears with a count."""
    by_date = {str(row.get("date")): int(row.get("count", 0)) for row in rows}
    return [{"date": key, "count": by_date.get(key, 0)} for key in _iter_utc_days(start, end)]


def fill_auth_failure_days(
    rows: list[dict[str, Any]],
    start: datetime,
    end: datetime,
) -> list[dict[str, Any]]:
    """Fill calendar days; zero-attempt days get rate 0.0 (no division by zero)."""
    by_date = {str(row.get("date")): row for row in rows}
    filled: list[dict[str, Any]] = []
    for key in _iter_utc_days(start, end):
        existing = by_date.get(key)
        if existing is None:
            filled.append(
                {
                    "date": key,
                    "failed_attempts": 0,
                    "succeeded_attempts": 0,
                    "total_attempts": 0,
                    "auth_failure_rate": 0.0,
                }
            )
        else:
            filled.append(
                {
                    "date": key,
                    "failed_attempts": int(existing.get("failed_attempts", 0)),
                    "succeeded_attempts": int(existing.get("succeeded_attempts", 0)),
                    "total_attempts": int(existing.get("total_attempts", 0)),
                    "auth_failure_rate": float(existing.get("auth_failure_rate", 0.0)),
                }
            )
    return filled
