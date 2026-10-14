"""POST /auth/logout cases from TESTING.md."""

from tests.support import (
    EMAIL,
    bearer,
    decision,
    login,
    refresh_rows,
    register_and_login,
    remove_refresh_tokens,
)


def test_logout_h1_revokes_refresh_tokens(client) -> None:
    tokens = register_and_login(client)

    logged_out = client.post("/auth/logout", headers=bearer(tokens["access_token"]))

    assert logged_out.status_code == 204
    reused = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert reused.status_code == 401
    assert decision(reused) == "Invalid token"


def test_logout_e1_logout_without_refresh_rows(client, auth_db_path) -> None:
    tokens = register_and_login(client)
    remove_refresh_tokens(auth_db_path)

    logged_out = client.post("/auth/logout", headers=bearer(tokens["access_token"]))

    assert logged_out.status_code == 204
    signed_in = login(client)
    assert signed_in.status_code == 200
    assert signed_in.json()["access_token"]
    assert signed_in.json()["refresh_token"]


def test_logout_f1_missing_credentials(client, auth_db_path) -> None:
    tokens = register_and_login(client)
    stored_before = [row["jti"] for row in refresh_rows(auth_db_path)]

    rejected = client.post("/auth/logout")

    assert rejected.status_code == 401
    assert decision(rejected) == "Not authenticated"
    assert [row["jti"] for row in refresh_rows(auth_db_path)] == stored_before
    refreshed = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200
    assert refreshed.json()["access_token"]


def test_logout_e2_known_gap(client) -> None:
    # Stateless JWT: logout revokes refresh tokens and leaves this access token usable.
    tokens = register_and_login(client)
    logged_out = client.post("/auth/logout", headers=bearer(tokens["access_token"]))
    assert logged_out.status_code == 204

    me = client.get("/auth/me", headers=bearer(tokens["access_token"]))

    assert me.status_code == 200
    assert me.json()["email"] == EMAIL
