from fastapi.testclient import TestClient

from tests.conftest import register_and_login


def test_project_crud_and_search(client: TestClient) -> None:
    headers = register_and_login(client, "alice@example.com")

    create_response = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"name": "Resume Project", "description": "Build a strong portfolio"},
    )
    assert create_response.status_code == 201
    project_id = create_response.json()["id"]

    list_response = client.get("/api/v1/projects?search=resume", headers=headers)
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1

    get_response = client.get(f"/api/v1/projects/{project_id}", headers=headers)
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "Resume Project"

    update_response = client.patch(
        f"/api/v1/projects/{project_id}",
        headers=headers,
        json={"name": "TaskFlow API"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "TaskFlow API"

    delete_response = client.delete(f"/api/v1/projects/{project_id}", headers=headers)
    assert delete_response.status_code == 204
    assert client.get(f"/api/v1/projects/{project_id}", headers=headers).status_code == 404


def test_users_cannot_access_each_others_projects(client: TestClient) -> None:
    alice_headers = register_and_login(client, "alice@example.com")
    bob_headers = register_and_login(client, "bob@example.com")

    project = client.post(
        "/api/v1/projects",
        headers=alice_headers,
        json={"name": "Private Project"},
    ).json()

    response = client.get(f"/api/v1/projects/{project['id']}", headers=bob_headers)
    update_response = client.patch(
        f"/api/v1/projects/{project['id']}",
        headers=bob_headers,
        json={"name": "Stolen Project"},
    )

    assert response.status_code == 404
    assert update_response.status_code == 404


def test_project_endpoints_require_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/projects")

    assert response.status_code == 401
