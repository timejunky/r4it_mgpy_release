# r4it_mgpy_release release branch

This branch contains the protected ManifestGuard payload only.

Layout:

```text
manifestguard/latest/
  manifest.json
  manifestguard-1.6.25-py3-none-any.whl
  SHA256SUMS.txt
```

The public bootstrap package downloads `manifest.json` from this branch and then installs the referenced protected wheel.