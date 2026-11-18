"""Read-only incident routes against the real Brasaland CSV."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.incidents import get_incident_record, read_incident_csv, seed_incidents
from app.main import app

CSV_FIELDS = (
    "incident_id",
    "date",
    "location_id",
    "category",
    "description",
    "status",
    "customer_id",
    "satisfaction_score",
    "reporter_id",
)


@pytest.fixture
def db_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "suppliers.json"
    monkeypatch.setattr("app.database.DEFAULT_DB_PATH", path)
    return path


@pytest.fixture
def client(db_path: Path):
    seed_incidents(db_path)
    with TestClient(app) as test_client:
        registered = test_client.post(
            "/users",
            json={"email": "staff@brasaland.com", "password": "secret-pass"},
        )
        assert registered.status_code == 201
        login = test_client.post(
            "/auth/login",
            json={"email": "staff@brasaland.com", "password": "secret-pass"},
        )
        assert login.status_code == 200
        test_client.headers.update(
            {"Authorization": f"Bearer {login.json()['access_token']}"}
        )
        yield test_client


def _csv_by_id() -> dict[str, dict]:
    return {record.incident_id: record.model_dump(mode="json") for record in read_incident_csv()}


def test_incident_routes_require_a_staff_token(db_path: Path):
    seed_incidents(db_path)
    with TestClient(app) as anonymous:
        listed = anonymous.get("/api/incidents")
        single = anonymous.get("/api/incidents/BRS-000001")
    assert listed.status_code == 401
    assert listed.json()["detail"] == "Not authenticated"
    assert single.status_code == 401


def test_list_returns_every_csv_row(client: TestClient):
    response = client.get("/api/incidents")
    assert response.status_code == 200
    body = response.json()
    expected = _csv_by_id()
    assert [row["incident_id"] for row in body] == list(expected)
    assert set(body[0]) == set(CSV_FIELDS)
    assert body[0] == expected["BRS-000001"]


def test_filters_match_the_csv(client: TestClient):
    records = list(_csv_by_id().values())
    listed = client.get("/api/incidents", params={"status": "OPEN", "category": "STAFF"})
    assert listed.status_code == 200
    assert listed.json() == [
        row for row in records if row["status"] == "OPEN" and row["category"] == "STAFF"
    ]


def test_status_filter_and_unknown_status(client: TestClient):
    records = list(_csv_by_id().values())
    opened = client.get("/api/incidents", params={"status": "OPEN"})
    assert opened.status_code == 200
    assert [row["incident_id"] for row in opened.json()] == [
        row["incident_id"] for row in records if row["status"] == "OPEN"
    ]
    rejected = client.get("/api/incidents", params={"status": "pending"})
    assert rejected.status_code == 422


def test_single_incident_and_missing(client: TestClient):
    expected = _csv_by_id()
    found = client.get("/api/incidents/BRS-000001")
    assert found.status_code == 200
    assert found.json() == expected["BRS-000001"]
    missing = client.get("/api/incidents/BRS-999999")
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Incident not found"


def test_blank_csv_cells_stay_null_and_the_row_is_kept(client: TestClient):
    expected = _csv_by_id()
    assert expected["BRS-000044"]["location_id"] is None
    assert expected["BRS-000049"]["category"] is None
    assert expected["BRS-000079"]["description"] is None
    assert expected["BRS-000086"]["status"] == "CLOSED"
    assert expected["BRS-000086"]["satisfaction_score"] is None
    for incident_id in ("BRS-000044", "BRS-000049", "BRS-000079", "BRS-000086"):
        response = client.get(f"/api/incidents/{incident_id}")
        assert response.status_code == 200
        assert response.json() == expected[incident_id]


def test_seed_is_idempotent_and_in_process_read_matches(db_path: Path):
    first = seed_incidents(db_path)
    second = seed_incidents(db_path)
    assert first.inserted == first.total == 100
    assert second.inserted == 0
    assert second.total == 100
    assert get_incident_record("BRS-000001").model_dump(mode="json") == _csv_by_id()[
        "BRS-000001"
    ]
    assert get_incident_record("BRS-999999") is None


def test_openapi_lists_read_routes_only(client: TestClient):
    document = client.get("/openapi.json")
    assert document.status_code == 200
    paths = document.json()["paths"]
    assert set(paths["/api/incidents"]) == {"get"}
    assert set(paths["/api/incidents/{incident_id}"]) == {"get"}
    created = client.post("/api/incidents", json={"incident_id": "BRS-000001"})
    assert created.status_code == 405
