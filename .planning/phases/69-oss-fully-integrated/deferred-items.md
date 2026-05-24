# Phase 69 Deferred Items

## test_readme_feature_matrix_sync.py — 2 failures (pre-existing, NOT caused by 69-01)

- **Discovered during:** 69-01 final baseline run (4150 passed / 2 failed / 26 skipped / 4 xpassed)
- **Failures:**
  1. `test_readme_feature_matrix_in_sync` — `scripts/launch/sync_feature_matrix.py --check` exits 1
  2. `test_feature_matrix_includes_all_completed_phases` — Phase 68 missing from README AUTO-GEN block
- **Verified pre-existing:** Both failures reproduce on `HEAD~4` (pre-69-01) — the gap is Phase 68's wrap-up
  (the AUTO-GEN feature-matrix block was never regenerated when 68P05 closed).
- **Out of scope for 69-01:** OSS-01 covers OSS docs presence only; this is a Phase 68 SHIPPED-but-not-pushed-to-README drift.
- **Recommended fix path:** `python scripts/launch/sync_feature_matrix.py --write` in a follow-up
  doc-only commit (or fold into the Phase 68 Wave 4 ENGINEERING-COMPLETE checklist if not done).
- **Decision:** Do NOT auto-fix in 69-01 (scope boundary). Park here; the next plan that touches
  README's feature-matrix block (likely 69-04 §SHIP-V4 wiring or 69-05 packaging-scaffolds when
  they update release-process.md) should run the sync script as part of their pre-commit gate.
