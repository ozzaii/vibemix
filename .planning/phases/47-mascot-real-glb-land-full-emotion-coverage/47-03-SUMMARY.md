---
phase: 47-mascot-real-glb-land-full-emotion-coverage
plan: 03
subsystem: mascot
tags: [mascot, event-dispatcher, state-machine, vitest]

requires:
  - phase: 47-mascot-real-glb-land-full-emotion-coverage
    plan: 02
    provides: Phase 47 pools + layer files
provides:
  - EVENT_LAYER_PRIORITY_MAP declarative event-to-layer fanout map (15 events × 4 layers)
  - event-coverage-matrix.test.ts (14 unit tests, full coverage matrix)
affects: [47-06, 47-08, MASCOT-05]

tech-stack:
  added: []
  patterns:
    - Event class as TypeScript discriminated union (15 EventClass members)
    - Declarative fanout map (single source of truth for layer routing)

key-files:
  modified:
    - tauri/ui/src/mascot/event-dispatcher.ts
  created:
    - tauri/ui/src/mascot/__tests__/event-coverage-matrix.test.ts

key-decisions:
  - "EVENT_LAYER_PRIORITY_MAP appended to event-dispatcher.ts as a Phase 47 § marker — preserves existing dispatcher logic byte-identical"
  - "KAAN_SPOKE intentionally empty fanout — talk-block rule per Phase 13 STATE_PRIORITY (mascot stays on Base during user speech)"
  - "15 event classes: 7 from v2.0 EventDetector + 8 from Phase 30 Hard Tek detectors"

patterns-established:
  - "Event-to-layer fanout via single map const, not scattered if/switch — testable, inspectable, change-trivial"

requirements-completed:
  - MASCOT-05

duration: 5min
completed: 2026-05-18
---

# Phase 47, Plan 03: EVENT_LAYER_PRIORITY_MAP Summary

**Added declarative EVENT_LAYER_PRIORITY_MAP to event-dispatcher.ts — a single source of truth for "when EVENT X fires, which mascot layers react?", covering all 15 event classes (7 v2.0 EventDetector + 8 Phase 30 Hard Tek) across the 4-layer state machine.**

## Performance

- **Duration:** 5 min (resume-from-stalled-state)
- **Tasks:** 2
- **Files modified:** 2
- **Vitest tests:** 14 new (event-coverage-matrix.test.ts)

## Accomplishments

- `event-dispatcher.ts` extended with `EVENT_LAYER_PRIORITY_MAP: Record<EventClass, LayerFanout>` constant covering all 15 event classes.
- `EventClass` union type defined: `TRACK_CHANGE | PHASE | LAYER_ARRIVAL | MIX_MOVE | HEARTBEAT | KAAN_SPOKE | MANUAL | DISTORTION_CLIMB | ACID_LINE_ENTRY | KICK_SWAP | SUB_LAYER_ARRIVAL | BREAKDOWN_KICK_KILL | REENTRY_KICK_LAND | KICK_DENSITY_SHIFT | PHRASE_BOUNDARY`.
- `LayerFanout` interface: `{ base?, emotion?, anticipation?, reaction? }` — each event maps to 1-4 layer firings.
- Existing dispatcher logic preserved byte-identical above the Phase 47 § marker.
- `event-coverage-matrix.test.ts` confirms: every EventClass has a map entry; KAAN_SPOKE has empty fanout; every layer type referenced is valid per types.ts.

## Files Created/Modified

- `tauri/ui/src/mascot/event-dispatcher.ts` — appended Phase 47 § block with EVENT_LAYER_PRIORITY_MAP + EventClass type
- `tauri/ui/src/mascot/__tests__/event-coverage-matrix.test.ts` — 14 unit tests across the 15×4 matrix

## Decisions Made

- KAAN_SPOKE fans out to nothing (empty LayerFanout) — preserves the Phase 13 STATE_PRIORITY rule (mascot stays on Base during user speech).
- HEARTBEAT fans out to base only (no emotion/reaction) — heartbeat is sustainment, not narrative.
- PHRASE_BOUNDARY fans out to reaction only — phrase boundaries are stylistic markers, not state changes.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

- Plan 47-06 (persona-smoke-harness) consumes EVENT_LAYER_PRIORITY_MAP to cycle through every layer firing.
- Plan 47-08 (CI audit) wires `vitest event-coverage-matrix` as the production gate.

---
*Phase: 47-mascot-real-glb-land-full-emotion-coverage*
*Completed: 2026-05-18*
