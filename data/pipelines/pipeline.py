"""Weekly Location Cost & Waste pipeline.

From the repository root:

    python3 data/pipelines/pipeline.py

``python`` is the same command when that executable is on ``PATH``. This machine
has ``python3`` and not ``python``. If the interpreter does not already have
``prefect`` and ``psycopg``, the process re-executes itself with
``uv run --project services/api``. The first run starts a local Prefect API on
127.0.0.1:8765 and keeps its files under ``.prefect-local/`` so retries, the
transform cache, and task state survive the next command. Later runs reuse
that API. Business rows are read and written only through ``DATABASE_URL`` on
the local dev Postgres.

The flow reads public.telemetry_events and writes only reporting tables.
It does not modify telemetry_events.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import uuid4

_PIPELINES = Path(__file__).resolve().parent
_REPO = _PIPELINES.parents[1]
_API_ROOT = _REPO / "services" / "api"


def _ensure_interpreter() -> None:
    """Re-exec under the API project when this interpreter cannot import Prefect."""
    if os.environ.get("BRASALAND_PIPELINE_REEXEC") == "1":
        return
    try:
        import prefect  # noqa: F401
        import psycopg  # noqa: F401
    except ImportError:
        uv = shutil.which("uv")
        if uv is None:
            raise SystemExit(
                "python data/pipelines/pipeline.py needs uv on PATH so it can "
                "run with the services/api environment."
            )
        os.environ["BRASALAND_PIPELINE_REEXEC"] = "1"
        os.execv(
            uv,
            [
                uv,
                "run",
                "--project",
                str(_API_ROOT),
                "python",
                str(Path(__file__).resolve()),
                *sys.argv[1:],
            ],
        )


_ensure_interpreter()
sys.path.insert(0, str(_API_ROOT))
sys.path.insert(0, str(_PIPELINES))

import db  # noqa: E402
import prefect  # noqa: E402
import psycopg  # noqa: E402
from prefect import flow, task  # noqa: E402
from prefect.context import refresh_global_settings_context  # noqa: E402

logger = logging.getLogger("brasaland.pipeline")

PIPELINE_NAME = "weekly_location_cost_waste"
EVENT_TYPES = (
    "inbound_order_created",
    "outbound_order_created",
    "stock_waste_registered",
    "stock_threshold_triggered",
    "ingredient_price_variance_detected",
)
KPI_EVENT_TYPES = frozenset(EVENT_TYPES) - {"outbound_order_created"}
CURRENCY_FOR_COUNTRY = {"CO": "COP", "US": "USD"}
LEASE = timedelta(minutes=15)
HEARTBEAT_INTERVAL = 5
PREFECT_PORT = 8765
# Three attempts after the first failure. Delays are 1s, 2s, and 4s, each
# jittered by Prefect, and only connection or transport errors are retried.
RETRY_DELAYS = [1, 2, 4]
TAKEOVER_REASON = (
    "Lease expired before the run finished; a later trigger marked this run "
    "failed and took over."
)
_ATTEMPT_COUNTS: dict[str, dict[str, int]] = {}
_REQUIRED = {
    "inbound_order_created": ("location_id", "country", "quantity", "unit_cost", "currency"),
    "outbound_order_created": ("location_id", "country", "quantity", "currency"),
    "stock_waste_registered": ("location_id", "country", "quantity", "unit_cost", "currency"),
    "stock_threshold_triggered": ("location_id", "country", "currency"),
    "ingredient_price_variance_detected": ("location_id", "country", "currency"),
}

EXTRACT_SQL = """
select id::text, timestamp, event_type, tags
from public.telemetry_events
where event_type = any(%(event_types)s)
  and timestamp >= %(window_start)s
  and timestamp < %(window_end)s
  and (
    timestamp > %(last_timestamp)s
    or (timestamp = %(last_timestamp)s and id > %(last_id)s::uuid)
  )
order by timestamp asc, id asc
limit %(batch_size)s
"""

UPSERT_SQL = """
insert into reporting.weekly_location_performance (
    location_id, country, week_start, total_purchase_cost, total_waste_cost,
    waste_ratio, stockout_events_count, price_alert_events_count, currency, computed_at
) values (
    %(location_id)s, %(country)s, %(week_start)s, %(total_purchase_cost)s,
    %(total_waste_cost)s, %(waste_ratio)s, %(stockout_events_count)s,
    %(price_alert_events_count)s, %(currency)s, %(computed_at)s
)
on conflict (location_id, week_start) do update set
    country = excluded.country,
    total_purchase_cost = excluded.total_purchase_cost,
    total_waste_cost = excluded.total_waste_cost,
    waste_ratio = excluded.waste_ratio,
    stockout_events_count = excluded.stockout_events_count,
    price_alert_events_count = excluded.price_alert_events_count,
    currency = excluded.currency,
    computed_at = excluded.computed_at
"""

DELETE_STALE_SQL = """
delete from reporting.weekly_location_performance
where week_start = %(week_start)s
  and not (location_id = any(%(location_ids)s))
"""


class PipelineLeaseHeld(RuntimeError):
    """Another run of this pipeline is already in the running state."""

    def __init__(self, active_run_id: str) -> None:
        super().__init__(active_run_id)
        self.active_run_id = active_run_id


class TransformError(RuntimeError):
    """A KPI-bearing source row cannot be published."""


def open_connection() -> Any:
    return db.connect()


def pipeline_version() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=_REPO,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def last_completed_week_start(today: date | None = None) -> date:
    current = today or datetime.now(timezone.utc).date()
    monday = current - timedelta(days=current.weekday())
    return monday - timedelta(days=7)


def _as_monday(value: date) -> date:
    if value.weekday() != 0:
        raise ValueError("week_start must be a Monday")
    if value > last_completed_week_start():
        raise ValueError("week_start must be a completed UTC week")
    return value


def source_window(week_start: date | None, trigger_type: str) -> tuple[datetime, datetime, date, list[date]]:
    """Half-open UTC window and the Monday partitions it recomputes."""
    if trigger_type == "schedule" or week_start is None:
        end_monday = last_completed_week_start() + timedelta(days=7)
        start_monday = end_monday - timedelta(days=14)
        requested = end_monday - timedelta(days=7)
    else:
        requested = _as_monday(week_start)
        start_monday = requested
        end_monday = requested + timedelta(days=7)
    weeks = []
    cursor = start_monday
    while cursor < end_monday:
        weeks.append(cursor)
        cursor += timedelta(days=7)
    start = datetime(start_monday.year, start_monday.month, start_monday.day, tzinfo=timezone.utc)
    end = datetime(end_monday.year, end_monday.month, end_monday.day, tzinfo=timezone.utc)
    return start, end, requested, weeks


def _tags(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    raise TransformError("tags must be an object")


def _money(quantity: Any, unit_cost: Any) -> Decimal:
    if isinstance(quantity, bool) or isinstance(unit_cost, bool):
        raise TransformError("quantity and unit_cost must be numbers")
    try:
        amount = Decimal(str(quantity)) * Decimal(str(unit_cost))
    except Exception as exc:
        raise TransformError("quantity and unit_cost must be numbers") from exc
    if amount <= 0:
        raise TransformError("cost events require a positive quantity and unit_cost")
    return amount


def _week_of(timestamp: Any) -> date:
    if isinstance(timestamp, str):
        timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    if not isinstance(timestamp, datetime) or timestamp.tzinfo is None:
        raise TransformError("timestamp must be timezone-aware")
    day = timestamp.astimezone(timezone.utc).date()
    return day - timedelta(days=day.weekday())


def transform_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Validate source rows and replace each location-week with a full recompute."""
    seen: dict[str, dict[str, Any]] = {}
    rejected = 0
    skipped = 0
    rejections: list[dict[str, str]] = []
    usable: list[dict[str, Any]] = []
    for event in events:
        event_type = event.get("event_type")
        if event_type not in EVENT_TYPES:
            rejected += 1
            rejections.append(
                {
                    "id": str(event.get("id")),
                    "event_type": str(event_type),
                    "reason": "unsupported event type",
                }
            )
            continue
        try:
            tags = _tags(event.get("tags"))
            missing = [key for key in _REQUIRED[event_type] if key not in tags]
            if missing:
                raise TransformError("missing " + ", ".join(missing))
            country = tags["country"]
            currency = tags["currency"]
            if CURRENCY_FOR_COUNTRY.get(country) != currency:
                raise TransformError("country/currency mismatch")
            identity = str(event["id"])
            payload = {"event_type": event_type, "timestamp": str(event["timestamp"]), "tags": tags}
            if identity in seen and seen[identity] != payload:
                raise TransformError("conflicting payload for one id")
            if identity in seen:
                skipped += 1
                continue
            seen[identity] = payload
            usable.append(
                {
                    "id": identity,
                    "event_type": event_type,
                    "week": _week_of(event["timestamp"]),
                    "tags": tags,
                }
            )
        except TransformError as exc:
            if event_type == "outbound_order_created":
                rejected += 1
                rejections.append(
                    {
                        "id": str(event.get("id")),
                        "event_type": str(event_type),
                        "reason": str(exc),
                    }
                )
                continue
            raise
    buckets: dict[tuple[str, str, date, str], dict[str, Any]] = {}
    location_pairs: dict[tuple[str, date], set[tuple[str, str]]] = {}
    for event in usable:
        if event["event_type"] == "outbound_order_created":
            continue
        tags = event["tags"]
        key = (tags["location_id"], tags["country"], event["week"], tags["currency"])
        location_pairs.setdefault((tags["location_id"], event["week"]), set()).add(
            (tags["country"], tags["currency"])
        )
        bucket = buckets.setdefault(
            key,
            {
                "location_id": tags["location_id"],
                "country": tags["country"],
                "week_start": event["week"],
                "currency": tags["currency"],
                "total_purchase_cost": Decimal("0"),
                "total_waste_cost": Decimal("0"),
                "stockout_ids": set(),
                "price_ids": set(),
            },
        )
        if event["event_type"] == "inbound_order_created":
            bucket["total_purchase_cost"] += _money(tags["quantity"], tags["unit_cost"])
        elif event["event_type"] == "stock_waste_registered":
            bucket["total_waste_cost"] += _money(tags["quantity"], tags["unit_cost"])
        elif event["event_type"] == "stock_threshold_triggered":
            bucket["stockout_ids"].add(event["id"])
        elif event["event_type"] == "ingredient_price_variance_detected":
            bucket["price_ids"].add(event["id"])
    for pairs in location_pairs.values():
        if len(pairs) > 1:
            raise TransformError("country/currency conflict for one location-week")
    rows = []
    for bucket in buckets.values():
        purchase = bucket["total_purchase_cost"]
        waste = bucket["total_waste_cost"]
        ratio = Decimal("0") if purchase == 0 else waste / purchase
        rows.append(
            {
                "location_id": bucket["location_id"],
                "country": bucket["country"],
                "week_start": bucket["week_start"],
                "total_purchase_cost": purchase,
                "total_waste_cost": waste,
                "waste_ratio": ratio,
                "stockout_events_count": len(bucket["stockout_ids"]),
                "price_alert_events_count": len(bucket["price_ids"]),
                "currency": bucket["currency"],
            }
        )
    rows.sort(key=lambda row: (row["week_start"], row["country"], row["location_id"]))
    return {
        "rows": rows,
        "rows_rejected": rejected,
        "rows_skipped_duplicate": skipped,
        "rejections": rejections,
    }


def _fetch_page(connection: Any, bounds: dict[str, Any]) -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute(EXTRACT_SQL, bounds)
        columns = [item[0] for item in cursor.description]
        return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def _extract(connection: Any, window_start: datetime, window_end: datetime, batch_size: int) -> list[dict[str, Any]]:
    # Transient connection failures are retried by the task. A retry restarts
    # this whole window instead of keeping a partial page.
    last_timestamp = window_start - timedelta(microseconds=1)
    last_id = "00000000-0000-0000-0000-000000000000"
    pages: list[dict[str, Any]] = []
    while True:
        batch = _fetch_page(
            connection,
            {
                "event_types": list(EVENT_TYPES),
                "window_start": window_start,
                "window_end": window_end,
                "last_timestamp": last_timestamp,
                "last_id": last_id,
                "batch_size": batch_size,
            },
        )
        pages.extend(batch)
        if len(batch) < batch_size:
            return pages
        last = batch[-1]
        last_timestamp = last["timestamp"]
        last_id = str(last["id"])


def _transform_cache_key(_context: Any, parameters: dict[str, Any]) -> str:
    """Key the cached aggregate by the window and the extracted rows, not the run id."""
    raw = json.dumps(
        {
            "window_start": parameters.get("window_start"),
            "window_end": parameters.get("window_end"),
            "events": parameters.get("events"),
        },
        default=str,
        sort_keys=True,
    )
    digest = hashlib.sha256(raw.encode()).hexdigest()
    return f"weekly-location-performance:{digest}"


def _is_transient(exc: BaseException) -> bool:
    if isinstance(exc, TransformError):
        return False
    if isinstance(exc, (psycopg.OperationalError, psycopg.InterfaceError, ConnectionError, TimeoutError)):
        return True
    cause = exc.__cause__
    if isinstance(cause, BaseException) and cause is not exc:
        return _is_transient(cause)
    return False


def _retry_transient(_task: Any, _task_run: Any, state: Any) -> bool:
    exc = getattr(state, "data", None)
    return isinstance(exc, BaseException) and _is_transient(exc)


def _note_attempt(run_id: str, name: str) -> None:
    bucket = _ATTEMPT_COUNTS.setdefault(run_id, {})
    bucket[name] = bucket.get(name, 0) + 1


def _retry_total(run_id: str) -> int:
    bucket = _ATTEMPT_COUNTS.get(run_id, {})
    return sum(max(count - 1, 0) for count in bucket.values())


def lease_is_live(lease_expires_at: datetime | None, now: datetime) -> bool:
    return lease_expires_at is not None and lease_expires_at > now


@task(
    retries=3,
    retry_delay_seconds=RETRY_DELAYS,
    retry_jitter_factor=0.2,
    retry_condition_fn=_retry_transient,
)
def extract_telemetry_events(
    run_id: str,
    window_start: datetime,
    window_end: datetime,
    batch_size: int = 500,
) -> list[dict[str, Any]]:
    """Read one bounded window from telemetry_events.

    Retries: 3. Only a transient dropped connection, timeout, or other transport
    failure is retried. Each wait is exponential (1s, 2s, 4s) plus jitter. Validation
    and contract errors are not retried. Each attempt reads the window from
    the first page again.
    """
    _note_attempt(run_id, "extract")
    with open_connection() as connection:
        return _extract(connection, window_start, window_end, batch_size)


@task(
    cache_key_fn=_transform_cache_key,
    cache_expiration=timedelta(minutes=15),
    persist_result=True,
)
def transform_weekly_location_performance(
    run_id: str,
    events: list[dict[str, Any]],
    window_start: datetime,
    window_end: datetime,
) -> dict[str, Any]:
    """Aggregate one extract into location-week rows.

    The cache key is the window plus the extracted events, so a second run of
    the same input inside 15 minutes reuses this result. A different window or
    a different payload does not. The saved time is what a later run compares.
    """
    del run_id
    result = transform_events(events)
    result["transformed_at"] = datetime.now(timezone.utc).isoformat()
    result["window_start"] = window_start.isoformat()
    result["window_end"] = window_end.isoformat()
    return result


@task(
    retries=3,
    retry_delay_seconds=RETRY_DELAYS,
    retry_jitter_factor=0.2,
    retry_condition_fn=_retry_transient,
)
def load_weekly_location_performance(run_id: str, transformed: dict[str, Any], affected_weeks: list[date]) -> int:
    """Replace each affected location-week.

    Retries: 3, with the same exponential delays and jitter as extract, and
    only for connection or transport failures. A lost lease or a contract
    error is not retried. A retry rolls the transaction back and upserts again.
    """
    _note_attempt(run_id, "load")
    rows = transformed["rows"]
    computed_at = datetime.now(timezone.utc)
    by_week: dict[date, list[str]] = {week: [] for week in affected_weeks}
    for row in rows:
        by_week.setdefault(row["week_start"], []).append(row["location_id"])
    with open_connection() as connection:
        with connection.transaction():
            _require_live_lease(connection, run_id)
            with connection.cursor() as cursor:
                for row in rows:
                    payload = dict(row)
                    payload["computed_at"] = computed_at
                    cursor.execute(UPSERT_SQL, payload)
                for week, location_ids in by_week.items():
                    cursor.execute(
                        DELETE_STALE_SQL,
                        {"week_start": week, "location_ids": location_ids},
                    )
    return len(rows)


def _require_live_lease(connection: Any, run_id: str) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select status, lease_expires_at
            from reporting.pipeline_runs
            where run_id = %(run_id)s
            for update
            """,
            {"run_id": run_id},
        )
        found = cursor.fetchone()
    if found is None or found[0] != "running" or found[1] is None or found[1] <= datetime.now(timezone.utc):
        raise TransformError("the pipeline lease is no longer valid")


def _insert_run(connection: Any, run: dict[str, Any]) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            insert into reporting.pipeline_runs (
                run_id, pipeline_name, trigger_type, requested_week_start, affected_weeks,
                started_at, finished_at, heartbeat_at, lease_expires_at, status,
                last_completed_stage, watermark_from, watermark_to, rows_extracted,
                records_processed, rows_transformed, rows_loaded, rows_rejected,
                rows_skipped_duplicate, retry_count, duration_ms, error_stage,
                error_summary, pipeline_version
            ) values (
                %(run_id)s, %(pipeline_name)s, %(trigger_type)s, %(requested_week_start)s,
                %(affected_weeks)s, %(started_at)s, null, %(heartbeat_at)s, %(lease_expires_at)s,
                'running', null, %(watermark_from)s, %(watermark_to)s, 0, 0, 0, 0, 0, 0, 0,
                null, null, null, %(pipeline_version)s
            )
            """,
            run,
        )


def create_run(week_start: date | None, trigger_type: str) -> dict[str, Any]:
    if trigger_type not in {"schedule", "manual", "backfill"}:
        raise ValueError("trigger_type must be schedule, manual, or backfill")
    window_start, window_end, requested, weeks = source_window(week_start, trigger_type)
    started = datetime.now(timezone.utc)
    run = {
        "run_id": str(uuid4()),
        "pipeline_name": PIPELINE_NAME,
        "trigger_type": trigger_type,
        "requested_week_start": requested,
        "affected_weeks": weeks,
        "started_at": started,
        "heartbeat_at": started,
        "lease_expires_at": started + LEASE,
        "watermark_from": window_start,
        "watermark_to": window_end,
        "pipeline_version": pipeline_version(),
        "status": "running",
        "finished_at": None,
        "records_processed": 0,
        "rows_extracted": 0,
        "rows_transformed": 0,
        "rows_loaded": 0,
        "rows_rejected": 0,
        "rows_skipped_duplicate": 0,
        "error_stage": None,
        "error_summary": None,
        "retry_count": 0,
    }
    with open_connection() as connection:
        try:
            with connection.transaction():
                _take_over_expired_or_refuse(connection)
                _insert_run(connection, run)
        except psycopg.errors.UniqueViolation as exc:
            active = _active_run_id()
            raise PipelineLeaseHeld(active or "unknown") from exc
    return run


def _take_over_expired_or_refuse(connection: Any) -> None:
    now = datetime.now(timezone.utc)
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select run_id::text, lease_expires_at
            from reporting.pipeline_runs
            where pipeline_name = %(pipeline_name)s and status = 'running'
            for update
            """,
            {"pipeline_name": PIPELINE_NAME},
        )
        existing = cursor.fetchone()
        if existing is None:
            return
        active_id, expires = existing
        if lease_is_live(expires, now):
            raise PipelineLeaseHeld(active_id)
        cursor.execute(
            """
            update reporting.pipeline_runs set
                status = 'failed',
                finished_at = %(now)s,
                error_stage = null,
                error_summary = %(reason)s,
                lease_expires_at = null
            where run_id = %(run_id)s
            """,
            {"now": now, "reason": TAKEOVER_REASON, "run_id": active_id},
        )


def _active_run_id() -> str | None:
    with open_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select run_id::text
                from reporting.pipeline_runs
                where pipeline_name = %(pipeline_name)s and status = 'running'
                limit 1
                """,
                {"pipeline_name": PIPELINE_NAME},
            )
            found = cursor.fetchone()
    return None if found is None else found[0]


def _finish(run: dict[str, Any], status: str, stage: str | None, error: str | None) -> dict[str, Any]:
    finished = datetime.now(timezone.utc)
    run["status"] = status
    run["finished_at"] = finished
    run["last_completed_stage"] = stage
    run["error_stage"] = stage if status == "failed" else None
    run["error_summary"] = error
    run["duration_ms"] = int((finished - run["started_at"]).total_seconds() * 1000)
    with open_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                update reporting.pipeline_runs set
                    status = %(status)s,
                    finished_at = %(finished_at)s,
                    last_completed_stage = %(last_completed_stage)s,
                    records_processed = %(records_processed)s,
                    rows_extracted = %(rows_extracted)s,
                    rows_transformed = %(rows_transformed)s,
                    rows_loaded = %(rows_loaded)s,
                    rows_rejected = %(rows_rejected)s,
                    rows_skipped_duplicate = %(rows_skipped_duplicate)s,
                    retry_count = %(retry_count)s,
                    duration_ms = %(duration_ms)s,
                    error_stage = %(error_stage)s,
                    error_summary = %(error_summary)s,
                    lease_expires_at = null
                where run_id = %(run_id)s
                """,
                run,
            )
        connection.commit()
    return run


def _public_run(run: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": run["run_id"],
        "pipeline_name": run["pipeline_name"],
        "trigger_type": run["trigger_type"],
        "requested_week_start": run["requested_week_start"],
        "affected_weeks": run["affected_weeks"],
        "status": run["status"],
        "started_at": run["started_at"],
        "finished_at": run["finished_at"],
        "records_processed": run["records_processed"],
        "rows_extracted": run["rows_extracted"],
        "rows_transformed": run["rows_transformed"],
        "rows_loaded": run["rows_loaded"],
        "rows_rejected": run["rows_rejected"],
        "rows_skipped_duplicate": run["rows_skipped_duplicate"],
        "error_stage": run["error_stage"],
        "error_summary": run["error_summary"],
        "watermark_from": run["watermark_from"],
        "watermark_to": run["watermark_to"],
        "pipeline_version": run["pipeline_version"],
    }


def _heartbeat(run_id: str) -> None:
    now = datetime.now(timezone.utc)
    with open_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                update reporting.pipeline_runs set
                    heartbeat_at = %(now)s,
                    lease_expires_at = %(expires)s
                where run_id = %(run_id)s and status = 'running'
                """,
                {"now": now, "expires": now + LEASE, "run_id": run_id},
            )
        connection.commit()


def _heartbeat_loop(run_id: str, stop: threading.Event) -> None:
    while not stop.is_set():
        try:
            _heartbeat(run_id)
        except Exception:
            logger.warning("pipeline lease heartbeat failed", exc_info=True)
        if stop.wait(HEARTBEAT_INTERVAL):
            return


def _write_snapshot_file(run_id: str, payload: dict[str, Any]) -> str:
    directory = _REPO / "data" / "eval"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{run_id}.json"
    path.write_text(json.dumps(payload, default=str, indent=2), encoding="utf-8")
    return str(path)


@task
def write_eval_snapshot(
    run_id: str,
    rows_extracted: int,
    rows_transformed: int,
    rows_rejected: int,
    rejections: list[dict[str, str]],
) -> str:
    """Write an optional audit file. A failure here must not fail the weekly report."""
    return _write_snapshot_file(
        run_id,
        {
            "run_id": run_id,
            "rows_extracted": rows_extracted,
            "rows_transformed": rows_transformed,
            "rows_rejected": rows_rejected,
            "rejections": rejections,
        },
    )


def _fail(run: dict[str, Any], stage: str, exc: BaseException) -> None:
    run["retry_count"] = _retry_total(run["run_id"])
    if run["status"] == "running":
        _finish(run, "failed", stage, str(exc)[:500])


@flow(name="business_performance_etl_flow")
def business_performance_etl_flow(
    week_start: date | None = None,
    trigger_type: str = "manual",
) -> dict[str, Any]:
    """One Weekly Location Cost & Waste run. A second live run is refused."""
    run = create_run(week_start, trigger_type)
    stop = threading.Event()
    beater = threading.Thread(
        target=_heartbeat_loop,
        args=(run["run_id"], stop),
        name="pipeline-lease-heartbeat",
        daemon=True,
    )
    beater.start()
    try:
        try:
            events = extract_telemetry_events(
                run["run_id"],
                run["watermark_from"],
                run["watermark_to"],
            )
        except Exception as exc:
            _fail(run, "extract", exc)
            raise
        run["rows_extracted"] = len(events)
        run["records_processed"] = len(events)
        try:
            transformed = transform_weekly_location_performance(
                run["run_id"],
                events,
                run["watermark_from"],
                run["watermark_to"],
            )
        except Exception as exc:
            _fail(run, "transform", exc)
            raise
        run["rows_transformed"] = len(transformed["rows"])
        run["rows_rejected"] = transformed["rows_rejected"]
        run["rows_skipped_duplicate"] = transformed["rows_skipped_duplicate"]
        snapshot = write_eval_snapshot(
            run["run_id"],
            run["rows_extracted"],
            run["rows_transformed"],
            run["rows_rejected"],
            transformed["rejections"],
            return_state=True,
        )
        if not snapshot.is_completed():
            note = f"optional eval snapshot failed: {snapshot.message}"
            logger.warning(note)
            run["optional_failure"] = note
        try:
            loaded = load_weekly_location_performance(
                run["run_id"],
                transformed,
                run["affected_weeks"],
            )
        except Exception as exc:
            summary = str(exc)[:500]
            if run.get("optional_failure"):
                summary = f"{run['optional_failure']} | {summary}"[:500]
            run["retry_count"] = _retry_total(run["run_id"])
            if run["status"] == "running":
                _finish(run, "failed", "load", summary)
            raise
        run["rows_loaded"] = loaded
        run["retry_count"] = _retry_total(run["run_id"])
        return _public_run(_finish(run, "success", "load", run.get("optional_failure")))
    finally:
        stop.set()
        beater.join(timeout=2)
        _ATTEMPT_COUNTS.pop(run["run_id"], None)


def get_latest_pipeline_run() -> dict[str, Any] | None:
    with open_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select run_id::text, pipeline_name, trigger_type, requested_week_start,
                       affected_weeks, status, started_at, finished_at, records_processed,
                       rows_extracted, rows_transformed, rows_loaded, rows_rejected,
                       rows_skipped_duplicate, error_stage, error_summary,
                       watermark_from, watermark_to, pipeline_version
                from reporting.pipeline_runs
                where pipeline_name = %(pipeline_name)s
                order by started_at desc
                limit 1
                """,
                {"pipeline_name": PIPELINE_NAME},
            )
            found = cursor.fetchone()
    if found is None:
        return None
    keys = (
        "run_id", "pipeline_name", "trigger_type", "requested_week_start",
        "affected_weeks", "status", "started_at", "finished_at", "records_processed",
        "rows_extracted", "rows_transformed", "rows_loaded", "rows_rejected",
        "rows_skipped_duplicate", "error_stage", "error_summary",
        "watermark_from", "watermark_to", "pipeline_version",
    )
    return dict(zip(keys, found, strict=True))


def get_weekly_location_performance(
    week_start: date | None,
    week_end: date | None,
    location_id: str | None,
    country: str | None,
) -> list[dict[str, Any]]:
    with open_connection() as connection:
        with connection.cursor() as cursor:
            if week_start is None and week_end is None:
                cursor.execute(
                    """
                    select max(week_start) from reporting.weekly_location_performance
                    """
                )
                latest = cursor.fetchone()
                if latest is None or latest[0] is None:
                    return []
                week_start = latest[0]
                week_end = latest[0]
            week_end = week_start if week_end is None else week_end
            cursor.execute(
                """
                select location_id, country, week_start, total_purchase_cost,
                       total_waste_cost, waste_ratio, stockout_events_count,
                       price_alert_events_count, currency, computed_at
                from reporting.weekly_location_performance
                where week_start >= %(week_start)s
                  and week_start <= %(week_end)s
                  and (%(location_id)s::text is null or location_id = %(location_id)s)
                  and (%(country)s::text is null or country = %(country)s)
                order by week_start, country, location_id
                """,
                {
                    "week_start": week_start,
                    "week_end": week_end,
                    "location_id": location_id,
                    "country": country,
                },
            )
            columns = [item[0] for item in cursor.description]
            return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def _prefect_healthy(api_url: str) -> bool:
    try:
        with urllib.request.urlopen(api_url + "/health", timeout=1) as response:
            return response.status == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def ensure_local_prefect() -> str:
    """Use a local Prefect API so task retries, cache, and state run for real.

    An already configured ``PREFECT_API_URL`` is left alone. Otherwise this
    starts one server on 127.0.0.1:8765 and reuses it on the next command.
    """
    configured = os.environ.get("PREFECT_API_URL")
    if configured:
        return configured
    home = _REPO / ".prefect-local"
    home.mkdir(mode=0o700, exist_ok=True)
    api_url = f"http://127.0.0.1:{PREFECT_PORT}/api"
    if not _prefect_healthy(api_url):
        env = os.environ.copy()
        env["PREFECT_HOME"] = str(home)
        env.pop("PREFECT_API_URL", None)
        env["PREFECT_UI_ENABLED"] = "0"
        env["PREFECT_SERVER_EPHEMERAL_ENABLED"] = "0"
        log_path = home / "server.log"
        log_file = log_path.open("ab")
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "--app-dir",
                str(Path(prefect.__file__).resolve().parent.parent),
                "--factory",
                "prefect.server.api.server:create_app",
                "--host",
                "127.0.0.1",
                "--port",
                str(PREFECT_PORT),
                "--log-level",
                "error",
            ],
            env=env,
            stdout=log_file,
            stderr=log_file,
            start_new_session=True,
        )
        (home / "server.pid").write_text(str(process.pid), encoding="utf-8")
        deadline = time.time() + 180
        while time.time() < deadline:
            if _prefect_healthy(api_url):
                break
            if process.poll() is not None:
                raise RuntimeError(
                    f"local Prefect server exited with code {process.returncode}; see {log_path}"
                )
            time.sleep(0.5)
        else:
            raise RuntimeError(f"local Prefect server did not become healthy within 180s; see {log_path}")
    os.environ["PREFECT_API_URL"] = api_url
    os.environ["PREFECT_HOME"] = str(home)
    refresh_global_settings_context()
    return api_url


def execute_flow(
    week_start: date | None = None,
    trigger_type: str = "manual",
) -> dict[str, Any]:
    """Run one pass through the Prefect engine. Call the flow, not its raw function."""
    from app.config import get_settings

    if not get_settings().database_url:
        raise RuntimeError("DATABASE_URL is not set")
    ensure_local_prefect()
    try:
        return business_performance_etl_flow(week_start=week_start, trigger_type=trigger_type)
    except PipelineLeaseHeld:
        raise
    except BaseException as exc:
        lease = _find_lease(exc)
        if lease is not None:
            raise lease from exc
        raise


def _find_lease(exc: BaseException) -> PipelineLeaseHeld | None:
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, PipelineLeaseHeld):
            return current
        current = current.__cause__ or current.__context__
    return None


def main() -> int:
    try:
        result = execute_flow(trigger_type="manual")
    except PipelineLeaseHeld as exc:
        print(f"pipeline lease held by {exc.active_run_id}", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 1
    print(result["status"], result["run_id"], "records_processed", result["records_processed"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
