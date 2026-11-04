"""GET /telemetry/report — Phase 2 reporting endpoint."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Callable

from fastapi import APIRouter, HTTPException, Query, status

import analysis
from cache import ReportCache
from report_period import (
    ReportPeriodError,
    fill_auth_failure_days,
    fill_zero_event_days,
    period_payload,
    resolve_period,
)
from repository import TelemetryRepositoryError

logger = logging.getLogger("brasaland.telemetry.report")

router = APIRouter(prefix="/telemetry", tags=["telemetry"])

_report_cache = ReportCache(ttl_seconds=60.0)

# Injectable for tests.
_cache: ReportCache = _report_cache
_now_fn: Callable[[], datetime] | None = None
_events_per_day = analysis.events_per_day
_error_rate_by_type = analysis.error_rate_by_type
_events_by_dimension = analysis.events_by_dimension
_auth_failure_rate = analysis.auth_failure_rate


def configure_report_runtime(
    *,
    cache: ReportCache | None = None,
    now_fn: Callable[[], datetime] | None = None,
    events_per_day: Callable[..., list] | None = None,
    error_rate_by_type: Callable[..., list] | None = None,
    events_by_dimension: Callable[..., list] | None = None,
    auth_failure_rate: Callable[..., list] | None = None,
) -> None:
    """Test hook to swap cache, clock, and metric callables."""
    global _cache, _now_fn
    global _events_per_day, _error_rate_by_type, _events_by_dimension
    global _auth_failure_rate
    if cache is not None:
        _cache = cache
    _now_fn = now_fn
    if events_per_day is not None:
        _events_per_day = events_per_day
    if error_rate_by_type is not None:
        _error_rate_by_type = error_rate_by_type
    if events_by_dimension is not None:
        _events_by_dimension = events_by_dimension
    if auth_failure_rate is not None:
        _auth_failure_rate = auth_failure_rate


def reset_report_runtime() -> None:
    configure_report_runtime(
        cache=_report_cache,
        now_fn=None,
        events_per_day=analysis.events_per_day,
        error_rate_by_type=analysis.error_rate_by_type,
        events_by_dimension=analysis.events_by_dimension,
        auth_failure_rate=analysis.auth_failure_rate,
    )
    _report_cache.clear()


def _build_report(start: datetime, end: datetime) -> dict[str, Any]:
    per_day = _events_per_day(start, end)
    error_rates = _error_rate_by_type(start, end)
    by_dimension = _events_by_dimension(start, end)
    auth_rates = _auth_failure_rate(start, end)
    return {
        "period": period_payload(start, end),
        "metrics": {
            "events_per_day": fill_zero_event_days(per_day, start, end),
            "error_rate_by_type": error_rates,
            "events_by_dimension": by_dimension,
            "auth_failure_rate": fill_auth_failure_days(auth_rates, start, end),
        },
    }


@router.get("/report")
def telemetry_report(
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
) -> dict[str, Any]:
    try:
        start, end = resolve_period(
            start_date,
            end_date,
            now=_now_fn() if _now_fn is not None else None,
        )
    except ReportPeriodError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    cached = _cache.get(start, end)
    if cached is not None:
        return cached

    try:
        payload = _build_report(start, end)
    except TelemetryRepositoryError as exc:
        logger.exception("telemetry report repository failure")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Telemetry data temporarily unavailable",
        ) from exc
    except Exception as exc:
        logger.exception("telemetry report analysis failure")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Telemetry report could not be generated",
        ) from exc

    _cache.set(start, end, payload)
    return payload
