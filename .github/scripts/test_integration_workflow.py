"""Tests for the snap integration-installation workflow."""

from contextlib import contextmanager
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import call, patch
from urllib.request import urlopen
import zipfile

import integration_fixture as fixture

spec = importlib.util.spec_from_file_location(
    "test_integration", Path(__file__).with_name("test-integration.py")
)
integration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(integration)

ONBOARDED = [
    {"step": step, "done": True}
    for step in ("user", "core_config", "analytics", "integration")
]


@contextmanager
def wheel_fixture():
    yield "http://127.0.0.1/test.whl"


class IntegrationWorkflowTest(unittest.TestCase):
    def test_wait_for_core_running(self):
        with (
            patch.object(
                integration,
                "request",
                side_effect=[{"state": "STARTING"}, {"state": "RUNNING"}],
            ) as request,
            patch.object(integration.time, "sleep") as sleep,
        ):
            result = integration.wait_ready(
                "/api/core/state", "token", expected_state="RUNNING"
            )
        self.assertEqual(result["state"], "RUNNING")
        self.assertEqual(request.call_count, 2)
        sleep.assert_called_once_with(2)

    def run_main(self, config, handlers, flow):
        responses = [
            {"auth_code": "code"},
            {"access_token": "token"},
            {},
            {},
            {},
            ONBOARDED,
            config,
            handlers,
            flow,
        ]
        with (
            patch.object(integration, "wait_ready") as ready,
            patch.object(integration, "request", side_effect=responses) as request,
            patch.object(integration, "run") as run,
            patch.object(integration, "serve_wheel", wheel_fixture),
        ):
            integration.main()
            return ready, request, run

    def test_install_and_discover_fixture(self):
        ready, request, run = self.run_main(
            {"components": ["marketplace"]},
            [fixture.DOMAIN],
            {"type": "form", "step_id": "user"},
        )
        self.assertEqual(
            ready.call_args_list,
            [call("/api/onboarding"), call("/api/core/state", "token", expected_state="RUNNING")],
        )
        self.assertEqual(
            request.call_args_list[-1],
            call(
                "/api/config/config_entries/flow",
                {"handler": fixture.DOMAIN},
                "token",
                timeout=360,
            ),
        )
        self.assertEqual(
            run.call_args_list,
            [
                call("sudo", "python3", ".github/scripts/integration_fixture.py",
                     "http://127.0.0.1/test.whl"),
                call("sudo", "snap", "restart", "home-assistant-snap"),
            ],
        )

    def test_failed_configuration_flow_fails_the_check(self):
        with self.assertRaisesRegex(RuntimeError, "did not reach its user form"):
            self.run_main(
                {"components": ["marketplace"]},
                [fixture.DOMAIN],
                {"type": "abort", "reason": "error"},
            )

    def test_missing_fixture_fails_before_starting_flow(self):
        with self.assertRaisesRegex(RuntimeError, "Test integration was not discovered"):
            self.run_main({"components": ["marketplace"]}, ["other"], {})

    def test_missing_marketplace_and_safe_mode_fail(self):
        with self.assertRaisesRegex(RuntimeError, "Marketplace component is not loaded"):
            self.run_main({"components": []}, [], {})
        with self.assertRaisesRegex(RuntimeError, "safe or recovery mode"):
            self.run_main({"safe_mode": True, "components": ["marketplace"]}, [], {})

    def test_incomplete_onboarding_fails_before_installing_fixture(self):
        responses = [
            {"auth_code": "code"}, {"access_token": "token"}, {}, {}, {},
            [{"step": "user", "done": False}],
        ]
        with (
            patch.object(integration, "wait_ready"),
            patch.object(integration, "request", side_effect=responses),
            patch.object(integration, "run") as run,
        ):
            with self.assertRaisesRegex(RuntimeError, "Onboarding incomplete"):
                integration.main()
            run.assert_not_called()

    def test_wheel_and_integration_fixture(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory)
            with fixture.serve_wheel() as url, patch.object(fixture, "DATA", data):
                with urlopen(url, timeout=5) as response:
                    wheel_bytes = response.read()
                    self.assertTrue(wheel_bytes.startswith(b"PK"))
                wheel_file = data / fixture.WHEEL
                wheel_file.write_bytes(wheel_bytes)
                with zipfile.ZipFile(wheel_file) as wheel:
                    self.assertIn(f"{fixture.NAME}/__init__.py", wheel.namelist())
                    self.assertIn(b"Version: 1.0", wheel.read(f"{fixture.DIST}/METADATA"))
                    self.assertIn(b"sha256=", wheel.read(f"{fixture.DIST}/RECORD"))
                fixture.prepare_integration(url)
                component = data / "custom_components" / fixture.DOMAIN
                manifest = json.loads((component / "manifest.json").read_text())
                self.assertEqual(manifest["domain"], fixture.DOMAIN)
                self.assertEqual(manifest["requirements"], [f"ci-snap-test-dependency @ {url}"])
                compile((component / "config_flow.py").read_text(), "config_flow.py", "exec")
                with self.assertRaises(FileExistsError):
                    fixture.prepare_integration(url)
                (data / "deps" / fixture.NAME).mkdir(parents=True)
                with self.assertRaisesRegex(RuntimeError, "already present"):
                    fixture.prepare_integration(url)

    def test_fixture_flow_imports_only_from_snap_deps(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory)
            deps = data / "deps"
            deps.mkdir()
            fixture.create_wheel(data)
            with zipfile.ZipFile(data / fixture.WHEEL) as wheel:
                wheel.extractall(deps)
            with patch.object(fixture, "DATA", data):
                # Prepare before exposing the wheel under the snap's deps directory.
                moved = data / "wheel_contents"
                deps.rename(moved)
                fixture.prepare_integration("http://127.0.0.1/test.whl")
                moved.rename(deps)
            fake_ha = data / "homeassistant"
            fake_ha.mkdir()
            (fake_ha / "__init__.py").write_text("")
            (fake_ha / "config_entries.py").write_text(
                "class ConfigFlow:\n"
                "    def __init_subclass__(cls, **kwargs): pass\n"
                "    def async_show_form(self, step_id): return {'step_id': step_id}\n"
            )
            component = data / "custom_components" / fixture.DOMAIN
            code = (
                "import asyncio, runpy, sys; "
                "m=runpy.run_path(sys.argv[1]); "
                "assert asyncio.run(m['SnapCITestFlow']().async_step_user())"
                " == {'step_id': 'user'}"
            )
            env = {**os.environ, "PYTHONPATH": f"{data}{os.pathsep}{deps}", "SNAP_DATA": str(data)}
            subprocess.run([sys.executable, "-c", code, str(component / "config_flow.py")],
                           env=env, check=True, capture_output=True, text=True)
            env["SNAP_DATA"] = str(data / "wrong")
            result = subprocess.run(
                [sys.executable, "-c", code, str(component / "config_flow.py")],
                env=env, capture_output=True, text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("CI dependency was not loaded from snap data", result.stderr)


if __name__ == "__main__":
    unittest.main()
