# Phase 49 Plan 06 — Summary

**Status:** complete
**Date:** 2026-05-18

## Files created / modified

- `docs/internal/copy-substitutions.md` (NEW) — vocabulary substitution dictionary (20+ rows)
- `scripts/audit/check_no_slop_install.py` (NEW) — sibling-script importing AI_SLOP_BLOCKLIST from parent
- `installer/companion/uninstall.sh` (NEW) — Mac preserve-default uninstall
- `installer/companion/uninstall.ps1` (NEW) — Win preserve-default uninstall
- `tauri/ui/src/wizard/uninstall-dialog.ts` (NEW) — confirmation dialog with clean opt-in
- `tests/audit/test_no_slop_install.py` (NEW) — 8 tests pass
- `tests/install/test_uninstall_preserve.py` (NEW) — 6 tests pass

## Requirements satisfied

- INSTALL-03 (anti-slop blocklist on installer/wizard surface, sibling-script pattern preserved)
- INSTALL-07 (uninstall preserves user library + debriefs + ghost_calibration unless --clean opt-in)

## Verification

`pytest tests/audit/test_no_slop_install.py tests/install/test_uninstall_preserve.py` — 14/14 pass.

`python3 -m scripts.audit.check_no_slop_install` — OK, 10 Phase 49 targets clean (no inline forbidden tokens).

Parent script `scripts/launch/check_no_ai_slop.py` pinned target paths UNCHANGED (sibling-pattern invariant verified by `test_parent_pinned_targets_unchanged`).

## Full Phase 49 test suite

`pytest tests/install/ tests/audit/test_companion_signing_gate.py tests/audit/test_no_slop_install.py tests/wizard/ tests/dist/test_60s_gate.py` — **68 passed, 1 platform-skipped**.
