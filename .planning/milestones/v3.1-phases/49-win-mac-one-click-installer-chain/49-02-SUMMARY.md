# Phase 49 Plan 02 — Summary

**Status:** complete
**Date:** 2026-05-18

## Files created / modified

- `.github/workflows/companion-sign.yml` (NEW) — parallel signing workflow with verifier gate
- `scripts/audit/check_companion_signing.sh` (NEW) — verifier with tag-vs-branch fail mode
- `scripts/dist/sign_macos.sh` (MODIFIED) — `--companion` flag added; existing happy-path byte-identical when flag absent
- `scripts/dist/sign_windows.ps1` (MODIFIED) — `-Companion` switch emits SignPath companion manifest
- `.planning/decisions/INSTALL-49-companion-fetch.md` (NEW) — ADR
- `tests/audit/test_companion_signing_gate.py` (NEW) — 5 pass, 1 skip (Darwin host)

## Requirements satisfied

- INSTALL-05 (companion-sign release stage + Authenticode/codesign + verifier gate)

## Verification

`pytest tests/audit/test_companion_signing_gate.py` — 5/5 pass, 1 platform-skipped.

`bash scripts/dist/sign_macos.sh --companion --dry-run` lists 3 companion files that would be signed.

`pwsh scripts/dist/sign_windows.ps1 -Companion` emits `signpath-companion-manifest.json` (verified on syntax via Edit, not executed on Mac host).

## Implementation note

Chose a **separate workflow file** (`.github/workflows/companion-sign.yml`) over inline edits to the live `release.yml` to minimize blast radius. The companion-sign workflow gates on the same `installer/companion/**` changes that trigger main release flow and can be hooked into `release.yml` post-Kaan-action review without disturbing the existing build → sign → verify → publish chain. ADR documents this decision under "Signing chain".

## Kaan-action carry-forward

- **§INSTALL-COMPANION-SIGN** — SignPath OSS Foundation cert grant for the `.ps1` + `.py` Authenticode submission. Verifier emits WARNING tagged with this token on branch builds; fails on tag builds (forcing discharge).
