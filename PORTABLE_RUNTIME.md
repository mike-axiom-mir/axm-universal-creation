# Portable runtime capsule

The repository's normal `PYTHONPATH=src` commands operate on the active checkout. The portable runtime builder creates a separate, reviewable ZIP that can run the same body after extraction without an editable checkout, package registry, account, cloud service, or network connection.

## Build and verify

From the repository root with Python 3.11 or newer:

```bash
PYTHONPATH=src python -m axm_uc.portable_cli build \
  --output /tmp/axm-universal-creation-runtime-v0.1.0.zip

PYTHONPATH=src python -m axm_uc.portable_cli verify \
  /tmp/axm-universal-creation-runtime-v0.1.0.zip
```

The build command writes only the requested ZIP and verifies it before returning `PASS`. It does not publish, install, adopt, merge, or modify the source machine. Rebuilding the same source bytes with the same declared source revision produces the same archive SHA-256.

The installed wheel exposes the same verifier as `axm-uc-portable verify`. Building still requires an explicit Universal Creation source body because the ordinary Python wheel does not carry the machine's multi-thousand-file canonical registry and asset body.

## Consume

Verify the ZIP before extraction. Then extract it and run its path-independent launcher from any working directory:

```bash
python /path/to/extracted/runtime/run.py inspect
python /path/to/extracted/runtime/run.py organ-census --limit 5
python /path/to/extracted/runtime/run.py assets
```

The launcher pins `--root` to its own extracted body. Creation commands therefore write only inside that extracted copy unless an explicit request selects another permitted output path.

## Integrity and provenance

`portable-runtime.manifest.json` contains:

- the exact source repository and observed or caller-declared revision;
- a deterministic digest over every declared file record;
- each file's normalized path, byte count, mode, and SHA-256;
- the exact `LICENSE` and `THIRD_PARTY.json` paths, with the third-party ledger hash;
- the required launcher and minimum Python version;
- an explicit no-adoption, no-source-change, no-CANON authority boundary.

The builder admits only Git-tracked files from its explicit runtime allowlist, so unrelated untracked workspace files cannot silently enter the capsule. Verification rejects duplicate or undeclared entries, missing runtime roots, hash/size/mode drift, path traversal, backslash paths, symlinks, unexpected compression or timestamps, non-exact manifests, and size/count limit violations. ZIP entries use fixed timestamps and stored bytes so container output does not depend on compressor behavior.

SHA-256 proves byte consistency against the manifest or a caller-pinned archive digest. It does not prove authorship, safety, semantic quality, or that a revision label came from a trusted signer. Verify the archive digest through a separately trusted channel when deliberate substitution is in scope.

## Included boundary

The capsule includes the Python runtime, canonical registry materialization, live/candidate capability records, executable-organ and Asset Atom libraries, current state, examples, creation/output roots, source/license ledgers, local assets, and runtime tools. It excludes Git history, CI configuration, tests, build debris, and operator-only collaboration files.

This proves portable local execution of the current Universal Creation body. It does not publish a package, choose a final brain architecture, admit candidates, or claim that every descriptive organ is executable.
