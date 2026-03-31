# r4it_mgpy_release release branch

This branch contains the protected ManifestGuard payload only.

Layout:

```text
manifestguard/
  latest/
    manifest.json
    manifestguard-1.6.26-py3-none-any.whl
    SHA256SUMS.txt
  1.6.25/
    manifest.json
    manifestguard-1.6.25-py3-none-any.whl
    SHA256SUMS.txt
  1.6.26/
    manifest.json
    manifestguard-1.6.26-py3-none-any.whl
    SHA256SUMS.txt
```

The public bootstrap package downloads `manifestguard/latest/manifest.json` by default and can resolve a version-specific manifest such as `manifestguard/1.6.26/manifest.json` when the user selects a payload version.