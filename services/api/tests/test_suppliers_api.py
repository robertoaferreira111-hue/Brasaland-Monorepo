"""HTTP behavior for the supplier API."""

import pytest
from fastapi.testclient import TestClient

from app.database import open_db, suppliers_table
from app.main import app
from app.seed import SUPPLIERS_SEED, seed_suppliers

SUPPLIER_FIELDS = {
    "name",
    "country",
    "categories",
    "rate_per_unit",
    "currency",
    "updated_at",
    "status",
    "contact_email",
    "notes",
    "id",
}


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = tmp_path / "suppliers.json"
    monkeypatch.setattr("app.database.DEFAULT_DB_PATH", path)
    return path


@pytest.fixture
def client(db_path):
    with TestClient(app) as test_client:
        yield test_client


def _payload(**overrides) -> dict:
    data = {
        "name": "New Grill Supply",
        "country": "USA",
        "categories": ["carne"],
        "rate_per_unit": 9.5,
        "currency": "USD",
        "status": "active",
        "contact_email": "new@example.com",
    }
    data.update(overrides)
    return data


def test_post_creates_supplier_with_id_and_timestamp(client):
    response = client.post("/suppliers", json=_payload())
    assert response.status_code == 201
    body = response.json()
    assert set(body) == SUPPLIER_FIELDS
    assert isinstance(body["id"], int)
    assert body["name"] == "New Grill Supply"
    assert body["notes"] is None
    assert body["updated_at"]
    assert "2000" not in body["updated_at"]


def test_post_rejects_invalid_payloads(client, db_path):
    cases = [
        _payload(status="archived"),
        _payload(rate_per_unit=0),
        _payload(rate_per_unit=-3),
        _payload(country="Colombia", currency="USD"),
        _payload(categories=["meat"]),
        _payload(categories=[]),
        _payload(updated_at="2000-01-01T00:00:00+00:00"),
        _payload(id=4),
    ]
    for payload in cases:
        response = client.post("/suppliers", json=payload)
        assert response.status_code == 422, payload

    db = open_db(db_path)
    try:
        assert len(suppliers_table(db)) == 0
    finally:
        db.close()


def test_get_returns_seeded_suppliers_and_filters(client, db_path):
    seed_suppliers(db_path)

    all_rows = client.get("/suppliers")
    assert all_rows.status_code == 200
    assert len(all_rows.json()) == 15

    colombia = client.get("/suppliers", params={"country": "Colombia"})
    assert colombia.status_code == 200
    assert {row["name"] for row in colombia.json()} == {
        record["name"] for record in SUPPLIERS_SEED if record["country"] == "Colombia"
    }

    meat = client.get("/suppliers", params={"category": "carne"})
    assert {row["name"] for row in meat.json()} == {
        record["name"] for record in SUPPLIERS_SEED if "carne" in record["categories"]
    }

    usa_meat = client.get(
        "/suppliers", params={"country": "USA", "category": "carne"}
    )
    assert [row["name"] for row in usa_meat.json()] == ["Miami Meat Distributors LLC"]

    dairy = client.get("/suppliers", params={"category": "lacteos"})
    assert [row["name"] for row in dairy.json()] == ["Distribuidora RefriCol"]

    assert client.get("/suppliers", params={"country": "Mexico"}).status_code == 422
    assert client.get("/suppliers", params={"category": "meat"}).status_code == 422


def test_get_one_and_missing(client):
    created = client.post("/suppliers", json=_payload()).json()
    found = client.get(f"/suppliers/{created['id']}")
    assert found.status_code == 200
    assert found.json()["name"] == "New Grill Supply"
    missing = client.get(f"/suppliers/{created['id'] + 99}")
    assert missing.status_code == 404


def test_patch_rate_persists_and_refreshes_timestamp(client, db_path):
    created = client.post("/suppliers", json=_payload()).json()
    original_timestamp = created["updated_at"]

    rejected = client.patch(
        f"/suppliers/{created['id']}/rate", json={"rate_per_unit": 0}
    )
    assert rejected.status_code == 422
    negative = client.patch(
        f"/suppliers/{created['id']}/rate", json={"rate_per_unit": -1}
    )
    assert negative.status_code == 422

    updated = client.patch(
        f"/suppliers/{created['id']}/rate", json={"rate_per_unit": 11.25}
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["rate_per_unit"] == 11.25
    assert body["updated_at"] != original_timestamp
    assert body["name"] == created["name"]

    db = open_db(db_path)
    try:
        stored = suppliers_table(db).get(doc_id=created["id"])
    finally:
        db.close()
    assert stored["rate_per_unit"] == 11.25
    assert stored["updated_at"] == body["updated_at"]

    missing = client.patch("/suppliers/999/rate", json={"rate_per_unit": 4})
    assert missing.status_code == 404


def test_patch_status_persists_without_changing_timestamp(client, db_path):
    created = client.post(
        "/suppliers", json=_payload(status="active")
    ).json()

    rejected = client.patch(
        f"/suppliers/{created['id']}/status", json={"status": "closed"}
    )
    assert rejected.status_code == 422

    updated = client.patch(
        f"/suppliers/{created['id']}/status", json={"status": "suspended"}
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "suspended"
    assert updated.json()["updated_at"] == created["updated_at"]

    db = open_db(db_path)
    try:
        stored = suppliers_table(db).get(doc_id=created["id"])
    finally:
        db.close()
    assert stored["status"] == "suspended"
    assert stored["updated_at"] == created["updated_at"]

    missing = client.patch(
        "/suppliers/999/status", json={"status": "active"}
    )
    assert missing.status_code == 404


def test_delete_removes_supplier(client):
    created = client.post("/suppliers", json=_payload()).json()
    deleted = client.delete(f"/suppliers/{created['id']}")
    assert deleted.status_code == 200
    assert deleted.json()["id"] == created["id"]
    assert client.get(f"/suppliers/{created['id']}").status_code == 404
    assert client.delete(f"/suppliers/{created['id']}").status_code == 404
