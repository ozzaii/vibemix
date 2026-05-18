---
phase: 47-mascot-real-glb-land-full-emotion-coverage
plan: 06
subsystem: mascot
tags: [mascot, persona-smoke, harness, screencast]

requires:
  - phase: 47-mascot-real-glb-land-full-emotion-coverage
    plan: 03
    provides: EVENT_LAYER_PRIORITY_MAP
  - phase: 47-mascot-real-glb-land-full-emotion-coverage
    plan: 05
    provides: 23 placeholder GLBs + manifest.json entries
provides:
  - 30s persona-smoke headless harness cycling every Phase 47 clip
  - scripts/mascot/persona_smoke.sh shell entry-point
  - tauri/ui/src/mascot/persona-smoke-harness.ts TypeScript harness
  - docs/mascot/README.md operator guide
affects: [47-07, 47-08, MASCOT-06]

tech-stack:
  added: []
  patterns:
    - Headless persona-smoke as MASCOT-06 acceptance signal
    - WebM screencast output at docs/mascot/persona_smoke.webm (gitignored)

key-files:
  created:
    - scripts/mascot/persona_smoke.sh
    - tauri/ui/src/mascot/persona-smoke-harness.ts
    - docs/mascot/README.md
    - tests/mascot/test_persona_smoke_shape.py

key-decisions:
  - "30s harness — long enough to cycle 23 clips with 1s minimum dwell, short enough to fit a CI step"
  - "Output webm gitignored — the artifact is meant for ad-hoc operator-facing verification, not in-repo proof"

patterns-established:
  - "Persona-smoke = MASCOT-06 acceptance gate: visible signal every shipped slot loads + renders"

requirements-completed:
  - MASCOT-06

duration: 6min
completed: 2026-05-18
---

# Phase 47, Plan 06: Persona-Smoke Harness Summary

**Built the 30-second headless persona-smoke harness that cycles every Phase 47 emotion + reaction at least once and emits a WebM screencast to docs/mascot/persona_smoke.webm — the MASCOT-06 visible acceptance signal that every shipped clip slot actually loads and renders.**

## Performance

- **Duration:** 6 min (resume-from-stalled-state)
- **Tasks:** 4
- **Files modified:** 4
- **Tests added:** 11 (test_persona_smoke_shape.py)

## Accomplishments

- `scripts/mascot/persona_smoke.sh` shell harness — orchestrates: build Tauri UI → spawn headless browser → drive the in-page harness → capture WebM.
- `tauri/ui/src/mascot/persona-smoke-harness.ts` — in-page harness module that cycles through every Phase 47 clip name in deterministic order (base → emotion → anticipation → reaction) with 1s dwell per clip.
- `docs/mascot/README.md` — operator guide explaining how to read the persona-smoke output + what discharge state each band signals.
- `tests/mascot/test_persona_smoke_shape.py` — 11 static-string smoke tests on the harness module + the shell wrapper.

## Files Created/Modified

- `scripts/mascot/persona_smoke.sh` — shell entry point (executable)
- `tauri/ui/src/mascot/persona-smoke-harness.ts` — in-page TypeScript harness
- `docs/mascot/README.md` — operator-facing mascot docs
- `tests/mascot/test_persona_smoke_shape.py` — 11 static-string tests

## Decisions Made

- 1s dwell per clip → 23 clips × 1s ≈ 23s + 2s crossfade transitions ≈ ~25s of actual rendering; 30s budget includes browser cold-start.
- WebM (vs MP4) — WebM is the open-format-default per project lean; ffmpeg available in CI.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

- Plan 47-07 (README hero render) reuses the harness pattern (single-clip render of react_hype_peak.glb).
- Plan 47-08 (CI audit) wires `event-coverage-matrix` vitest into mascot-audit.yml (separate from this Plan 06's harness output, which is operator-facing not CI-blocking).

---
*Phase: 47-mascot-real-glb-land-full-emotion-coverage*
*Completed: 2026-05-18*
