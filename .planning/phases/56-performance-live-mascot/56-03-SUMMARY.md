---
phase: 56-performance-live-mascot
plan: 03
subsystem: ui
tags: [mascot, three.js, state-machine, anti-slop, vitest, typescript, ws-bus, latency, perf]

# Dependency graph
requires:
  - phase: 56-performance-live-mascot
    plan: 01
    provides: "SnapshotSlice.music/voice + the music-confirmation guard in stateForPhase (drop/peak/breakdown level-confirmed); multi_mode_sequence + anti_slop_drop_quiet fixtures"
  - phase: 13-3d-mascot-overlay
    provides: "pure event-dispatcher + state-machine FSM + priority/block ladder + fixture-replay harness + dispatch-latency integration test (the rig + tests this plan extends)"
provides:
  - "six_mode_reachability trace + assertion: all six contract modes (idle/vibing/building/drop/breakdown/speaking) proven reachable from real canonical bus events (LIVE-05a ≥6-distinct-modes acceptance)"
  - "speaking_overrides_music trace + held assertion: talk_loop (priority 80) blocks an incoming music PHASE mid-talk via the existing block rule (LIVE-05a speaking-overrides-music)"
  - "mood-is-a-tint + emotion==null no-op assertions pinning the tint discipline (mood/emotion never branch the FSM)"
  - "a synthetic mode-transition frame in test_mascot_dispatch_latency.py with p95 < 50ms held (PERF-03 webview-side floor)"
affects: [57-sexify-finish, mascot, live-drive-uat]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Reachability-as-a-trace: prove ≥6 distinct modes by replaying one ordered walk that enters each from its real bus event, ordering steps so consecutive states differ (re-entering a state records no transition)"
    - "Positive held-mode assertion: prove a blocked/denied event by asserting the PRIOR state PERSISTS (and counting transitions), never an empty expectedTransitions list"
    - "Replace-don't-add for fixed-count latency harnesses: a synthetic mode-transition frame REPLACES one seq frame (keeping seq + t_emit_ns) so emit==drain==FRAME_COUNT and the sanity gate holds"
    - "Mood/emotion are renderer tints, not FSM branches: a mood/emotion-carrying snapshot frame is a state-READER (dispatchEvent returns null); the dispatcher selects the same mode regardless of mood, and emotion==null is a no-op"

key-files:
  created: []
  modified:
    - "tauri/ui/src/mascot/__fixtures__/event-traces.json (six_mode_reachability + speaking_overrides_music traces, criterion 5)"
    - "tauri/ui/src/mascot/state-machine-fixtures.test.ts (six-mode reachability assertion; speaking-overrides-music held assertion; mood-is-a-tint + emotion==null no-op assertions)"
    - "tests/integration/test_mascot_dispatch_latency.py (synthetic mode-transition frame replacing one seq frame; MODE_TRANSITION_FRAME const; PERF-03 docstring)"

key-decisions:
  - "Kept the EXISTING states + EXISTING priority ladder — no new MascotState union members, no parallel priority system, no level-driven speaking path. Speaking stays the event-driven AI_GENERATING_REPLY -> talk_loop path; the talk-block rule (state-machine.ts:165-174) already enforces speaking-overrides-music."
  - "Ordered the six-mode walk so the drop (dance_hard) is interleaved BETWEEN the two energetic phases (groove/build both -> idle_bop_to_beat_energetic). Re-entering the same state records no transition, so each step must land on a different state to be matched by the ±100ms auto-runner."
  - "Held assertions are POSITIVE (assert talk_loop persists / count transitions), mirroring talk_blocks_dance + anti_slop_drop_quiet — the well-formed check forbids an empty expectedTransitions list."
  - "The mode-transition latency frame REPLACES one seq frame (still carrying seq + t_emit_ns) rather than adding a 101st emit — keeps server-emit == client-drain == FRAME_COUNT so the ≥95-valid-sample sanity gate stays satisfied; P95_BUDGET_MS left at 50.0 (no budget loosening)."

patterns-established:
  - "Reachability trace: one ordered walk proving ≥N distinct modes each enter from a real bus event."
  - "Positive held-mode assertion for denied/blocked events (prior state persists)."
  - "FSM purity preserved: no Date.now/setTimeout/three imports in event-dispatcher.ts (grep gate clean)."

requirements-completed: [LIVE-05, LIVE-05a, PERF-03]

# Metrics
duration: 9min
completed: 2026-05-21
---

# Phase 56 Plan 03: Six-mode reachability + speaking-overrides-music + PERF-03 floor Summary

**Closed the remaining LIVE-05a contract items on the shipped Three.js rig: all six contract modes are proven reachable from real canonical bus events, the AI-speaking path provably overrides every music mode via the existing talk-block rule, mood/emotion are pinned as renderer tints (never FSM branches), and a synthetic mode-transition frame in the dispatch-latency test confirms the mode machine adds no measurable sidecar->client latency (p95 ~0.22ms, well under the 50ms PERF-03 budget).**

## Performance

- **Duration:** ~9 min
- **Started:** 2026-05-21T09:52:00Z
- **Completed:** 2026-05-21T10:01:00Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- Added the `six_mode_reachability` trace + an explicit LIVE-05a acceptance assertion: a single ordered walk enters each of the six contract modes (idle/vibing/building/drop/breakdown/speaking) from its real canonical bus event, reaching ≥4 distinct entered states across the six phase/event steps.
- Added the `speaking_overrides_music` trace + a discriminating held-mode assertion: a music `PHASE->groove` DURING `talk_loop` is denied (`blocked_by_talk`), so talk_loop persists across the whole talk window — no idle/dance state appears while the AI is speaking. Returns to a music-context state on `AI_REPLY_DONE`.
- Pinned the tint discipline (Pitfall 5): a mood-only snapshot frame produces no transition, `PHASE->drop` picks `dance_hard` regardless of mood (mood never branches the FSM), and an `emotion==null` (or any emotion) frame is a dispatcher no-op.
- Extended `test_mascot_dispatch_latency.py` with a synthetic mode-transition frame that REPLACES one seq frame (still carrying `seq` + `t_emit_ns`); p95 stays at ~0.22ms under the unchanged 50.0ms budget — PERF-03's webview-side floor pinned.
- FSM purity preserved (no Date.now/setTimeout/three in event-dispatcher.ts); full vitest (703 tests) + tsc + both integration tests + the Python cross-language taxonomy pin all green.

## Task Commits

Each task was committed atomically:

1. **Task 1: Six-mode reachability trace** - `364ae66` (test)
2. **Task 2: Speaking-overrides-music proof + mood/emotion tint discipline** - `1f228ec` (test)
3. **Task 3: Mode-transition frame in dispatch-latency (PERF-03)** - `d26db06` (test)

_All tasks are test/fixture extensions of an already-shipped rig — no new production logic was required (the states, priority ladder, block rule, and 56-01 music-confirmation guard already exist), so each task is a `test(...)` commit per the conventional-commit table._

## Files Created/Modified
- `tauri/ui/src/mascot/__fixtures__/event-traces.json` - Added `six_mode_reachability` (criterion 5) and `speaking_overrides_music` (criterion 5) traces in the verified on-disk schema (name/criterion/description/messages[{t,msg}]/expectedTransitions[{after_t,state}], nested music/voice level shape).
- `tauri/ui/src/mascot/state-machine-fixtures.test.ts` - Added the six-mode reachability assertion (all six modes enter from real events, ≥4 distinct states), the speaking-overrides-music held assertion (denied groove records no transition; no idle/dance during talk), the mood-is-a-tint assertion (mood-only snapshot = no transition; same target regardless of mood), and the emotion==null no-op assertion.
- `tests/integration/test_mascot_dispatch_latency.py` - Added the `MODE_TRANSITION_FRAME` const; the `server_handler` now emits one PHASE->drop-shaped mode-transition frame (still carrying seq + t_emit_ns) in place of a seq frame; PERF-03 + MASCOT-08 budget rationale documented in the docstring. `P95_BUDGET_MS` unchanged at 50.0; both loops stay bound to `range(FRAME_COUNT)`.

## Decisions Made
- **Extend-and-pin, no new modes.** Used the existing `idle_breathe` / `idle_bop_to_beat_energetic` / `dance_hard` / `talk_loop` states and the existing STATE_PRIORITY ladder. The talk-block rule already enforces speaking-overrides-music, so no parallel level-driven speaking path or new priority system was added.
- **Interleave the drop between the two energetic phases.** groove and build both map to `idle_bop_to_beat_energetic`; re-entering the same state records no transition. The first reachability draft missed an expectedTransition (5/6 matched) for exactly this reason — reordering to `silent → groove → drop → build → breakdown → speaking` makes every consecutive step a genuine state change.
- **Positive, well-formed held assertions.** Both the speaking-block and the (pre-existing) anti-slop held proofs assert the PRIOR state persists and count transitions, never emitting an empty `expectedTransitions` list (the harness well-formed check forbids it).
- **Replace, don't add, for the latency frame.** The mode-transition frame replaces one seq frame so server-emit == client-drain == FRAME_COUNT and the ≥95-valid-sample sanity gate stays satisfied; the 50.0ms budget was left untouched.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Provided test runner via node_modules symlink**
- **Found during:** Task 1 (baseline test run)
- **Issue:** The fresh worktree had no `tauri/ui/node_modules`, so `vitest`/`tsc` were unavailable.
- **Fix:** Symlinked `tauri/ui/node_modules` to the already-installed main-checkout `node_modules` (REUSE of vetted, already-installed packages — NOT a package-manager install of any new/unverified dependency). The symlink is untracked and was never staged/committed (verified `git diff --cached --name-only` on every commit).
- **Files modified:** none committed (symlink only; not tracked)
- **Committed in:** n/a (untracked tooling)

**2. [Rule 3 - Blocking] Ran Python tests via the main-checkout venv against the worktree tree**
- **Found during:** Task 1 (Python taxonomy pin)
- **Issue:** The worktree has no `.venv`; `source .venv/bin/activate` failed.
- **Fix:** Invoked the main-checkout interpreter (`/Users/ozai/projects/dj-set-ai/.venv/bin/python3`) with `PYTHONPATH=<worktree>/src` and cwd at the worktree root, so pytest reads the worktree's fixture + test files. This is a tooling/run-path adjustment, not a code change.
- **Files modified:** none
- **Committed in:** n/a (test-run mechanics)

**3. [Rule 1 - Bug] Removed a self-referential trace-name mention from the description string**
- **Found during:** Task 2 (acceptance grep `grep -c speaking_overrides_music`)
- **Issue:** The trace `description` referenced the explicit `it(...)` test name, which contained the trace name, so `grep -c` returned 2 instead of the acceptance's expected 1.
- **Fix:** Reworded the description to "the explicit held-mode it(...) assertion" (no trace-name repeat). `grep -c` now returns 1.
- **Files modified:** tauri/ui/src/mascot/__fixtures__/event-traces.json
- **Committed in:** 1f228ec (Task 2)

---

**Total deviations:** 3 (2 Rule 3 - blocking tooling/run-path; 1 Rule 1 - acceptance-grep correctness). No scope creep — all code changes within the plan's named `files_modified` set.

## Issues Encountered
- **Six-mode reachability initially matched 5/6.** The first draft ordered the walk silent → groove → build → drop → breakdown, but groove and build both map to `idle_bop_to_beat_energetic`; re-entering the same state records no transition, so the build step's expectedTransition had no matching actual. Fixed by interleaving the drop (`dance_hard`) between the two energetic phases so every consecutive step is a real state change. Re-verified: 6/6 expectedTransitions matched.
- **`pytest -q` on the file directly does not auto-skip integration tests.** The project's "default run skips integration" convention is realized by passing `-m "not integration ..."` (no conftest-level deselection). Confirmed both tests carry `@pytest.mark.integration` and are deselected under `-m "not integration"` (2 deselected) — the acceptance is satisfied by the marker + the documented fast-run filter, not an auto-skip.

## Known Stubs
None — this plan is pure test/fixture coverage of an already-shipped rig. No new production code, no placeholder data, no unwired components.

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness
- The LIVE-05a contract is now fully pinned at the test layer: ≥6 distinct modes each gated to a real bus event, speaking-overrides-music proven via the existing block rule, mood/emotion tint discipline enforced, and PERF-03's webview-side floor confirmed.
- The felt "does the mascot feel alive across its modes under a real set on Kaan's Mac" success criterion is explicitly NOT marked complete — it rides the Kaan-action live-drive UAT surface (per 56-CONTEXT deferred items + the plan's scope guardrail).
- Phase 57 (Sexify) can supply per-mode art against a proven, testable mode/treatment mapping.

## Self-Check: PASSED

- All 3 modified files present on disk and committed.
- All 3 task commits present in git (364ae66, 1f228ec, d26db06).
- Verification re-run green: full vitest 703 passed, tsc --noEmit clean, purity grep clean on event-dispatcher.ts, 6 integration tests passed (taxonomy + dispatch-latency), Python taxonomy pin 4 passed.

---
*Phase: 56-performance-live-mascot*
*Completed: 2026-05-21*
