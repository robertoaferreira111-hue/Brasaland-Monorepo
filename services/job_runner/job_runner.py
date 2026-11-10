"""Persistence for public.job_runs.

This module opens DATABASE_URL with psycopg. It does not import the FastAPI
app. data/pipelines/db.py is not reused because that helper imports
services/api/app.config.
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from typing import Any
from uuid import UUID

import psycopg
from dotenv import load_dotenv

_REPO = Path(__file__).resolve().parents[2]
_API_ROOT = _REPO / "services" / "api"


def _load_database_url() -> str | None:
    """Read DATABASE_URL the same way the API settings do, without importing them."""
    for path in (_REPO / ".env" / "local", _REPO / ".env", _API_ROOT / ".env"):
        if path.is_file():
            load_dotenv(path, override=False)
    raw = os.getenv("DATABASE_URL")
    if raw is None or raw.strip() == "":
        return None
    return raw


class ProcessingLockHeld(Exception):
    """The database rejected a second processing row for this job."""

    def __init__(self, job_name: str) -> None:
        super().__init__(job_name)
        self.job_name = job_name


def connect() -> Any:
    """Open one connection. The caller commits and closes it."""
    url = _load_database_url()
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg.connect(url)


def _run_id(value: str | UUID) -> str:
    return str(value)


def _finish(connection: Any) -> None:
    try:
        connection.commit()
    finally:
        connection.close()


def create_run(job_name: str, target_date: date) -> str:
    """Insert a pending row and return its id."""
    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                insert into public.job_runs (job_name, target_date, status)
                values (%(job_name)s, %(target_date)s, 'pending')
                returning id
                """,
                {"job_name": job_name, "target_date": target_date},
            )
            row = cursor.fetchone()
        if row is None:
            raise RuntimeError("job_runs insert did not return an id")
        run_id = _run_id(row[0])
    except Exception:
        connection.rollback()
        connection.close()
        raise
    _finish(connection)
    return run_id


def mark_processing(run_id: str) -> None:
    """Move the row to processing and set started_at."""
    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                update public.job_runs
                set status = 'processing', started_at = now()
                where id = %(run_id)s
                """,
                {"run_id": run_id},
            )
            if cursor.rowcount != 1:
                raise RuntimeError(f"job_runs row {run_id} was not updated")
    except psycopg.errors.UniqueViolation as exc:
        connection.rollback()
        connection.close()
        raise ProcessingLockHeld(run_id) from exc
    except Exception:
        connection.rollback()
        connection.close()
        raise
    _finish(connection)


def claim_run(job_name: str, target_date: date) -> str:
    """Insert a row and mark it processing in one transaction.

    A losing claim rolls back, so it leaves neither a pending nor a processing
    row. The partial unique index on processing rows is what rejects it.
    """
    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                insert into public.job_runs (job_name, target_date, status)
                values (%(job_name)s, %(target_date)s, 'pending')
                returning id
                """,
                {"job_name": job_name, "target_date": target_date},
            )
            row = cursor.fetchone()
            if row is None:
                raise RuntimeError("job_runs insert did not return an id")
            run_id = _run_id(row[0])
            cursor.execute(
                """
                update public.job_runs
                set status = 'processing', started_at = now()
                where id = %(run_id)s
                """,
                {"run_id": run_id},
            )
    except psycopg.errors.UniqueViolation as exc:
        connection.rollback()
        connection.close()
        raise ProcessingLockHeld(job_name) from exc
    except Exception:
        connection.rollback()
        connection.close()
        raise
    _finish(connection)
    return run_id


def fail_if_processing(run_id: str, error_message: str) -> None:
    """Mark a still-processing row failed. A terminal row is left unchanged."""
    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                update public.job_runs
                set status = 'failed',
                    finished_at = now(),
                    error_message = %(error_message)s
                where id = %(run_id)s
                  and status = 'processing'
                """,
                {"run_id": run_id, "error_message": error_message},
            )
    except Exception:
        connection.rollback()
        connection.close()
        raise
    _finish(connection)


def mark_completed(run_id: str) -> None:
    """Move the row to completed and set finished_at."""
    _update(
        run_id,
        """
        update public.job_runs
        set status = 'completed', finished_at = now()
        where id = %(run_id)s
        """,
    )


def mark_failed(run_id: str, error_message: str) -> None:
    """Move the row to failed and store finished_at and error_message."""
    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                update public.job_runs
                set status = 'failed',
                    finished_at = now(),
                    error_message = %(error_message)s
                where id = %(run_id)s
                """,
                {"run_id": run_id, "error_message": error_message},
            )
            if cursor.rowcount != 1:
                raise RuntimeError(f"job_runs row {run_id} was not updated")
    except Exception:
        connection.rollback()
        connection.close()
        raise
    _finish(connection)


def has_processing_lock(job_name: str) -> bool:
    """True when any row for this job is processing."""
    return _exists(
        """
        select 1
        from public.job_runs
        where job_name = %(job_name)s
          and status = 'processing'
        """,
        {"job_name": job_name},
    )


def has_completed_for_date(job_name: str, target_date: date) -> bool:
    """True when a completed row exists for this job and calendar date."""
    return _exists(
        """
        select 1
        from public.job_runs
        where job_name = %(job_name)s
          and target_date = %(target_date)s
          and status = 'completed'
        """,
        {"job_name": job_name, "target_date": target_date},
    )


def _update(run_id: str, sql: str) -> None:
    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, {"run_id": run_id})
            if cursor.rowcount != 1:
                raise RuntimeError(f"job_runs row {run_id} was not updated")
    except Exception:
        connection.rollback()
        connection.close()
        raise
    _finish(connection)


def _exists(sql: str, params: dict[str, Any]) -> bool:
    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchone() is not None
    finally:
        connection.close()
