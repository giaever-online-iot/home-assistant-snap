#!/usr/bin/env python3

import snapcraft
import snapcraft.plugins.v2 as plugins
from typing import Any, Dict, List, Set
import os

"""
See snapcraft.plugins.v2.python.PythonPlugin

Plugin forces removal of 'typing' package
after setup, as 'typing' is causing problems
for python >= 3.7, see:

- https://github.com/pypa/pip/issues/8272
"""
class PluginImpl(plugins.python.PythonPlugin):
    def get_build_commands(self) -> List[str]:
        cmds = super().get_build_commands()
        for idx, cmd in enumerate(cmds):
            if cmd.strip().startswith('pip install -c') and "requirements_all" in cmd:
                cmds[idx] = f"{cmd.strip()} --use-deprecated=legacy-resolver"
            elif "[ -f setup.py ]" in cmd:
                # Use cfg instead of py
                cmds[idx] = cmd.replace('[ -f setup.py ]', '"${SNAPCRAFT_PYTHON_INTERPRETER}" -m build')
        return cmds
