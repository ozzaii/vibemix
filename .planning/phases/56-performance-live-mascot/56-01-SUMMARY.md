---
phase: 56-performance-live-mascot
plan: 01
subsystem: ui
tags: [mascot, three.js, state-machine, anti-slop, vitest, typescript, ws-bus]

# Dependency graph
requires:
  - phase: 13-3d-mascot-overlay
    provides: "pure event-dispatcher + state-machine FSM + fixture-replay harness (the rig this plan extends)"
  - phase: 52
    provides: "ws_bus flat mascot frame carrying music/voice/phase/mood/genre"
provides:
  - "SnapshotSlice extended with music/voice (0..1) levels, threaded both from the live flat ws frame (index.ts) and the nested fixture frame (harness)"
  - "music-confirmation defence-in-depth guard on drop/peak/breakdown mode entry (LIVE-05a anti-slop control)"
  - "multi_mode_sequence + anti_slop_drop_quiet vitest fixtures pinning the contract"
affects: [57-sexify-finish, mascot, live-drive-uat]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Phase-led, music-confirmed mode selection: trust state.phase but block the flip when the music level contradicts it (return null = mode held)"
    - "Flat-vs-nested level duality: live ws frame carries music/voice as top-level floats; fixture frame carries them nested as {rms,peak}; both feed the same SnapshotSlice numeric fields"
    - "Discriminating held-mode test via settle-to-groove seed (a removed guard re-flips to dance_hard and is caught)"

key-files:
  created: []
  modified:
    - "tauri/ui/src/mascot/event-dispatcher.ts (SnapshotSlice music/voice + PEAK_RMS/LOW_RMS guard in stateForPhase)"
    - "tauri/ui/src/mascot/index.ts (thread flat music/voice off the live ws frame)"
    - "tauri/ui/src/mascot/state-machine-fixtures.test.ts (harness reads nested rms; new guard + held-mode tests)"
    - "tauri/ui/src/mascot/event-dispatcher.test.ts (snap consts widened; 6 guard tests)"
    - "tauri/ui/src/mascot/__fixtures__/event-traces.json (2 new traces)"

key-decisions:
  - "Mirrored Python thresholds verbatim (PEAK_RMS=0.110, LOW_RMS=0.040 from src/vibemix/audio/constants.py) as named TS consts — never magic numbers"
  - "drop AND peak both gated by PEAK_RMS (same loud-section family); breakdown gated by LOW_RMS; groove/build/low/silent unchanged (not in the contract's guard column)"
  - "anti_slop_drop_quiet seeds dance_hard then settles to groove BEFORE the contradictory quiet drop, so the held-mode test genuinely discriminates a removed guard (verified by neutralizing the guard mid-execution)"

patterns-established:
  - "Music-confirmation guard: contradictory phase/level → return null → current mode persists (mirrors the existing default:return null anti-slop discipline)"
  - "FSM purity preserved: no Date.now/setTimeout/three imports in event-dispatcher.ts"

requirements-completed: [LIVE-05, LIVE-05a]

# Metrics
duration: 11min
completed: 2026-05-21
---

# Phase 56 Plan 01: Mascot music-confirmation anti-slop guard Summary

**Closed the LIVE-05a anti-slop gap on the shipped Three.js rig: SnapshotSlice now carries music/voice levels and drop/peak/breakdown mode entry requires the music level to confirm the phase — a spurious `phase=drop` during a quiet section no longer fires the peak animation.**

## Performance

- **Duration:** ~11 min
- **Started:** 2026-05-21T06:37:00Z
- **Completed:** 2026-05-21T06:48:02Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments
- Extended `SnapshotSlice` with `music`/`voice` (0..1), threaded from BOTH the live flat ws frame (index.ts) and the nested `{rms,peak}` fixture frame (harness) into the same numeric fields.
- Added the defence-in-depth music-confirmation guard to `stateForPhase`: `drop`/`peak` require `music >= PEAK_RMS (0.110)`, `breakdown` requires `music < LOW_RMS (0.040)`; a contradictory frame returns `null` → current mode held (the highest-value anti-slop control in the phase).
- Added two LIVE-05a acceptance fixtures (`multi_mode_sequence`, `anti_slop_drop_quiet`) plus an explicit discriminating held-mode test that was verified to FAIL if the guard is removed.
- FSM purity preserved (no Date.now/setTimeout/three imports); all 697 vitest tests + typecheck + the Python cross-language taxonomy pin stay green.

## Task Commits

Each task was committed atomically (TDD: RED test then GREEN implementation within each task commit):

1. **Task 1: Extend SnapshotSlice with music/voice + thread it** - `193ff60` (feat)
2. **Task 2: Music-confirmation guard on drop/peak/breakdown** - `b9d1909` (feat)
3. **Task 3: multi-mode + anti-slop contradiction fixtures** - `eff26c1` (test)

## Files Created/Modified
- `tauri/ui/src/mascot/event-dispatcher.ts` - SnapshotSlice gains music/voice; PEAK_RMS/LOW_RMS named consts; `stateForPhase(phase, music)` guard; PHASE case threads `snapshot.music`.
- `tauri/ui/src/mascot/index.ts` - Reads `m.music`/`m.voice` as flat floats off the live ws frame, defaulting to prior.
- `tauri/ui/src/mascot/state-machine-fixtures.test.ts` - Harness reads nested `music.rms`/`voice.rms`; DEFAULT_SNAPSHOT gains music/voice; new SnapshotSlice + discriminating held-mode tests.
- `tauri/ui/src/mascot/event-dispatcher.test.ts` - Snapshot consts widened (drop snaps carry loud music); 6 new guard tests (held/confirmed for drop/peak/breakdown, unguarded phases unchanged).
- `tauri/ui/src/mascot/__fixtures__/event-traces.json` - `multi_mode_sequence` + `anti_slop_drop_quiet` traces (criterion 5).

## Decisions Made
- **Thresholds mirror Python verbatim.** `PEAK_RMS=0.11`, `LOW_RMS=0.04` declared as named TS consts citing `src/vibemix/audio/constants.py`; the mascot's mode boundaries now agree with `state.phase`.
- **drop and peak share the PEAK_RMS gate** (same loud-section family per UI-SPEC §The 6 modes); breakdown gated by LOW_RMS. groove/build/low/silent are unchanged — they were not gated by the contract.
- **Discriminating anti-slop fixture.** `anti_slop_drop_quiet` settles to groove (idle_bop) before the contradictory quiet drop so a removed guard would re-flip to dance_hard and be caught; verified mid-execution by temporarily neutralizing the guard (held-mode test went RED, then restored).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Provided test runner via node_modules symlink**
- **Found during:** Task 1 (baseline test run)
- **Issue:** The fresh worktree had no `tauri/ui/node_modules`, so `vitest`/`tsc` were unavailable; the plan's verify steps could not run.
- **Fix:** Symlinked `tauri/ui/node_modules` to the already-installed main-checkout `node_modules` (dependency REUSE of vetted, already-installed packages — NOT a package-manager install of any new/unverified dependency). The symlink is git-ignored locally and never staged/committed.
- **Files modified:** none committed (symlink only; not tracked)
- **Verification:** `vitest`/`tsc` resolve and run; `git diff --cached` confirms no node_modules in any commit.
- **Committed in:** n/a (untracked tooling)

**2. [Rule 3 - Blocking] Widened existing test snapshot consts for the new interface + guard**
- **Found during:** Task 1 (typecheck) and forward into Task 2 (guard semantics)
- **Issue:** Widening `SnapshotSlice` broke `event-dispatcher.test.ts` snap consts (missing music/voice) and a strict-null edge in the harness nested-rms reader; additionally the drop-asserting consts (`HIGH_CONF_SNAP`/`LOW_CONF_SNAP`) needed `music >= PEAK_RMS` to stay valid once the Task-2 guard landed.
- **Fix:** Added `music`/`voice` to all three snap consts (drop snaps carry `music: 0.3`, a real loud drop); restructured the harness `nestedRms` helper to narrow `.rms` cleanly under `noUncheckedIndexedAccess`.
- **Files modified:** tauri/ui/src/mascot/event-dispatcher.test.ts, tauri/ui/src/mascot/state-machine-fixtures.test.ts
- **Verification:** `tsc --noEmit` clean; full vitest green.
- **Committed in:** 193ff60 (Task 1) and b9d1909 (Task 2)

---

**Total deviations:** 2 auto-fixed (both Rule 3 - blocking)
**Impact on plan:** Both necessary to run the plan's own verify steps and to keep the widened interface + guard semantically correct. No scope creep — all within the plan's named `files_modified` set.

## Issues Encountered
- **Edit landed in the MAIN checkout, not the worktree (one occurrence, caught immediately).** The first RED edit used a MAIN-checkout absolute path (`/Users/ozai/projects/dj-set-ai/tauri/ui/...`) instead of the worktree path (`/Users/ozai/projects/dj-set-ai/.claude/worktrees/agent-.../tauri/ui/...`). Detected via a grep that showed the new code absent from the worktree but present in main. Reverted the main-checkout file with `git checkout --` (in the main repo) and re-applied every subsequent edit against the verified worktree path prefix. No main-checkout commit was ever made; the leak was confined to the working tree and fully reverted.
- **Held-mode test initially non-discriminating.** The first `anti_slop_drop_quiet` design seeded dance_hard and fired the quiet drop while still in dance_hard — a broken guard returns the same state, so `machine.current !== before` is false and no second transition records, masking the regression. Fixed by inserting a settle-to-groove step so a removed guard produces a real idle→dance transition; re-verified the test now goes RED with the guard neutralized.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- The mascot's mode boundaries now agree with `state.phase` on the shipped Three.js rig; LIVE-05/05a anti-slop guard is in place and pinned by fixtures + cross-language taxonomy test.
- The felt "does the mascot feel alive across its modes" sign-off on Kaan's Mac remains Kaan-action (live-drive UAT), per 56-CONTEXT deferred items.
- Phase 57 (Sexify) can supply per-mode art; the treatment/mode mapping is proven and testable before art lands.

## Self-Check: PASSED

- All 5 modified files present on disk.
- All 4 commits present in git (193ff60, b9d1909, eff26c1, 983b507).
- Verification re-run green: 697 vitest tests, `tsc --noEmit` clean, purity grep clean, Python taxonomy pin 4 passed.

---
*Phase: 56-performance-live-mascot*
*Completed: 2026-05-21*
