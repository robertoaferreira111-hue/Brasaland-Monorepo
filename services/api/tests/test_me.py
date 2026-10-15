"""GET /auth/me cases from TESTING.md."""

from tests.support import (
    EMAIL,
    bearer,
    decision,
    register,
    register_and_login,
    remove_users,
    signed_token,
)


def test_me_h1_returns_updated_profile(client) -> None:
    tokens = register_and_login(client)
    headers = bearer(tokens["access_token"])
    saved = client.put(
        "/profiles/me",
        headers=headers,
        json={"name": " Camila ", "phone": " +57 300 ", "address": " Medellin "},
    )
    assert saved.status_code == 200

    me = client.get("/auth/me", headers=headers)

    assert me.status_code == 200
    assert me.json()["email"] == EMAIL
    assert me.json()["name"] == "Camila"
    assert me.json()["phone"] == "+57 300"
    assert me.json()["address"] == "Medellin"


def test_me_e1_empty_profile_fields(client) -> None:
    tokens = register_and_login(client)

    me = client.get("/auth/me", headers=bearer(tokens["access_token"]))

    assert me.status_code == 200
    assert me.json()["email"] == EMAIL
    assert me.json()["name"] == ""
    assert me.json()["phone"] == ""
    assert me.json()["address"] == ""


def test_me_f1_expired_access_token(client) -> None:
    assert register(client).status_code == 201
    token = signed_token(EMAIL, "access", minutes_until_expiry=-5)

    me = client.get("/auth/me", headers=bearer(token))

    assert me.status_code == 401
    assert decision(me) == "Session expired"


def test_me_f2_missing_credentials(client) -> None:
    me = client.get("/auth/me")

    assert me.status_code == 401
    assert decision(me) == "Not authenticated"


def test_me_f3_refresh_token_as_access(client) -> None:
    tokens = register_and_login(client)

    me = client.get("/auth/me", headers=bearer(tokens["refresh_token"]))

    assert me.status_code == 401
    assert decision(me) == "Invalid token"


def test_me_f4_unsigned_token(client) -> None:
    me = client.get("/auth/me", headers=bearer("not-a-signed-token"))

    assert me.status_code == 401
    assert decision(me) == "Invalid token"


def test_me_signed_token_without_subject(client) -> None:
    token = signed_token(EMAIL, "access", minutes_until_expiry=60, include_subject=False)

    me = client.get("/auth/me", headers=bearer(token))

    assert me.status_code == 401
    assert decision(me) == "Invalid token"


def test_me_e2_deleted_user(client, auth_db_path) -> None:
    tokens = register_and_login(client)
    remove_users(auth_db_path)

    me = client.get("/auth/me", headers=bearer(tokens["access_token"]))

    assert me.status_code == 401
    assert decision(me) == "Not authenticated"
