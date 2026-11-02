"""POST /telemetry/events counts, per-event rejection, and one bulk insert."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.errors import STORAGE_UNAVAILABLE, StorageError
from app.main import app
from app.telemetry_store import TelemetryBatchStore, get_telemetry_store

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

    def insert_batch(self, events: list[dict[str, Any]]) -> None:
        self.batches.append(list(events))


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
    assert store.batches[0][0]["event_type"] == "staff_login_failed"


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


def test_unconfigured_store_does_not_report_success() -> None:
    app.dependency_overrides.pop(get_telemetry_store, None)
    with TestClient(app, raise_server_exceptions=False) as test_client:
        response = test_client.post(
            "/telemetry/events", json={"events": [_login_failed()]}
        )
    assert response.status_code == 500
    assert response.json() == {"detail": STORAGE_UNAVAILABLE}
