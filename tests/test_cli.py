from __future__ import annotations

import argparse
import os
import unittest
from unittest import mock

from manifestguard_bootstrap.cli import (
    _WINDOWS_INSTALL_HANDOFF_ENV,
    _handoff_install,
    _resolve_python_handoff_executable,
    _should_handoff_install,
)


class CliTests(unittest.TestCase):
    def test_resolve_python_handoff_executable_prefers_sibling_python(self) -> None:
        with mock.patch("manifestguard_bootstrap.cli.sys.executable", "C:/venv/Scripts/manifestguard.exe"), mock.patch(
            "manifestguard_bootstrap.cli.Path.exists",
            return_value=True,
        ):
            self.assertEqual(_resolve_python_handoff_executable(), "C:\\venv\\Scripts\\python.exe")

    def test_should_handoff_install_on_windows(self) -> None:
        args = argparse.Namespace(command="install-protected", dry_run=False)
        with mock.patch("manifestguard_bootstrap.cli.os.name", "nt"), mock.patch.dict(os.environ, {}, clear=True):
            self.assertTrue(_should_handoff_install(args))

    def test_should_not_handoff_install_for_dry_run(self) -> None:
        args = argparse.Namespace(command="install-protected", dry_run=True)
        with mock.patch("manifestguard_bootstrap.cli.os.name", "nt"), mock.patch.dict(os.environ, {}, clear=True):
            self.assertFalse(_should_handoff_install(args))

    def test_handoff_install_spawns_python_module_with_env_marker(self) -> None:
        with mock.patch("manifestguard_bootstrap.cli._resolve_python_handoff_executable", return_value="C:/venv/Scripts/python.exe"), mock.patch(
            "manifestguard_bootstrap.cli.subprocess.Popen"
        ) as popen, mock.patch.dict(os.environ, {}, clear=True):
            result = _handoff_install(["install-protected", "--venv"])

        self.assertEqual(result, 0)
        popen.assert_called_once()
        command = popen.call_args.args[0]
        env = popen.call_args.kwargs["env"]
        self.assertEqual(
            command,
            ["C:/venv/Scripts/python.exe", "-m", "manifestguard_bootstrap.cli", "install-protected", "--venv"],
        )
        self.assertEqual(env[_WINDOWS_INSTALL_HANDOFF_ENV], "1")


if __name__ == "__main__":
    unittest.main()