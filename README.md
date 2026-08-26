# manifestguard

Public **bootstrap** package for ManifestGuard. It does **not** ship the scanner.

- Free: `pip install manifestguard` (this wrapper only).
- Trial/Pro: activate a R4IT token, then **My Licenses** ZIP or `py -3.12 -m manifestguard license update-apply`.
- Do **not** use `pip install --upgrade manifestguard` to update Pro. That command refreshes this bootstrap and can replace a paid install.

Purpose:

- `dev` branch: source of truth for the public bootstrap installer.
- `main` branch: reviewed source ready for public release.
- `release` branch: protected payload artifacts (operator / GitHub override only).

Twine uploads must come from this repository. The MGPY monorepo must never be published to PyPI.

Versioning rule:

- Wrapper-only public bumps stay on the last public bootstrap line as `.postN` (this release: `1.6.46.post5`).
- Do not retag this package as the current Pro ZIP version (for example `1.6.61`). A higher bootstrap version would make `pip install --upgrade manifestguard` look newer than an older Pro install and replace the scanner with this thin wrapper.
- The protected payload on Zebra is versioned independently (`mgpy-1.6.61` and later).

## Customer path

```powershell
py -3.12 -m pip install --user manifestguard
py -3.12 -m manifestguard --version
```

Then buy/activate. Apply Trial/Pro with My Licenses or:

```powershell
py -3.12 -m manifestguard license update-apply
```

Optional first-run lifecycle ping (no license key; fail-open): set `MGPY_ACCEPT_ZEBRA_LIFECYCLE=1`. Opt out: `MGPY_SKIP_ZEBRA_LIFECYCLE=1`.

## Operator GitHub override

`show-manifest`, `check-update`, and `install-protected` fetch the `release` branch and stay retired unless `MGPY_ALLOW_GITHUB_BOOTSTRAP=1`.

```powershell
$env:MGPY_ALLOW_GITHUB_BOOTSTRAP = "1"
manifestguard show-manifest
manifestguard check-update --payload-version 1.6.46
py -3.12 -m manifestguard_bootstrap.cli install-protected --user
```

Important for the currently shipped protected payload:

- Use Python 3.12 for the protected install path (cp312 wheel).
- On Windows prefer explicit interpreter calls for protected steps.

## Release Branch Layout

The `release` branch is expected to contain:

```text
manifestguard/
  latest/
    manifest.json
    manifestguard-<version>-<python-tag>-<abi-tag>-<platform>.whl
    release.json
    SHA256SUMS.txt
  <version>/
    manifest.json
    manifestguard-<version>-<python-tag>-<abi-tag>-<platform>.whl
    release.json
    SHA256SUMS.txt
```

`manifestguard/latest/manifest.json` is the default bootstrap entrypoint.
Version-specific commands such as `--payload-version 1.6.46` resolve to `manifestguard/1.6.46/manifest.json`.
Each `manifest.json` must include the wheel URL and SHA256 hash.

## Helper Script

Use `tools/publish_release_payload.ps1` while checked out to the `release` branch to copy a protected packet from the releaser output into the branch layout and generate both the `latest` and version-specific manifests.
