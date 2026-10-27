"""One SQL INSERT for every accepted telemetry event in a batch."""

import os
from pathlib import Path
from typing import Protocol

from psycopg.types.json import Json

from app.models import TelemetryEvent
from app.telemetry_config import TELEMETRY_SERVICE

MIGRATION_PATH = (
    Path(__file__).resolve().parents[3]
    / "supabase"
    / "migrations"
    / "20261027022000_create_telemetry_events.sql"
)

INSERT_COLUMNS = (
    "event_id",
    '"timestamp"',
    "session_id",
    "user_id",
    "event_type",
    "entity_action",
    "schema_version",
    "request_id",
    "service",
    "tags",
)

ROW_KEYS = (
    "event_id",
    "timestamp",
    "session_id",
    "user_id",
    "event_type",
    "entity_action",
    "schema_version",
    "request_id",
    "service",
    "tags",
)


class TelemetryStoreError(Exception):
    """The bulk insert did not complete."""


class TelemetryStore(Protocol):
    def insert_many(self, rows: list[dict]) -> None:
        """Persist every row in one call. Raise TelemetryStoreError on failure."""


def event_row(event: TelemetryEvent, service: str = TELEMETRY_SERVICE) -> dict:
    """Map one validated event onto the migration columns. `tags` is `properties`."""
    return {
        "event_id": event.eventId,
        "timestamp": event.timestamp,
        "session_id": event.sessionId,
        "user_id": event.userId,
        "event_type": event.event_type,
        "entity_action": event.entity_action,
        "schema_version": event.schemaVersion,
        "request_id": event.requestId,
        "service": service,
        "tags": event.properties,
    }


def bulk_insert_sql(row_count: int) -> str:
    """One INSERT statement. An empty batch is not an INSERT."""
    if row_count < 1:
        raise TelemetryStoreError("bulk insert requires at least one row")
    width = len(INSERT_COLUMNS)
    one_row = "(" + ",".join(["%s"] * width) + ")"
    values = ",".join([one_row] * row_count)
    return (
        f"INSERT INTO public.telemetry_events ({', '.join(INSERT_COLUMNS)}) "
        f"VALUES {values}"
    )


def _parameters(rows: list[dict]) -> list:
    parameters = []
    for row in rows:
        for key in ROW_KEYS:
            value = row[key]
            parameters.append(Json(value) if key == "tags" else value)
    return parameters


class PostgresTelemetryStore:
    """Supabase is Postgres. This store sends one INSERT for the whole batch.

    The connection context commits that statement, or rolls it back if it fails.
    """

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def insert_many(self, rows: list[dict]) -> None:
        if not rows:
            return
        import psycopg

        statement = bulk_insert_sql(len(rows))
        try:
            with psycopg.connect(self.database_url) as connection:
                connection.execute(statement, _parameters(rows))
        except TelemetryStoreError:
            raise
        except Exception as exc:
            raise TelemetryStoreError("bulk insert failed") from exc


class UnconfiguredTelemetryStore:
    """Fails the bulk insert. It does not open a database connection."""

    def insert_many(self, rows: list[dict]) -> None:
        del rows
        raise TelemetryStoreError("No database URL is configured")


def database_url() -> str | None:
    url = os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL")
    if url is None or not url.strip():
        return None
    return url.strip()


def get_telemetry_store() -> TelemetryStore:
    url = database_url()
    if url is None:
        return UnconfiguredTelemetryStore()
    return PostgresTelemetryStore(url)
