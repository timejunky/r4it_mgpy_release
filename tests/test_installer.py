from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from manifestguard_bootstrap.installer import (
    PayloadManifest,
    build_pip_install_command,
    build_raw_manifest_url,
    build_version_manifest_path,
    compare_versions,
    detect_install_mode,
    fetch_manifest,
    get_update_status,
    resolve_manifest_path,
    sha256_of_file,
)


class InstallerTests(unittest.TestCase):
    def test_build_raw_manifest_url(self) -> None:
        url = build_raw_manifest_url("timejunky/r4it_mgpy_release", "release", "manifestguard/latest/manifest.json")
        self.assertEqual(
            url,
            "https://raw.githubusercontent.com/timejunky/r4it_mgpy_release/release/manifestguard/latest/manifest.json",
        )

    def test_build_version_manifest_path(self) -> None:
        self.assertEqual(build_version_manifest_path("1.6.25"), "manifestguard/1.6.25/manifest.json")

    def test_resolve_manifest_path_prefers_payload_version(self) -> None:
        self.assertEqual(
            resolve_manifest_path("manifestguard/latest/manifest.json", "1.6.25"),
            "manifestguard/1.6.25/manifest.json",
        )

    def test_detect_install_mode_prefers_venv_when_active(self) -> None:
        with mock.patch("manifestguard_bootstrap.installer.sys.prefix", "venv"), mock.patch(
            "manifestguard_bootstrap.installer.sys.base_prefix", "base"
        ), mock.patch.dict("manifestguard_bootstrap.installer.os.environ", {}, clear=True):
            self.assertEqual(detect_install_mode(False, False), "venv")

    def test_detect_install_mode_defaults_to_user(self) -> None:
        with mock.patch("manifestguard_bootstrap.installer.sys.prefix", "same"), mock.patch(
            "manifestguard_bootstrap.installer.sys.base_prefix", "same"
        ), mock.patch.dict("manifestguard_bootstrap.installer.os.environ", {}, clear=True):
            self.assertEqual(detect_install_mode(False, False), "user")

    def test_build_pip_install_command_for_user(self) -> None:
        command = build_pip_install_command("python", Path("payload.whl"), "user")
        self.assertEqual(command[-1], "--user")

    def test_sha256_of_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            sample = Path(temp_dir) / "sample.txt"
            sample.write_text("hello", encoding="utf-8")
            self.assertEqual(
                sha256_of_file(sample),
                "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824",
            )

    def test_compare_versions(self) -> None:
        self.assertLess(compare_versions("1.6.24", "1.6.25"), 0)
        self.assertEqual(compare_versions("1.6.25", "1.6.25"), 0)
        self.assertGreater(compare_versions("1.6.26", "1.6.25"), 0)

    def test_get_update_status_for_missing_installation(self) -> None:
        self.assertEqual(
            get_update_status("1.6.25", None),
            {
                "installed_version": None,
                "target_version": "1.6.25",
                "update_available": True,
                "status": "not-installed",
            },
        )

    def test_get_update_status_for_available_update(self) -> None:
        self.assertEqual(
            get_update_status("1.6.25", "1.6.24"),
            {
                "installed_version": "1.6.24",
                "target_version": "1.6.25",
                "update_available": True,
                "status": "update-available",
            },
        )

    def test_fetch_manifest(self) -> None:
        payload = {
            "version": "1.6.25",
            "wheel_url": "https://example.invalid/manifestguard-1.6.25.whl",
            "sha256": "abc123",
        }
        data = json.dumps(payload).encode("utf-8")
        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.__exit__.return_value = None
        response.read.return_value = data
        response.__iter__.return_value = iter([data])
        with mock.patch("urllib.request.urlopen", return_value=response):
            manifest = fetch_manifest("https://example.invalid/manifest.json")
        self.assertEqual(
            manifest,
            PayloadManifest(version="1.6.25", wheel_url="https://example.invalid/manifestguard-1.6.25.whl", sha256="abc123"),
        )


if __name__ == "__main__":
    unittest.main()
