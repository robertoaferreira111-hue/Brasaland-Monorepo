"""Persist one dead-letter row per exhausted Celery task."""

from __future__ import annotations

import psycopg

from app.config import get_settings


def record_dlq_entry(
    *,
    task_id: str,
    task_name: str,
    attempt: int,
    error_message: str,
) -> None:
    """Insert one row. A second call with the same task_id does nothing."""
    url = get_settings().database_url
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    with psycopg.connect(url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                insert into public.dlq_tasks (task_id, task_name, attempt, error_message)
                values (%(task_id)s, %(task_name)s, %(attempt)s, %(error_message)s)
                on conflict (task_id) do nothing
                """,
                {
                    "task_id": task_id,
                    "task_name": task_name,
                    "attempt": attempt,
                    "error_message": error_message,
                },
            )
        connection.commit()
