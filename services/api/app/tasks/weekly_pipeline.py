"""Run one weekly pipeline inside the Celery worker.

The message carries only week_start (an ISO date, or null) and trigger_type.
The ETL runs in this process via execute_flow. start_pipeline_run is not used:
that function returns after starting a daemon thread.
"""

from __future__ import annotations

import importlib
import logging
import os
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any

from celery.exceptions import MaxRetriesExceededError, Retry

from app.celery_app import celery_app
from app.dlq import record_dlq_entry

logger = logging.getLogger("brasaland.tasks.pipeline")

_FAIL_FOR_TEST = "BRASALAND_PIPELINE_TASK_FAIL_FOR_TEST"
_pipeline: Any = None


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    candidates: list[Path] = []
    configured = os.environ.get("BRASALAND_ROOT")
    if configured:
        candidates.append(Path(configured))
    if len(here.parents) > 4:
        candidates.append(here.parents[4])
    candidates.append(Path("/opt/brasaland"))
    for path in candidates:
        if (path / "data" / "pipelines" / "pipeline.py").is_file():
            return path
    raise RuntimeError("data/pipelines/pipeline.py is missing")


def _pipeline_module() -> Any:
    """Import pipeline the way services/reporting/router.py does."""
    global _pipeline
    if _pipeline is not None:
        return _pipeline
    root = _repo_root()
    for entry in (root / "services" / "api", root / "data" / "pipelines"):
        text = str(entry)
        if text not in sys.path:
            sys.path.insert(0, text)
    _pipeline = importlib.import_module("pipeline")
    return _pipeline


def _week_start(value: str | None) -> date | None:
    if value is None or value.strip() == "":
        return None
    return date.fromisoformat(value)


def _fail_for_test() -> bool:
    raw = os.getenv(_FAIL_FOR_TEST, "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _log(task_id: str, attempt: int, status: str, duration_ms: int, error: str | None) -> None:
    if error is None:
        logger.info(
            "task_id=%s attempt=%s status=%s duration_ms=%s",
            task_id,
            attempt,
            status,
            duration_ms,
        )
        return
    logger.error(
        "task_id=%s attempt=%s status=%s duration_ms=%s error=%s",
        task_id,
        attempt,
        status,
        duration_ms,
        error,
    )


@celery_app.task(bind=True, max_retries=3, name="app.tasks.run_weekly_pipeline")
def run_weekly_pipeline(
    self: Any,
    week_start: str | None = None,
    trigger_type: str = "manual",
) -> dict[str, str]:
    """Run the weekly ETL. SoftTimeLimitExceeded follows the same failure path."""
    started = time.monotonic()
    attempt = self.request.retries + 1
    task_id = self.request.id or ""
    try:
        if _fail_for_test():
            raise RuntimeError(f"{_FAIL_FOR_TEST} is set")
        result = _pipeline_module().execute_flow(
            week_start=_week_start(week_start),
            trigger_type=trigger_type,
        )
    except Retry:
        raise
    except Exception as exc:
        duration_ms = int((time.monotonic() - started) * 1000)
        message = str(exc).strip() or exc.__class__.__name__
        _log(task_id, attempt, "failure", duration_ms, message)
        # Celery 5.7 re-raises exc when retry() is past max_retries, so the
        # dead-letter row is written before that call. MaxRetriesExceededError
        # is still recorded if this version raises it instead.
        if self.request.retries >= self.max_retries:
            record_dlq_entry(
                task_id=task_id,
                task_name=self.name,
                attempt=attempt,
                error_message=message,
            )
            raise
        countdown = 10 * (2 ** self.request.retries)
        try:
            raise self.retry(exc=exc, countdown=countdown)
        except MaxRetriesExceededError:
            record_dlq_entry(
                task_id=task_id,
                task_name=self.name,
                attempt=attempt,
                error_message=message,
            )
            raise
    duration_ms = int((time.monotonic() - started) * 1000)
    _log(task_id, attempt, "success", duration_ms, None)
    return {"run_id": str(result["run_id"]), "status": str(result["status"])}
