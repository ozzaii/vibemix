---
phase: 47-mascot-real-glb-land-full-emotion-coverage
plan: 05
subsystem: mascot
tags: [mascot, placeholder, glb, manifest]

requires:
  - phase: 47-mascot-real-glb-land-full-emotion-coverage
    plan: 02
    provides: pools.ts + layer files
  - phase: 47-mascot-real-glb-land-full-emotion-coverage
    plan: 04
    provides: per-family bundle gate
provides:
  - 23 placeholder GLB stubs at Phase 47 slot paths (alias existing Phase 22-02 content)
  - tauri/ui/assets/mascot/manifest.json extended with 23 new animations[] entries
  - scripts/mascot/seed_phase_47_placeholders.py reseed-on-demand helper
  - PLACEHOLDER_NOTE.md documents the alias/discharge contract
affects: [47-06, 47-07, MASCOT-01]

tech-stack:
  added: []
  patterns:
    - Placeholder-as-alias pattern (file copy from Phase 22-02 prep_settle.glb)
    - Expected-fail UX: placeholders below per-family floor signal pending discharge

key-files:
  created:
    - tauri/ui/assets/mascot/animations/base_idle.glb (and 22 siblings — 23 total Phase 47 stubs)
    - scripts/mascot/seed_phase_47_placeholders.py
    - tests/mascot/test_manifest_json_phase_47.py
  modified:
    - tauri/ui/assets/mascot/manifest.json
    - tauri/ui/assets/mascot/animations/PLACEHOLDER_NOTE.md

key-decisions:
  - "Placeholders alias existing Phase 22-02 content (prep_settle.glb body copy) — no new asset bytes, just file copies"
  - "Bundle gate's sub-band exit-2 IS the operator-facing reminder that VIS-04 discharge is pending"
  - "manifest.json animations[] entries land WITHOUT modification to the existing 5 legacy entries — additive only"

patterns-established:
  - "23 new manifest.json entries follow the existing schema: { file, clip, states }"
  - "Placeholder seeding helper at scripts/mascot/seed_phase_47_placeholders.py — invocable repeatedly"

requirements-completed:
  - MASCOT-01

duration: 7min
completed: 2026-05-18
---

# Phase 47, Plan 05: 23 Placeholder GLB Stubs + Manifest Extension Summary

**Shipped 23 placeholder GLB stubs at the Phase 47 slot paths (alias Phase 22-02 prep_settle.glb body) so the asset loader does not 404 in dev before §VIS-04 discharge, and extended tauri/ui/assets/mascot/manifest.json with 23 corresponding animations[] entries.**

## Performance

- **Duration:** 7 min (resume-from-stalled-state)
- **Tasks:** 4
- **Files modified:** 26 (23 GLB stubs + 3 source files)
- **Tests added:** 6 (test_manifest_json_phase_47.py)

## Accomplishments

- 23 new placeholder GLBs in `tauri/ui/assets/mascot/animations/`: 3 base_*, 5 emotion_*, 5 new prep_* (kick/breakdown/drop/layer/mix), 10 react_*.
- Each placeholder is a copy of `prep_settle.glb` (~44 KB) — same content, new file path matching the slot stem.
- `manifest.json` animations[] extended with 23 new entries following the existing `{file, clip, states}` schema; existing 5 legacy entries preserved verbatim.
- `scripts/mascot/seed_phase_47_placeholders.py` ships as the reseed-on-demand helper (idempotent — checks existing GLBs before copy).
- `PLACEHOLDER_NOTE.md` updated to document the Phase 47 alias contract.
- 6 pytest tests pin: manifest schema valid JSON, 23 new animations entries, every Phase 47 family slot in manifest, no legacy entry mutated.

## Files Created/Modified

- `tauri/ui/assets/mascot/animations/{base_idle,base_breathe,base_sway,emotion_joy,emotion_trust,emotion_surprise,emotion_anticipation,emotion_focus,prep_kick,prep_breakdown,prep_drop,prep_layer,prep_mix,react_kick_swap,react_sub_layer,react_breakdown,react_reentry,react_phrase_boundary,react_distortion_climb,react_acid_line,react_mix_in,react_mix_out,react_hype_peak}.glb` — 23 stubs
- `tauri/ui/assets/mascot/manifest.json` — 23 new animations[] entries
- `tauri/ui/assets/mascot/animations/PLACEHOLDER_NOTE.md` — Phase 47 discharge contract documented
- `scripts/mascot/seed_phase_47_placeholders.py` — idempotent reseed helper
- `tests/mascot/test_manifest_json_phase_47.py` — 6 manifest-shape tests

## Decisions Made

- Aliased placeholders to `prep_settle.glb` instead of generating distinct fake animations — keeps file bytes minimal and ensures the 44 KB sub-band signal is the SAME for every slot (clean diff signal on discharge).
- Manifest entries use the same minimal `{file, clip, states}` shape as the legacy 5 — no Phase 47-specific schema additions.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

- Plan 47-06 (persona-smoke-harness) loads every clip name via the manifest — all 28 paths resolve.
- Plan 47-07 (README hero render) reads from `react_hype_peak.glb` placeholder (stays a placeholder until discharge).
- Plan 47-08 (CI audit) bundle gate exits 2 on these placeholders by design.

---
*Phase: 47-mascot-real-glb-land-full-emotion-coverage*
*Completed: 2026-05-18*
