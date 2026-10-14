"""POST /auth/refresh cases from TESTING.md."""

from tests.support import (
    EMAIL,
    bearer,
    decision,
    refresh_rows,
    register,
    register_and_login,
    remove_users,
    signed_token,
    store_refresh,
)


def test_refresh_h1_rotates_tokens(client) -> None:
    tokens = register_and_login(client)

    refreshed = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})

    assert refreshed.status_code == 200
    new_tokens = refreshed.json()
    assert new_tokens["access_token"]
    assert new_tokens["refresh_token"]
    assert new_tokens["refresh_token"] != tokens["refresh_token"]
    reused = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert reused.status_code == 401
    me = client.get("/auth/me", headers=bearer(new_tokens["access_token"]))
    assert me.status_code == 200
    assert me.json()["email"] == EMAIL


def test_refresh_e1_empty_refresh_token(client, auth_db_path) -> None:
    response = client.post("/auth/refresh", json={"refresh_token": ""})

    assert response.status_code == 422
    assert "access_token" not in response.json()
    assert refresh_rows(auth_db_path) == []


def test_refresh_f1_expired_refresh_token(client, auth_db_path) -> None:
    assert register(client).status_code == 201
    jti = "expired-refresh-jti"
    store_refresh(auth_db_path, jti, EMAIL)
    token = signed_token(EMAIL, "refresh", minutes_until_expiry=-5, jti=jti)

    response = client.post("/auth/refresh", json={"refresh_token": token})

    assert response.status_code == 401
    assert decision(response) == "Session expired"
    # Expiry is rejected before the stored jti is revoked or replaced.
    assert [row["jti"] for row in refresh_rows(auth_db_path)] == [jti]


def test_refresh_f2_reused_refresh_token(client) -> None:
    tokens = register_and_login(client)
    first = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert first.status_code == 200

    reused = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})

    assert reused.status_code == 401
    assert decision(reused) == "Invalid token"


def test_refresh_f3_access_token_as_refresh(client) -> None:
    tokens = register_and_login(client)

    response = client.post("/auth/refresh", json={"refresh_token": tokens["access_token"]})

    assert response.status_code == 401
    assert decision(response) == "Invalid token"


def test_refresh_f4_deleted_user(client, auth_db_path) -> None:
    tokens = register_and_login(client)
    stored = [row["jti"] for row in refresh_rows(auth_db_path)]
    remove_users(auth_db_path)

    response = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})

    assert response.status_code == 401
    assert decision(response) == "Invalid token"
    assert [row["jti"] for row in refresh_rows(auth_db_path)] == stored


def test_refresh_f5_missing_jti(client) -> None:
    assert register(client).status_code == 201
    token = signed_token(EMAIL, "refresh", minutes_until_expiry=60, jti=None)

    response = client.post("/auth/refresh", json={"refresh_token": token})

    assert response.status_code == 401
    assert decision(response) == "Invalid token"
