"""Shared auth-test helpers. Token expiry is set on the token, not by sleeping."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
from tinydb import Query

from app.database import open_db, refresh_table, users_table
from app.security import ALGORITHM, SECRET_KEY

EMAIL = "staff.user@brasaland.com"
PASSWORD = "secret-pass"


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def signed_token(
    subject: str,
    token_type: str,
    *,
    minutes_until_expiry: int,
    jti: str | None = "fixed-jti",
    include_subject: bool = True,
) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, object] = {
        "type": token_type,
        "iat": int((now - timedelta(hours=1)).timestamp()),
        "exp": int((now + timedelta(minutes=minutes_until_expiry)).timestamp()),
    }
    if include_subject:
        payload["sub"] = subject
    if jti is not None:
        payload["jti"] = jti
    encoded = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return encoded if isinstance(encoded, str) else encoded.decode("utf-8")


def decision(response) -> str:
    detail = response.json().get("detail")
    return detail if isinstance(detail, str) else ""


def error_names_field(response, field: str) -> bool:
    # The field name is the business signal. The validation-error envelope is not.
    detail = response.json().get("detail")
    if not isinstance(detail, list):
        return False
    return any(
        isinstance(item, dict) and field in item.get("loc", ())
        for item in detail
    )


def no_tokens(response) -> bool:
    body = response.json()
    return "access_token" not in body and "refresh_token" not in body


def user_emails(db_path: Path) -> list[str]:
    db = open_db(db_path)
    try:
        return [row["email"] for row in users_table(db).all()]
    finally:
        db.close()


def refresh_rows(db_path: Path) -> list[dict]:
    db = open_db(db_path)
    try:
        return [dict(row) for row in refresh_table(db).all()]
    finally:
        db.close()


def remove_users(db_path: Path) -> None:
    db = open_db(db_path)
    try:
        users_table(db).remove(Query().email.exists())
    finally:
        db.close()


def remove_refresh_tokens(db_path: Path) -> None:
    db = open_db(db_path)
    try:
        refresh_table(db).remove(Query().jti.exists())
    finally:
        db.close()


def store_refresh(db_path: Path, jti: str, email: str) -> None:
    db = open_db(db_path)
    try:
        refresh_table(db).insert({"jti": jti, "email": email})
    finally:
        db.close()


def register(client, email: str = EMAIL, password: str = PASSWORD):
    return client.post("/users", json={"email": email, "password": password})


def login(client, email: str = EMAIL, password: str = PASSWORD):
    return client.post("/auth/login", json={"email": email, "password": password})


def register_and_login(client, email: str = EMAIL, password: str = PASSWORD) -> dict:
    created = register(client, email, password)
    assert created.status_code == 201
    signed_in = login(client, email, password)
    assert signed_in.status_code == 200
    return signed_in.json()
