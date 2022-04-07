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
        #  cmds.insert(1, 'python3 -m pip install --upgrade pip');
        #  cmds.insert(2, 'python3 -m pip install -U "setuptools<58"')
        #cmds.insert(1, 'pip install --trusted-host pypi.python.org --trusted-host files.pythonhosted.org --trusted-host pypi.org --upgrade pip')
        for idx, cmd in enumerate(cmds):
            if cmd.strip().startswith('pip install -c'):
                cmds[idx] = f"{cmd.strip()} --use-deprecated=legacy-resolver"
            # Find position where to inject pip uninstall
            #  if cmd.strip().startswith('[ -f setup.py ]'):
            #      xcmds = cmd.split("&&", 1)
            #      # Inject and force removal
            #      # cmds[idx] = f"{xcmds[0]} && pip uninstall -y typing uuid && {xcmds[1]}"
            #      cmds[idx] = f"{xcmds[0]} && pip uninstall -y typing uuid && {xcmds[1]}"
        #  print(cmds)
        return cmds
