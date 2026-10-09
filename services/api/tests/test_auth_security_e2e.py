"""Security-focused integration checks for password recovery flows."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest
from fastapi.testclient import TestClient

from app.config import clear_settings_cache
from app.database import open_db, reset_tokens_table, users_table
from app.email import build_reset_link, send_password_reset_email
from app.main import app
from app.rate_limit import reset_forgot_password_limits
from app.security import hash_password, verify_password
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
    path = tmp_path / "security.json"
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


def test_password_stored_as_bcrypt_not_plaintext(db_path, user):
    db = open_db(db_path)
    try:
        stored = get_user_by_email(users_table(db), "lucia@brasaland.com")
    finally:
        db.close()
    assert stored is not None
    assert stored["password_hash"].startswith("$2")
    assert "ChangeMe123!" not in stored["password_hash"]
    assert verify_password("ChangeMe123!", stored["password_hash"])
    assert hash_password("ChangeMe123!") != "ChangeMe123!"


def test_full_recovery_flow_persists_and_logs_in(client, user, db_path, monkeypatch):
    captured: dict = {}

    def capture(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr("app.routers.auth.send_password_reset_email", capture)

    forgot = client.post("/auth/forgot-password", json={"email": "lucia@brasaland.com"})
    unknown = client.post("/auth/forgot-password", json={"email": "ghost@brasaland.com"})
    assert forgot.status_code == 200
    assert unknown.status_code == 200
    assert forgot.json() == unknown.json()

    token = captured["raw_token"]
    link = build_reset_link("http://localhost:3001", token)
    assert link.startswith("http://localhost:3001/reset-password?token=")
    assert token in link

    reset = client.post(
        "/auth/reset-password",
        json={"token": token, "new_password": "RecoveredPass9!"},
    )
    assert reset.status_code == 200

    db = open_db(db_path)
    try:
        rows = reset_tokens_table(db).all()
        assert all(row.get("used_at") is not None for row in rows)
        assert all("token_hash" in row and row["token_hash"] != token for row in rows)
        stored = get_user_by_email(users_table(db), "lucia@brasaland.com")
        assert verify_password("RecoveredPass9!", stored["password_hash"])
    finally:
        db.close()

    assert client.post(
        "/auth/login",
        json={"email": "lucia@brasaland.com", "password": "ChangeMe123!"},
    ).status_code == 401
    assert (
        client.post(
            "/auth/login",
            json={"email": "lucia@brasaland.com", "password": "RecoveredPass9!"},
        ).status_code
        == 200
    )


def test_concurrent_reset_allows_only_one_success(client, user, monkeypatch):
    captured: dict = {}

    def capture(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr("app.routers.auth.send_password_reset_email", capture)
    assert client.post("/auth/forgot-password", json={"email": "lucia@brasaland.com"}).status_code == 200
    token = captured["raw_token"]

    def attempt(password: str) -> int:
        with TestClient(app) as threaded_client:
            response = threaded_client.post(
                "/auth/reset-password",
                json={"token": token, "new_password": password},
            )
            return response.status_code

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [
            pool.submit(attempt, f"ConcurrentPass{i}!")
            for i in range(8)
        ]
        statuses = [future.result() for future in as_completed(futures)]

    assert statuses.count(200) == 1
    assert statuses.count(400) == 7

    login_new = client.post(
        "/auth/login",
        json={"email": "lucia@brasaland.com", "password": "ChangeMe123!"},
    )
    assert login_new.status_code == 401


def test_change_password_old_rejected_new_accepted(client, user):
    login = client.post(
        "/auth/login",
        json={"email": "lucia@brasaland.com", "password": "ChangeMe123!"},
    )
    token = login.json()["access_token"]
    changed = client.post(
        "/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": "ChangeMe123!", "new_password": "BrandNewPass1!"},
    )
    assert changed.status_code == 200
    assert client.post(
        "/auth/login",
        json={"email": "lucia@brasaland.com", "password": "ChangeMe123!"},
    ).status_code == 401
    assert client.post(
        "/auth/login",
        json={"email": "lucia@brasaland.com", "password": "BrandNewPass1!"},
    ).status_code == 200


def test_email_failure_logs_status_not_secrets(client, user, monkeypatch, caplog):
    import httpx

    def fake_post(*_args, **_kwargs):
        request = httpx.Request("POST", "https://api.resend.com/emails")
        return httpx.Response(401, request=request, json={"message": "invalid API key"})

    monkeypatch.setattr("app.email.httpx.post", fake_post)

    with caplog.at_level(logging.ERROR, logger="app.email"):
        response = client.post(
            "/auth/forgot-password",
            json={"email": "lucia@brasaland.com"},
        )

    assert response.status_code == 503
    joined = " ".join(record.getMessage() for record in caplog.records)
    assert "status=401" in joined
    assert "re_test_key" not in joined
    assert "ChangeMe123!" not in joined


def test_send_password_reset_email_calls_resend_shape(auth_env, monkeypatch):
    from app.config import get_settings

    calls: list = []

    def fake_post(url, **kwargs):
        calls.append({"url": url, "json": kwargs["json"], "headers": kwargs["headers"]})
        request = __import__("httpx").Request("POST", url)
        return __import__("httpx").Response(200, request=request, json={"id": "msg_1"})

    monkeypatch.setattr("app.email.httpx.post", fake_post)
    settings = get_settings()
    send_password_reset_email(
        to_email="lucia@brasaland.com",
        raw_token="raw-token-value",
        settings=settings,
    )
    assert len(calls) == 1
    assert calls[0]["url"] == "https://api.resend.com/emails"
    assert calls[0]["json"]["to"] == ["lucia@brasaland.com"]
    assert "raw-token-value" in calls[0]["json"]["text"]
    assert "raw-token-value" in calls[0]["json"]["html"]
    assert "Authorization" in calls[0]["headers"]
    # Header exists but test secret must not leak into app logs (checked elsewhere).
    assert calls[0]["json"]["text"].count("token=") == 1
