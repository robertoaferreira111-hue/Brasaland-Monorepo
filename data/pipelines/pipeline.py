"""Weekly Location Cost & Waste pipeline.

Run from the repository, with services/api dependencies available:

    cd services/api && uv run python ../../data/pipelines/pipeline.py

The flow reads public.telemetry_events and writes only reporting tables.
It does not modify telemetry_events.
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import uuid4

_PIPELINES = Path(__file__).resolve().parent
_REPO = _PIPELINES.parents[1]
sys.path.insert(0, str(_REPO / "services" / "api"))
sys.path.insert(0, str(_PIPELINES))

import db  # noqa: E402
import psycopg  # noqa: E402
from prefect import flow, task  # noqa: E402
from prefect.states import State  # noqa: E402

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
    usable: list[dict[str, Any]] = []
    for event in events:
        event_type = event.get("event_type")
        if event_type not in EVENT_TYPES:
            rejected += 1
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
        except TransformError:
            if event_type == "outbound_order_created":
                rejected += 1
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
    return f"weekly-location-performance:{parameters['run_id']}"


@task(retries=3, retry_delay_seconds=[1, 2, 4])
def extract_telemetry_events(
    run_id: str,
    window_start: datetime,
    window_end: datetime,
    batch_size: int = 500,
) -> list[dict[str, Any]]:
    """Read one bounded window from telemetry_events.

    Retries cover dropped connections and timeouts only. Each attempt reads the
    window from the first page again.
    """
    del run_id
    with open_connection() as connection:
        return _extract(connection, window_start, window_end, batch_size)


@task(cache_key_fn=_transform_cache_key, cache_expiration=timedelta(minutes=15))
def transform_weekly_location_performance(
    run_id: str,
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    """Aggregate one extract into location-week rows.

    The cache reuses that aggregate if a later load attempt is retried for the
    same run. It expires so a corrected rerun does not keep a stale result.
    """
    del run_id
    return transform_events(events)


@task(retries=3, retry_delay_seconds=[1, 2, 4])
def load_weekly_location_performance(run_id: str, transformed: dict[str, Any], affected_weeks: list[date]) -> int:
    """Replace each affected location-week. A retry rolls back and upserts again."""
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
    }
    try:
        with open_connection() as connection:
            with connection.transaction():
                _insert_run(connection, run)
    except psycopg.errors.UniqueViolation as exc:
        active = _active_run_id()
        raise PipelineLeaseHeld(active or "unknown") from exc
    return run


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


@flow(name="business_performance_etl_flow")
def business_performance_etl_flow(
    week_start: date | None = None,
    trigger_type: str = "manual",
) -> dict[str, Any]:
    """One Weekly Location Cost & Waste run. A second live run is refused."""
    run = create_run(week_start, trigger_type)
    try:
        events = _read_events(run, return_state=True)
        run["rows_extracted"] = len(events)
        run["records_processed"] = len(events)
        transformed = transform_weekly_location_performance.fn(run["run_id"], events)
        run["rows_transformed"] = len(transformed["rows"])
        run["rows_rejected"] = transformed["rows_rejected"]
        run["rows_skipped_duplicate"] = transformed["rows_skipped_duplicate"]
        loaded = load_weekly_location_performance.fn(
            run["run_id"],
            transformed,
            run["affected_weeks"],
        )
        run["rows_loaded"] = loaded
        return _public_run(_finish(run, "success", "load", None))
    except PipelineLeaseHeld:
        raise
    except Exception as exc:
        if run["status"] == "running":
            _finish(run, "failed", "transform", str(exc)[:500])
        raise


def _read_events(run: dict[str, Any], *, return_state: bool = True) -> list[dict[str, Any]]:
    """Read the run window.

    With a Prefect API URL, return_state=True keeps a failed extract on this run
    instead of skipping the audit update. Otherwise the task body runs directly.
    """
    if return_state and os.environ.get("PREFECT_API_URL"):
        extract_state: State = extract_telemetry_events(
            run["run_id"],
            run["watermark_from"],
            run["watermark_to"],
            return_state=True,
        )
        if not extract_state.is_completed():
            message = "Source read failed after retries"
            _finish(run, "failed", "extract", message)
            raise RuntimeError(message)
        return extract_state.result()
    return extract_telemetry_events.fn(
        run["run_id"],
        run["watermark_from"],
        run["watermark_to"],
    )


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


def main() -> int:
    try:
        result = business_performance_etl_flow.fn(trigger_type="manual")
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 1
    print(result["status"], result["run_id"], "records_processed", result["records_processed"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
