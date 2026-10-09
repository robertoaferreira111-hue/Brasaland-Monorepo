"""TinyDB helpers for application users."""

from __future__ import annotations

from datetime import datetime, timezone

from tinydb import Query
from tinydb.table import Table

from app.security import hash_password


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_email(email: str) -> str:
    return email.strip().lower()


def public_user(document: dict, user_id: int | None = None) -> dict:
    """Return a user dict safe for API responses (no password hash)."""
    doc_id = user_id if user_id is not None else document.get("id")
    if doc_id is None and hasattr(document, "doc_id"):
        doc_id = document.doc_id
    return {
        "id": doc_id,
        "email": document["email"],
        "created_at": document.get("created_at"),
        "password_changed_at": document.get("password_changed_at"),
    }


def get_user_by_email(table: Table, email: str) -> dict | None:
    row = table.get(Query().email == normalize_email(email))
    if row is None:
        return None
    data = dict(row)
    data["id"] = row.doc_id
    return data


def get_user_by_id(table: Table, user_id: int) -> dict | None:
    row = table.get(doc_id=user_id)
    if row is None:
        return None
    data = dict(row)
    data["id"] = user_id
    return data


def create_user(table: Table, *, email: str, password: str) -> dict:
    normalized = normalize_email(email)
    if get_user_by_email(table, normalized) is not None:
        raise ValueError("email already registered")
    now = _utcnow()
    document = {
        "email": normalized,
        "password_hash": hash_password(password),
        "created_at": now,
        "password_changed_at": now,
    }
    doc_id = table.insert(document)
    return get_user_by_id(table, doc_id)  # type: ignore[return-value]


def update_password(table: Table, user_id: int, new_password: str) -> dict | None:
    current = get_user_by_id(table, user_id)
    if current is None:
        return None
    table.update(
        {
            "password_hash": hash_password(new_password),
            "password_changed_at": _utcnow(),
        },
        doc_ids=[user_id],
    )
    return get_user_by_id(table, user_id)
