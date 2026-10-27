"""POST /telemetry/events persists accepted events in one bulk insert."""

import logging

import pytest
from tinydb import TinyDB

from app.main import app
from app.models import TelemetryEvent
from app.telemetry_config import TELEMETRY_PATH, TELEMETRY_SERVICE
from app.telemetry_store import TelemetryStoreError, event_row, get_telemetry_store

OPAQUE_USER = "opaque-staff-1"
SECRET_LOCATION = "SECRET-LOCATION-XYZ"


class RecordingStore:
    def __init__(self) -> None:
        self.calls: list[list[dict]] = []
        self.fail = False

    def insert_many(self, rows: list[dict]) -> None:
        self.calls.append(list(rows))
        if self.fail:
            raise TelemetryStoreError("database unavailable")


def _ids(suffix: str) -> dict[str, str]:
    return {
        "eventId": f"11111111-1111-4111-8111-1111111111{suffix}",
        "sessionId": "22222222-2222-4222-8222-222222222222",
        "requestId": "33333333-3333-4333-8333-333333333333",
    }


def inbound_event(location_id: str = "loc-poblado") -> dict:
    body = _ids("11")
    body.update(
        {
            "timestamp": "2026-10-26T20:32:00Z",
            "userId": OPAQUE_USER,
            "event_type": "inbound_order_created",
            "entity_action": "inbound_order_created",
            "schemaVersion": "1.0.0",
            "properties": {
                "location_id": location_id,
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


def logged_in_event() -> dict:
    body = _ids("22")
    body.update(
        {
            "timestamp": "2026-10-26T20:32:01Z",
            "userId": OPAQUE_USER,
            "event_type": "user_logged_in",
            "entity_action": "user_logged_in",
            "schemaVersion": "1.0.0",
            "properties": {"auth_method": "password"},
        }
    )
    return body


def invalid_event() -> dict:
    event = logged_in_event()
    event["entity_action"] = "user_logged_out"
    return event


@pytest.fixture()
def store():
    recording = RecordingStore()
    app.dependency_overrides[get_telemetry_store] = lambda: recording
    yield recording
    app.dependency_overrides.pop(get_telemetry_store, None)


def _assert_counts(body: dict, received: int, stored: int, rejected: int) -> None:
    assert body == {"received": received, "stored": stored, "rejected": rejected}
    assert body["received"] == body["stored"] + body["rejected"]


def test_all_valid_batch_is_one_bulk_insert(client, store) -> None:
    first = inbound_event()
    second = logged_in_event()
    response = client.post(TELEMETRY_PATH, json={"events": [first, second]})
    assert response.status_code == 200
    _assert_counts(response.json(), received=2, stored=2, rejected=0)
    assert len(store.calls) == 1
    assert store.calls[0] == [
        event_row(TelemetryEvent.model_validate(first), TELEMETRY_SERVICE),
        event_row(TelemetryEvent.model_validate(second), TELEMETRY_SERVICE),
    ]
    assert store.calls[0][0]["tags"] == first["properties"]
    assert store.calls[0][0]["service"] == "brasaland-api"


def test_mixed_batch_stores_only_valid_events(client, store) -> None:
    response = client.post(
        TELEMETRY_PATH,
        json={"events": [inbound_event(), invalid_event(), "nope"]},
    )
    assert response.status_code == 200
    _assert_counts(response.json(), received=3, stored=1, rejected=2)
    assert len(store.calls) == 1
    assert [row["event_type"] for row in store.calls[0]] == ["inbound_order_created"]


def test_all_invalid_batch_does_not_insert(client, store) -> None:
    response = client.post(
        TELEMETRY_PATH,
        json={"events": [invalid_event(), {"event_type": "user_logged_in"}]},
    )
    assert response.status_code == 200
    _assert_counts(response.json(), received=2, stored=0, rejected=2)
    assert store.calls == []


def test_empty_batch_does_not_insert(client, store) -> None:
    response = client.post(TELEMETRY_PATH, json={"events": []})
    assert response.status_code == 200
    _assert_counts(response.json(), received=0, stored=0, rejected=0)
    assert store.calls == []


def test_malformed_envelope_does_not_insert(client, store) -> None:
    not_json = client.post(
        TELEMETRY_PATH,
        content=b"{",
        headers={"Content-Type": "application/json"},
    )
    not_an_array = client.post(TELEMETRY_PATH, json={"events": {}})
    missing = client.post(TELEMETRY_PATH, json={})
    assert not_json.status_code == 422
    assert not_an_array.status_code == 422
    assert missing.status_code == 422
    assert store.calls == []


def test_database_failure_is_not_reported_as_stored(client, store) -> None:
    store.fail = True
    response = client.post(TELEMETRY_PATH, json={"events": [logged_in_event()]})
    assert response.status_code == 500
    assert response.json() == {"detail": "Telemetry events were not stored"}
    assert "stored" not in response.json()
    assert len(store.calls) == 1


def test_unconfigured_store_does_not_claim_success(client) -> None:
    response = client.post(TELEMETRY_PATH, json={"events": [logged_in_event()]})
    assert response.status_code == 500
    assert response.json()["detail"] == "Telemetry events were not stored"


def test_success_path_does_not_open_tinydb(client, store, auth_db_path, monkeypatch) -> None:
    def refuse_database(*_args, **_kwargs):
        raise AssertionError("TinyDB opened")

    monkeypatch.setattr(TinyDB, "__init__", refuse_database)
    response = client.post(TELEMETRY_PATH, json={"events": [logged_in_event()]})
    assert response.status_code == 200
    assert not auth_db_path.exists()


def test_schema_rejection_does_not_drop_valid_events(client, store) -> None:
    unknown_property = logged_in_event()
    unknown_property["properties"]["email"] = "staff@brasaland.com"
    wrong_type = inbound_event()
    wrong_type["eventId"] = "11111111-1111-4111-8111-111111111199"
    wrong_type["properties"]["quantity"] = "2"
    response = client.post(
        TELEMETRY_PATH,
        json={"events": [logged_in_event(), unknown_property, wrong_type]},
    )
    assert response.status_code == 200
    _assert_counts(response.json(), received=3, stored=1, rejected=2)
    assert len(store.calls) == 1
    assert [row["event_type"] for row in store.calls[0]] == ["user_logged_in"]


def test_log_omits_event_payload(client, store, caplog) -> None:
    caplog.set_level(logging.INFO)
    response = client.post(
        TELEMETRY_PATH,
        json={"events": [inbound_event(SECRET_LOCATION), logged_in_event()]},
    )
    assert response.status_code == 200
    assert "event_types=inbound_order_created,user_logged_in" in caplog.text
    assert SECRET_LOCATION not in caplog.text
    assert OPAQUE_USER not in caplog.text
    assert "auth_method" not in caplog.text
    assert "password" not in caplog.text
