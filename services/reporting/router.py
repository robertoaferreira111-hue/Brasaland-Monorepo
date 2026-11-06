"""HTTP adapters for the Weekly Location Cost & Waste pipeline.

These routes call data/pipelines/pipeline.py. They do not reimplement extract,
transform, or load, and they do not write telemetry_events.
"""

from __future__ import annotations

import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict

_REPO = Path(__file__).resolve().parents[2]
_API = _REPO / "services" / "api"
_PIPELINES = _REPO / "data" / "pipelines"
sys.path.insert(0, str(_API))
sys.path.insert(0, str(_PIPELINES))

from app.deps import current_user_email  # noqa: E402
from pipeline import (  # noqa: E402
    PipelineLeaseHeld,
    business_performance_etl_flow,
    get_latest_pipeline_run,
    get_weekly_location_performance,
    last_completed_week_start,
)

router = APIRouter(prefix="/reporting", tags=["reporting"])


class TriggerBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    week_start: date | None = None
    trigger_type: Literal["manual", "backfill"] = "manual"


class LocationRow(BaseModel):
    location_id: str
    country: str
    week_start: date
    total_purchase_cost: float
    total_waste_cost: float
    waste_ratio: float
    stockout_events_count: int
    price_alert_events_count: int
    currency: str
    computed_at: datetime


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


@router.get("/pipeline-runs/latest")
def latest_pipeline_run(_email: str = Depends(current_user_email)) -> dict[str, Any]:
    try:
        row = get_latest_pipeline_run()
    except Exception as exc:
        raise _storage_unavailable(exc) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No pipeline run has been recorded")
    return row


@router.post("/pipeline-runs", status_code=status.HTTP_202_ACCEPTED)
def trigger_pipeline_run(body: TriggerBody, _email: str = Depends(current_user_email)) -> dict[str, Any]:
    try:
        if body.week_start is not None:
            _require_monday(body.week_start, "week_start")
        return business_performance_etl_flow.fn(body.week_start, body.trigger_type)
    except PipelineLeaseHeld as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "pipeline_run_in_progress",
                "message": "A weekly_location_cost_waste run already holds a live lease",
                "active_run_id": exc.active_run_id,
            },
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except RuntimeError as exc:
        if "DATABASE_URL" in str(exc):
            raise _storage_unavailable(exc) from exc
        raise


@router.get("/weekly-location-performance")
def weekly_location_performance(
    week_start: date | None = None,
    week_end: date | None = None,
    location_id: str | None = None,
    country: str | None = Query(default=None, pattern="^(CO|US)$"),
    _email: str = Depends(current_user_email),
) -> dict[str, Any]:
    if week_start is not None:
        _require_monday(week_start, "week_start")
    if week_end is not None:
        _require_monday(week_end, "week_end")
    if week_start is not None and week_end is not None and week_end < week_start:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="week_end is before week_start")
    try:
        rows = get_weekly_location_performance(week_start, week_end, location_id, country)
    except Exception as exc:
        raise _storage_unavailable(exc) from exc
    if not rows and (week_start is not None or week_end is not None):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No published week in the requested range")
    locations = [LocationRow.model_validate(row).model_dump(mode="json") for row in rows]
    start = week_start or (rows[0]["week_start"] if rows else None)
    end = week_end or start
    return {
        "week_start": start,
        "week_end": end,
        "filters": {"location_id": location_id, "country": country},
        "data_status": "complete" if locations else "no_rows",
        "coverage": "observed_locations_only",
        "locations": locations,
    }
