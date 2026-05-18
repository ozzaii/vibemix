---
phase: 47-mascot-real-glb-land-full-emotion-coverage
plan: 08
subsystem: mascot
tags: [mascot, ci-grep-gate, anti-slop, poc-immutability]

requires:
  - phase: 47-mascot-real-glb-land-full-emotion-coverage
    plan: 03
    provides: event-coverage-matrix.test.ts
  - phase: 47-mascot-real-glb-land-full-emotion-coverage
    plan: 04
    provides: check_bundle_size.sh + check_manifest_complete.py
  - phase: 47-mascot-real-glb-land-full-emotion-coverage
    plan: 05
    provides: 23 placeholder GLBs
  - phase: 47-mascot-real-glb-land-full-emotion-coverage
    plan: 06
    provides: persona-smoke harness
  - phase: 47-mascot-real-glb-land-full-emotion-coverage
    plan: 07
    provides: README hero render scaffold
provides:
  - .github/workflows/mascot-tauri-only.yml mascot.html grep gate (closes Pitfall 4)
  - .github/workflows/mascot-audit.yml aggregated audit workflow (5 jobs)
  - scripts/mascot/check_no_ai_slop_phase47.py Phase 47 sibling anti-slop gate
  - tests/mascot/test_ci_grep_gates.py CI gate emptiness assertions
affects: [MASCOT-08, Phase 48 readiness]

tech-stack:
  added: []
  patterns:
    - Sibling-script pattern for anti-slop (preserves single-source-of-truth contract on launch-side)
    - Allowlist-aware grep gate (excludes POC-immutability tests that legitimately name mascot.html as protected)

key-files:
  created:
    - .github/workflows/mascot-tauri-only.yml
    - .github/workflows/mascot-audit.yml
    - scripts/mascot/check_no_ai_slop_phase47.py
    - tests/mascot/test_ci_grep_gates.py

key-decisions:
  - "Phase 47 anti-slop sibling script (scripts/mascot/check_no_ai_slop_phase47.py) instead of mid-execute extending scripts/launch/check_no_ai_slop.py — anti-stall discipline: do not redesign shared CI tooling mid-phase"
  - "Sibling re-imports AI_SLOP_BLOCKLIST from the canonical launch script — single source of truth preserved"
  - "Grep gate allowlist excludes 6 POC-immutability test files that legitimately name mascot.html as a PROTECTED file (opposite of the Pitfall 4 regression class)"

patterns-established:
  - "Sibling-script CI pattern: scope a shared tool's behavior to a new phase by creating phase-scoped wrappers that re-import constants from the canonical script"
  - "Allowlist-aware grep: bash + python both use the same regex/basename exclusion list — tests and CI gate stay synchronized"

requirements-completed:
  - MASCOT-08

duration: 8min
completed: 2026-05-18
---

# Phase 47, Plan 08: CI Grep Gates + Aggregated Audit Workflow Summary

**Wired the Phase 47 CI grep gates as the final acceptance signal: mascot.html grep gate closes Pitfall 4 with a 6-file POC-immutability allowlist, anti-slop coverage extends to all new Phase 47 docs via a sibling script that re-imports the canonical blocklist, and mascot-audit.yml aggregates all 5 Phase 47 audit jobs into a single CI signal.**

## Performance

- **Duration:** 8 min (resume-from-stalled-state)
- **Tasks:** 4
- **Files created:** 4
- **Tests added:** 7 (test_ci_grep_gates.py)

## Accomplishments

- `.github/workflows/mascot-tauri-only.yml` ships the Pitfall 4 closure: grep mascot.html across `tests/ e2e/ scripts/ci/` with a 6-file allowlist for POC-immutability tests (test_g5_poc_files_untouched.py, test_repo_scrub.py, test_pipeline.py, test_phase05_verification.py, test_no_api_key_surface.py, test_ci_grep_gates.py).
- `.github/workflows/mascot-audit.yml` aggregates 5 jobs: bundle-gate (continue-on-error: true until VIS-04 discharge), manifest-completeness, anti-slop, mascot-tauri-only-grep, event-coverage (vitest).
- `scripts/mascot/check_no_ai_slop_phase47.py` sibling anti-slop gate: scopes the 16-token blocklist + `\bdeeply\s+\w+` regex to 7 Phase 47 artifact paths. Re-imports `AI_SLOP_BLOCKLIST` from the canonical `scripts/launch/check_no_ai_slop.py` for single-source-of-truth preservation.
- `tests/mascot/test_ci_grep_gates.py` ships 7 tests asserting: no mascot.html in test/ci surface (with allowlist), mascot-tauri-only.yml exists, mascot-audit.yml exists, sibling anti-slop script exists + covers Phase 47 paths, canonical launch-side script untouched (still scoped to launch_copy/), sibling runs clean (exit 0), mascot.html easter-egg byte-identity invariant documented.

## Files Created/Modified

- `.github/workflows/mascot-tauri-only.yml` — Pitfall 4 grep gate workflow with allowlist
- `.github/workflows/mascot-audit.yml` — aggregated 5-job Phase 47 audit workflow
- `scripts/mascot/check_no_ai_slop_phase47.py` — Phase 47-scoped anti-slop gate (sibling pattern)
- `tests/mascot/test_ci_grep_gates.py` — 7 CI gate assertion tests

## Decisions Made

- **Sibling-script pattern** (per orchestrator anti-stall discipline): the canonical `scripts/launch/check_no_ai_slop.py` stays scoped to `scripts/dayzero/launch_copy/` per its CONTEXT §specifics single-source-of-truth contract. Extending the launch-side target list mid-execute would have broken the launch contract. The sibling script at `scripts/mascot/check_no_ai_slop_phase47.py` re-imports the blocklist from the launch script for single-source-of-truth preservation while scoping the gate to Phase 47 paths.
- **Grep allowlist over scope-restriction:** the plan called for a broad `grep -rn "mascot.html" tests/ e2e/ scripts/ci/`. Real run found 5 legitimate references in POC-immutability tests (Phase 37-06 byte-identity gates, Phase 5 verification, security scan). Allowlist captures the file basenames that legitimately name mascot.html as a PROTECTED file — the OPPOSITE of the Pitfall 4 regression class.
- `mascot-bundle-gate` job in `mascot-audit.yml` is `continue-on-error: true` until VIS-04 discharge: placeholder GLBs intentionally sub-band exit-2 is the documented expected-fail UX.

## Deviations from Plan

**1. [Anti-stall — Compatibility] Sibling anti-slop script instead of extending launch-side**
- **Found during:** Task 2 (extend scripts/launch/check_no_ai_slop.py target list)
- **Issue:** Plan called for extending the launch-side `check_no_ai_slop.py` with Phase 47 target paths. The script's contract is narrowly scoped to `scripts/dayzero/launch_copy/` per its CONTEXT §specifics single-source-of-truth declaration; in-place extension would have broken the launch contract.
- **Fix:** Created `scripts/mascot/check_no_ai_slop_phase47.py` as a sibling script that re-imports `AI_SLOP_BLOCKLIST` from the canonical launch script and scopes the gate to Phase 47 artifact paths.
- **Files modified:** `scripts/mascot/check_no_ai_slop_phase47.py` (new), `.github/workflows/mascot-audit.yml` (invokes the sibling).
- **Verification:** Both `scripts/launch/check_no_ai_slop.py` (still scoped to `scripts/dayzero/launch_copy/`) AND the new sibling exit 0; `test_ci_grep_gates.py` confirms both contracts hold.

**2. [Quality — Compatibility] Grep gate allowlist for POC-immutability tests**
- **Found during:** Task 4 (run test_ci_grep_gates.py)
- **Issue:** Plan's `grep -rn "mascot.html" tests/ e2e/ scripts/ci/` matched 6 files that legitimately name mascot.html as a PROTECTED file (Phase 37-06 byte-identity gates, Phase 5 verification, security HTML scan, plus this very test file in docstrings).
- **Fix:** Updated `.github/workflows/mascot-tauri-only.yml` + `.github/workflows/mascot-audit.yml` + `tests/mascot/test_ci_grep_gates.py` to filter the grep output through a 6-basename allowlist before raising a Pitfall 4 violation.
- **Files modified:** 3 (workflow + workflow + test).
- **Verification:** `test_ci_grep_gates.py` 7 tests green; allowlist documented inline.

**Total deviations:** 2 auto-fixed (both anti-stall / compatibility). **Impact on plan:** Preserves the launch-side single-source-of-truth contract AND closes Pitfall 4 without breaking pre-existing POC-immutability gates. No scope creep.

## Issues Encountered

None — both deviations resolved via documented anti-stall patterns.

## Next Phase Readiness

- Phase 47 engineering-green: 8 plans / 8 SUMMARY.md ✓.
- Pending Kaan-action: §VIS-04 Mixamo retargets (28 .fbx files via the discharge CLI). Bundle gate will flip from exit 2 → exit 0 on discharge.
- Phase 48 (OPP) depends on Phase 46 schema, not Phase 47 — ready to dispatch.

---
*Phase: 47-mascot-real-glb-land-full-emotion-coverage*
*Completed: 2026-05-18*
