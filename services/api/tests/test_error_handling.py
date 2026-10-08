"""Structured error responses and safe failure boundaries."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.database import open_db, suppliers_table
from app.errors import (
    STORAGE_UNAVAILABLE,
    STORED_DATA_INVALID,
    StorageError,
    UNEXPECTED_ERROR,
)
from app.main import app
from app.routers import suppliers as suppliers_router


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = tmp_path / "suppliers.json"
    monkeypatch.setattr("app.database.DEFAULT_DB_PATH", path)
    return path


@pytest.fixture
def client(db_path):
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def _assert_safe_error_body(body: dict, expected_detail: str) -> None:
    assert body == {"detail": expected_detail}
    serialized = json.dumps(body)
    assert "Traceback" not in serialized
    assert "/Users/" not in serialized
    assert "suppliers.json" not in serialized
    assert "OSError" not in serialized


def test_missing_supplier_returns_structured_404(client):
    response = client.get("/suppliers/999")
    assert response.status_code == 404
    _assert_safe_error_body(response.json(), "Supplier not found")


def test_validation_error_preserves_422_detail_list(client):
    response = client.post(
        "/suppliers",
        json={
            "name": "Bad",
            "country": "USA",
            "categories": ["carne"],
            "rate_per_unit": 0,
            "currency": "USD",
            "status": "active",
        },
    )
    assert response.status_code == 422
    body = response.json()
    assert "detail" in body
    assert isinstance(body["detail"], list)
    assert body["detail"]


def test_storage_failure_returns_safe_500(client, monkeypatch):
    def boom(*_args, **_kwargs):
        raise StorageError("Storage unavailable")

    monkeypatch.setattr("app.database.open_db", boom)
    response = client.get("/suppliers")
    assert response.status_code == 500
    _assert_safe_error_body(response.json(), STORAGE_UNAVAILABLE)


def test_corrupt_supplier_get_returns_safe_500(client, db_path):
    db = open_db(db_path)
    try:
        doc_id = suppliers_table(db).insert(
            {
                "name": "Broken Row",
                "country": "Atlantis",
                "categories": [],
                "rate_per_unit": -1,
                "currency": "XYZ",
                "status": "archived",
                "updated_at": "not-a-timestamp",
            }
        )
    finally:
        db.close()

    response = client.get(f"/suppliers/{doc_id}")
    assert response.status_code == 500
    _assert_safe_error_body(response.json(), STORED_DATA_INVALID)


def test_list_skips_corrupt_rows_and_returns_valid_ones(client, db_path):
    created = client.post(
        "/suppliers",
        json={
            "name": "Healthy Supply",
            "country": "USA",
            "categories": ["carne"],
            "rate_per_unit": 4.5,
            "currency": "USD",
            "status": "active",
        },
    )
    assert created.status_code == 201

    db = open_db(db_path)
    try:
        suppliers_table(db).insert(
            {
                "name": "Broken Row",
                "country": "Atlantis",
                "categories": "not-a-list",
                "rate_per_unit": -1,
                "currency": "XYZ",
                "status": "archived",
                "updated_at": "not-a-timestamp",
            }
        )
    finally:
        db.close()

    response = client.get("/suppliers")
    assert response.status_code == 200
    names = {row["name"] for row in response.json()}
    assert names == {"Healthy Supply"}


def test_unhandled_exception_returns_safe_500(client, monkeypatch):
    def boom(*_args, **_kwargs):
        raise RuntimeError("secret path /Users/roberto/project/data/suppliers.json")

    monkeypatch.setattr(suppliers_router, "persist_supplier", boom)
    response = client.post(
        "/suppliers",
        json={
            "name": "Will Fail",
            "country": "USA",
            "categories": ["carne"],
            "rate_per_unit": 3,
            "currency": "USD",
            "status": "active",
        },
    )
    assert response.status_code == 500
    _assert_safe_error_body(response.json(), UNEXPECTED_ERROR)
