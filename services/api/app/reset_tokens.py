"""Hashed password-reset token persistence in TinyDB."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from tinydb import Query
from tinydb.table import Table

from app.security import generate_reset_token, hash_token


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def issue_reset_token(
    table: Table,
    *,
    user_id: int,
    expire_minutes: int,
) -> tuple[str, int]:
    """Create a single-use reset token. Returns (raw_token, document_id)."""
    raw = generate_reset_token()
    now = _utcnow()
    doc_id = table.insert(
        {
            "token_hash": hash_token(raw),
            "user_id": user_id,
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(minutes=expire_minutes)).isoformat(),
            "used_at": None,
        }
    )
    return raw, doc_id


def find_valid_token(table: Table, raw_token: str) -> dict | None:
    row = table.get(Query().token_hash == hash_token(raw_token))
    if row is None:
        return None
    data = dict(row)
    data["id"] = row.doc_id
    if data.get("used_at") is not None:
        return None
    if _parse_dt(data["expires_at"]) <= _utcnow():
        return None
    return data


def consume_valid_token(table: Table, raw_token: str) -> dict | None:
    """Mark a valid unused token as used via a conditional update.

    Returns the consumed record, or ``None`` if the token is missing, expired,
    already used, or lost a concurrent consume race.
    """
    token_hash = hash_token(raw_token)
    row = table.get(Query().token_hash == token_hash)
    if row is None:
        return None
    if _parse_dt(row["expires_at"]) <= _utcnow():
        return None

    now = _utcnow().isoformat()
    token_q = Query()
    updated_ids = table.update(
        {"used_at": now},
        (token_q.token_hash == token_hash)
        & (token_q.used_at.test(lambda value: value is None)),
    )
    if not updated_ids:
        return None

    data = dict(row)
    data["id"] = row.doc_id
    data["used_at"] = now
    return data


def mark_token_used(table: Table, token_id: int) -> None:
    table.update({"used_at": _utcnow().isoformat()}, doc_ids=[token_id])


def invalidate_user_tokens(table: Table, user_id: int) -> None:
    """Mark every unused token for the user as used (e.g. after password change)."""
    now = _utcnow().isoformat()
    unused_ids = [
        row.doc_id
        for row in table.search(Query().user_id == user_id)
        if row.get("used_at") is None
    ]
    if unused_ids:
        table.update({"used_at": now}, doc_ids=unused_ids)
