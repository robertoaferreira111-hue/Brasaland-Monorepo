from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_register_login_me_profile_logout_refresh(auth_db_path) -> None:
    email = "new.user@brasaland.com"
    password = "secret-pass"

    register = client.post("/users", json={"email": email, "password": password})
    assert register.status_code == 201
    assert register.json()["email"] == email

    bad_login = client.post(
        "/auth/login",
        json={"email": email, "password": "wrong"},
    )
    assert bad_login.status_code == 401
    assert bad_login.json()["detail"] == "Incorrect email or password"

    login = client.post("/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    tokens = login.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    me = client.get("/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == email

    profile = client.put(
        "/profiles/me",
        headers=headers,
        json={"name": "Camila", "phone": "+57 300", "address": "Medellin"},
    )
    assert profile.status_code == 200
    body = profile.json()
    assert body["name"] == "Camila"
    assert body["phone"] == "+57 300"
    assert body["address"] == "Medellin"

    me_after = client.get("/auth/me", headers=headers)
    assert me_after.json()["name"] == "Camila"

    refresh = client.post(
        "/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refresh.status_code == 200
    new_access = refresh.json()["access_token"]
    assert new_access != tokens["access_token"]

    logout = client.post("/auth/logout", headers={"Authorization": f"Bearer {new_access}"})
    assert logout.status_code == 204

    stale_refresh = client.post(
        "/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert stale_refresh.status_code == 401

    me_still_ok = client.get("/auth/me", headers={"Authorization": f"Bearer {new_access}"})
    assert me_still_ok.status_code == 200
