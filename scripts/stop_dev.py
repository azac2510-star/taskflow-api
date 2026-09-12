import json
import subprocess
from pathlib import Path
from urllib.request import urlopen

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_PATH = PROJECT_ROOT / ".taskflow_runtime.json"


def main() -> None:
    if not RUNTIME_PATH.exists():
        print("TaskFlow is not running.")
        return

    try:
        runtime = json.loads(RUNTIME_PATH.read_text(encoding="utf-8"))
        with urlopen(f"{runtime['base_url']}/health", timeout=2) as response:
            if response.status != 200:
                raise OSError("Health check failed")
    except (KeyError, OSError, ValueError):
        RUNTIME_PATH.unlink(missing_ok=True)
        print("Removed stale TaskFlow runtime information.")
        return

    pid = int(runtime["pid"])
    subprocess.run(
        ["taskkill", "/PID", str(pid), "/T", "/F"],
        check=False,
        capture_output=True,
        text=True,
    )
    RUNTIME_PATH.unlink(missing_ok=True)
    print("TaskFlow stopped.")


if __name__ == "__main__":
    main()
