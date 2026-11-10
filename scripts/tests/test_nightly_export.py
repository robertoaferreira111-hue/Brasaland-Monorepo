"""Orchestration tests for scripts/nightly_export.py."""

from __future__ import annotations

import csv
import importlib.util
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from threading import Thread
from uuid import uuid4

import pytest

from job_runner.job_runner import _load_database_url, connect

_REPO = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "nightly_export",
    _REPO / "scripts" / "nightly_export.py",
)
assert _SPEC is not None and _SPEC.loader is not None
nightly_export = importlib.util.module_from_spec(_SPEC)
sys.modules["nightly_export"] = nightly_export
_SPEC.loader.exec_module(nightly_export)

_DAY = date(1999, 3, 1)


@pytest.fixture
def database_url(monkeypatch: pytest.MonkeyPatch) -> str:
    url = _load_database_url()
    if not url:
        pytest.skip("DATABASE_URL is not set")
    monkeypatch.setenv("DATABASE_URL", url)
    return url


@pytest.fixture
def clean_day(database_url: str):
    del database_url
    created: list[date] = []

    def use(day: date) -> date:
        created.append(day)
        _delete_job(day)
        path = nightly_export.export_path(day)
        if path.exists():
            path.unlink()
        temporary = path.with_suffix(".csv.tmp")
        if temporary.exists():
            temporary.unlink()
        return day

    yield use
    for day in created:
        _delete_job(day)
        path = nightly_export.export_path(day)
        if path.exists():
            path.unlink()


def _delete_job(day: date) -> None:
    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                delete from public.job_runs
                where job_name = %(job_name)s and target_date = %(target_date)s
                """,
                {"job_name": nightly_export.JOB_NAME, "target_date": day},
            )
        connection.commit()
    finally:
        connection.close()


def _status(day: date) -> str | None:
    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select status, error_message
                from public.job_runs
                where job_name = %(job_name)s and target_date = %(target_date)s
                """,
                {"job_name": nightly_export.JOB_NAME, "target_date": day},
            )
            found = cursor.fetchone()
    finally:
        connection.close()
    if found is None:
        return None
    return found[0]


def _output(capsys: pytest.CaptureFixture[str]) -> str:
    captured = capsys.readouterr()
    return captured.out + captured.err


def test_default_target_date_is_yesterday_utc(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TARGET_DATE", raising=False)

    class Frozen(datetime):
        @classmethod
        def now(cls, tz: timezone | None = None) -> datetime:
            return datetime(2026, 11, 10, 2, 0, tzinfo=timezone.utc)

    monkeypatch.setattr(nightly_export, "datetime", Frozen)
    assert nightly_export.resolve_target_date() == date(2026, 11, 9)


def test_target_date_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TARGET_DATE", "2026-01-15")
    assert nightly_export.resolve_target_date() == date(2026, 1, 15)


def test_invalid_target_date_exits_before_a_row(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    database_url: str,
) -> None:
    del database_url
    before = _count_jobs()
    monkeypatch.setenv("TARGET_DATE", "15-01-2026")
    assert nightly_export.main() == 1
    assert _count_jobs() == before
    text = _output(capsys)
    assert "ERROR nightly_export status=failed" in text
    assert "invalid TARGET_DATE" in text


def test_missing_database_url_exits_before_a_row(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    database_url: str,
) -> None:
    monkeypatch.setenv("TARGET_DATE", "1999-03-02")
    before = _count_jobs()
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(nightly_export, "database_url", lambda: None)
    assert nightly_export.main() == 1
    monkeypatch.setenv("DATABASE_URL", database_url)
    assert _count_jobs() == before
    text = _output(capsys)
    assert "DATABASE_URL is not set" in text
    assert "target_date=1999-03-02" in text


def test_duplicate_completed_day_skips(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    clean_day,
) -> None:
    day = clean_day(_DAY + timedelta(days=3))
    monkeypatch.setenv("TARGET_DATE", day.isoformat())
    called = {"n": 0}

    def pipeline(url: str) -> None:
        del url
        called["n"] += 1

    monkeypatch.setattr(nightly_export, "run_pipeline", pipeline)
    nightly_export.mark_completed(nightly_export.claim_run(nightly_export.JOB_NAME, day))
    assert nightly_export.main() == 0
    text = _output(capsys)
    assert called["n"] == 0
    assert not nightly_export.export_path(day).exists()
    assert "status=skipped" in text
    assert "reason=duplicate" in text
    assert "target_date=" + day.isoformat() in text


def test_processing_lock_cancels(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    clean_day,
) -> None:
    day = clean_day(_DAY + timedelta(days=4))
    other = clean_day(_DAY + timedelta(days=5))
    monkeypatch.setenv("TARGET_DATE", day.isoformat())
    nightly_export.claim_run(nightly_export.JOB_NAME, other)
    assert nightly_export.main() == 0
    text = _output(capsys)
    assert "status=cancelled" in text
    assert "reason=processing_lock" in text
    assert _status(day) is None
    assert _status(other) == "processing"


def test_success_exports_and_completes(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    clean_day,
) -> None:
    day = clean_day(_DAY + timedelta(days=6))
    monkeypatch.setenv("TARGET_DATE", day.isoformat())
    event_id = str(uuid4())
    _insert_event(event_id, day)
    called = {"n": 0}

    def pipeline(url: str) -> None:
        called["n"] += 1
        assert url

    monkeypatch.setattr(nightly_export, "run_pipeline", pipeline)
    try:
        assert nightly_export.main() == 0
    finally:
        _delete_event(event_id)
    assert called["n"] == 1
    assert _status(day) == "completed"
    text = _output(capsys)
    assert "status=started" in text
    assert "status=completed" in text
    assert f"target_date={day.isoformat()}" in text
    with nightly_export.export_path(day).open(encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    assert rows[0] == list(nightly_export._COLUMNS)
    assert rows[1][0] == event_id
    assert rows[1][1].endswith("Z")
    assert rows[1][7].startswith("{")


def test_existing_csv_is_not_rewritten(
    monkeypatch: pytest.MonkeyPatch,
    clean_day,
) -> None:
    day = clean_day(_DAY + timedelta(days=7))
    monkeypatch.setenv("TARGET_DATE", day.isoformat())
    path = nightly_export.export_path(day)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("kept\n", encoding="utf-8")
    monkeypatch.setattr(nightly_export, "run_pipeline", lambda url: None)
    assert nightly_export.main() == 0
    assert path.read_text(encoding="utf-8") == "kept\n"


def test_pipeline_failure_ends_failed(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    clean_day,
) -> None:
    day = clean_day(_DAY + timedelta(days=8))
    monkeypatch.setenv("TARGET_DATE", day.isoformat())

    def pipeline(url: str) -> None:
        del url
        raise RuntimeError("pipeline exit code 1")

    monkeypatch.setattr(nightly_export, "run_pipeline", pipeline)
    assert nightly_export.main() == 1
    assert _status(day) == "failed"
    text = _output(capsys)
    assert "ERROR nightly_export status=failed" in text
    assert 'error="pipeline exit code 1"' in text
    assert f"target_date={day.isoformat()}" in text


def test_failure_recorder_still_clears_processing(
    monkeypatch: pytest.MonkeyPatch,
    clean_day,
) -> None:
    day = clean_day(_DAY + timedelta(days=9))
    monkeypatch.setenv("TARGET_DATE", day.isoformat())
    monkeypatch.setattr(
        nightly_export,
        "run_pipeline",
        lambda url: (_ for _ in ()).throw(RuntimeError("pipeline exit code 1")),
    )
    monkeypatch.setattr(
        nightly_export,
        "mark_failed",
        lambda run_id, error_message: (_ for _ in ()).throw(RuntimeError("recorder down")),
    )
    assert nightly_export.main() == 1
    assert _status(day) == "failed"


def test_lost_claim_cancels_without_a_row(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    clean_day,
) -> None:
    day = clean_day(_DAY + timedelta(days=10))
    monkeypatch.setenv("TARGET_DATE", day.isoformat())
    monkeypatch.setattr(nightly_export, "has_processing_lock", lambda job_name: False)

    def lose(job_name: str, target_date: date) -> str:
        del job_name, target_date
        raise nightly_export.ProcessingLockHeld("nightly_export")

    monkeypatch.setattr(nightly_export, "claim_run", lose)
    assert nightly_export.main() == 0
    assert _status(day) is None
    text = _output(capsys)
    assert "status=cancelled" in text
    assert "reason=processing_lock" in text


def test_two_callers_one_winner(
    monkeypatch: pytest.MonkeyPatch,
    clean_day,
) -> None:
    day = clean_day(_DAY + timedelta(days=11))
    monkeypatch.setenv("TARGET_DATE", day.isoformat())
    monkeypatch.setattr(nightly_export, "run_pipeline", lambda url: None)
    results: list[int] = []

    def attempt() -> None:
        results.append(nightly_export.main())

    threads = [Thread(target=attempt), Thread(target=attempt)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
    assert sorted(results) == [0, 0]
    assert _status(day) == "completed"


def _count_jobs() -> int:
    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute("select count(*) from public.job_runs")
            found = cursor.fetchone()
    finally:
        connection.close()
    assert found is not None
    return int(found[0])


def _insert_event(event_id: str, day: date) -> None:
    stamp = datetime(day.year, day.month, day.day, 12, tzinfo=timezone.utc)
    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                insert into public.telemetry_events (
                    id, timestamp, service, event_type, level, value, message, tags
                ) values (
                    %(id)s, %(timestamp)s, 'api', 'staff_login_failed', 'error',
                    1, 'staff_session.login_failed', '{"outcome":"invalid_credentials"}'::jsonb
                )
                """,
                {"id": event_id, "timestamp": stamp},
            )
        connection.commit()
    finally:
        connection.close()


def _delete_event(event_id: str) -> None:
    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "delete from public.telemetry_events where id = %(id)s",
                {"id": event_id},
            )
        connection.commit()
    finally:
        connection.close()
