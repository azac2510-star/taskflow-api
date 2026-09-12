import argparse
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_PATH = PROJECT_ROOT / ".taskflow_runtime.json"


def resolve_base_url(explicit_url: str | None) -> str:
    if explicit_url:
        return explicit_url.rstrip("/")
    if RUNTIME_PATH.exists():
        try:
            runtime = json.loads(RUNTIME_PATH.read_text(encoding="utf-8"))
            return runtime["base_url"].rstrip("/")
        except (KeyError, OSError, ValueError):
            pass
    return "http://127.0.0.1:8000"


def api_request(
    base_url: str,
    method: str,
    path: str,
    payload: dict | None = None,
    form: bool = False,
    token: str | None = None,
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

    request = Request(
        f"{base_url}{path}",
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urlopen(request, timeout=10) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body) if body else {}
    except HTTPError as exc:
        body = exc.read().decode("utf-8")
        try:
            parsed_body = json.loads(body) if body else {}
        except json.JSONDecodeError:
            parsed_body = {"raw": body}
        return exc.code, parsed_body


def register(base_url: str, email: str, full_name: str) -> None:
    status, body = api_request(
        base_url,
        "POST",
        "/api/v1/auth/register",
        {
            "email": email,
            "full_name": full_name,
            "password": "isolation-password-123",
        },
    )
    assert status == 201, f"Register failed for {email}: {status} {body}"


def login(base_url: str, email: str) -> str:
    status, body = api_request(
        base_url,
        "POST",
        "/api/v1/auth/login",
        {"username": email, "password": "isolation-password-123"},
        form=True,
    )
    assert status == 200, f"Login failed for {email}: {status} {body}"
    return body["access_token"]


def run(base_url: str) -> None:
    run_id = uuid4().hex[:8]
    alice_email = f"isolation-alice-{run_id}@example.com"
    bob_email = f"isolation-bob-{run_id}@example.com"

    print(f"1. Checking TaskFlow at {base_url}")
    status, health = api_request(base_url, "GET", "/health")
    assert status == 200 and health.get("status") == "ok", (
        f"TaskFlow is not healthy: {status} {health}"
    )

    print("2. Creating two independent users")
    register(base_url, alice_email, "Alice Isolation")
    register(base_url, bob_email, "Bob Isolation")
    alice_token = login(base_url, alice_email)
    bob_token = login(base_url, bob_email)

    print("3. Creating a private project as Alice")
    status, project = api_request(
        base_url,
        "POST",
        "/api/v1/projects",
        {"name": f"Isolation Project {run_id}", "description": "Owned by Alice"},
        token=alice_token,
    )
    assert status == 201, f"Project creation failed: {status} {project}"
    project_id = project["id"]

    print("4. Bob tries to read Alice's project")
    status, body = api_request(
        base_url,
        "GET",
        f"/api/v1/projects/{project_id}",
        token=bob_token,
    )
    assert status == 404, f"Security failure: Bob read Alice's project: {status} {body}"
    print("   PASS: returned HTTP 404")

    print("5. Bob tries to modify Alice's project")
    status, body = api_request(
        base_url,
        "PATCH",
        f"/api/v1/projects/{project_id}",
        {"name": "Stolen Project"},
        token=bob_token,
    )
    assert status == 404, f"Security failure: Bob changed Alice's project: {status} {body}"
    print("   PASS: returned HTTP 404")

    print("6. Bob tries to create a task inside Alice's project")
    status, body = api_request(
        base_url,
        "POST",
        f"/api/v1/projects/{project_id}/tasks",
        {"title": "Intruder task"},
        token=bob_token,
    )
    assert status == 404, f"Security failure: Bob used Alice's project: {status} {body}"
    print("   PASS: returned HTTP 404")

    print("7. Alice confirms that her project is still accessible")
    status, body = api_request(
        base_url,
        "GET",
        f"/api/v1/projects/{project_id}",
        token=alice_token,
    )
    assert status == 200 and body["name"] == f"Isolation Project {run_id}", (
        f"Alice cannot read her own project: {status} {body}"
    )
    print("   PASS: returned HTTP 200")

    api_request(
        base_url,
        "DELETE",
        f"/api/v1/projects/{project_id}",
        token=alice_token,
    )
    print("")
    print("USER ISOLATION PASSED")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-url",
        help="TaskFlow base URL. Defaults to .taskflow_runtime.json or port 8000.",
    )
    args = parser.parse_args()
    base_url = resolve_base_url(args.base_url)

    try:
        run(base_url)
    except (AssertionError, KeyError, URLError) as exc:
        raise SystemExit(
            f"USER ISOLATION FAILED: {exc}\n"
            "Make sure TaskFlow is running, then try again."
        ) from exc


if __name__ == "__main__":
    main()
