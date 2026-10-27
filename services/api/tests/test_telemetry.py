"""Telemetry stub: validate a batch, acknowledge it, and store nothing."""

import logging

from tinydb import TinyDB

from app.telemetry_config import (
    DEFAULT_TELEMETRY_ENDPOINT,
    TELEMETRY_ENDPOINT,
    TELEMETRY_PATH,
    path_from_endpoint,
)

SECRET_LOCATION = "SECRET-LOCATION-XYZ"
OPAQUE_USER = "opaque-staff-1"


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


def test_path_from_telemetry_endpoint_setting() -> None:
    assert path_from_endpoint(DEFAULT_TELEMETRY_ENDPOINT) == "/telemetry/events"
    assert path_from_endpoint("https://collector.example/custom/events") == "/custom/events"
    assert TELEMETRY_PATH == path_from_endpoint(TELEMETRY_ENDPOINT)


def test_post_is_available_and_get_is_rejected(client) -> None:
    options = client.get("/openapi.json")
    assert options.status_code == 200
    path = options.json()["paths"][TELEMETRY_PATH]
    assert list(path) == ["post"]

    rejected = client.get(TELEMETRY_PATH)
    assert rejected.status_code == 405


def test_valid_batch_returns_received_count(client) -> None:
    response = client.post(
        TELEMETRY_PATH,
        json={"events": [inbound_event(), logged_in_event()]},
    )
    assert response.status_code == 200
    assert response.json() == {"received": 2}


def test_logs_count_and_event_types_without_payload(client, caplog) -> None:
    caplog.set_level(logging.INFO)
    response = client.post(
        TELEMETRY_PATH,
        json={"events": [inbound_event(SECRET_LOCATION), logged_in_event()]},
    )
    assert response.status_code == 200
    assert "count=2" in caplog.text
    assert "inbound_order_created" in caplog.text
    assert "user_logged_in" in caplog.text
    assert SECRET_LOCATION not in caplog.text
    assert OPAQUE_USER not in caplog.text
    assert "auth_method" not in caplog.text
    assert "password" not in caplog.text


def test_empty_batch_is_rejected(client) -> None:
    response = client.post(TELEMETRY_PATH, json={"events": []})
    assert response.status_code == 422


def test_malformed_batch_is_rejected(client) -> None:
    not_json = client.post(
        TELEMETRY_PATH,
        content=b"{",
        headers={"Content-Type": "application/json"},
    )
    not_an_array = client.post(TELEMETRY_PATH, json={"events": {}})
    not_an_event = client.post(TELEMETRY_PATH, json={"events": ["nope"]})
    assert not_json.status_code == 422
    assert not_an_array.status_code == 422
    assert not_an_event.status_code == 422


def test_missing_required_field_is_rejected(client) -> None:
    event = inbound_event()
    del event["eventId"]
    response = client.post(TELEMETRY_PATH, json={"events": [event]})
    assert response.status_code == 422


def test_invalid_property_type_is_rejected(client) -> None:
    event = inbound_event()
    event["properties"]["quantity"] = "2"
    response = client.post(TELEMETRY_PATH, json={"events": [event]})
    assert response.status_code == 422
    assert "quantity" in response.text


def test_unknown_property_is_rejected(client) -> None:
    event = logged_in_event()
    event["properties"]["email"] = "staff@brasaland.com"
    response = client.post(TELEMETRY_PATH, json={"events": [event]})
    assert response.status_code == 422


def test_valid_batch_does_not_open_a_database(client, auth_db_path, monkeypatch) -> None:
    def refuse_database(*_args, **_kwargs):
        raise AssertionError("TinyDB opened")

    monkeypatch.setattr(TinyDB, "__init__", refuse_database)
    response = client.post(TELEMETRY_PATH, json={"events": [logged_in_event()]})
    assert response.status_code == 200
    assert response.json() == {"received": 1}
    assert not auth_db_path.exists()
