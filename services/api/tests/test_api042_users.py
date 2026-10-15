"""API-042: users resource group (POST /users), outside the /auth router."""

from tests.support import error_names_field, register, user_emails


def test_api042_users_happy_creates_account(client, auth_db_path) -> None:
    response = register(client, email="api042.users@brasaland.com", password="secret-pass")

    assert response.status_code == 201
    assert response.json()["email"] == "api042.users@brasaland.com"
    assert response.json()["name"] == ""
    assert "password" not in response.json()
    assert "api042.users@brasaland.com" in user_emails(auth_db_path)


def test_api042_users_edge_duplicate_email(client, auth_db_path) -> None:
    assert register(client, email="api042.dup@brasaland.com").status_code == 201

    duplicate = register(client, email="api042.dup@brasaland.com")

    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "An account with this email already exists"
    assert user_emails(auth_db_path).count("api042.dup@brasaland.com") == 1


def test_api042_users_failure_invalid_email(client, auth_db_path) -> None:
    response = register(client, email="not-a-valid-address")

    assert response.status_code == 422
    assert error_names_field(response, "email")
    assert user_emails(auth_db_path) == []
