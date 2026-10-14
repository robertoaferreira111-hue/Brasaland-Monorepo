"""PUT /profiles/me cases from TESTING.md."""

from tests.support import EMAIL, bearer, decision, register_and_login, signed_token

SAVED = {"name": "Camila", "phone": "+57 300", "address": "Medellin"}


def _save_profile(client, access: str) -> None:
    saved = client.put("/profiles/me", headers=bearer(access), json=SAVED)
    assert saved.status_code == 200


def _profile(client, access: str) -> dict:
    me = client.get("/auth/me", headers=bearer(access))
    assert me.status_code == 200
    return me.json()


def test_profile_h1_strips_and_saves(client) -> None:
    tokens = register_and_login(client)
    access = tokens["access_token"]

    updated = client.put(
        "/profiles/me",
        headers=bearer(access),
        json={"name": " Camila ", "phone": " +57 300 ", "address": " Medellin "},
    )

    assert updated.status_code == 200
    assert updated.json()["email"] == EMAIL
    assert updated.json()["name"] == "Camila"
    assert updated.json()["phone"] == "+57 300"
    assert updated.json()["address"] == "Medellin"
    assert _profile(client, access) == {
        "email": EMAIL,
        "name": "Camila",
        "phone": "+57 300",
        "address": "Medellin",
    }


def test_profile_e1_whitespace_name(client) -> None:
    tokens = register_and_login(client)
    access = tokens["access_token"]
    _save_profile(client, access)

    rejected = client.put(
        "/profiles/me",
        headers=bearer(access),
        json={"name": "   ", "phone": "+1 305", "address": "Miami"},
    )

    assert rejected.status_code == 422
    assert decision(rejected) == "Name, phone, and address are required"
    assert _profile(client, access)["name"] == SAVED["name"]
    assert _profile(client, access)["phone"] == SAVED["phone"]
    assert _profile(client, access)["address"] == SAVED["address"]


def test_profile_f1_expired_access_token(client) -> None:
    tokens = register_and_login(client)
    _save_profile(client, tokens["access_token"])
    expired = signed_token(EMAIL, "access", minutes_until_expiry=-5)

    rejected = client.put(
        "/profiles/me",
        headers=bearer(expired),
        json={"name": "Lucia", "phone": "+57 301", "address": "Cali"},
    )

    assert rejected.status_code == 401
    assert decision(rejected) == "Session expired"
    assert _profile(client, tokens["access_token"])["name"] == SAVED["name"]


def test_profile_e2_empty_phone(client) -> None:
    tokens = register_and_login(client)
    access = tokens["access_token"]
    _save_profile(client, access)

    rejected = client.put(
        "/profiles/me",
        headers=bearer(access),
        json={"name": "Lucia", "phone": "", "address": "Cali"},
    )

    assert rejected.status_code == 422
    assert decision(rejected) == "Name, phone, and address are required"
    assert _profile(client, access)["phone"] == SAVED["phone"]
    assert _profile(client, access)["name"] == SAVED["name"]


def test_profile_f2_missing_credentials(client) -> None:
    tokens = register_and_login(client)
    _save_profile(client, tokens["access_token"])

    rejected = client.put(
        "/profiles/me",
        json={"name": "Lucia", "phone": "+57 301", "address": "Cali"},
    )

    assert rejected.status_code == 401
    assert decision(rejected) == "Not authenticated"
    assert _profile(client, tokens["access_token"])["name"] == SAVED["name"]
