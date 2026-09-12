from datetime import date, timedelta

from fastapi.testclient import TestClient

from tests.conftest import register_and_login


def create_project(client: TestClient, headers: dict[str, str]) -> int:
    response = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"name": "TaskFlow Launch"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_task_crud_filtering_and_stats(client: TestClient) -> None:
    headers = register_and_login(client, "alice@example.com")
    project_id = create_project(client, headers)

    first_task = client.post(
        f"/api/v1/projects/{project_id}/tasks",
        headers=headers,
        json={
            "title": "Write API tests",
            "priority": "high",
            "status": "done",
        },
    )
    second_task = client.post(
        f"/api/v1/projects/{project_id}/tasks",
        headers=headers,
        json={
            "title": "Deploy to production",
            "priority": "urgent",
            "due_date": (date.today() - timedelta(days=1)).isoformat(),
        },
    )
    assert first_task.status_code == 201
    assert second_task.status_code == 201

    filtered_response = client.get(
        f"/api/v1/projects/{project_id}/tasks?status=todo&priority=urgent",
        headers=headers,
    )
    assert filtered_response.status_code == 200
    assert filtered_response.json()["total"] == 1
    assert filtered_response.json()["items"][0]["title"] == "Deploy to production"

    task_id = second_task.json()["id"]
    update_response = client.patch(
        f"/api/v1/tasks/{task_id}",
        headers=headers,
        json={"status": "in_progress"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "in_progress"

    stats_response = client.get(f"/api/v1/projects/{project_id}/stats", headers=headers)
    assert stats_response.status_code == 200
    assert stats_response.json() == {
        "total": 2,
        "todo": 0,
        "in_progress": 1,
        "done": 1,
        "cancelled": 0,
        "overdue": 1,
        "completion_rate": 50.0,
    }

    delete_response = client.delete(f"/api/v1/tasks/{task_id}", headers=headers)
    assert delete_response.status_code == 204
    assert client.get(f"/api/v1/tasks/{task_id}", headers=headers).status_code == 404


def test_users_cannot_access_each_others_tasks(client: TestClient) -> None:
    alice_headers = register_and_login(client, "alice@example.com")
    bob_headers = register_and_login(client, "bob@example.com")
    project_id = create_project(client, alice_headers)

    task = client.post(
        f"/api/v1/projects/{project_id}/tasks",
        headers=alice_headers,
        json={"title": "Private task"},
    ).json()

    get_response = client.get(f"/api/v1/tasks/{task['id']}", headers=bob_headers)
    create_response = client.post(
        f"/api/v1/projects/{project_id}/tasks",
        headers=bob_headers,
        json={"title": "Intruder task"},
    )

    assert get_response.status_code == 404
    assert create_response.status_code == 404


def test_deleting_project_cascades_to_tasks(client: TestClient) -> None:
    headers = register_and_login(client, "alice@example.com")
    project_id = create_project(client, headers)
    task = client.post(
        f"/api/v1/projects/{project_id}/tasks",
        headers=headers,
        json={"title": "Temporary task"},
    ).json()

    delete_response = client.delete(f"/api/v1/projects/{project_id}", headers=headers)
    replacement_project_id = create_project(client, headers)
    replacement_stats = client.get(
        f"/api/v1/projects/{replacement_project_id}/stats",
        headers=headers,
    )

    assert delete_response.status_code == 204
    assert client.get(f"/api/v1/tasks/{task['id']}", headers=headers).status_code == 404
    assert replacement_stats.status_code == 200
    assert replacement_stats.json()["total"] == 0
