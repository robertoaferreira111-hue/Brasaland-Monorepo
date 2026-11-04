"""POST /telemetry/events counts, per-event rejection, and one bulk insert."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import clear_settings_cache
from app.errors import STORAGE_UNAVAILABLE, StorageError
from app.main import app
from app.telemetry_event import TelemetryEvent
from app.telemetry_mapping import map_event_to_row
from app.telemetry_store import (
    SupabaseTelemetryStore,
    TelemetryBatchStore,
    get_telemetry_store,
)

_EVENT_ID = "6b9c2a10-7e2d-4c1a-9f0e-1a2b3c4d5e6f"
_REQUEST_ID = "6b9c2a10-7e2d-4c1a-9f0e-1a2b3c4d5e6a"


def _login_failed() -> dict[str, Any]:
    return {
        "eventId": _EVENT_ID,
        "timestamp": "2026-11-02T22:00:00Z",
        "sessionId": None,
        "userId": None,
        "event_type": "staff_login_failed",
        "entity_action": "staff_session.login_failed",
        "schemaVersion": "1.0.0",
        "requestId": _REQUEST_ID,
        "properties": {"outcome": "invalid_credentials"},
    }


class RecordingStore(TelemetryBatchStore):
    def __init__(self) -> None:
        self.batches: list[list[dict[str, Any]]] = []
        self.rows_by_id: dict[str, dict[str, Any]] = {}

    def insert_batch(self, events: list[dict[str, Any]]) -> int:
        self.batches.append(list(events))
        inserted = 0
        for row in events:
            event_id = row["id"]
            if event_id in self.rows_by_id:
                continue
            self.rows_by_id[event_id] = row
            inserted += 1
        return inserted


class FailingStore(TelemetryBatchStore):
    def insert_batch(self, events: list[dict[str, Any]]) -> None:
        del events
        raise StorageError("Storage unavailable")


@pytest.fixture
def store() -> RecordingStore:
    recording = RecordingStore()
    app.dependency_overrides[get_telemetry_store] = lambda: recording
    try:
        yield recording
    finally:
        app.dependency_overrides.pop(get_telemetry_store, None)


@pytest.fixture
def client(store: RecordingStore) -> TestClient:
    del store
    with TestClient(app) as test_client:
        yield test_client


def test_all_valid_batch_is_one_insert(client: TestClient, store: RecordingStore) -> None:
    first = _login_failed()
    second = _login_failed()
    second["eventId"] = "7c8d3b21-8f3e-4d2b-8a1f-2b3c4d5e6f70"
    response = client.post("/telemetry/events", json={"events": [first, second]})
    assert response.status_code == 200
    assert response.json() == {"received": 2, "stored": 2, "rejected": 0}
    assert len(store.batches) == 1
    assert len(store.batches[0]) == 2
    row = store.batches[0][0]
    assert row["event_type"] == "staff_login_failed"
    assert row["service"] == "api"
    assert row["level"] == "error"
    assert row["tags"] == {"outcome": "invalid_credentials"}
    assert row["id"] == first["eventId"]
    assert "eventId" not in row


def test_mixed_batch_stores_only_valid_events(
    client: TestClient, store: RecordingStore
) -> None:
    response = client.post(
        "/telemetry/events",
        json={"events": [_login_failed(), {"event_type": "not-an-event"}, "bad"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body == {"received": 3, "stored": 1, "rejected": 2}
    assert body["received"] == body["stored"] + body["rejected"]
    assert len(store.batches) == 1
    assert len(store.batches[0]) == 1


def test_all_invalid_batch_does_not_insert(
    client: TestClient, store: RecordingStore
) -> None:
    response = client.post(
        "/telemetry/events",
        json={"events": [{}, {"eventId": "not-a-uuid"}]},
    )
    assert response.status_code == 200
    assert response.json() == {"received": 2, "stored": 0, "rejected": 2}
    assert store.batches == []


def test_empty_batch_does_not_insert(client: TestClient, store: RecordingStore) -> None:
    response = client.post("/telemetry/events", json={"events": []})
    assert response.status_code == 200
    assert response.json() == {"received": 0, "stored": 0, "rejected": 0}
    assert store.batches == []


@pytest.mark.parametrize(
    "payload",
    [{}, {"events": "nope"}, {"events": None}, {"events": [], "extra": True}],
)
def test_malformed_envelope_is_not_success(
    client: TestClient, store: RecordingStore, payload: dict
) -> None:
    response = client.post("/telemetry/events", json=payload)
    assert response.status_code == 422
    assert "received" not in response.json()
    assert store.batches == []


def test_database_failure_is_not_successful_storage() -> None:
    app.dependency_overrides[get_telemetry_store] = lambda: FailingStore()
    try:
        with TestClient(app, raise_server_exceptions=False) as test_client:
            response = test_client.post(
                "/telemetry/events", json={"events": [_login_failed()]}
            )
    finally:
        app.dependency_overrides.pop(get_telemetry_store, None)
    assert response.status_code == 500
    assert response.json() == {"detail": STORAGE_UNAVAILABLE}
    assert "stored" not in response.json()


def test_runtime_schema_is_packaged_with_the_app() -> None:
    from app.telemetry_event import _SCHEMA_PATH, load_telemetry_schema

    load_telemetry_schema.cache_clear()
    docs = (
        Path(__file__).resolve().parents[3]
        / "docs"
        / "telemetry"
        / "event-schemas.json"
    )
    assert _SCHEMA_PATH.name == "telemetry_event_schema.json"
    assert _SCHEMA_PATH.parent.name == "app"
    assert "docs" not in _SCHEMA_PATH.parts
    assert _SCHEMA_PATH.read_bytes() == docs.read_bytes()
    assert load_telemetry_schema()["title"] == "Brasaland telemetry event schemas"


def test_unconfigured_store_does_not_report_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Ignore a developer .env so this case stays unconfigured in CI and locally.
    monkeypatch.setattr("app.config._load_env_files", lambda: None)
    monkeypatch.setenv("SUPABASE_URL", "")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "")
    clear_settings_cache()
    app.dependency_overrides.pop(get_telemetry_store, None)
    try:
        with TestClient(app, raise_server_exceptions=False) as test_client:
            response = test_client.post(
                "/telemetry/events", json={"events": [_login_failed()]}
            )
    finally:
        clear_settings_cache()
    assert response.status_code == 500
    assert response.json() == {"detail": STORAGE_UNAVAILABLE}


def _inbound_order() -> dict[str, Any]:
    return {
        "eventId": "6b9c2a10-7e2d-4c1a-9f0e-1a2b3c4d5e6f",
        "timestamp": "2026-11-02T22:00:00Z",
        "sessionId": "6b9c2a10-7e2d-4c1a-9f0e-1a2b3c4d5e6b",
        "userId": "stf_ab12cd34",
        "event_type": "inbound_order_created",
        "entity_action": "inbound_order.created",
        "schemaVersion": "1.0.0",
        "requestId": "6b9c2a10-7e2d-4c1a-9f0e-1a2b3c4d5e6c",
        "properties": {
            "location_id": "loc_co_01",
            "country": "CO",
            "supplier_id": "sup_01",
            "product_id": "prd_beef",
            "product_category": "protein",
            "quantity": 12.5,
            "unit": "kg",
            "currency": "COP",
            "unit_cost": 10,
        },
    }


def _outbound_order() -> dict[str, Any]:
    return {
        "eventId": "7c8d3b21-8f3e-4d2b-8a1f-2b3c4d5e6f70",
        "timestamp": "2026-11-02T22:05:00Z",
        "sessionId": "6b9c2a10-7e2d-4c1a-9f0e-1a2b3c4d5e6b",
        "userId": "stf_ab12cd34",
        "event_type": "outbound_order_created",
        "entity_action": "outbound_order.created",
        "schemaVersion": "1.0.0",
        "requestId": "6b9c2a10-7e2d-4c1a-9f0e-1a2b3c4d5e6d",
        "properties": {
            "location_id": "loc_us_01",
            "country": "US",
            "product_id": "prd_beef",
            "product_category": "protein",
            "quantity": 2,
            "unit": "kg",
            "currency": "USD",
        },
    }


def test_row_mapping_for_business_and_technical_events() -> None:
    inbound = map_event_to_row(TelemetryEvent.model_validate(_inbound_order()))
    outbound = map_event_to_row(TelemetryEvent.model_validate(_outbound_order()))
    technical = map_event_to_row(TelemetryEvent.model_validate(_login_failed()))
    assert inbound["level"] == "info"
    assert inbound["value"] == 12.5
    assert inbound["message"] == "inbound_order.created"
    assert inbound["id"] == _inbound_order()["eventId"]
    assert inbound["tags"]["country"] == "CO"
    assert inbound["tags"]["location_id"] == "loc_co_01"
    assert "eventId" not in inbound["tags"]
    assert outbound["event_type"] == "outbound_order_created"
    assert outbound["tags"]["country"] == "US"
    assert outbound["value"] == 2
    assert technical["level"] == "error"
    assert technical["value"] is None
    assert technical["service"] == "api"
    assert set(inbound) == {
        "id",
        "timestamp",
        "service",
        "event_type",
        "level",
        "value",
        "message",
        "tags",
    }


def test_supabase_store_inserts_the_batch_once() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        body = json.loads(request.content)
        return httpx.Response(201, json=body)

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="https://example.supabase.co",
    )
    store = SupabaseTelemetryStore(
        "https://example.supabase.co",
        "service-role-key",
        client,
    )
    rows = [{"event_type": "staff_login_failed"}, {"event_type": "inbound_order_created"}]
    assert store.insert_batch(rows) == 2
    assert len(seen) == 1
    request = seen[0]
    assert request.url.path == "/rest/v1/telemetry_events"
    assert request.url.params["on_conflict"] == "id"
    assert request.headers["apikey"] == "service-role-key"
    assert request.headers["authorization"] == "Bearer service-role-key"
    assert "resolution=ignore-duplicates" in request.headers["prefer"]
    assert json.loads(request.content) == rows


def test_supabase_store_failure_does_not_return_a_count() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(500, json={"message": "db down"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    store = SupabaseTelemetryStore("https://example.supabase.co", "service-role-key", client)
    with pytest.raises(StorageError):
        store.insert_batch([{"event_type": "staff_login_failed"}])


def test_duplicate_event_id_in_one_batch_stores_one_row(
    client: TestClient, store: RecordingStore
) -> None:
    first = _login_failed()
    second = _login_failed()
    second["timestamp"] = "2026-11-02T22:01:00Z"
    response = client.post("/telemetry/events", json={"events": [first, second]})
    assert response.status_code == 200
    assert response.json() == {"received": 2, "stored": 1, "rejected": 0}
    assert list(store.rows_by_id) == [_EVENT_ID]
    assert store.rows_by_id[_EVENT_ID]["id"] == _EVENT_ID
    assert len(store.batches) == 1
    assert len(store.batches[0]) == 1


def test_same_event_id_across_batches_stays_one_row(
    client: TestClient, store: RecordingStore
) -> None:
    first = client.post("/telemetry/events", json={"events": [_login_failed()]})
    second = client.post("/telemetry/events", json={"events": [_login_failed()]})
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == {"received": 1, "stored": 1, "rejected": 0}
    assert second.json() == {"received": 1, "stored": 0, "rejected": 0}
    assert list(store.rows_by_id) == [_EVENT_ID]


def test_mixed_batch_of_new_and_repeated_events(
    client: TestClient, store: RecordingStore
) -> None:
    client.post("/telemetry/events", json={"events": [_login_failed()]})
    repeated = _login_failed()
    fresh = _login_failed()
    fresh["eventId"] = "7c8d3b21-8f3e-4d2b-8a1f-2b3c4d5e6f70"
    response = client.post(
        "/telemetry/events",
        json={"events": [repeated, fresh, repeated]},
    )
    assert response.status_code == 200
    assert response.json() == {"received": 3, "stored": 1, "rejected": 0}
    assert set(store.rows_by_id) == {_EVENT_ID, fresh["eventId"]}


def test_invalid_event_id_is_still_rejected(
    client: TestClient, store: RecordingStore
) -> None:
    response = client.post(
        "/telemetry/events",
        json={"events": [_login_failed(), {"eventId": "not-a-uuid"}, _login_failed()]},
    )
    assert response.status_code == 200
    assert response.json() == {"received": 3, "stored": 1, "rejected": 1}
    assert list(store.rows_by_id) == [_EVENT_ID]


def test_repeated_id_from_supabase_is_not_an_error() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        body = json.loads(request.content)
        if calls["n"] == 1:
            return httpx.Response(201, json=body)
        return httpx.Response(201, json=[])

    client = httpx.Client(transport=httpx.MockTransport(handler))
    store = SupabaseTelemetryStore(
        "https://example.supabase.co",
        "service-role-key",
        client,
    )
    row = {"id": _EVENT_ID, "event_type": "staff_login_failed"}
    assert store.insert_batch([row]) == 1
    assert store.insert_batch([row]) == 0


def test_migration_declares_eight_columns_and_three_indexes() -> None:
    sql = (
        Path(__file__).resolve().parents[1]
        / "supabase"
        / "migrations"
        / "20261102180000_create_telemetry_events.sql"
    ).read_text(encoding="utf-8").lower()
    for name in (
        "id",
        "timestamp",
        "service",
        "event_type",
        "level",
        "value",
        "message",
        "tags",
    ):
        assert name in sql
    assert "idx_telemetry_events_timestamp" in sql
    assert "idx_telemetry_events_event_type" in sql
    assert "idx_telemetry_events_tags" in sql
    assert "using gin" in sql
    assert "drop table" not in sql
    assert "delete from" not in sql
