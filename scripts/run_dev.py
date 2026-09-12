import argparse
import json
import os
import secrets
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"
ENV_EXAMPLE_PATH = PROJECT_ROOT / ".env.example"
RUNTIME_PATH = PROJECT_ROOT / ".taskflow_runtime.json"


def ensure_environment() -> None:
    if ENV_PATH.exists():
        return

    content = ENV_EXAMPLE_PATH.read_text(encoding="utf-8")
    secret = secrets.token_urlsafe(48)
    content = content.replace(
        "replace-this-with-a-random-string-of-at-least-32-bytes",
        secret,
    )
    ENV_PATH.write_text(content, encoding="utf-8")
    print("Created .env with a random SECRET_KEY.")


def dependencies_are_installed() -> bool:
    try:
        import fastapi  # noqa: F401
        import sqlalchemy  # noqa: F401
        import uvicorn  # noqa: F401
    except ImportError:
        return False
    return True


def install_dependencies() -> None:
    print("Installing project dependencies. This may take a few minutes...")
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "-e", ".[dev]"],
        cwd=PROJECT_ROOT,
    )


def port_is_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return sock.connect_ex(("127.0.0.1", port)) != 0


def choose_port(preferred_port: int) -> int:
    if preferred_port > 0 and port_is_available(preferred_port):
        return preferred_port

    for port in range(8000, 8101):
        if port_is_available(port):
            return port
    raise RuntimeError("No available port found between 8000 and 8100")


def read_running_instance() -> dict | None:
    if not RUNTIME_PATH.exists():
        return None
    try:
        runtime = json.loads(RUNTIME_PATH.read_text(encoding="utf-8"))
        with urlopen(f"{runtime['base_url']}/health", timeout=1) as response:
            if response.status == 200:
                return runtime
    except (KeyError, OSError, URLError, ValueError):
        RUNTIME_PATH.unlink(missing_ok=True)
    return None


def schedule_browser_open(url: str) -> None:
    def open_later() -> None:
        time.sleep(1.5)
        webbrowser.open(url)

    threading.Thread(target=open_later, daemon=True).start()


def run_server(host: str, port: int, reload_enabled: bool, open_browser: bool) -> None:
    from uvicorn import run

    from taskflow.config import get_settings

    settings = get_settings()
    base_url = f"http://{host}:{port}"
    console_url = f"{base_url}/demo"
    docs_url = f"{base_url}/docs"
    runtime = {
        "pid": os.getpid(),
        "host": host,
        "port": port,
        "base_url": base_url,
        "console_url": console_url,
        "docs_url": docs_url,
        "database_url": settings.database_url,
    }
    RUNTIME_PATH.write_text(json.dumps(runtime, indent=2), encoding="utf-8")

    print("")
    print("=" * 64)
    print(f"{settings.app_name} is starting")
    print(f"TaskFlow Console: {console_url}")
    print(f"Swagger UI: {docs_url}")
    print(f"Health check: {base_url}/health")
    print("Press Ctrl+C to stop the server.")
    print("=" * 64)
    print("")

    if open_browser:
        schedule_browser_open(console_url)

    try:
        run(
            "taskflow.main:app",
            host=host,
            port=port,
            reload=reload_enabled,
        )
    finally:
        try:
            current_runtime = json.loads(RUNTIME_PATH.read_text(encoding="utf-8"))
            if current_runtime.get("pid") == os.getpid():
                RUNTIME_PATH.unlink(missing_ok=True)
        except (OSError, ValueError):
            pass


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--no-reload", action="store_true")
    args = parser.parse_args()

    ensure_environment()
    if not dependencies_are_installed():
        install_dependencies()

    running = read_running_instance()
    if running is not None:
        console_url = running.get("console_url", running["docs_url"])
        print(f"TaskFlow is already running at {console_url}")
        if not args.no_browser:
            webbrowser.open(console_url)
        return

    port = choose_port(args.port)
    if args.check:
        print("Launch check passed.")
        print(f"Available port: {port}")
        print(f"Python: {sys.executable}")
        return

    run_server(
        host=args.host,
        port=port,
        reload_enabled=not args.no_reload,
        open_browser=not args.no_browser,
    )


if __name__ == "__main__":
    main()
