"""SIGINT and SIGTERM must end a live run as failed."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

import pytest

from job_runner.job_runner import _load_database_url, connect

_REPO = Path(__file__).resolve().parents[2]


@pytest.fixture
def database_url() -> str:
    url = _load_database_url()
    if not url:
        pytest.skip("DATABASE_URL is not set")
    return url


def _release(day: date) -> None:
    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                delete from public.job_runs
                where job_name = 'nightly_export' and target_date = %(day)s
                """,
                {"day": day},
            )
            cursor.execute(
                """
                update reporting.pipeline_runs
                set status = 'failed',
                    finished_at = now(),
                    error_summary = 'signal test stopped the pipeline process',
                    lease_expires_at = null
                where pipeline_name = 'weekly_location_cost_waste'
                  and status = 'running'
                """
            )
        connection.commit()
    finally:
        connection.close()
    for suffix in (".csv", ".csv.tmp"):
        path = _REPO / "data" / "raw" / f"telemetry_{day.isoformat()}{suffix}"
        if path.exists():
            path.unlink()


def _status(day: date) -> tuple[str, str | None] | None:
    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select status, error_message
                from public.job_runs
                where job_name = 'nightly_export' and target_date = %(day)s
                """,
                {"day": day},
            )
            found = cursor.fetchone()
    finally:
        connection.close()
    if found is None:
        return None
    return found[0], found[1]


def _processing_count() -> int:
    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select count(*)
                from public.job_runs
                where job_name = 'nightly_export' and status = 'processing'
                """
            )
            found = cursor.fetchone()
    finally:
        connection.close()
    assert found is not None
    return int(found[0])


@pytest.mark.parametrize(
    ("day", "signum", "name"),
    [
        (date(1999, 4, 1), signal.SIGTERM, "SIGTERM"),
        (date(1999, 4, 2), signal.SIGINT, "SIGINT"),
    ],
)
def test_signal_marks_the_run_failed(
    database_url: str,
    day: date,
    signum: int,
    name: str,
) -> None:
    _release(day)
    env = os.environ.copy()
    env["DATABASE_URL"] = database_url
    env["TARGET_DATE"] = day.isoformat()
    process = subprocess.Popen(
        [sys.executable, str(_REPO / "scripts" / "nightly_export.py")],
        cwd=_REPO,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    stderr = ""
    recorded: tuple[str, str | None] | None = None
    try:
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            found = _status(day)
            if found is not None and found[0] == "processing":
                time.sleep(0.2)
                process.send_signal(signum)
                break
            if process.poll() is not None:
                break
            time.sleep(0.2)
        _stdout, stderr = process.communicate(timeout=30)
        recorded = _status(day)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)
        _release(day)
    assert process.returncode not in (0, None)
    assert "ERROR nightly_export status=failed" in stderr
    assert name in stderr
    assert recorded is not None
    assert recorded[0] == "failed"
    assert recorded[1] is not None and name in recorded[1]
    assert _processing_count() == 0
