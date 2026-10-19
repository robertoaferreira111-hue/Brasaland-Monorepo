"""POST /users cases from TESTING.md."""

from tests.support import (
    EMAIL,
    PASSWORD,
    error_names_field,
    login,
    register,
    user_emails,
)


def test_users_h1_new_account(client, auth_db_path) -> None:
    response = register(client, email="  Staff.User@Brasaland.com  ", password=PASSWORD)

    assert response.status_code == 201
    profile = response.json()
    assert profile["email"] == EMAIL
    assert profile["name"] == ""
    assert profile["phone"] == ""
    assert profile["address"] == ""
    assert "password" not in profile
    assert user_emails(auth_db_path) == [EMAIL]
    assert login(client, EMAIL, PASSWORD).status_code == 200


def test_users_e1_duplicate_email(client, auth_db_path) -> None:
    assert register(client).status_code == 201

    duplicate = register(client)

    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "An account with this email already exists"
    assert user_emails(auth_db_path) == [EMAIL]


def test_users_f1_invalid_email(client, auth_db_path) -> None:
    response = register(client, email="not-an-email")

    assert response.status_code == 422
    assert error_names_field(response, "email")
    assert user_emails(auth_db_path) == []


def test_users_e2_empty_password(client, auth_db_path) -> None:
    response = register(client, password="")

    assert response.status_code == 422
    assert user_emails(auth_db_path) == []


def test_users_e3_duplicate_email_case_and_spaces(client, auth_db_path) -> None:
    assert register(client, email=EMAIL).status_code == 201

    duplicate = register(client, email="  STAFF.USER@brasaland.com  ")

    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "An account with this email already exists"
    assert user_emails(auth_db_path) == [EMAIL]


def test_users_h2_optional_profile_fields(client) -> None:
    response = register(
        client,
        email="profile.user@brasaland.com",
        password=PASSWORD,
    )
    assert response.status_code == 201

    with_profile = client.post(
        "/users",
        json={
            "email": "named.user@brasaland.com",
            "password": PASSWORD,
            "name": " Camila ",
            "phone": " +57 300 ",
            "address": " Medellín ",
        },
    )

    assert with_profile.status_code == 201
    profile = with_profile.json()
    assert profile["name"] == "Camila"
    assert profile["phone"] == "+57 300"
    assert profile["address"] == "Medellín"


def test_users_e4_space_password(client) -> None:
    assert register(client, password=" ").status_code == 201

    assert login(client, EMAIL, " ").status_code == 200
    assert login(client, EMAIL, "").status_code == 401
