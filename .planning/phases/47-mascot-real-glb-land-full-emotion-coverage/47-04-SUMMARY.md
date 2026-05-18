---
phase: 47-mascot-real-glb-land-full-emotion-coverage
plan: 04
subsystem: mascot
tags: [mascot, bundle-gate, manifest, draco]

requires:
  - phase: 47-mascot-real-glb-land-full-emotion-coverage
    plan: 01
    provides: SLOT_FAMILIES + assets/mascot/source/MANIFEST.yaml
provides:
  - check_bundle_size.sh extended to per-family Tier 2 bands via prefix routing
  - check_manifest_complete.py manifest <-> on-disk parity gate
  - docs/mascot/BUNDLE-DECISION.md audit trail (draco-first / 30 MB bump fallback)
affects: [47-08, MASCOT-03]

tech-stack:
  added: []
  patterns:
    - Bash case-statement prefix routing for per-family size bands
    - Expected-fail UX preserved: placeholders sub-band until VIS-04 discharge

key-files:
  created:
    - scripts/mascot/check_manifest_complete.py
    - docs/mascot/BUNDLE-DECISION.md
    - tests/mascot/test_bundle_gate_families.py
  modified:
    - scripts/mascot/check_bundle_size.sh
    - tests/mascot/test_bundle_size_cap.py

key-decisions:
  - "Draco-retune-first / 30 MB bump fallback documented in BUNDLE-DECISION.md as auditable record"
  - "Expected-fail UX preserved — placeholder GLBs sub-band exit non-zero until VIS-04 discharge"
  - "Phase 43 test_bundle_size_cap.py updated to match Phase 47 contract — newer phase wins per project convention"

patterns-established:
  - "Per-family bash gate uses prefix routing (base/emotion/prep/react) to band lookup — single source of truth in retarget_to_neon_rebel.py SLOT_FAMILIES"
  - "Bundle gate exit 2 = Tier 2 placeholder fail (NOT a CI break per docs/mascot/BUNDLE-DECISION.md continue-on-error)"

requirements-completed:
  - MASCOT-03

duration: 6min
completed: 2026-05-18
---

# Phase 47, Plan 04: Bundle Gate Per-Family Extension Summary

**Extended check_bundle_size.sh Tier 2 to per-family size bands via bash prefix routing, added manifest <-> on-disk parity gate, and documented the draco-first / 30 MB bump fallback decision in BUNDLE-DECISION.md.**

## Performance

- **Duration:** 6 min (resume-from-stalled-state)
- **Tasks:** 4
- **Files modified:** 5
- **Tests added:** 9 (test_bundle_gate_families.py)

## Accomplishments

- `check_bundle_size.sh` Tier 2 rewritten with `band_for_prefix()` case statement: `base) 200 600` / `emotion) 300 900` / `prep) 400 1200` / `react) 400 1200`.
- For-loop iterates `base_*.glb emotion_*.glb prep_*.glb react_*.glb`; each match routed to its band; outside-band entries reported with exact byte offset.
- `check_manifest_complete.py` cross-references `assets/mascot/source/MANIFEST.yaml` against on-disk `tauri/ui/assets/mascot/animations/*.glb` — exits 0 when 28 manifest rows match 28 family-prefix GLBs.
- `docs/mascot/BUNDLE-DECISION.md` documents the draco-first strategy + 30 MB bump fallback + 4-family cumulative ceiling table showing ~23.2 MB target with ~1.8 MB headroom under the 25 MB cap.
- Anti-slop blocklist clean on BUNDLE-DECISION.md (16 tokens + `\bdeeply\s+\w+` regex).
- Pre-existing `test_bundle_size_cap.py` (Phase 43) updated: replaced the `"400 * 1024"` literal-string assertion (broken by Phase 47's `(( min_kb * 1024 ))` refactor) with the new contract assertion `'prep) echo "400 1200"'`.

## Files Created/Modified

- `scripts/mascot/check_bundle_size.sh` — full Tier 2 rewrite with per-family prefix routing
- `scripts/mascot/check_manifest_complete.py` — manifest <-> inventory parity gate (executable)
- `docs/mascot/BUNDLE-DECISION.md` — audit trail for the draco-first decision
- `tests/mascot/test_bundle_gate_families.py` — 9 static-string tests pin the band routing
- `tests/mascot/test_bundle_size_cap.py` — Phase 43 contract test updated to match Phase 47 wrapper

## Decisions Made

- Kept legacy_prep family routed via the same `prep) 400 1200` case (no need for a separate `legacy_prep) ...` branch — the band is identical to anticipation).
- Manifest check exits 0 if `status: placeholder` rows lack on-disk GLBs (placeholders only flag drift when marked `status: retargeted`).

## Deviations from Plan

**1. [Quality - Compatibility] Updated Phase 43 test_bundle_size_cap.py**
- **Found during:** Task 1 (rewrite Tier 2 block)
- **Issue:** Phase 43 test asserted `"400 * 1024"` literal string in the wrapper body; Phase 47 refactor uses `(( min_kb * 1024 ))` with `min_kb=400` instead. Test fails after refactor.
- **Fix:** Updated the Phase 43 test's `test_per_clip_band_constants_match_context` to assert `'prep) echo "400 1200"'` instead — the new canonical contract pinned by the case statement.
- **Files modified:** `tests/mascot/test_bundle_size_cap.py`
- **Verification:** Both `test_bundle_size_cap.py` (6 tests) AND `test_bundle_gate_families.py` (9 tests) green.

**Total deviations:** 1 auto-fixed (test contract update). **Impact on plan:** Aligns Phase 43 test with Phase 47 contract per project convention (newer phase wins). No scope creep.

## Issues Encountered

None.

## Next Phase Readiness

- Plan 47-05 (placeholder GLBs) ships 23 stub GLBs that intentionally fail the new band check — that's the documented expected-fail UX.
- Plan 47-08 (CI audit aggregation) wires `check_bundle_size.sh` as a `continue-on-error: true` job in mascot-audit.yml — placeholder fail is signal, not failure.

---
*Phase: 47-mascot-real-glb-land-full-emotion-coverage*
*Completed: 2026-05-18*
