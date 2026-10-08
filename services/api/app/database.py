"""TinyDB persistence for users and refresh tokens."""

from collections.abc import Iterator
from pathlib import Path
from typing import Any

from tinydb import Query, TinyDB
from tinydb.table import Table

from app.models import ProfileResponse, RegisterUser
from app.security import hash_password, verify_password

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "auth.json"
USERS_TABLE = "users"
REFRESH_TABLE = "refresh_tokens"


def open_db(path: Path | None = None) -> TinyDB:
    db_path = Path(path) if path is not None else DEFAULT_DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return TinyDB(db_path)


def users_table(db: TinyDB) -> Table:
    return db.table(USERS_TABLE)


def refresh_table(db: TinyDB) -> Table:
    return db.table(REFRESH_TABLE)


def get_users_table() -> Iterator[Table]:
    db = open_db()
    try:
        yield users_table(db)
    finally:
        db.close()


def get_refresh_table() -> Iterator[Table]:
    db = open_db()
    try:
        yield refresh_table(db)
    finally:
        db.close()


def find_user(table: Table, email: str) -> dict[str, Any] | None:
    rows = table.search(Query().email == email)
    if not rows:
        return None
    return dict(rows[0])


def profile_from_user(user: dict[str, Any]) -> ProfileResponse:
    return ProfileResponse(
        email=user["email"],
        name=user.get("name", "") or "",
        phone=user.get("phone", "") or "",
        address=user.get("address", "") or "",
    )


def create_user(table: Table, payload: RegisterUser) -> ProfileResponse:
    if find_user(table, payload.email):
        raise ValueError("An account with this email already exists")
    digest, salt = hash_password(payload.password)
    document = {
        "email": payload.email,
        "password_digest": digest,
        "password_salt": salt,
        "name": "",
        "phone": "",
        "address": "",
    }
    table.insert(document)
    return profile_from_user(document)


def authenticate_user(table: Table, email: str, password: str) -> dict[str, Any] | None:
    user = find_user(table, email.strip().lower())
    if user is None:
        return None
    if not verify_password(password, user["password_salt"], user["password_digest"]):
        return None
    return user


def update_profile(
    table: Table,
    email: str,
    *,
    name: str,
    phone: str,
    address: str,
) -> ProfileResponse | None:
    user = find_user(table, email)
    if user is None:
        return None
    updated = {
        **user,
        "name": name.strip(),
        "phone": phone.strip(),
        "address": address.strip(),
    }
    table.update(updated, Query().email == email)
    return profile_from_user(updated)


def store_refresh_token(table: Table, jti: str, email: str) -> None:
    table.insert({"jti": jti, "email": email})


def refresh_token_active(table: Table, jti: str, email: str) -> bool:
    rows = table.search((Query().jti == jti) & (Query().email == email))
    return len(rows) > 0


def revoke_refresh_token(table: Table, jti: str) -> None:
    table.remove(Query().jti == jti)


def revoke_all_refresh_tokens(table: Table, email: str) -> None:
    table.remove(Query().email == email)
