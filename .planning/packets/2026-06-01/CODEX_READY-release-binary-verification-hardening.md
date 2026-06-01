# CODEX_READY: Release Binary Verification Hardening

Date: 2026-06-01
Author: Codex
Status: LAND packet, release-verifier hardening slice
Package: Package 13C - Release Binary Verification Hardening

## Decision

LAND this slice as `fix(dist): harden release binary verification`.

This package hardens the post-sign artifact scanner so it remains strict for
real branded secret shapes while avoiding false positives from generated
code-signature resources, hash manifests, native blobs, and embedded `sk-`
substrings inside longer symbols.

## Files

- `scripts/dist/verify_binary.py`
- `tests/dist/test_verify_binary.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`
- `.planning/packets/2026-06-01/INDEX.md`
- `.planning/packets/2026-06-01/CODEX_READY-release-binary-verification-hardening.md`

## What Changed

- OpenAI `sk-` detection now requires token boundaries and a bounded token
  length, preventing native-symbol false positives while still detecting
  standalone secret-looking keys.
- The high-noise generic 39-character heuristic now runs only on source/config
  file types where it has useful signal.
- Generated code-signature resources and package hash manifests are skipped for
  generic scanning.
- Strict branded patterns still scan native blobs and source/config payloads.

## Evidence

Unit tests:

```text
uv run pytest -q tests/dist/test_verify_binary.py
25 passed in 0.16s
```

Lint:

```text
uv run ruff check scripts/dist/verify_binary.py tests/dist/test_verify_binary.py
All checks passed!
```

Current rebuilt macOS app verifier:

```text
uv run python -m scripts.dist.verify_binary tauri/src-tauri/target/release/bundle/macos/vibemix.app --report /tmp/vibemix-codex-checks/verify-report-current-macos-app.json
[verify_binary] scanned=407 hits=0 report=/tmp/vibemix-codex-checks/verify-report-current-macos-app.json
```

Report:

```json
{
  "binary_count": 407,
  "flagged_strings": [],
  "hits": [],
  "scanned": 407,
  "status": "clean"
}
```

Whitespace:

```text
git diff --check -- scripts/dist/verify_binary.py tests/dist/test_verify_binary.py
```

## Boundaries

- No broad staging, no commit, and no product-release claim.
- This proves the verifier logic and current local rebuilt `.app` scan. It does
  not make the later signed/notarized release artifact current.
- The `/tmp` report is scratch evidence; this packet records the durable result.

## Next Required Proof

Rerun the verifier after the final settled source state is rebuilt and signed,
then keep it in the release pipeline after signing/notarization so generated
signature resources are part of the scanned bundle shape without causing noisy
generic false positives.
