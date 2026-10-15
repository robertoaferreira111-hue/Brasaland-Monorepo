"""POST /auth/login cases from TESTING.md."""

from tests.support import EMAIL, PASSWORD, decision, login, no_tokens, register, register_and_login


def test_login_h1_issues_usable_tokens(client) -> None:
    tokens = register_and_login(client)

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert me.status_code == 200
    assert me.json()["email"] == EMAIL

    refreshed = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200
    follow_up = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {refreshed.json()['access_token']}"},
    )
    assert follow_up.status_code == 200
    assert follow_up.json()["email"] == EMAIL


def test_login_e1_empty_password(client) -> None:
    assert register(client).status_code == 201

    response = login(client, password="")

    assert response.status_code == 401
    assert decision(response) == "Incorrect email or password"
    assert no_tokens(response)


def test_login_f1_wrong_password(client) -> None:
    assert register(client).status_code == 201

    response = login(client, password="wrong-pass")

    assert response.status_code == 401
    assert decision(response) == "Incorrect email or password"
    assert no_tokens(response)


def test_login_f2_unknown_email(client) -> None:
    response = login(client, email="nobody@brasaland.com", password=PASSWORD)

    assert response.status_code == 401
    assert decision(response) == "Incorrect email or password"
    assert no_tokens(response)


def test_login_e2_blank_email(client) -> None:
    spaced = login(client, email="   ", password=PASSWORD)
    empty = login(client, email="", password=PASSWORD)

    assert spaced.status_code == 401
    assert empty.status_code == 401
    assert decision(spaced) == "Incorrect email or password"
    assert decision(empty) == "Incorrect email or password"
    assert no_tokens(spaced)
    assert no_tokens(empty)


def test_login_e3_email_case_and_spaces(client) -> None:
    assert register(client, email=EMAIL, password=PASSWORD).status_code == 201

    response = login(client, email="  STAFF.USER@Brasaland.com  ", password=PASSWORD)

    assert response.status_code == 200
    access = response.json()["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert me.status_code == 200
    assert me.json()["email"] == EMAIL
