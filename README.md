# r4it_mgpy_release

Public bootstrap package for `manifestguard`.

Purpose:

- `dev` branch: source of truth for the public bootstrap installer.
- `main` branch: reviewed source ready for public release.
- `release` branch: protected payload artifacts only (PyArmor-built wheel + metadata).

The public PyPI package does not ship the protected ManifestGuard code. Instead, it provides a CLI that can fetch the latest protected wheel from this repository's `release` branch and install it into the current virtual environment or user site.

Versioning rule:

- The public bootstrap package should normally use the same version as the protected ManifestGuard payload it installs.
- If the bootstrap wrapper needs a packaging-only fix without a payload change, use a post-release such as `1.6.26.post1`.

## Commands

Create a local editable install of the bootstrap package:

```powershell
f:\r4it\dev\r4it_mgpy_release\.venv\Scripts\python.exe -m pip install -e .
```

Show the protected payload manifest configured for download:

```powershell
manifestguard show-manifest
```

Show the manifest for a specific protected version:

```powershell
manifestguard show-manifest --payload-version 1.6.26
```

Check whether the selected payload is newer than the currently installed `manifestguard` version:

```powershell
manifestguard check-update
manifestguard check-update --payload-version 1.6.26
```

If only the public bootstrap wrapper is installed, `check-update` reports `bootstrap-only` until the protected payload has actually been installed.

Install the protected payload into the active virtual environment if present, otherwise user-wide:

```powershell
manifestguard install-protected
```

Force a specific target mode:

```powershell
manifestguard install-protected --venv
manifestguard install-protected --user
manifestguard install-protected --payload-version 1.6.26
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
  <version>/
    manifest.json
    manifestguard-<version>-py3-none-any.whl
    release.json
    SHA256SUMS.txt
```

`manifestguard/latest/manifest.json` is the default bootstrap entrypoint.
Version-specific commands such as `--payload-version 1.6.26` resolve to `manifestguard/1.6.26/manifest.json`.
Each `manifest.json` must include the wheel URL and SHA256 hash.

## Helper Script

Use `tools/publish_release_payload.ps1` while checked out to the `release` branch to copy a protected packet from the releaser output into the branch layout and generate both the `latest` and version-specific manifests.
