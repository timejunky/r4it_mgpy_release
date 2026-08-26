"""Optional first-run POST to Zebra module ``mgpy_pypi`` (no license key).

Fail-open. Never blocks the bootstrap CLI. Consent via
``MGPY_ACCEPT_ZEBRA_LIFECYCLE=1`` only (no prompt here).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import urllib.error
import urllib.request

_DEV_API = "http://api.dev.streamingzebra.loc"
_LIFE_API = "https://api.streamingzebra.com"
_EVENT_PATH = "/api/v2/lifecycle/event"
_ACCEPT_ENV = "MGPY_ACCEPT_ZEBRA_LIFECYCLE"
_SKIP_ENV = "MGPY_SKIP_ZEBRA_LIFECYCLE"


def _truthy(source: dict[str, str], key: str) -> bool:
    return str(source.get(key) or "").strip() in {"1", "true", "TRUE", "yes"}


def _marker_path() -> Path:
    if os.name == "nt":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "ManifestGuard" / "zebra-pypi-reported.txt"
    return Path.home() / ".manifestguard" / "zebra-pypi-reported.txt"


def _semver(version: str) -> str:
    parts: list[str] = []
    for token in str(version or "").lstrip("vV").replace("-", ".").split("."):
        if token.isdigit():
            parts.append(token)
        else:
            break
        if len(parts) == 3:
            break
    if len(parts) >= 2:
        return ".".join(parts[:3])
    return "0.0.0"


def maybe_report_pypi_bootstrap(version: str, env: dict[str, str] | None = None) -> None:
    source = env if env is not None else os.environ
    if _truthy(source, _SKIP_ENV) or not _truthy(source, _ACCEPT_ENV):
        return
    marker = _marker_path()
    if marker.exists():
        return
    api = _DEV_API if str(source.get("MGPY_ZEBRA_DEV") or "").strip() == "1" else _LIFE_API
    body = json.dumps(
        {
            "module_name": "mgpy_pypi",
            "event": "install",
            "current_version": _semver(version),
            "company_key": "ready-4-it",
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        api.rstrip("/") + _EVENT_PATH,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "MGPY-Bootstrap-Lifecycle",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            ok = int(getattr(response, "status", 200) or 200) < 400
    except (urllib.error.URLError, TimeoutError, OSError):
        return
    if not ok:
        return
    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("1", encoding="utf-8")
    except OSError:
        return
