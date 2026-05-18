---
phase: 47-mascot-real-glb-land-full-emotion-coverage
plan: 02
subsystem: mascot
tags: [mascot, pools, layers, emotion, reaction, anticipation, vitest]

requires:
  - phase: 47-mascot-real-glb-land-full-emotion-coverage
    plan: 01
    provides: 28-slot SLOT_FAMILIES taxonomy + MIXAMO-CLIP-SOURCES guidance
provides:
  - pools.ts extended with PHASE_47_BASE_POOL / PHASE_47_EMOTION_POOL / PHASE_47_ANTICIPATION_POOL / PHASE_47_REACTION_POOL
  - layers/phase47-emotion.ts (sibling to phase 31 emotion.ts, 5-emotion taxonomy)
  - layers/phase47-reaction.ts (sibling reaction.ts, 10-clip taxonomy)
  - layers/anticipation.ts (NEW layer for 5 new prep_kick/breakdown/drop/layer/mix slots)
  - types.ts extended with EmotionClip / ReactionClip / AnticipationClip type unions
affects: [47-03, 47-05, 47-06]

tech-stack:
  added: []
  patterns:
    - Sibling-layer-file pattern preserves existing Phase 31/43 byte contracts while adding Phase 47 taxonomies
    - PriorityStack composition stays additive — new layers compose alongside existing layers

key-files:
  created:
    - tauri/ui/src/mascot/layers/phase47-emotion.ts
    - tauri/ui/src/mascot/layers/phase47-reaction.ts
    - tauri/ui/src/mascot/layers/anticipation.ts
    - tauri/ui/src/mascot/layers/anticipation.test.ts
    - tauri/ui/src/mascot/__tests__/pools-extension.test.ts
  modified:
    - tauri/ui/src/mascot/pools.ts
    - tauri/ui/src/mascot/types.ts

key-decisions:
  - "Sibling files (phase47-emotion.ts / phase47-reaction.ts) instead of editing existing emotion.ts/reaction.ts — preserves the Phase 31/43 MOOD_POOLS + KIND_TO_SLOT verbatim test contract"
  - "Anticipation layer is BRAND NEW (no Phase 31 equivalent); priority 70 between base (50) and reaction (80)"
  - "Type unions stay narrow per family — EmotionClip = 5 Phase 47 stems, ReactionClip = 10 stems, AnticipationClip = 5 new prep_* stems"

patterns-established:
  - "Layer priority ladder: base 50 < emotion 60 < anticipation 70 < reaction 80 (Phase 47 ordering)"
  - "Pool constants prefixed PHASE_47_* to disambiguate from the legacy Phase 31 / Phase 43 pools"

requirements-completed:
  - MASCOT-04

duration: 12min
completed: 2026-05-18
---

# Phase 47, Plan 02: pools.ts + Layer Refactor Summary

**Added Phase 47 pools (base / emotion / anticipation / reaction) and three layer files (phase47-emotion, phase47-reaction, anticipation) preserving the existing Phase 31/43 byte contracts via sibling-file pattern.**

## Performance

- **Duration:** 12 min (resume-from-stalled-state)
- **Tasks:** 7
- **Files modified:** 7
- **Vitest tests:** 16 new (pools-extension 8, anticipation.test 8)

## Accomplishments

- `pools.ts` extended with 4 PHASE_47_* pool constants — base, emotion, anticipation, reaction — each maps slot stem to clip metadata.
- Existing Phase 31/43 MOOD_POOLS + KIND_TO_SLOT preserved byte-identical (Phase 43 § VIS-05 contract pinned by `pools.test.ts` greps).
- `layers/phase47-emotion.ts` ships the 5-emotion taxonomy (joy/trust/surprise/anticipation/focus) at priority 60.
- `layers/phase47-reaction.ts` ships the 10-clip reaction taxonomy at priority 80.
- `layers/anticipation.ts` (NEW) ships the 5 event-class-specific prep clips at priority 70.
- `types.ts` extended with EmotionClip / ReactionClip / AnticipationClip + PHASE_47_EMOTIONS / PHASE_47_REACTIONS / PHASE_47_ANTICIPATIONS type-narrow tuples.
- Vitest green: 27 test files / 177 tests pass; new pools-extension test (8) + anticipation.test (8) + event-coverage-matrix (14, Plan 47-03 file but landed here for module coupling).

## Files Created/Modified

- `tauri/ui/src/mascot/pools.ts` — 4 new pool constants, additive
- `tauri/ui/src/mascot/types.ts` — type unions + tuple constants for the 3 new taxonomies
- `tauri/ui/src/mascot/layers/phase47-emotion.ts` — sibling emotion layer (5-emotion taxonomy)
- `tauri/ui/src/mascot/layers/phase47-reaction.ts` — sibling reaction layer (10-clip taxonomy)
- `tauri/ui/src/mascot/layers/anticipation.ts` — new layer (5 prep_kick/breakdown/drop/layer/mix slots)
- `tauri/ui/src/mascot/layers/anticipation.test.ts` — 8 unit tests
- `tauri/ui/src/mascot/__tests__/pools-extension.test.ts` — 8 unit tests

## Decisions Made

- Sibling-file pattern (`phase47-emotion.ts` next to existing `emotion.ts`) instead of editing existing files — the Phase 31 emotion.ts ships the v2.0 4-emotion vocabulary which is referenced by external tests; preserving it byte-identical avoids cascading regressions.
- Anticipation layer priority 70 sits between emotion (60) and reaction (80) — anticipation outranks emotion (event-class signal stronger than mood) but yields to reaction (active event still wins).

## Deviations from Plan

**1. [Quality - Compatibility] Sibling layer files instead of in-place edit**
- **Found during:** Task 3 (refresh emotion.ts to 5-clip taxonomy)
- **Issue:** Plan called for editing emotion.ts in place. The existing file ships a 4-emotion vocabulary (neutral/focused/hyped/concerned) referenced by `pools.test.ts` via verbatim grep — in-place edit breaks the Phase 31/43 contract.
- **Fix:** Created `phase47-emotion.ts` as a sibling layer; existing `emotion.ts` preserved byte-identical.
- **Files modified:** none in-place; only new files added.
- **Verification:** `pools.test.ts` still green; new `pools-extension.test.ts` covers the Phase 47 additions.

**Total deviations:** 1 auto-fixed (compatibility). **Impact on plan:** Preserves the Phase 31/43 contract while delivering Plan 47-02's Phase 47 taxonomies. No scope creep.

## Issues Encountered

None.

## Next Phase Readiness

- Plan 47-03 (event-dispatcher EVENT_LAYER_PRIORITY_MAP) can route events to the new Phase 47 layers via the new pool constants.
- Plan 47-06 (persona-smoke-harness) cycles through every new clip name via the new pools.

---
*Phase: 47-mascot-real-glb-land-full-emotion-coverage*
*Completed: 2026-05-18*
