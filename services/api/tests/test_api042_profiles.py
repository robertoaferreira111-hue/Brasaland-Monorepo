"""API-042: profiles resource group (PUT /profiles/me), outside the /auth router."""

from tests.support import bearer, decision, register_and_login


def test_api042_profiles_happy_updates_contact_fields(client) -> None:
    tokens = register_and_login(client, email="api042.profile@brasaland.com")
    access = tokens["access_token"]

    updated = client.put(
        "/profiles/me",
        headers=bearer(access),
        json={"name": " Lucia ", "phone": " +57 301 ", "address": " Cali "},
    )

    assert updated.status_code == 200
    assert updated.json()["email"] == "api042.profile@brasaland.com"
    assert updated.json()["name"] == "Lucia"
    assert updated.json()["phone"] == "+57 301"
    assert updated.json()["address"] == "Cali"
    me = client.get("/auth/me", headers=bearer(access))
    assert me.json()["name"] == "Lucia"


def test_api042_profiles_edge_blank_address(client) -> None:
    tokens = register_and_login(client, email="api042.edge@brasaland.com")
    access = tokens["access_token"]
    saved = client.put(
        "/profiles/me",
        headers=bearer(access),
        json={"name": "Camila", "phone": "+57 300", "address": "Medellin"},
    )
    assert saved.status_code == 200

    rejected = client.put(
        "/profiles/me",
        headers=bearer(access),
        json={"name": "Camila", "phone": "+57 300", "address": "   "},
    )

    assert rejected.status_code == 422
    assert decision(rejected) == "Name, phone, and address are required"
    assert client.get("/auth/me", headers=bearer(access)).json()["address"] == "Medellin"


def test_api042_profiles_failure_unauthenticated(client) -> None:
    tokens = register_and_login(client, email="api042.fail@brasaland.com")
    access = tokens["access_token"]
    saved = client.put(
        "/profiles/me",
        headers=bearer(access),
        json={"name": "Camila", "phone": "+57 300", "address": "Medellin"},
    )
    assert saved.status_code == 200

    rejected = client.put(
        "/profiles/me",
        json={"name": "Other", "phone": "+1 305", "address": "Miami"},
    )

    assert rejected.status_code == 401
    assert decision(rejected) == "Not authenticated"
    assert client.get("/auth/me", headers=bearer(access)).json()["name"] == "Camila"
