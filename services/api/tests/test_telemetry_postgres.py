"""Apply the migration to Postgres and read the rows back."""

import json
from pathlib import Path

import pgserver
import psycopg
import pytest
from psycopg.errors import RaiseException

from app.telemetry_config import TELEMETRY_PATH
from app.telemetry_store import MIGRATION_PATH, bulk_insert_sql

SECRET_LOCATION = "SECRET-LOCATION-XYZ"


def _ids(suffix: str) -> dict[str, str]:
    return {
        "eventId": f"44444444-4444-4444-8444-4444444444{suffix}",
        "sessionId": "55555555-5555-4555-8555-555555555555",
        "requestId": "66666666-6666-4666-8666-666666666666",
    }


def inbound_event() -> dict:
    body = _ids("11")
    body.update(
        {
            "timestamp": "2026-10-26T20:32:00Z",
            "userId": "opaque-staff-1",
            "event_type": "inbound_order_created",
            "entity_action": "inbound_order_created",
            "schemaVersion": "1.0.0",
            "properties": {
                "location_id": SECRET_LOCATION,
                "country": "CO",
                "product_id": "beef-loin",
                "product_category": "protein",
                "quantity": 2,
                "unit": "kg",
                "currency": "COP",
                "supplier_id": "sup-1",
                "unit_cost": 10,
                "inbound_order_id": "in-1",
            },
        }
    )
    return body


def outbound_event() -> dict:
    body = _ids("22")
    body.update(
        {
            "timestamp": "2026-10-26T20:40:00Z",
            "userId": "opaque-staff-1",
            "event_type": "outbound_order_created",
            "entity_action": "outbound_order_created",
            "schemaVersion": "1.0.0",
            "properties": {
                "location_id": "loc-miami",
                "country": "US",
                "product_id": "beef-loin",
                "product_category": "protein",
                "quantity": 1,
                "unit": "kg",
                "currency": "USD",
                "outbound_order_id": "out-1",
                "reason": "prep_consumption",
            },
        }
    )
    return body


def technical_event() -> dict:
    body = _ids("33")
    body.update(
        {
            "timestamp": "2026-10-26T20:41:00Z",
            "userId": None,
            "event_type": "user_login_failed",
            "entity_action": "user_login_failed",
            "schemaVersion": "1.0.0",
            "properties": {
                "error_code": "invalid_credentials",
                "attempt_bucket": "1",
            },
        }
    )
    return body


def _apply(connection: psycopg.Connection) -> None:
    script = MIGRATION_PATH.read_text(encoding="utf-8")
    connection.execute(script)


@pytest.fixture()
def postgres_url(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    server = pgserver.get_server(tmp_path / "pgdata", cleanup_mode="delete")
    uri = server.get_uri()
    monkeypatch.setenv("DATABASE_URL", uri)
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    with psycopg.connect(uri, autocommit=True) as connection:
        _apply(connection)
    yield uri
    server.stop() if hasattr(server, "stop") else None


def test_bulk_insert_sql_is_one_statement() -> None:
    statement = bulk_insert_sql(3)
    assert statement.count("INSERT") == 1
    assert statement.count("%s") == 30


def test_postgres_stores_representative_events_and_rejects_mutations(
    client, postgres_url
) -> None:
    mixed = client.post(
        TELEMETRY_PATH,
        json={
            "events": [
                inbound_event(),
                outbound_event(),
                technical_event(),
                {"event_type": "not-an-event"},
            ]
        },
    )
    assert mixed.status_code == 200
    assert mixed.json() == {"received": 4, "stored": 3, "rejected": 1}

    invalid_only = client.post(
        TELEMETRY_PATH,
        json={"events": [{"event_type": "still-not"}]},
    )
    assert invalid_only.status_code == 200
    assert invalid_only.json() == {"received": 1, "stored": 0, "rejected": 1}

    with psycopg.connect(postgres_url) as connection:
        columns = connection.execute(
            """
            SELECT column_name, udt_name, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'telemetry_events'
            ORDER BY ordinal_position
            """
        ).fetchall()
        indexes = connection.execute(
            """
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE schemaname = 'public' AND tablename = 'telemetry_events'
            ORDER BY indexname
            """
        ).fetchall()
        rows = connection.execute(
            """
            SELECT event_type, "timestamp", service, tags, user_id
            FROM telemetry_events
            ORDER BY event_type
            """
        ).fetchall()
        writer_update = connection.execute(
            """
            SELECT has_table_privilege(
                'telemetry_writer', 'public.telemetry_events', 'UPDATE'
            )
            """
        ).fetchone()
        writer_delete = connection.execute(
            """
            SELECT has_table_privilege(
                'telemetry_writer', 'public.telemetry_events', 'DELETE'
            )
            """
        ).fetchone()
        writer_insert = connection.execute(
            """
            SELECT has_table_privilege(
                'telemetry_writer', 'public.telemetry_events', 'INSERT'
            )
            """
        ).fetchone()
        with pytest.raises(RaiseException, match="cannot be updated or deleted"):
            connection.execute(
                "UPDATE public.telemetry_events SET event_type = 'changed'"
            )
        connection.rollback()
        with pytest.raises(RaiseException, match="cannot be updated or deleted"):
            connection.execute("DELETE FROM public.telemetry_events")
        connection.rollback()
        remaining = connection.execute(
            "SELECT count(*) FROM public.telemetry_events"
        ).fetchone()

    assert [(name, udt, nullable) for name, udt, nullable in columns] == [
        ("id", "int8", "NO"),
        ("event_id", "uuid", "NO"),
        ("timestamp", "timestamptz", "NO"),
        ("session_id", "uuid", "NO"),
        ("user_id", "text", "YES"),
        ("event_type", "text", "NO"),
        ("entity_action", "text", "NO"),
        ("schema_version", "text", "NO"),
        ("request_id", "uuid", "NO"),
        ("service", "text", "NO"),
        ("tags", "jsonb", "NO"),
    ]
    index_defs = {name: definition for name, definition in indexes}
    assert "telemetry_events_timestamp_idx" in index_defs
    assert '"timestamp"' in index_defs["telemetry_events_timestamp_idx"]
    assert "telemetry_events_event_type_idx" in index_defs
    assert "(event_type)" in index_defs["telemetry_events_event_type_idx"]
    assert "USING gin (tags)" in index_defs["telemetry_events_tags_gin_idx"]
    assert writer_update == (False,)
    assert writer_delete == (False,)
    assert writer_insert == (True,)
    assert remaining == (3,)
    stored = {row[0]: row for row in rows}
    assert set(stored) == {
        "inbound_order_created",
        "outbound_order_created",
        "user_login_failed",
    }
    inbound = stored["inbound_order_created"]
    assert inbound[2] == "brasaland-api"
    tags = inbound[3] if isinstance(inbound[3], dict) else json.loads(inbound[3])
    assert tags["location_id"] == SECRET_LOCATION
    assert tags["country"] == "CO"
    assert tags["currency"] == "COP"
    assert "email" not in tags
    outbound_tags = stored["outbound_order_created"][3]
    if not isinstance(outbound_tags, dict):
        outbound_tags = json.loads(outbound_tags)
    assert outbound_tags["reason"] == "prep_consumption"
    assert outbound_tags["country"] == "US"
    assert stored["user_login_failed"][4] is None


def test_postgres_failure_is_not_reported_as_stored(
    client, postgres_url, monkeypatch
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://invalid:invalid@127.0.0.1:1/none")
    response = client.post(TELEMETRY_PATH, json={"events": [technical_event()]})
    assert response.status_code == 500
    assert response.json() == {"detail": "Telemetry events were not stored"}
    with psycopg.connect(postgres_url) as connection:
        count = connection.execute(
            "SELECT count(*) FROM public.telemetry_events"
        ).fetchone()
    assert count == (0,)
