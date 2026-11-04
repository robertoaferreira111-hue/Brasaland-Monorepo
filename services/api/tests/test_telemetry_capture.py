"""Telemetry capture: mapping, isolation, and HTTP response stability."""

from __future__ import annotations

from typing import Any

import pytest

from app.errors import StorageError
from app.telemetry import (
    emit_staff_login_failed,
    persist_telemetry_event,
)
from tests.support import register_and_login


@pytest.fixture()
def capture_rows(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def fake_post(endpoint: str, headers: dict, json: dict) -> None:
        del endpoint, headers
        rows.append(json)

        class _Resp:
            status_code = 201

        return _Resp()

    class _Client:
        def __init__(self, *args: object, **kwargs: object) -> None:
            del args, kwargs

        def __enter__(self) -> "_Client":
            return self

        def __exit__(self, *args: object) -> None:
            del args

        def post(self, endpoint: str, headers: dict, json: dict) -> object:
            return fake_post(endpoint, headers, json)

    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-service-role")
    monkeypatch.setattr("app.telemetry.httpx.Client", _Client)
    return rows


def test_persist_maps_eight_columns(capture_rows: list[dict[str, Any]]) -> None:
    persist_telemetry_event(
        event_type="staff_login_failed",
        level="error",
        message="Staff login rejected",
        tags={"outcome": "invalid_credentials"},
    )
    assert len(capture_rows) == 1
    row = capture_rows[0]
    assert set(row) >= {
        "id",
        "timestamp",
        "service",
        "event_type",
        "level",
        "tags",
        "message",
    }
    assert row["service"] == "api"
    assert row["event_type"] == "staff_login_failed"
    assert row["level"] == "error"
    assert row["tags"] == {"outcome": "invalid_credentials"}
    assert row["timestamp"].endswith("Z")


def test_persist_swallows_transport_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Boom:
        def __init__(self, *args: object, **kwargs: object) -> None:
            del args, kwargs

        def __enter__(self) -> "_Boom":
            return self

        def __exit__(self, *args: object) -> None:
            del args

        def post(self, *args: object, **kwargs: object) -> object:
            del args, kwargs
            raise RuntimeError("network down")

    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-service-role")
    monkeypatch.setattr("app.telemetry.httpx.Client", _Boom)
    emit_staff_login_failed()  # must not raise


def test_failed_login_emits_and_keeps_401(
    client, capture_rows: list[dict[str, Any]]
) -> None:
    response = client.post(
        "/auth/login",
        json={"email": "nobody@brasaland.com", "password": "nope"},
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Incorrect email or password"}
    assert any(r["event_type"] == "staff_login_failed" for r in capture_rows)


def test_unauthenticated_suppliers_emits_protected_route(
    client, capture_rows: list[dict[str, Any]]
) -> None:
    response = client.get("/suppliers")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"
    assert any(
        r["event_type"] == "protected_route_unauthenticated"
        and r["tags"]["route"] == "/suppliers"
        for r in capture_rows
    )


def test_validation_error_emits_422(
    client, capture_rows: list[dict[str, Any]]
) -> None:
    response = client.post("/auth/login", json={})
    assert response.status_code == 422
    assert "detail" in response.json()
    assert any(
        r["event_type"] == "request_validation_rejected"
        and r["tags"]["status_code"] == 422
        for r in capture_rows
    )


def test_supplier_create_emits_business_event(
    client, capture_rows: list[dict[str, Any]]
) -> None:
    tokens = register_and_login(client)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    payload = {
        "name": "Telemetry Meat Co",
        "country": "Colombia",
        "currency": "COP",
        "categories": ["carne"],
        "rate_per_unit": 12.5,
        "status": "active",
        "contact_email": "ops@example.com",
    }
    response = client.post("/suppliers", json=payload, headers=headers)
    assert response.status_code == 201
    body = response.json()
    assert any(
        r["event_type"] == "supplier_created"
        and r["tags"]["supplier_id"] == str(body["id"])
        and r["level"] == "info"
        and "contact_email" not in r["tags"]
        for r in capture_rows
    )


def test_storage_unavailable_emits(
    client, capture_rows: list[dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    tokens = register_and_login(client)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    def broken_table():
        raise StorageError("Storage unavailable")
        yield  # pragma: no cover

    monkeypatch.setattr("app.routers.suppliers.get_table", broken_table)

    response = client.get("/suppliers", headers=headers)
    assert response.status_code == 500
    assert response.json() == {"detail": "Storage unavailable"}
    assert any(r["event_type"] == "storage_unavailable" for r in capture_rows)
