"""Atomic processing claims against the partial unique index."""

from __future__ import annotations

from datetime import date, timedelta
from threading import Barrier, Thread
from uuid import uuid4

import pytest

from job_runner import (
    ProcessingLockHeld,
    claim_run,
    create_run,
    has_processing_lock,
    mark_completed,
    mark_failed,
    mark_processing,
)
from job_runner.job_runner import _load_database_url, connect

_DAY = date(1999, 2, 1)
_OTHER = _DAY + timedelta(days=1)


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


def _statuses(name: str) -> list[str]:
    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select status
                from public.job_runs
                where job_name = %(job_name)s
                order by created_at, status
                """,
                {"job_name": name},
            )
            return [row[0] for row in cursor.fetchall()]
    finally:
        connection.close()


def test_concurrent_claims_have_one_winner(job_name: str) -> None:
    barrier = Barrier(2)
    results: list[str] = []
    errors: list[BaseException] = []

    def attempt(target: date) -> None:
        try:
            barrier.wait(timeout=5)
            results.append(claim_run(job_name, target))
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [
        Thread(target=attempt, args=(_DAY,)),
        Thread(target=attempt, args=(_OTHER,)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert len(results) == 1
    assert len(errors) == 1
    assert isinstance(errors[0], ProcessingLockHeld)
    assert sorted(_statuses(job_name)) == ["processing"]
    assert has_processing_lock(job_name) is True


def test_completed_row_releases_the_claim(job_name: str) -> None:
    first = claim_run(job_name, _DAY)
    mark_completed(first)
    second = claim_run(job_name, _OTHER)
    assert first != second
    assert sorted(_statuses(job_name)) == ["completed", "processing"]


def test_failed_row_releases_the_claim(job_name: str) -> None:
    first = claim_run(job_name, _DAY)
    mark_failed(first, "pipeline exit code 1")
    claim_run(job_name, _OTHER)
    assert sorted(_statuses(job_name)) == ["failed", "processing"]


def test_mark_processing_rejects_a_second_claim(job_name: str) -> None:
    winner = create_run(job_name, _DAY)
    loser = create_run(job_name, _OTHER)
    mark_processing(winner)
    with pytest.raises(ProcessingLockHeld):
        mark_processing(loser)
    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select status from public.job_runs where id = %(run_id)s
                """,
                {"run_id": loser},
            )
            found = cursor.fetchone()
    finally:
        connection.close()
    assert found is not None
    assert found[0] == "pending"
    assert sorted(_statuses(job_name)) == ["pending", "processing"]
