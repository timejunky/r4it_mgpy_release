from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from urllib.error import URLError

from manifestguard_bootstrap.zebra_pypi import _semver, maybe_report_pypi_bootstrap


class ZebraPypiTests(unittest.TestCase):
    def test_semver_strips_post_release(self) -> None:
        self.assertEqual(_semver("1.6.46.post5"), "1.6.46")
        self.assertEqual(_semver("v1.6.61"), "1.6.61")
        self.assertEqual(_semver(""), "0.0.0")

    def test_maybe_report_skips_without_consent(self) -> None:
        with mock.patch("urllib.request.urlopen") as urlopen:
            maybe_report_pypi_bootstrap("1.6.46.post5", env={})
        urlopen.assert_not_called()

    def test_maybe_report_skips_when_opted_out(self) -> None:
        with mock.patch("urllib.request.urlopen") as urlopen:
            maybe_report_pypi_bootstrap(
                "1.6.46.post5",
                env={"MGPY_ACCEPT_ZEBRA_LIFECYCLE": "1", "MGPY_SKIP_ZEBRA_LIFECYCLE": "1"},
            )
        urlopen.assert_not_called()

    def test_maybe_report_posts_mgpy_pypi_install_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            marker = Path(tmp_dir) / "zebra-pypi-reported.txt"
            response = mock.MagicMock()
            response.__enter__.return_value = response
            response.__exit__.return_value = None
            response.status = 200
            response.read.return_value = b"{}"
            with mock.patch(
                "manifestguard_bootstrap.zebra_pypi._marker_path",
                return_value=marker,
            ), mock.patch("urllib.request.urlopen", return_value=response) as urlopen:
                maybe_report_pypi_bootstrap(
                    "1.6.46.post5",
                    env={"MGPY_ACCEPT_ZEBRA_LIFECYCLE": "1", "MGPY_ZEBRA_DEV": "1"},
                )
                maybe_report_pypi_bootstrap(
                    "1.6.46.post5",
                    env={"MGPY_ACCEPT_ZEBRA_LIFECYCLE": "1", "MGPY_ZEBRA_DEV": "1"},
                )

            self.assertTrue(marker.exists())
            urlopen.assert_called_once()
            request = urlopen.call_args.args[0]
            self.assertIn("api.dev.streamingzebra.loc", request.full_url)
            payload = json.loads(request.data.decode("utf-8"))
            self.assertEqual(payload["module_name"], "mgpy_pypi")
            self.assertEqual(payload["event"], "install")
            self.assertEqual(payload["current_version"], "1.6.46")
            self.assertEqual(payload["company_key"], "ready-4-it")

    def test_maybe_report_fail_open_on_network_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            marker = Path(tmp_dir) / "zebra-pypi-reported.txt"
            with mock.patch(
                "manifestguard_bootstrap.zebra_pypi._marker_path",
                return_value=marker,
            ), mock.patch("urllib.request.urlopen", side_effect=URLError("down")):
                maybe_report_pypi_bootstrap(
                    "1.6.46.post5",
                    env={"MGPY_ACCEPT_ZEBRA_LIFECYCLE": "1"},
                )
            self.assertFalse(marker.exists())


if __name__ == "__main__":
    unittest.main()
