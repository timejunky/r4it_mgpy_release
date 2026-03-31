from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path

DEFAULT_REPOSITORY = "timejunky/r4it_mgpy_release"
DEFAULT_BRANCH = "release"
DEFAULT_MANIFEST_ROOT = "manifestguard"
DEFAULT_MANIFEST_PATH = "manifestguard/latest/manifest.json"
_MISSING = object()


@dataclass(frozen=True)
class PayloadManifest:
    version: str
    wheel_url: str
    sha256: str
    python_requires: str | None = None
    notes: str | None = None


def build_version_manifest_path(
    payload_version: str,
    manifest_root: str = DEFAULT_MANIFEST_ROOT,
) -> str:
    normalized_version = payload_version.strip()
    if not normalized_version:
        raise ValueError("payload_version must not be empty.")
    return f"{manifest_root}/{normalized_version}/manifest.json"


def resolve_manifest_path(manifest_path: str, payload_version: str | None = None) -> str:
    if payload_version:
        return build_version_manifest_path(payload_version)
    return manifest_path


def build_raw_manifest_url(
    repository: str = DEFAULT_REPOSITORY,
    branch: str = DEFAULT_BRANCH,
    manifest_path: str = DEFAULT_MANIFEST_PATH,
) -> str:
    return f"https://raw.githubusercontent.com/{repository}/{branch}/{manifest_path}"


def fetch_manifest(url: str, timeout: int = 30) -> PayloadManifest:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        payload = json.load(response)
    return PayloadManifest(
        version=payload["version"],
        wheel_url=payload["wheel_url"],
        sha256=payload["sha256"],
        python_requires=payload.get("python_requires"),
        notes=payload.get("notes"),
    )


def get_installed_manifestguard_version() -> str | None:
    try:
        return importlib.metadata.version("manifestguard")
    except importlib.metadata.PackageNotFoundError:
        return None


def compare_versions(left: str, right: str) -> int:
    def normalize_part(part: str) -> tuple[int, int | str]:
        return (0, int(part)) if part.isdigit() else (1, part)

    left_parts = [normalize_part(part) for part in left.split(".")]
    right_parts = [normalize_part(part) for part in right.split(".")]
    max_len = max(len(left_parts), len(right_parts))
    padding = (0, 0)
    left_parts.extend([padding] * (max_len - len(left_parts)))
    right_parts.extend([padding] * (max_len - len(right_parts)))
    if left_parts < right_parts:
        return -1
    if left_parts > right_parts:
        return 1
    return 0


def get_update_status(
    target_version: str,
    installed_version: str | None | object = _MISSING,
) -> dict[str, str | bool | None]:
    if installed_version is _MISSING:
        installed_version = get_installed_manifestguard_version()
    if installed_version is None:
        return {
            "installed_version": None,
            "target_version": target_version,
            "update_available": True,
            "status": "not-installed",
        }

    comparison = compare_versions(installed_version, target_version)
    if comparison < 0:
        status = "update-available"
        update_available = True
    elif comparison == 0:
        status = "up-to-date"
        update_available = False
    else:
        status = "ahead-of-target"
        update_available = False

    return {
        "installed_version": installed_version,
        "target_version": target_version,
        "update_available": update_available,
        "status": status,
    }


def detect_install_mode(use_user: bool, use_venv: bool) -> str:
    if use_user and use_venv:
        raise ValueError("Choose either user or venv mode, not both.")
    if use_user:
        return "user"
    if use_venv:
        return "venv"
    if os.environ.get("VIRTUAL_ENV") or sys.prefix != getattr(sys, "base_prefix", sys.prefix):
        return "venv"
    return "user"


def sha256_of_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_file(url: str, destination: Path, timeout: int = 60) -> Path:
    with urllib.request.urlopen(url, timeout=timeout) as response, destination.open("wb") as handle:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)
    return destination


def build_pip_install_command(python_executable: str, wheel_path: Path, mode: str) -> list[str]:
    command = [python_executable, "-m", "pip", "install", "--upgrade", str(wheel_path)]
    if mode == "user":
        command.append("--user")
    return command


def install_payload(
    manifest: PayloadManifest,
    mode: str,
    python_executable: str | None = None,
    dry_run: bool = False,
) -> list[str]:
    python_executable = python_executable or sys.executable
    with tempfile.TemporaryDirectory(prefix="manifestguard-bootstrap-") as temp_dir:
        wheel_name = Path(manifest.wheel_url).name
        wheel_path = Path(temp_dir) / wheel_name
        download_file(manifest.wheel_url, wheel_path)
        actual_hash = sha256_of_file(wheel_path)
        if actual_hash.lower() != manifest.sha256.lower():
            raise RuntimeError(
                f"Downloaded wheel hash mismatch. expected={manifest.sha256} actual={actual_hash}"
            )
        command = build_pip_install_command(python_executable, wheel_path, mode)
        if dry_run:
            return command
        subprocess.run(command, check=True)
        return command
