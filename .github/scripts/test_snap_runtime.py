"""Exercise the patched Home Assistant startup using the installed snap source."""

import ast
from importlib import metadata
import os
from pathlib import Path
import site
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import integration_fixture


class StopBeforeDispatch(Exception):
    """Stop once startup has initialized the import path."""


class SnapRuntimeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = Path(os.environ["HA_MAIN_PATH"])
        tree = ast.parse(source.read_text(), filename=str(source))
        main = next(
            node for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "main"
        )
        module = ast.Module(body=[main], type_ignores=[])
        namespace = {
            "os": os,
            "site": site,
            "sys": sys,
            "is_snap_env": lambda: True,
            "validate_python": lambda: None,
            "validate_environment": lambda: None,
            "get_arguments": lambda: (_ for _ in ()).throw(StopBeforeDispatch()),
        }
        exec(compile(module, str(source), "exec"), namespace)
        cls.namespace = namespace

    def test_creates_user_site_and_loads_new_dependency(self):
        with tempfile.TemporaryDirectory() as directory:
            user_site = Path(directory) / "deps" / "site-packages"
            wheel_dir = Path(directory) / "wheel"
            wheel_dir.mkdir()
            integration_fixture.create_wheel(wheel_dir)
            with (
                patch.object(site, "getusersitepackages", return_value=str(user_site)),
                patch.object(sys, "path", sys.path.copy()),
                patch.dict(sys.path_importer_cache, {str(user_site): None}),
            ):
                with self.assertRaises(StopBeforeDispatch):
                    self.namespace["main"]()
                self.assertEqual(sys.path[0], str(user_site))
                self.assertTrue(user_site.is_dir())
                with zipfile.ZipFile(wheel_dir / integration_fixture.WHEEL) as wheel:
                    wheel.extractall(user_site)
                try:
                    imported = __import__(integration_fixture.NAME)
                    self.assertTrue(Path(imported.__file__).is_relative_to(user_site))
                    self.assertEqual(metadata.version("ci-snap-test-dependency"), "1.0")
                finally:
                    sys.modules.pop(integration_fixture.NAME, None)

    def test_non_snap_startup_does_not_change_import_path(self):
        with (
            patch.dict(self.namespace, {"is_snap_env": lambda: False}),
            patch.object(sys, "path", sys.path.copy()),
            patch.object(site, "getusersitepackages") as user_site,
        ):
            original = sys.path.copy()
            with self.assertRaises(StopBeforeDispatch):
                self.namespace["main"]()
            self.assertEqual(sys.path, original)
            user_site.assert_not_called()


if __name__ == "__main__":
    unittest.main()
