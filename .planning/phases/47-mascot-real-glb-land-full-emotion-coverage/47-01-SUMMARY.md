---
phase: 47-mascot-real-glb-land-full-emotion-coverage
plan: 01
subsystem: mascot
tags: [mascot, retarget-cli, mixamo, manifest]

requires:
  - phase: 43-rig-and-glb-discharge
    provides: 5-slot retarget CLI scaffold; MIXAMO-CLIP-SOURCES.md baseline
provides:
  - 28-slot retarget CLI (5 legacy + 3 base + 5 emotion + 5 anticipation + 10 reaction)
  - Per-family size bands (base 200-600 KB / emotion 300-900 KB / prep+react 400-1200 KB)
  - assets/mascot/source/MANIFEST.yaml schema as in-repo provenance log
  - MIXAMO-CLIP-SOURCES.md extended with 18 new selection-guidance rows + per-family aesthetic guardrails
  - .gitignore rule for Mixamo source .fbx (Adobe-account license; no redistribution)
affects: [47-02, 47-04, 47-05, 47-06, MASCOT-02, VIS-04-discharge]

tech-stack:
  added: []
  patterns:
    - SLOT_FAMILIES taxonomy as single source of truth for slot-to-family routing
    - Manifest-as-audit-trail; raw assets gitignored, provenance committed

key-files:
  created:
    - assets/mascot/source/MANIFEST.yaml
    - tests/mascot/__init__.py
    - tests/mascot/test_retarget_cli_slots.py
  modified:
    - scripts/mascot/retarget_to_neon_rebel.py
    - scripts/mascot/MIXAMO-CLIP-SOURCES.md
    - .gitignore

key-decisions:
  - "SLOT_FAMILIES dict keyed by family with slots[] + size_band_kb tuple — declarative, testable"
  - "anticipation family adds NEW prep_kick/prep_breakdown/prep_drop/prep_layer/prep_mix slots, kept disjoint from legacy_prep"
  - "Source .fbx files gitignored; MANIFEST.yaml is the in-repo audit trail (Mixamo Adobe-account license)"

patterns-established:
  - "SLOT_FAMILIES contract: family -> {slots: [...], size_band_kb: (min, max)} — referenced by bundle gate via prefix routing"
  - "Per-family size bands derived from clip complexity (looping baseline = tightest, reaction one-shots = loosest)"

requirements-completed:
  - MASCOT-02

duration: 8min
completed: 2026-05-18
---

# Phase 47, Plan 01: Retarget CLI 28-Slot Extension Summary

**Extended the Phase 43-05 retarget CLI from 5 to 28 slots across 5 families with per-family size bands, plus the assets/mascot/source/MANIFEST.yaml provenance schema and MIXAMO-CLIP-SOURCES.md selection guidance for the eventual §VIS-04 discharge.**

## Performance

- **Duration:** 8 min (resume-from-stalled-state)
- **Tasks:** 4
- **Files modified:** 6
- **Tests added:** 9 (test_retarget_cli_slots.py)

## Accomplishments

- SLOT_FAMILIES dict in `scripts/mascot/retarget_to_neon_rebel.py` ships 28 slots across 5 families: legacy_prep (5), base (3), emotion (5), anticipation (5), reaction (10).
- Per-family size bands locked: base 200-600 KB, emotion 300-900 KB, anticipation+reaction 400-1200 KB (matches the legacy_prep band).
- `--slot` argparse choices expanded to all 28 entries; new `--slot-family` flag added for batch retargeting an entire family.
- Post-retarget step appends a YAML row to assets/mascot/source/MANIFEST.yaml capturing `{slot, mixamo_search_term, downloaded_at_iso, sha256_source, draco_level, output_bytes, status}`.
- MIXAMO-CLIP-SOURCES.md extended to 206 lines with 4 new family sections + per-family aesthetic guardrails citing project_visual_direction_cdj_whisper.
- `.gitignore` block added for `assets/mascot/source/*.fbx` + `*.glb` with MANIFEST.yaml allowlisted.
- 9 pytest smoke tests confirm: 5 families, 28 slots total, per-family counts, legacy_prep verbatim preservation, anticipation family disjoint from legacy_prep, react_hype_peak present, all 5 size bands match design.

## Files Created/Modified

- `scripts/mascot/retarget_to_neon_rebel.py` — SLOT_FAMILIES taxonomy + per-family band lookup + --slot-family batch flag + manifest append step
- `scripts/mascot/MIXAMO-CLIP-SOURCES.md` — 18 new selection-guidance rows across 4 family H2 sections; CDJ Whisper aesthetic guardrails per family
- `assets/mascot/source/MANIFEST.yaml` — schema_version 1, 28 placeholder rows
- `.gitignore` — Mixamo source-file allowlist rule
- `tests/mascot/__init__.py` — package marker
- `tests/mascot/test_retarget_cli_slots.py` — 9 static-import smoke tests

## Decisions Made

- Kept legacy_prep family intact (Phase 22-02 placeholders preserved verbatim) instead of merging into the new anticipation family — preserves the Phase 43-05 contract while Phase 47 adds the event-class-specific prep_kick/prep_breakdown/etc. slots.
- Manifest schema uses `status: placeholder | retargeted` instead of separate file-exists check — gives Kaan a single auditable signal per slot.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

- Plan 47-02 (pools.ts + emotion.ts + reaction.ts + anticipation.ts) can lift the 28-slot taxonomy directly.
- Plan 47-04 (bundle gate per-family extension) reads SLOT_FAMILIES bands via bash prefix routing.
- Plan 47-05 (placeholder GLBs) populates the 23 new slot paths.

---
*Phase: 47-mascot-real-glb-land-full-emotion-coverage*
*Completed: 2026-05-18*
