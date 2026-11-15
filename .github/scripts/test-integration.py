#!/usr/bin/env python3
"""Onboard Home Assistant and exercise custom integration dependency installation."""

import json
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

from integration_fixture import DOMAIN, serve_wheel

BASE = "http://localhost:8123"
CLIENT_ID = f"{BASE}/"


def request(path, data=None, token=None, form=False, timeout=180):
    headers = {}
    if data is not None:
        if form:
            body = urllib.parse.urlencode(data).encode()
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            body = json.dumps(data).encode()
            headers["Content-Type"] = "application/json"
    else:
        body = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(BASE + path, data=body, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as err:
        raise RuntimeError(
            f"{path}: HTTP {err.code}: {err.read().decode(errors='replace')}"
        ) from err


def wait_ready(path, token=None, expected_state=None):
    deadline = time.monotonic() + 300
    last_error = None
    while time.monotonic() < deadline:
        try:
            response = request(path, token=token, timeout=5)
            if expected_state is None or response.get("state") == expected_state:
                return response
            last_error = f"state: {response}"
        except (urllib.error.URLError, TimeoutError, RuntimeError) as err:
            last_error = err
        time.sleep(2)
    raise TimeoutError(f"Home Assistant did not become ready at {path}: {last_error}")


def run(*args):
    subprocess.run(args, check=True, timeout=600)


def main():
    wait_ready("/api/onboarding")
    user = request(
        "/api/onboarding/users",
        {
            "name": "CI Test",
            "username": "ci_test",
            "password": "ci-test-password",
            "client_id": CLIENT_ID,
            "language": "en",
        },
    )
    token = request(
        "/auth/token",
        {
            "grant_type": "authorization_code",
            "code": user["auth_code"],
            "client_id": CLIENT_ID,
        },
        form=True,
    )["access_token"]
    request("/api/onboarding/core_config", {}, token)
    request("/api/onboarding/analytics", {}, token)
    request(
        "/api/onboarding/integration",
        {"client_id": CLIENT_ID, "redirect_uri": CLIENT_ID},
        token,
    )
    status = request("/api/onboarding", token=token)
    done = {step["step"] for step in status if step["done"]}
    if not {"user", "core_config", "analytics", "integration"} <= done or not all(
        step["done"] for step in status
    ):
        raise RuntimeError(f"Onboarding incomplete: {status}")

    with serve_wheel() as wheel_url:
        run("sudo", "python3", ".github/scripts/integration_fixture.py", wheel_url)
        run("sudo", "snap", "restart", "home-assistant-snap")
        state = wait_ready("/api/core/state", token, expected_state="RUNNING")
        print(f"Home Assistant core state: {state}", flush=True)
        config = request("/api/config", token=token)
        if config.get("safe_mode") or config.get("recovery_mode"):
            raise RuntimeError("Home Assistant is in safe or recovery mode")
        if "marketplace" not in config["components"]:
            raise RuntimeError("Built-in Marketplace component is not loaded")
        handlers = request("/api/config/config_entries/flow_handlers", token=token)
        if DOMAIN not in handlers:
            raise RuntimeError(
                f"Test integration was not discovered among {len(handlers)} configuration flows"
            )
        print("Marketplace is loaded and the test integration was discovered.", flush=True)

        flow = request(
            "/api/config/config_entries/flow", {"handler": DOMAIN}, token, timeout=360
        )
        if flow.get("type") != "form" or flow.get("step_id") != "user":
            raise RuntimeError(f"Test integration did not reach its user form: {flow}")
    print("The integration imported its newly installed Python dependency from snap data.")


if __name__ == "__main__":
    main()
