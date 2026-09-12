from fastapi.testclient import TestClient

from tests.conftest import register_and_login


def test_health_check(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_demo_console_is_available(client: TestClient) -> None:
    response = client.get("/demo")

    assert response.status_code == 200
    assert "TaskFlow 操作台" in response.text


def test_register_login_and_read_current_user(client: TestClient) -> None:
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "Alice@Example.com",
            "full_name": "Alice",
            "password": "correct-horse-123",
        },
    )
    assert register_response.status_code == 201
    assert register_response.json()["email"] == "alice@example.com"

    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": "alice@example.com", "password": "correct-horse-123"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    me_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["full_name"] == "Alice"


def test_duplicate_registration_returns_conflict(client: TestClient) -> None:
    register_and_login(client, "alice@example.com")

    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "ALICE@example.com",
            "full_name": "Another Alice",
            "password": "another-password-123",
        },
    )

    assert response.status_code == 409


def test_wrong_password_and_missing_token_are_rejected(client: TestClient) -> None:
    register_and_login(client, "alice@example.com")

    wrong_password_response = client.post(
        "/api/v1/auth/login",
        data={"username": "alice@example.com", "password": "wrong-password"},
    )
    me_response = client.get("/api/v1/auth/me")

    assert wrong_password_response.status_code == 401
    assert me_response.status_code == 401


def test_short_password_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "alice@example.com",
            "full_name": "Alice",
            "password": "short",
        },
    )

    assert response.status_code == 422
