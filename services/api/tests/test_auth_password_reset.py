"""Backend coverage for password recovery and change flows."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.config import clear_settings_cache
from app.database import open_db, reset_tokens_table, users_table
from app.email import EmailDeliveryError
from app.main import app
from app.rate_limit import reset_forgot_password_limits
from app.security import hash_token, verify_password
from app.users import create_user, get_user_by_email


@pytest.fixture
def auth_env(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret-at-least-32-bytes-long")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
    monkeypatch.setenv("RESET_TOKEN_EXPIRE_MINUTES", "30")
    monkeypatch.setenv("FRONTEND_URL", "http://localhost:3001")
    monkeypatch.setenv("RESEND_API_KEY", "re_test_key")
    monkeypatch.setenv("EMAIL_FROM", "Brasaland <test@brasaland.com>")
    clear_settings_cache()
    reset_forgot_password_limits()
    yield
    clear_settings_cache()
    reset_forgot_password_limits()


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = tmp_path / "app.json"
    monkeypatch.setattr("app.database.DEFAULT_DB_PATH", path)
    return path


@pytest.fixture
def client(auth_env, db_path):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def user(db_path):
    db = open_db(db_path)
    try:
        return create_user(
            users_table(db),
            email="lucia@brasaland.com",
            password="ChangeMe123!",
        )
    finally:
        db.close()


def _login(client: TestClient, email: str = "lucia@brasaland.com", password: str = "ChangeMe123!") -> str:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    body = response.json()
    assert "password" not in body
    assert "password_hash" not in body
    return body["access_token"]


def test_forgot_password_same_response_for_unknown_email(client, user, monkeypatch):
    sent: dict = {}

    def capture(**kwargs):
        sent.update(kwargs)

    monkeypatch.setattr("app.routers.auth.send_password_reset_email", capture)

    known = client.post("/auth/forgot-password", json={"email": "lucia@brasaland.com"})
    unknown = client.post("/auth/forgot-password", json={"email": "nobody@brasaland.com"})

    assert known.status_code == 200
    assert unknown.status_code == 200
    assert known.json() == unknown.json()
    assert "password" not in known.json()
    assert sent["to_email"] == "lucia@brasaland.com"
    assert sent["raw_token"]


def test_forgot_password_unknown_email_does_not_send(client, user, monkeypatch):
    calls: list = []
    monkeypatch.setattr(
        "app.routers.auth.send_password_reset_email",
        lambda **kwargs: calls.append(kwargs),
    )
    response = client.post("/auth/forgot-password", json={"email": "missing@example.com"})
    assert response.status_code == 200
    assert calls == []


def test_forgot_password_email_failure_returns_503(client, user, monkeypatch):
    def boom(**kwargs):
        raise EmailDeliveryError("provider down")

    monkeypatch.setattr("app.routers.auth.send_password_reset_email", boom)
    response = client.post("/auth/forgot-password", json={"email": "lucia@brasaland.com"})
    assert response.status_code == 503
    assert "Unable to send recovery email" in response.json()["detail"]


def test_reset_password_success_and_single_use(client, user, db_path, monkeypatch):
    captured: dict = {}

    def capture(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr("app.routers.auth.send_password_reset_email", capture)
    assert client.post("/auth/forgot-password", json={"email": "lucia@brasaland.com"}).status_code == 200
    token = captured["raw_token"]

    db = open_db(db_path)
    try:
        rows = reset_tokens_table(db).all()
        assert len(rows) == 1
        assert rows[0]["token_hash"] == hash_token(token)
        assert rows[0]["token_hash"] != token
    finally:
        db.close()

    first = client.post(
        "/auth/reset-password",
        json={"token": token, "new_password": "NewPass456!"},
    )
    assert first.status_code == 200
    assert "password_hash" not in first.json()

    # Old password no longer works; new password does.
    assert client.post(
        "/auth/login",
        json={"email": "lucia@brasaland.com", "password": "ChangeMe123!"},
    ).status_code == 401
    assert _login(client, password="NewPass456!")

    reuse = client.post(
        "/auth/reset-password",
        json={"token": token, "new_password": "AnotherPass789!"},
    )
    assert reuse.status_code == 400


def test_reset_password_rejects_invalid_token(client, user):
    response = client.post(
        "/auth/reset-password",
        json={"token": "not-a-real-token", "new_password": "NewPass456!"},
    )
    assert response.status_code == 400


def test_reset_password_rejects_expired_token(client, user, db_path):
    from app.reset_tokens import issue_reset_token

    db = open_db(db_path)
    try:
        tokens = reset_tokens_table(db)
        raw, doc_id = issue_reset_token(tokens, user_id=user["id"], expire_minutes=30)
        expired_at = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        tokens.update({"expires_at": expired_at}, doc_ids=[doc_id])
    finally:
        db.close()

    response = client.post(
        "/auth/reset-password",
        json={"token": raw, "new_password": "NewPass456!"},
    )
    assert response.status_code == 400


def test_change_password_requires_auth(client, user):
    response = client.post(
        "/auth/change-password",
        json={"current_password": "ChangeMe123!", "new_password": "NewPass456!"},
    )
    assert response.status_code == 401


def test_change_password_rejects_wrong_current(client, user):
    token = _login(client)
    response = client.post(
        "/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": "WrongPass!", "new_password": "NewPass456!"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Current password is incorrect"


def test_change_password_success(client, user, db_path):
    token = _login(client)
    response = client.post(
        "/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": "ChangeMe123!", "new_password": "NewPass456!"},
    )
    assert response.status_code == 200
    assert "password_hash" not in response.json()

    db = open_db(db_path)
    try:
        stored = get_user_by_email(users_table(db), "lucia@brasaland.com")
        assert stored is not None
        assert verify_password("NewPass456!", stored["password_hash"])
        assert not verify_password("ChangeMe123!", stored["password_hash"])
    finally:
        db.close()

    assert client.post(
        "/auth/login",
        json={"email": "lucia@brasaland.com", "password": "ChangeMe123!"},
    ).status_code == 401
    assert _login(client, password="NewPass456!")


def test_reset_link_uses_configured_frontend_url(auth_env):
    from app.config import get_settings
    from app.email import build_reset_link

    link = build_reset_link(get_settings().frontend_url, "abc123")
    assert link == "http://localhost:3001/reset-password?token=abc123"


def test_forgot_password_rate_limit_keeps_same_public_message(client, user, monkeypatch):
    from app.rate_limit import FORGOT_MAX_ATTEMPTS

    calls: list = []
    monkeypatch.setattr(
        "app.routers.auth.send_password_reset_email",
        lambda **kwargs: calls.append(kwargs),
    )
    bodies = []
    for _ in range(FORGOT_MAX_ATTEMPTS + 2):
        response = client.post(
            "/auth/forgot-password",
            json={"email": "lucia@brasaland.com"},
        )
        assert response.status_code == 200
        bodies.append(response.json())
    assert len({tuple(body.items()) for body in bodies}) == 1
    assert len(calls) == FORGOT_MAX_ATTEMPTS
