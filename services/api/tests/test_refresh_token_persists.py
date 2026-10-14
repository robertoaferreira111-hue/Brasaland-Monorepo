"""Check that login still stores a refresh token when two database handles are open."""

from fastapi.testclient import TestClient

from app.database import open_db, refresh_table
from app.main import app

client = TestClient(app)


def test_login_refresh_row_survives_two_db_connections(auth_db_path) -> None:
    email = "refresh.persist@brasaland.com"
    password = "secret-pass"

    registered = client.post("/users", json={"email": email, "password": password})
    assert registered.status_code == 201

    login = client.post("/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    body = login.json()
    assert body["access_token"]
    assert body["refresh_token"]

    db = open_db(auth_db_path)
    try:
        stored = refresh_table(db).all()
    finally:
        db.close()
    assert len(stored) == 1
    assert stored[0]["email"] == email

    refreshed = client.post("/auth/refresh", json={"refresh_token": body["refresh_token"]})
    assert refreshed.status_code == 200
    assert refreshed.json()["access_token"]
    assert refreshed.json()["refresh_token"] != body["refresh_token"]
