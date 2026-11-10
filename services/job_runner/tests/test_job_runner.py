"""job_runs transitions against the Postgres named by DATABASE_URL."""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest

from job_runner import (
    create_run,
    has_completed_for_date,
    has_processing_lock,
    mark_completed,
    mark_failed,
    mark_processing,
)
from job_runner.job_runner import _load_database_url, connect

_DAY = date(2026, 11, 8)
_OTHER_DAY = _DAY + timedelta(days=1)


@pytest.fixture
def database_url() -> str:
    url = _load_database_url()
    if not url:
        pytest.skip("DATABASE_URL is not set")
    return url


@pytest.fixture
def job_name(database_url: str):
    del database_url
    name = f"test_job_runner_{uuid4().hex}"
    yield name
    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "delete from public.job_runs where job_name = %(job_name)s",
                {"job_name": name},
            )
        connection.commit()
    finally:
        connection.close()


def _row(run_id: str) -> dict:
    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select job_name, target_date, status, started_at, finished_at,
                       error_message, created_at
                from public.job_runs
                where id = %(run_id)s
                """,
                {"run_id": run_id},
            )
            found = cursor.fetchone()
    finally:
        connection.close()
    assert found is not None
    keys = (
        "job_name",
        "target_date",
        "status",
        "started_at",
        "finished_at",
        "error_message",
        "created_at",
    )
    return dict(zip(keys, found, strict=True))


def test_package_does_not_import_the_api_app() -> None:
    source = Path(__file__).resolve().parents[1].joinpath("job_runner.py").read_text(
        encoding="utf-8"
    )
    imports = [
        line.strip()
        for line in source.splitlines()
        if line.startswith("import ") or line.startswith("from ")
    ]
    assert "import fastapi" not in imports
    assert "from app.config import get_settings" not in imports
    assert "from app.main import app" not in imports
    assert not any("pipelines" in line for line in imports)
    assert "app" not in sys.modules
    assert "app.main" not in sys.modules
    assert "fastapi" not in sys.modules


def test_create_run_inserts_pending(job_name: str) -> None:
    run_id = create_run(job_name, _DAY)
    row = _row(run_id)
    assert row["job_name"] == job_name
    assert row["target_date"] == _DAY
    assert row["status"] == "pending"
    assert row["started_at"] is None
    assert row["finished_at"] is None
    assert row["error_message"] is None
    assert row["created_at"] is not None
    assert has_processing_lock(job_name) is False
    assert has_completed_for_date(job_name, _DAY) is False


def test_pending_to_processing_sets_started_at(job_name: str) -> None:
    run_id = create_run(job_name, _DAY)
    mark_processing(run_id)
    row = _row(run_id)
    assert row["status"] == "processing"
    assert row["started_at"] is not None
    assert row["finished_at"] is None
    assert has_processing_lock(job_name) is True
    assert has_completed_for_date(job_name, _DAY) is False


def test_processing_to_completed_sets_finished_at(job_name: str) -> None:
    run_id = create_run(job_name, _DAY)
    mark_processing(run_id)
    mark_completed(run_id)
    row = _row(run_id)
    assert row["status"] == "completed"
    assert row["started_at"] is not None
    assert row["finished_at"] is not None
    assert has_processing_lock(job_name) is False
    assert has_completed_for_date(job_name, _DAY) is True
    assert has_completed_for_date(job_name, _OTHER_DAY) is False


def test_processing_to_failed_stores_the_error(job_name: str) -> None:
    run_id = create_run(job_name, _DAY)
    mark_processing(run_id)
    mark_failed(run_id, "pipeline exit code 1")
    row = _row(run_id)
    assert row["status"] == "failed"
    assert row["finished_at"] is not None
    assert row["error_message"] == "pipeline exit code 1"
    assert has_processing_lock(job_name) is False
    assert has_completed_for_date(job_name, _DAY) is False


def test_lock_and_completion_are_scoped_to_the_job_and_date(database_url: str) -> None:
    del database_url
    first = f"test_job_runner_{uuid4().hex}"
    second = f"test_job_runner_{uuid4().hex}"
    try:
        first_id = create_run(first, _DAY)
        create_run(second, _DAY)
        create_run(first, _OTHER_DAY)
        mark_processing(first_id)
        assert has_processing_lock(first) is True
        assert has_processing_lock(second) is False
        mark_completed(first_id)
        assert has_completed_for_date(first, _DAY) is True
        assert has_completed_for_date(first, _OTHER_DAY) is False
        assert has_completed_for_date(second, _DAY) is False
    finally:
        connection = connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    delete from public.job_runs
                    where job_name = any(%(names)s)
                    """,
                    {"names": [first, second]},
                )
            connection.commit()
        finally:
            connection.close()


def test_unknown_run_id_is_rejected(database_url: str) -> None:
    del database_url
    missing = str(uuid4())
    with pytest.raises(RuntimeError, match="was not updated"):
        mark_processing(missing)
    with pytest.raises(RuntimeError, match="was not updated"):
        mark_completed(missing)
    with pytest.raises(RuntimeError, match="was not updated"):
        mark_failed(missing, "missing")


def test_status_check_rejects_other_values(database_url: str) -> None:
    del database_url
    connection = connect()
    try:
        with connection.cursor() as cursor:
            with pytest.raises(psycopg.errors.CheckViolation):
                cursor.execute(
                    """
                    insert into public.job_runs (job_name, target_date, status)
                    values ('test_job_runner_bad_status', %(target_date)s, 'locked')
                    """,
                    {"target_date": _DAY},
                )
        connection.rollback()
    finally:
        connection.close()


def test_job_runs_catalog(database_url: str) -> None:
    del database_url
    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select column_name, data_type, is_nullable
                from information_schema.columns
                where table_schema = 'public' and table_name = 'job_runs'
                order by ordinal_position
                """
            )
            columns = {
                name: (data_type, nullable)
                for name, data_type, nullable in cursor.fetchall()
            }
            cursor.execute(
                """
                select pg_get_constraintdef(oid)
                from pg_constraint
                where conrelid = 'public.job_runs'::regclass
                  and contype = 'c'
                """
            )
            checks = [row[0] for row in cursor.fetchall()]
            cursor.execute(
                """
                select indexdef
                from pg_indexes
                where schemaname = 'public' and tablename = 'job_runs'
                """
            )
            indexes = [row[0] for row in cursor.fetchall()]
            cursor.execute(
                """
                select column_name
                from information_schema.columns
                where table_schema = 'reporting' and table_name = 'pipeline_runs'
                order by ordinal_position
                """
            )
            pipeline_columns = [row[0] for row in cursor.fetchall()]
    finally:
        connection.close()

    assert columns["id"][0] == "uuid"
    assert columns["job_name"] == ("text", "NO")
    assert columns["target_date"] == ("date", "NO")
    assert columns["status"] == ("text", "NO")
    assert columns["started_at"][0] == "timestamp with time zone"
    assert columns["finished_at"][0] == "timestamp with time zone"
    assert columns["error_message"] == ("text", "YES")
    assert columns["created_at"] == ("timestamp with time zone", "NO")
    assert any("pending" in check and "processing" in check for check in checks)
    assert any("completed" in check and "failed" in check for check in checks)
    joined = "\n".join(indexes)
    assert "job_name, status" in joined
    assert "job_name, target_date" in joined
    assert "run_id" in pipeline_columns
    assert "target_date" not in pipeline_columns
