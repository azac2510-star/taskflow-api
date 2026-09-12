import argparse
import json
from datetime import date, timedelta
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4


def api_request(
    base_url: str,
    method: str,
    path: str,
    payload: dict | None = None,
    token: str | None = None,
    form: bool = False,
) -> tuple[int, dict]:
    headers = {"Accept": "application/json"}
    data = None
    if payload is not None:
        if form:
            data = urlencode(payload).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(f"{base_url.rstrip('/')}{path}", data=data, headers=headers, method=method)
    with urlopen(request, timeout=10) as response:
        body = response.read().decode("utf-8")
        return response.status, json.loads(body) if body else {}


def run(base_url: str) -> None:
    email = f"smoke-{uuid4().hex[:12]}@example.com"
    password = "smoke-test-password-123"

    status, health = api_request(base_url, "GET", "/health")
    assert status == 200 and health["status"] == "ok"

    status, user = api_request(
        base_url,
        "POST",
        "/api/v1/auth/register",
        {
            "email": email,
            "full_name": "Smoke Test",
            "password": password,
        },
    )
    assert status == 201

    _, login = api_request(
        base_url,
        "POST",
        "/api/v1/auth/login",
        {"username": email, "password": password},
        form=True,
    )
    token = login["access_token"]

    _, project = api_request(
        base_url,
        "POST",
        "/api/v1/projects",
        {"name": "HTTP Smoke Test", "description": "Created by scripts/smoke_test.py"},
        token=token,
    )
    project_id = project["id"]

    _, task = api_request(
        base_url,
        "POST",
        f"/api/v1/projects/{project_id}/tasks",
        {
            "title": "Verify real HTTP flow",
            "priority": "high",
            "due_date": (date.today() + timedelta(days=7)).isoformat(),
        },
        token=token,
    )

    _, stats = api_request(
        base_url,
        "GET",
        f"/api/v1/projects/{project_id}/stats",
        token=token,
    )
    assert stats["total"] == 1 and stats["todo"] == 1, (
        f"Unexpected stats: {stats}; project={project}; task={task}"
    )

    api_request(
        base_url,
        "PATCH",
        f"/api/v1/tasks/{task['id']}",
        {"status": "done"},
        token=token,
    )
    _, completed_stats = api_request(
        base_url,
        "GET",
        f"/api/v1/projects/{project_id}/stats",
        token=token,
    )
    assert completed_stats["done"] == 1 and completed_stats["completion_rate"] == 100.0

    api_request(base_url, "DELETE", f"/api/v1/projects/{project_id}", token=token)

    _, replacement_project = api_request(
        base_url,
        "POST",
        "/api/v1/projects",
        {"name": "Cascade Regression Check"},
        token=token,
    )
    _, replacement_stats = api_request(
        base_url,
        "GET",
        f"/api/v1/projects/{replacement_project['id']}/stats",
        token=token,
    )
    assert replacement_stats["total"] == 0, {
        "message": "Deleting a project left orphan tasks",
        "stats": replacement_stats,
    }
    api_request(
        base_url,
        "DELETE",
        f"/api/v1/projects/{replacement_project['id']}",
        token=token,
    )

    print(f"Smoke test passed: user={user['email']}, project_id={project_id}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    run(args.base_url)
