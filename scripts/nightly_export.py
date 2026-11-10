"""Independent nightly export. Run from the repository root.

    python3 scripts/nightly_export.py

TARGET_DATE=YYYY-MM-DD selects a day. When it is unset, the day is yesterday
in UTC.

DATABASE_URL must be in the process environment, or in the first file that
exists among ``.env/local``, ``.env``, and ``services/api/.env``. The committed
schedule is ``scripts/nightly_export.crontab``. It loads DATABASE_URL and PATH
from an env file outside this repository. See ``scripts/nightly_export.env.example``.

The system interpreter does not have psycopg. When this file is the program,
it asks ``uv`` for the services/api interpreter and replaces itself with that
program, so SIGINT and SIGTERM reach this process. Cron's PATH must include
``uv``. The pipeline child inherits DATABASE_URL.

The CSV under ``data/raw/`` is a backup. The pipeline subprocess reads
``telemetry_events`` from Postgres.
"""

from __future__ import annotations

import csv
import json
import os
import re
import shutil
import signal
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[1]


class RunInterrupted(Exception):
    """SIGINT or SIGTERM arrived while the run was in progress."""

    def __init__(self, signum: int) -> None:
        self.signum = signum
        super().__init__(signal.Signals(signum).name)


def _on_signal(signum: int, _frame: object) -> None:
    raise RunInterrupted(signum)


def _ensure_interpreter() -> None:
    """Replace this process with the API interpreter when psycopg is missing.

    ``uv run`` would stay as the parent. Replacing this process with the
    interpreter ``uv`` selects keeps SIGINT and SIGTERM on the script.
    """
    if os.environ.get("BRASALAND_NIGHTLY_REEXEC") == "1":
        return
    try:
        import dotenv  # noqa: F401
        import psycopg  # noqa: F401
    except ImportError:
        uv = shutil.which("uv")
        if uv is None:
            raise SystemExit(
                "python scripts/nightly_export.py needs uv on PATH so it can "
                "run with the services/api environment."
            )
        os.environ["BRASALAND_NIGHTLY_REEXEC"] = "1"
        interpreter = subprocess.check_output(
            [
                uv,
                "run",
                "--project",
                str(_REPO / "services" / "api"),
                "python",
                "-c",
                "import sys; print(sys.executable)",
            ],
            text=True,
        ).strip()
        os.execv(interpreter, [interpreter, str(Path(__file__).resolve()), *sys.argv[1:]])


def _install_signal_handlers() -> None:
    signal.signal(signal.SIGINT, _on_signal)
    signal.signal(signal.SIGTERM, _on_signal)


if __name__ == "__main__":
    _ensure_interpreter()
    _install_signal_handlers()
sys.path.insert(0, str(_REPO / "services"))

from job_runner import (  # noqa: E402
    ProcessingLockHeld,
    claim_run,
    fail_if_processing,
    has_completed_for_date,
    has_processing_lock,
    mark_completed,
    mark_failed,
)
from job_runner.job_runner import _load_database_url, connect  # noqa: E402

JOB_NAME = "nightly_export"
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_COLUMNS = (
    "id",
    "timestamp",
    "service",
    "event_type",
    "level",
    "value",
    "message",
    "tags",
)


def resolve_target_date() -> date:
    """Return TARGET_DATE, or yesterday in UTC when the variable is unset."""
    raw = os.getenv("TARGET_DATE")
    if raw is None or raw.strip() == "":
        return datetime.now(timezone.utc).date() - timedelta(days=1)
    text = raw.strip()
    if _DATE.fullmatch(text) is None:
        raise ValueError(f"invalid TARGET_DATE: {text}")
    return date.fromisoformat(text)


def database_url() -> str | None:
    """Resolve DATABASE_URL from the environment, then the repo env files."""
    return _load_database_url()


def export_path(target: date) -> Path:
    return _REPO / "data" / "raw" / f"telemetry_{target.isoformat()}.csv"


def log(
    level: str,
    status: str,
    target: date | None = None,
    **fields: str,
) -> None:
    """Write one UTC line. ERROR goes to stderr."""
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    parts = [stamp, level, JOB_NAME, f"status={status}"]
    if target is not None:
        parts.append(f"target_date={target.isoformat()}")
    for key, value in fields.items():
        if key == "error":
            cleaned = value.replace("\n", " ").replace('"', "'")
            parts.append(f'error="{cleaned}"')
        else:
            parts.append(f"{key}={value}")
    stream = sys.stderr if level == "ERROR" else sys.stdout
    print(" ".join(parts), file=stream, flush=True)


def export_events(target: date) -> None:
    """Write the UTC day's events when the CSV is not already there."""
    path = export_path(target)
    if path.exists():
        return
    start = datetime(target.year, target.month, target.day, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select id::text, timestamp, service, event_type, level,
                       value, message, tags
                from public.telemetry_events
                where timestamp >= %(start)s
                  and timestamp < %(end)s
                order by timestamp asc, id asc
                """,
                {"start": start, "end": end},
            )
            rows = cursor.fetchall()
    finally:
        connection.close()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".csv.tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(_COLUMNS)
            for row in rows:
                writer.writerow(_csv_row(row))
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def run_pipeline(url: str) -> None:
    """Run the weekly pipeline. A non-zero exit is a failure.

    The child's output stays out of the nightly log. The pipeline reads
    ``telemetry_events`` from Postgres, not the CSV. A signal stops the child
    so its lease does not stay running after this process records failure.
    """
    process = subprocess.Popen(
        [sys.executable, "data/pipelines/pipeline.py"],
        cwd=_REPO,
        env={**os.environ, "DATABASE_URL": url},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    try:
        return_code = process.wait()
    except BaseException:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        raise
    if return_code != 0:
        raise RuntimeError(f"pipeline exit code {return_code}")


def main() -> int:
    try:
        target = resolve_target_date()
    except ValueError as exc:
        log("ERROR", "failed", error=str(exc))
        return 1
    url = database_url()
    if not url:
        log("ERROR", "failed", target, error="DATABASE_URL is not set")
        return 1
    os.environ["DATABASE_URL"] = url
    if has_processing_lock(JOB_NAME):
        log("INFO", "cancelled", target, reason="processing_lock")
        return 0
    if has_completed_for_date(JOB_NAME, target):
        log("INFO", "skipped", target, reason="duplicate")
        return 0
    try:
        run_id = claim_run(JOB_NAME, target)
    except ProcessingLockHeld:
        log("INFO", "cancelled", target, reason="processing_lock")
        return 0
    log("INFO", "started", target)
    try:
        try:
            export_events(target)
            run_pipeline(url)
            mark_completed(run_id)
        except Exception as exc:
            message = str(exc)
            try:
                mark_failed(run_id, message)
            except Exception as record_error:
                message = f"could not record failure: {record_error}; {message}"
            log("ERROR", "failed", target, error=message)
            return 1
        log("INFO", "completed", target)
        return 0
    finally:
        fail_if_processing(run_id, "run ended while processing")


def _csv_row(row: tuple[Any, ...]) -> list[str]:
    event_id, stamp, service, event_type, level, value, message, tags = row
    return [
        event_id,
        _iso(stamp),
        service,
        event_type,
        level,
        _number(value),
        "" if message is None else str(message),
        json.dumps(tags if tags is not None else {}, default=str, separators=(",", ":")),
    ]


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _number(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return format(value, "f")
    return str(value)


if __name__ == "__main__":
    raise SystemExit(main())
