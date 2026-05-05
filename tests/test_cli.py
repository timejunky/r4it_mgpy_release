from __future__ import annotations

import argparse
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from manifestguard_bootstrap.cli import (
    _WINDOWS_INSTALL_HANDOFF_ENV,
    _detect_ui_language,
    _print_first_run_guidance_once,
    _handoff_install,
    _resolve_python_handoff_executable,
    _should_handoff_install,
)


class CliTests(unittest.TestCase):
    def test_detect_ui_language_prefers_manifestguard_lang(self) -> None:
        with mock.patch.dict(os.environ, {"MANIFESTGUARD_LANG": "tr_TR"}, clear=True), mock.patch(
            "manifestguard_bootstrap.cli.locale.getlocale",
            return_value=("de_DE", "UTF-8"),
        ):
            self.assertEqual(_detect_ui_language(), "tr")

    def test_detect_ui_language_from_env(self) -> None:
        with mock.patch.dict(os.environ, {"LANG": "de_DE.UTF-8"}, clear=True), mock.patch(
            "manifestguard_bootstrap.cli.locale.getlocale",
            return_value=("en_US", "UTF-8"),
        ):
            self.assertEqual(_detect_ui_language(), "de")

    def test_detect_ui_language_falls_back_to_english(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch(
            "manifestguard_bootstrap.cli.locale.getlocale",
            return_value=("es_ES", "UTF-8"),
        ):
            self.assertEqual(_detect_ui_language(), "en")

    def test_print_first_run_guidance_once_prints_and_creates_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            marker = Path(tmp_dir) / "bootstrap-first-run.txt"
            with mock.patch("manifestguard_bootstrap.cli._first_run_marker_path", return_value=marker), mock.patch(
                "manifestguard_bootstrap.cli._detect_ui_language",
                return_value="fr",
            ), mock.patch("builtins.print") as print_mock:
                _print_first_run_guidance_once()

            self.assertTrue(marker.exists())
            self.assertGreaterEqual(print_mock.call_count, 7)
            first_line = print_mock.call_args_list[0].args[0]
            self.assertIn("bootstrap ManifestGuard", first_line)
            printed_lines = [call.args[0] for call in print_mock.call_args_list]
            self.assertTrue(any("check-update" in line for line in printed_lines))

    def test_print_first_run_guidance_once_skips_when_marker_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            marker = Path(tmp_dir) / "bootstrap-first-run.txt"
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_text("exists", encoding="utf-8")

            with mock.patch("manifestguard_bootstrap.cli._first_run_marker_path", return_value=marker), mock.patch(
                "builtins.print"
            ) as print_mock:
                _print_first_run_guidance_once()

            print_mock.assert_not_called()

    def test_resolve_python_handoff_executable_prefers_sibling_python(self) -> None:
        with mock.patch("manifestguard_bootstrap.cli.sys.executable", "venv/Scripts/manifestguard.exe"), mock.patch(
            "manifestguard_bootstrap.cli.Path.exists",
            return_value=True,
        ):
            self.assertEqual(_resolve_python_handoff_executable(), "venv\\Scripts\\python.exe")

    def test_resolve_python_handoff_executable_falls_back_to_base_executable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            base_python = tmp_path / "python.exe"
            base_python.touch()

            scripts_dir = tmp_path / "Scripts"
            scripts_dir.mkdir()
            launcher = scripts_dir / "manifestguard.exe"
            launcher.touch()

            with mock.patch("manifestguard_bootstrap.cli.sys.executable", str(launcher)), mock.patch(
                "manifestguard_bootstrap.cli.sys._base_executable",
                str(base_python),
                create=True,
            ):
                resolved = Path(_resolve_python_handoff_executable())

            self.assertEqual(resolved, base_python)

    def test_should_handoff_install_on_windows(self) -> None:
        args = argparse.Namespace(command="install-protected", dry_run=False)
        with mock.patch("manifestguard_bootstrap.cli.os.name", "nt"), mock.patch.dict(os.environ, {}, clear=True):
            self.assertTrue(_should_handoff_install(args))

    def test_should_not_handoff_install_for_dry_run(self) -> None:
        args = argparse.Namespace(command="install-protected", dry_run=True)
        with mock.patch("manifestguard_bootstrap.cli.os.name", "nt"), mock.patch.dict(os.environ, {}, clear=True):
            self.assertFalse(_should_handoff_install(args))

    def test_handoff_install_spawns_python_module_with_env_marker(self) -> None:
        with mock.patch("manifestguard_bootstrap.cli._resolve_python_handoff_executable", return_value="venv/Scripts/python.exe"), mock.patch(
            "manifestguard_bootstrap.cli.subprocess.Popen"
        ) as popen, mock.patch.dict(os.environ, {}, clear=True):
            result = _handoff_install(["install-protected", "--venv"])

        self.assertEqual(result, 0)
        popen.assert_called_once()
        command = popen.call_args.args[0]
        env = popen.call_args.kwargs["env"]
        self.assertEqual(
            command,
            ["venv/Scripts/python.exe", "-m", "manifestguard_bootstrap.cli", "install-protected", "--venv"],
        )
        self.assertEqual(env[_WINDOWS_INSTALL_HANDOFF_ENV], "1")


if __name__ == "__main__":
    unittest.main()