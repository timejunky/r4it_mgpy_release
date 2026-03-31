# r4it_mgpy_release

Public bootstrap package for `manifestguard`.

Purpose:

- `dev` branch: source of truth for the public bootstrap installer.
- `main` branch: reviewed source ready for public release.
- `release` branch: protected payload artifacts only (PyArmor-built wheel + metadata).

The public PyPI package does not ship the protected ManifestGuard code. Instead, it provides a CLI that can fetch the latest protected wheel from this repository's `release` branch and install it into the current virtual environment or user site.

## Commands

Create a local editable install of the bootstrap package:

```powershell
f:\r4it\dev\r4it_mgpy_release\.venv\Scripts\python.exe -m pip install -e .
```

Show the protected payload manifest configured for download:

```powershell
manifestguard show-manifest
```

Install the protected payload into the active virtual environment if present, otherwise user-wide:

```powershell
manifestguard install-protected
```

Force a specific target mode:

```powershell
manifestguard install-protected --venv
manifestguard install-protected --user
```

## Release Branch Layout

The `release` branch is expected to contain:

```text
manifestguard/
  latest/
    manifest.json
    manifestguard-<version>-py3-none-any.whl
    release.json
    SHA256SUMS.txt
```

`manifest.json` is the bootstrap entrypoint and must include the wheel URL and SHA256 hash.

## Helper Script

Use `tools/publish_release_payload.ps1` while checked out to the `release` branch to copy a protected packet from the releaser output into the branch layout and generate `manifest.json`.
