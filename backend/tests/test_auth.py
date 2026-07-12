import jwt
from fastapi.testclient import TestClient

from app.utils.config import settings


def registration_payload() -> dict[str, str]:
    return {
        "name": "Arjun Rao",
        "email": "arjun@example.com",
        "password": "secure-password-123",
    }


def test_register_returns_user_and_jwt(client: TestClient) -> None:
    response = client.post("/api/v1/auth/register", json=registration_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"
    assert len(body["access_token"].split(".")) == 3
    claims = jwt.decode(
        body["access_token"],
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )
    assert claims["sub"] == body["user"]["id"]
    assert "iat" in claims
    assert "exp" in claims
    assert body["user"]["email"] == "arjun@example.com"
    assert "password" not in str(body).lower()

    session = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert session.status_code == 200
    assert session.json()["role"] == "athlete"
    assert session.json()["user"]["email"] == "arjun@example.com"


def test_register_rejects_duplicate_email(client: TestClient) -> None:
    client.post("/api/v1/auth/register", json=registration_payload())
    response = client.post("/api/v1/auth/register", json=registration_payload())

    assert response.status_code == 409


def test_login_returns_jwt(client: TestClient) -> None:
    client.post("/api/v1/auth/register", json=registration_payload())
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "ARJUN@example.com", "password": "secure-password-123"},
    )

    assert response.status_code == 200
    assert response.json()["user"]["email"] == "arjun@example.com"


def test_login_rejects_invalid_password(client: TestClient) -> None:
    client.post("/api/v1/auth/register", json=registration_payload())
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "arjun@example.com", "password": "incorrect"},
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_register_validates_name_email_and_password(client: TestClient) -> None:
    invalid_payloads = [
        {
            "name": " ",
            "email": "athlete@example.com",
            "password": "secure-password-123",
        },
        {
            "name": "Athlete",
            "email": "not-an-email",
            "password": "secure-password-123",
        },
        {
            "name": "Athlete",
            "email": "athlete@example.com",
            "password": "passwordonly",
        },
    ]

    for payload in invalid_payloads:
        response = client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 422
