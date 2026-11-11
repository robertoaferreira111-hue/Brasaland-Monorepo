"""Celery application for the Brasaland API.

The worker is a separate process:

    uv run celery -A app.celery_app worker --loglevel=info

Nothing in the FastAPI app starts this process.
"""

from __future__ import annotations

import os

from celery import Celery

from app.config import _int_env, _load_env_files

# Soft limit sits above the measured worst case: ensure_local_prefect can poll
# for 180s, and the ETL itself ran up to 85s. Hard limit leaves 60s after the
# soft limit so the task can exit before the worker kills it. Both are
# overridable. The Redis visibility timeout is twice the hard limit so a
# running task is not redelivered as lost.
_DEFAULT_SOFT_TIME_LIMIT = 300
_DEFAULT_TIME_LIMIT = 360

_load_env_files()

_redis_url = os.getenv("REDIS_URL", "").strip()
if not _redis_url:
    raise RuntimeError("REDIS_URL is not set")

_soft_time_limit = _int_env("CELERY_TASK_SOFT_TIME_LIMIT", _DEFAULT_SOFT_TIME_LIMIT)
_time_limit = _int_env("CELERY_TASK_TIME_LIMIT", _DEFAULT_TIME_LIMIT)
if _soft_time_limit >= _time_limit:
    raise RuntimeError(
        "CELERY_TASK_SOFT_TIME_LIMIT must be lower than CELERY_TASK_TIME_LIMIT"
    )

celery_app = Celery("brasaland", broker=_redis_url, backend=_redis_url)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=_soft_time_limit,
    task_time_limit=_time_limit,
    result_expires=86400,
    broker_connection_retry_on_startup=True,
    broker_transport_options={"visibility_timeout": _time_limit * 2},
)
celery_app.autodiscover_tasks(["app"], related_name="tasks", force=True)
