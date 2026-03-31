from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .installer import (
    DEFAULT_BRANCH,
    DEFAULT_MANIFEST_PATH,
    DEFAULT_REPOSITORY,
    build_raw_manifest_url,
    detect_install_mode,
    fetch_manifest,
    install_payload,
)


def _add_common_manifest_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repository", default=DEFAULT_REPOSITORY, help="GitHub repository slug")
    parser.add_argument("--branch", default=DEFAULT_BRANCH, help="Git branch hosting the protected payload")
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

    manifest_url = build_raw_manifest_url(args.repository, args.branch, args.manifest_path)
    manifest = fetch_manifest(manifest_url)

    if args.command == "show-manifest":
        payload = {
            "manifest_url": manifest_url,
            "version": manifest.version,
            "wheel_url": manifest.wheel_url,
            "sha256": manifest.sha256,
            "python_requires": manifest.python_requires,
            "notes": manifest.notes,
        }
        print(json.dumps(payload, indent=2))
        return 0

    if args.command == "install-protected":
        mode = detect_install_mode(args.user, args.venv)
        command = install_payload(manifest, mode, dry_run=args.dry_run)
        if args.dry_run:
            print(" ".join(command))
        return 0

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
