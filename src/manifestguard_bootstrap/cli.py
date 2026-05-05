from __future__ import annotations

import argparse
import json
import locale
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from . import __version__
from .installer import (
    DEFAULT_BRANCH,
    DEFAULT_MANIFEST_PATH,
    DEFAULT_REPOSITORY,
    build_raw_manifest_url,
    detect_install_mode,
    fetch_manifest,
    get_update_status,
    install_payload,
    resolve_manifest_path,
)

_WINDOWS_INSTALL_HANDOFF_ENV = "MANIFESTGUARD_BOOTSTRAP_INSTALL_HANDOFF"

_FIRST_RUN_GUIDANCE_LINES: dict[str, list[str]] = {
    "en": [
        "ManifestGuard bootstrap is installed.",
        "Recommended next step: manifestguard install-protected",
        "For user-wide install: manifestguard install-protected --user",
        "For current virtual environment: manifestguard install-protected --venv",
        "Inspect payload metadata: manifestguard show-manifest",
        "Check updates manually: manifestguard check-update",
        "After protected install, verify runtime: python -m manifestguard --version",
    ],
    "de": [
        "ManifestGuard Bootstrap ist installiert.",
        "Empfohlener nächster Schritt: manifestguard install-protected",
        "Für benutzerweite Installation: manifestguard install-protected --user",
        "Für die aktuelle virtuelle Umgebung: manifestguard install-protected --venv",
        "Payload-Metadaten anzeigen: manifestguard show-manifest",
        "Updates manuell prüfen: manifestguard check-update",
        "Nach Protected-Install Runtime prüfen: python -m manifestguard --version",
    ],
    "fr": [
        "Le bootstrap ManifestGuard est installe.",
        "Etape suivante recommandee: manifestguard install-protected",
        "Pour une installation utilisateur: manifestguard install-protected --user",
        "Pour l'environnement virtuel actif: manifestguard install-protected --venv",
        "Afficher les metadonnees du payload: manifestguard show-manifest",
        "Verifier les mises a jour manuellement: manifestguard check-update",
        "Apres installation protegee, verifier le runtime: python -m manifestguard --version",
    ],
    "lb": [
        "ManifestGuard Bootstrap ass installéiert.",
        "Empfohlene nächste Schrëtt: manifestguard install-protected",
        "Fir eng Benotzer-Installatioun: manifestguard install-protected --user",
        "Fir dat aktuellt virtuellt Ëmfeld: manifestguard install-protected --venv",
        "Payload-Metadonnéeën weisen: manifestguard show-manifest",
        "Updates manuell iwwerpréiwen: manifestguard check-update",
        "No der Protected-Installatioun Runtime iwwerpréiwen: python -m manifestguard --version",
    ],
    "tr": [
        "ManifestGuard bootstrap kuruldu.",
        "Onerilen sonraki adim: manifestguard install-protected",
        "Kullanici kapsami kurulum icin: manifestguard install-protected --user",
        "Mevcut sanal ortam icin: manifestguard install-protected --venv",
        "Payload metaverisini goster: manifestguard show-manifest",
        "Guncellemeleri elle kontrol et: manifestguard check-update",
        "Korumali kurulumdan sonra runtime'i dogrula: python -m manifestguard --version",
    ],
}


def _detect_ui_language() -> str:
    preferred = os.environ.get("MANIFESTGUARD_LANG")
    if preferred:
        lang = preferred.split(".", 1)[0].split("_", 1)[0].lower()
        if lang in _FIRST_RUN_GUIDANCE_LINES:
            return lang

    for env_name in ("LC_ALL", "LANG"):
        raw = os.environ.get(env_name)
        if raw:
            lang = raw.split(".", 1)[0].split("_", 1)[0].lower()
            if lang in _FIRST_RUN_GUIDANCE_LINES:
                return lang

    locale_value, _ = locale.getlocale()
    if locale_value:
        lang = locale_value.split("_", 1)[0].lower()
        if lang in _FIRST_RUN_GUIDANCE_LINES:
            return lang

    return "en"


def _first_run_marker_path() -> Path:
    if os.name == "nt":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "ManifestGuard" / "bootstrap-first-run.txt"
    return Path.home() / ".manifestguard" / "bootstrap-first-run.txt"


def _print_first_run_guidance_once() -> None:
    marker = _first_run_marker_path()
    if marker.exists():
        return

    for line in _FIRST_RUN_GUIDANCE_LINES[_detect_ui_language()]:
        print(line)

    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(__version__, encoding="utf-8")
    except OSError:
        return


def _resolve_python_handoff_executable() -> str:
    executable = Path(sys.executable)

    candidates: list[Path] = []
    candidates.append(executable.with_name("python.exe"))

    base_executable = getattr(sys, "_base_executable", None)
    if base_executable:
        candidates.append(Path(base_executable))

    base_prefix = Path(sys.base_prefix)
    candidates.append(base_prefix / "python.exe")
    candidates.append(base_prefix / "Scripts" / "python.exe")

    prefix = Path(sys.prefix)
    candidates.append(prefix / "python.exe")
    candidates.append(prefix / "Scripts" / "python.exe")

    which_python = shutil.which("python")
    if which_python:
        candidates.append(Path(which_python))

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    return sys.executable


def _should_handoff_install(args: argparse.Namespace) -> bool:
    return (
        os.name == "nt"
        and args.command == "install-protected"
        and not args.dry_run
        and os.environ.get(_WINDOWS_INSTALL_HANDOFF_ENV) != "1"
    )


def _handoff_install(argv: list[str]) -> int:
    env = os.environ.copy()
    env[_WINDOWS_INSTALL_HANDOFF_ENV] = "1"
    command = [_resolve_python_handoff_executable(), "-m", "manifestguard_bootstrap.cli", *argv]
    subprocess.Popen(command, env=env)
    print("Re-launched payload installation via python.exe to avoid Windows launcher file locking.")
    return 0


def _add_common_manifest_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repository", default=DEFAULT_REPOSITORY, help="GitHub repository slug")
    parser.add_argument("--branch", default=DEFAULT_BRANCH, help="Git branch hosting the protected payload")
    parser.add_argument(
        "--payload-version",
        help="Payload version selector, for example '1.6.25' or 'latest'",
    )
    parser.add_argument(
        "--manifest-path",
        default=DEFAULT_MANIFEST_PATH,
        help="Path to manifest.json inside the repository branch",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="manifestguard")
    parser.add_argument("--version", action="version", version=f"%(prog)s bootstrap {__version__}")

    subparsers = parser.add_subparsers(dest="command", required=True)

    show_manifest = subparsers.add_parser("show-manifest", help="Show the protected payload manifest")
    _add_common_manifest_args(show_manifest)

    check_update = subparsers.add_parser(
        "check-update",
        help="Compare the installed ManifestGuard version against the selected protected payload manifest",
    )
    _add_common_manifest_args(check_update)

    install_protected = subparsers.add_parser(
        "install-protected",
        help="Download and install the protected ManifestGuard wheel from GitHub",
    )
    _add_common_manifest_args(install_protected)
    install_protected.add_argument("--user", action="store_true", help="Install to the user site")
    install_protected.add_argument("--venv", action="store_true", help="Install into the active virtual environment")
    install_protected.add_argument("--dry-run", action="store_true", help="Print the pip command without executing it")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    argv = list(argv if argv is not None else sys.argv[1:])

    _print_first_run_guidance_once()

    manifest_path = resolve_manifest_path(args.manifest_path, getattr(args, "payload_version", None))
    manifest_url = build_raw_manifest_url(args.repository, args.branch, manifest_path)
    manifest = fetch_manifest(manifest_url)

    if args.command == "show-manifest":
        payload = {
            "manifest_url": manifest_url,
            "manifest_path": manifest_path,
            "version": manifest.version,
            "wheel_url": manifest.wheel_url,
            "sha256": manifest.sha256,
            "python_requires": manifest.python_requires,
            "notes": manifest.notes,
        }
        print(json.dumps(payload, indent=2))
        return 0

    if args.command == "check-update":
        payload = {
            "manifest_url": manifest_url,
            "manifest_path": manifest_path,
            **get_update_status(manifest.version),
        }
        print(json.dumps(payload, indent=2))
        return 0

    if args.command == "install-protected":
        if _should_handoff_install(args):
            return _handoff_install(argv)
        if os.name == "nt" and os.environ.get(_WINDOWS_INSTALL_HANDOFF_ENV) == "1":
            time.sleep(1.0)
        mode = detect_install_mode(args.user, args.venv)
        command = install_payload(manifest, mode, dry_run=args.dry_run)
        if args.dry_run:
            print(" ".join(command))
        return 0

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
