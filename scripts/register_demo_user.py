import json
import subprocess
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = "http://127.0.0.1:8000"
EMAIL = "demo@example.com"
PASSWORD = "12345678"


def main() -> None:
    register_request = Request(
        f"{BASE_URL}/api/v1/auth/register",
        data=json.dumps(
            {
                "email": EMAIL,
                "full_name": "Alice",
                "password": PASSWORD,
            }
        ).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(register_request, timeout=10) as response:
            print(f"Registration status: {response.status}")
            print(response.read().decode("utf-8"))
    except HTTPError as error:
        if error.code == 409:
            print("Demo account already exists.")
        else:
            print(f"Registration failed: HTTP {error.code}")
            print(error.read().decode("utf-8"))
            raise

    login_request = Request(
        f"{BASE_URL}/api/v1/auth/login",
        data=urlencode({"username": EMAIL, "password": PASSWORD}).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urlopen(login_request, timeout=10) as response:
        token = json.loads(response.read().decode("utf-8"))["access_token"]
        print("Login verified.")
        print(f"Full token: {token}")
        try:
            subprocess.run(["clip"], input=token, text=True, check=True)
            print("Token copied to clipboard.")
        except (FileNotFoundError, subprocess.CalledProcessError):
            print("Could not copy the token automatically.")


if __name__ == "__main__":
    main()
