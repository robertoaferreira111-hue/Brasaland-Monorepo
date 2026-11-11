"""HTTP adapters for the Weekly Location Cost & Waste pipeline.

These routes call data/pipelines/pipeline.py. They do not reimplement extract,
transform, or load, and they do not write telemetry_events.

GET /reporting/weekly-location-performance returns only week_start and locations.
Each location has the eight briefing fields. There is no location registry, so
the list is the locations observed in telemetry for that week.

Errors follow the staff API: 401 when the caller is not authenticated, 422 when
week_start is not a Monday or is not a completed week, 404 when that week has
no published rows, and 503 when reporting storage is unavailable.
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict

_REPO = Path(__file__).resolve().parents[2]
_API = _REPO / "services" / "api"
_PIPELINES = _REPO / "data" / "pipelines"
sys.path.insert(0, str(_API))
sys.path.insert(0, str(_PIPELINES))

import redis

from app.config import _load_env_files  # noqa: E402
from app.deps import current_user_email  # noqa: E402
from app.tasks.weekly_pipeline import run_weekly_pipeline  # noqa: E402
from pipeline import (  # noqa: E402
    get_latest_pipeline_run,
    get_weekly_location_performance,
    last_completed_week_start,
    live_lease_run_id,
)


def _open_broker() -> None:
    """Connect once at import so the first enqueue does not pay for setup."""
    _load_env_files()
    url = os.getenv("REDIS_URL", "").strip()
    if not url:
        return
    client = redis.Redis.from_url(url, socket_connect_timeout=1, socket_timeout=1)
    client.ping()
    with run_weekly_pipeline.app.connection_for_write() as connection:
        connection.ensure_connection(max_retries=0, timeout=1)


try:
    _open_broker()
except Exception:
    logging.getLogger("brasaland.reporting").warning("Redis broker was not reachable at startup")

router = APIRouter(prefix="/reporting", tags=["reporting"])

_LOCATION_FIELDS = (
    "location_id",
    "country",
    "total_purchase_cost",
    "total_waste_cost",
    "waste_ratio",
    "stockout_events_count",
    "price_alert_events_count",
    "currency",
)


class TriggerBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    week_start: date | None = None
    trigger_type: Literal["manual", "backfill", "schedule"] | None = None


class LocationPerformance(BaseModel):
    location_id: str
    country: str
    total_purchase_cost: float
    total_waste_cost: float
    waste_ratio: float
    stockout_events_count: int
    price_alert_events_count: int
    currency: str


def _storage_unavailable(exc: Exception) -> HTTPException:
    if isinstance(exc, RuntimeError) and "DATABASE_URL" in str(exc):
        return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Reporting storage unavailable")
    if type(exc).__name__ in {"OperationalError", "InterfaceError"}:
        return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Reporting storage unavailable")
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Reporting request failed")


def _require_monday(value: date, name: str) -> date:
    if value.weekday() != 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{name} must be a Monday")
    if value > last_completed_week_start() + timedelta(days=7):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{name} is not a completed week")
    return value


def _accepted_trigger(body: TriggerBody) -> str:
    if body.trigger_type == "schedule":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="schedule is not accepted on this route",
        )
    if body.week_start is None:
        if body.trigger_type not in (None, "manual"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="an explicit week_start is required for a backfill",
            )
        return "manual"
    if body.trigger_type not in (None, "backfill"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="an explicit week_start is a backfill",
        )
    return "backfill"


@router.get("/pipeline-runs/latest")
def latest_pipeline_run(_email: str = Depends(current_user_email)) -> dict[str, Any]:
    try:
        row = get_latest_pipeline_run()
    except Exception as exc:
        raise _storage_unavailable(exc) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No pipeline run has been recorded")
    return row


class QueueUnavailable(Exception):
    """The Celery broker could not accept a task."""


def _enqueue_weekly_pipeline(week_start: date | None, trigger_type: str) -> str:
    """Publish identifiers only. A one-second broker check avoids a hung request."""
    _load_env_files()
    url = os.getenv("REDIS_URL", "").strip()
    if not url:
        raise QueueUnavailable("REDIS_URL is not set")
    client = redis.Redis.from_url(url, socket_connect_timeout=1, socket_timeout=1)
    try:
        client.ping()
    except Exception as exc:
        raise QueueUnavailable("Redis is unreachable") from exc
    week = None if week_start is None else week_start.isoformat()
    try:
        queued = run_weekly_pipeline.delay(week, trigger_type)
    except Exception as exc:
        raise QueueUnavailable("Redis is unreachable") from exc
    return str(queued.id)


@router.post("/pipeline-runs", status_code=status.HTTP_202_ACCEPTED)
def trigger_pipeline_run(body: TriggerBody, _email: str = Depends(current_user_email)) -> dict[str, str]:
    try:
        if body.week_start is not None:
            _require_monday(body.week_start, "week_start")
        trigger_type = _accepted_trigger(body)
        active = live_lease_run_id()
    except HTTPException:
        raise
    except Exception as exc:
        raise _storage_unavailable(exc) from exc
    if active is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "pipeline_run_in_progress",
                "message": "A weekly_location_cost_waste run already holds a live lease",
                "active_run_id": active,
            },
        )
    try:
        task_id = _enqueue_weekly_pipeline(body.week_start, trigger_type)
    except QueueUnavailable as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Queue unavailable") from exc
    return {"task_id": task_id}


@router.get("/weekly-location-performance")
def weekly_location_performance(
    week_start: date | None = None,
    location_id: str | None = None,
    country: str | None = Query(default=None, pattern="^(CO|US)$"),
    _email: str = Depends(current_user_email),
) -> dict[str, Any]:
    if week_start is not None:
        _require_monday(week_start, "week_start")
    try:
        rows = get_weekly_location_performance(week_start, week_start, location_id, country)
    except Exception as exc:
        raise _storage_unavailable(exc) from exc
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No published week in the requested range")
    published = week_start or rows[0]["week_start"]
    locations = [
        LocationPerformance.model_validate({field: row[field] for field in _LOCATION_FIELDS}).model_dump(mode="json")
        for row in rows
    ]
    return {"week_start": published, "locations": locations}
