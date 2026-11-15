"""Create a disposable integration and Python dependency for snap testing."""

import base64
from contextlib import contextmanager
import csv
from functools import partial
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import zipfile

NAME = "ci_snap_test_dependency"
WHEEL = f"{NAME}-1.0-py3-none-any.whl"
DIST = f"{NAME}-1.0.dist-info"
DATA = Path("/var/snap/home-assistant-snap/current")
DOMAIN = "snap_ci_test"


def create_wheel(directory):
    files = {
        f"{NAME}/__init__.py": b'"""CI dependency installed by Home Assistant."""\n',
        f"{DIST}/METADATA": b"Metadata-Version: 2.1\nName: ci-snap-test-dependency\nVersion: 1.0\n",
        f"{DIST}/WHEEL": b"Wheel-Version: 1.0\nGenerator: CI\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
    }
    record = io.StringIO(newline="")
    writer = csv.writer(record, lineterminator="\n")
    for name, contents in files.items():
        digest = base64.urlsafe_b64encode(hashlib.sha256(contents).digest()).rstrip(b"=")
        writer.writerow((name, f"sha256={digest.decode()}", len(contents)))
    writer.writerow((f"{DIST}/RECORD", "", ""))
    files[f"{DIST}/RECORD"] = record.getvalue().encode()
    with zipfile.ZipFile(Path(directory) / WHEEL, "w") as archive:
        for name, contents in files.items():
            archive.writestr(name, contents)


@contextmanager
def serve_wheel():
    with tempfile.TemporaryDirectory() as directory:
        create_wheel(directory)
        handler = partial(SimpleHTTPRequestHandler, directory=directory)
        with ThreadingHTTPServer(("127.0.0.1", 0), handler) as server:
            thread = threading.Thread(target=server.serve_forever)
            thread.start()
            try:
                yield f"http://127.0.0.1:{server.server_port}/{WHEEL}"
            finally:
                server.shutdown()
                thread.join()


def prepare_integration(url):
    deps = DATA / "deps"
    if deps.exists() and next(deps.rglob(NAME), None):
        raise RuntimeError("The test dependency is already present")
    component = DATA / "custom_components" / DOMAIN
    component.mkdir(parents=True, exist_ok=False)
    manifest = {
        "domain": DOMAIN,
        "name": "Snap CI test",
        "version": "1.0.0",
        "documentation": "https://github.com/giaever-online-iot/home-assistant-snap",
        "codeowners": [],
        "config_flow": True,
        "iot_class": "local_push",
        "requirements": [f"ci-snap-test-dependency @ {url}"],
    }
    (component / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (component / "__init__.py").write_text('"""Disposable integration for CI."""\n')
    (component / "config_flow.py").write_text(
        '"""Test dependency installation and import."""\n'
        "import os\n"
        "from pathlib import Path\n"
        "import ci_snap_test_dependency\n"
        "from homeassistant.config_entries import ConfigFlow\n"
        "\n"
        "if not Path(ci_snap_test_dependency.__file__).resolve().is_relative_to("
        "Path(os.environ['SNAP_DATA']).resolve() / 'deps'):\n"
        "    raise RuntimeError('CI dependency was not loaded from snap data')\n"
        "\n"
        "class SnapCITestFlow(ConfigFlow, domain='snap_ci_test'):\n"
        "    async def async_step_user(self, user_input=None):\n"
        "        return self.async_show_form(step_id='user')\n"
    )


if __name__ == "__main__":
    if len(sys.argv) != 2 or os.geteuid() != 0:
        raise SystemExit("Usage: sudo python3 integration_fixture.py WHEEL_URL")
    prepare_integration(sys.argv[1])
