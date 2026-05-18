# Phase 49 Plan 01 — Summary

**Status:** complete
**Date:** 2026-05-18

## Files created

- `installer/companion/driver_manifest.json` — BlackHole + VB-CABLE manifest with placeholder SHA-256
- `installer/companion/fetch_drivers.sh` (Mac) — fetch + SHA-256 verify + install
- `installer/companion/fetch_drivers.ps1` (Win) — fetch + SHA-256 verify + install
- `installer/companion/audio_config.py` — routing + 48 kHz probe
- `installer/companion/onboarding_copy.json` — wizard strings (single source-of-truth)
- `installer/companion/README.md` — contract docs + AIza ban + SHA-256 discharge
- `installer/companion/__init__.py` — package marker
- `tests/install/test_driver_manifest_schema.py` — manifest validation (10 tests pass)
- `tests/install/test_audio_config.py` — probe + privacy/security gates (11 tests pass)

## Requirements satisfied

- INSTALL-04 (companion driver fetch + SHA-256 verify + vendor-signed installer)
- INSTALL-09 (routing automation) — scaffold + 48 kHz probe entry points
- INSTALL-10 (BlackHole 48 kHz post-install probe) — Mac CoreAudio probe + Win WASAPI probe stubs

## Verification

`pytest tests/install/test_audio_config.py tests/install/test_driver_manifest_schema.py` — 21/21 pass.

`installer/companion/fetch_drivers.sh --dry-run` exits 0 (returns `already_installed` on Kaan's BlackHole-equipped Mac, which is correct behavior).

## Kaan-action carry-forward

- **§INSTALL-COMPANION-SIGN** — SHA-256 placeholders in manifest pending SignPath cert discharge. Documented in `installer/companion/README.md` § "SHA-256 placeholder discharge".
