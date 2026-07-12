from fastapi.testclient import TestClient


def register_user(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Initial Name",
            "email": email,
            "password": "secure-password-123",
        },
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def profile_payload(name: str = "Aarav Kumar") -> dict:
    return {
        "name": name,
        "age": 20,
        "gender": "Male",
        "state": "Karnataka",
        "sport": "Running",
        "experience": 4,
    }


def test_profile_requires_authentication(client: TestClient) -> None:
    assert client.get("/profile").status_code == 401
    assert client.put("/profile", json=profile_payload()).status_code == 401


def test_get_returns_404_before_profile_creation(client: TestClient) -> None:
    headers = register_user(client, "new-profile@example.com")

    response = client.get("/profile", headers=headers)

    assert response.status_code == 404


def test_put_creates_and_get_returns_profile(client: TestClient) -> None:
    headers = register_user(client, "profile@example.com")

    update_response = client.put(
        "/profile",
        headers=headers,
        json=profile_payload(),
    )
    get_response = client.get("/profile", headers=headers)

    assert update_response.status_code == 200
    assert update_response.json() == profile_payload()
    assert get_response.status_code == 200
    assert get_response.json() == profile_payload()


def test_put_updates_existing_profile_and_user_name(client: TestClient) -> None:
    headers = register_user(client, "update-profile@example.com")
    client.put("/profile", headers=headers, json=profile_payload())
    updated = profile_payload(name="Meera Sharma")
    updated["sport"] = "Jumping"
    updated["experience"] = 6

    response = client.put("/profile", headers=headers, json=updated)

    assert response.status_code == 200
    assert response.json() == updated


def test_profiles_are_isolated_by_authenticated_user(client: TestClient) -> None:
    first_headers = register_user(client, "first-profile@example.com")
    second_headers = register_user(client, "second-profile@example.com")
    first = profile_payload(name="First Athlete")
    second = profile_payload(name="Second Athlete")
    client.put("/profile", headers=first_headers, json=first)
    client.put("/profile", headers=second_headers, json=second)

    assert client.get("/profile", headers=first_headers).json() == first
    assert client.get("/profile", headers=second_headers).json() == second


def test_profile_validation_returns_422(client: TestClient) -> None:
    headers = register_user(client, "invalid-profile@example.com")
    invalid = profile_payload()
    invalid["age"] = 3
    invalid["experience"] = -1

    response = client.put("/profile", headers=headers, json=invalid)

    assert response.status_code == 422
