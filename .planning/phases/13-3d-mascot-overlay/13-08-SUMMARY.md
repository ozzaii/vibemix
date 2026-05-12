---
phase: 13-3d-mascot-overlay
plan: 08
subsystem: verification
tags: [verification, smoke-test, dispatch-latency, fixtures, event-taxonomy, mascot, checkpoint]

# Dependency graph
requires:
  - phase: 13-3d-mascot-overlay
    plan: 04
    provides: "Pure state-machine (planTransition / applyTransition / tickIdleTimeout) + MascotState union + STATE_CLASS / STATE_PRIORITY"
  - phase: 13-3d-mascot-overlay
    plan: 06
    provides: "Pure dispatchEvent — AI event taxonomy → MascotState requests + followups"
  - phase: 13-3d-mascot-overlay
    plan: 07
    provides: "MOOD_PROFILES + particle-puff + setMoodLighting + handleMoodChange"
  - phase: 13-3d-mascot-overlay
    plans: [01, 02, 03, 05]
    provides: "Asset bundle + overlay window + tray + settings drawer + sidecar mood/bpm_confidence/downbeat_phase fields"
provides:
  - "tauri/ui/src/mascot/__fixtures__/event-traces.json — 9 deterministic event-trace sequences covering the AI-event taxonomy from CONTEXT.md Area 3"
  - "tauri/ui/src/mascot/state-machine-fixtures.test.ts — fixture replay harness running each trace through dispatchEvent + applyTransition with deterministic clock + pendingSwitch + followup drain"
  - "tests/integration/test_mascot_dispatch_latency.py — pytest integration test: real WS server on free port, 100 frames @ 30Hz, asserts p95 sidecar→localhost < 50ms"
  - "tests/integration/test_mascot_event_taxonomy_e2e.py — Python cross-language pin: fixture's event subtypes + MascotStates match the canonical Python-side vocabulary"
  - ".planning/phases/13-3d-mascot-overlay/13-VERIFICATION.md — Phase 13 verification report (status: human_needed) covering 6 ROADMAP success criteria"
  - ".planning/phases/13-3d-mascot-overlay/13-08-MANUAL-SMOKE.md — 30-item manual smoke checklist for Kaan's rig pass"
affects: [Phase 14 polish loop (picks up any visual-quality items surfaced during manual smoke)]

# Tech tracking
tech-stack:
  added:
    - "pytest marker `integration` registered in pyproject.toml [tool.pytest.ini_options] markers"
  patterns:
    - "Cross-language fixture pin: same event-traces.json drives both vitest replay (state-machine math) AND pytest Python-side schema validation (canonical taxonomy + MascotState union). Drift in either direction surfaces immediately."
    - "Free-port discovery via socket.bind(0) + closing context manager — avoids hardcoded 8765 collisions when test runs while a live vibemix process holds the port"
    - "time.perf_counter_ns() pair on both server emit + client receive — monotonic, high-resolution, not subject to NTP adjustment mid-test. Both timestamps share the same process-wide clock so subtraction is meaningful."
    - "Linear-interpolation percentile computed without numpy — keeps the test importable in stripped CI environments + makes the math auditable"
    - "Fixture expectedTransitions tolerance: ±100ms — covers ~5% drift at 120-128 BPM; tight enough to catch real regressions, loose enough to not flake on event-loop jitter"

key-files:
  created:
    - "tauri/ui/src/mascot/__fixtures__/event-traces.json (245 lines — 9 trace sequences)"
    - "tauri/ui/src/mascot/state-machine-fixtures.test.ts (290 lines — 11 vitest cases)"
    - "tests/integration/__init__.py (5 lines — package marker)"
    - "tests/integration/test_mascot_dispatch_latency.py (175 lines — 2 pytest cases)"
    - "tests/integration/test_mascot_event_taxonomy_e2e.py (200 lines — 4 pytest cases)"
    - ".planning/phases/13-3d-mascot-overlay/13-VERIFICATION.md (160 lines — phase verification report)"
    - ".planning/phases/13-3d-mascot-overlay/13-08-MANUAL-SMOKE.md (135 lines — 30-item rig checklist)"
  modified:
    - "pyproject.toml (+1 line — `integration:` marker registered)"

key-decisions:
  - "Fixture expectations were adjusted to match the actual state-machine math, not the literal numbers in the plan's example snippet. The plan example used bpm=128/conf=0.85/phase=0.0 with an expected followup at after_t=900ms — but with those signals the followup re-enters planTransition, sees a high-confidence beat-lock condition, and schedules for the next downbeat ~1875ms later. To pin the EVENT-MAPPING contract (the contract the fixture is really for) without the beat-lock math complicating things, the fixture's `track_change_then_idle` uses bpm_confidence=0.4 so the followup falls through to switch_now."
  - "mood_swap_teacher fixture asserts only the initial puff_particle transition. The dispatcher's documented followup `idle_breathe @ 500ms` IS emitted, but state-machine's block rule (effect priority 100 > idle priority 20) correctly denies it — that's intentional: the renderer handles the puff→idle exit when the effect clip naturally completes its 500ms lifetime. The renderer-side puff-exit verification is in manual smoke items #18 and #29."
  - "Dispatch-latency budget split: < 50ms p95 on the sidecar side leaves ≥ 50ms of slack for the webview-side JS dispatch + rAF schedule + crossfade kickoff. Measured p95 on this machine was 0.28ms — 178× under budget. This pins the SIDECAR-SIDE half of MASCOT-08; the webview side is covered by pure-function tests in vitest (plan + apply <1ms each)."
  - "test_mascot_event_taxonomy_e2e.py is the file the plan frontmatter listed under files_modified but no task explicitly wrote — implemented as a Python-side schema-validity check of the JSON fixture. Pinning both sides against types.ts + dispatcher.ts means a future plan adding a new event subtype OR removing a MascotState will fail this test if the fixture isn't updated in lock-step. Closes the warning surfaced by the GSD plan-check."
  - "Manual smoke checklist file path is `13-08-MANUAL-SMOKE.md` (executor objective) NOT `MANUAL-SMOKE-CHECKLIST.md` (plan frontmatter). Followed the executor's explicit objective override; the file content is the 30-item walkthrough from PLAN Task 2 verbatim. Plan frontmatter's filename reference is treated as a documentation pointer, not a hard contract."

# Metrics
duration: ~45min
completed: 2026-05-12
tasks_complete: "2/3 automated; 1/3 awaits Kaan's manual rig pass"
commits: 2 (Task 1 + Task 2)
new_tests: 17 (11 vitest + 2 latency pytest + 4 taxonomy pytest)
total_loc: ~1170
dispatch_latency_p95_ms: 0.28
dispatch_latency_p99_ms: 0.37
---

# Phase 13 Plan 08: Verification fixtures + dispatch-latency pytest + 30-item manual smoke Summary

Closed Phase 13's automated verification surface — 11 fixture-driven state-machine replay tests pin every event in the AI-event taxonomy (CONTEXT Area 3), a real-WS dispatch-latency pytest asserts sidecar→localhost-receive p95 at 0.28ms (178× under the 50ms sidecar-side budget for MASCOT-08), a Python cross-language fixture-validity check guards against JS↔Py vocabulary drift, and a 30-item manual smoke checklist hands Phase 13's final UAT to Kaan's rig. Phase 13 status: **code-complete pending UAT** (same close pattern as Phase 12).

## Performance

- **Duration:** ~45 min
- **Completed:** 2026-05-12
- **Tasks committed:** 2 / 3 (Task 3 is the manual smoke checkpoint — STOPS here for Kaan)
- **Commits:** 2 atomic test commits
- **Tests added:** 17 (11 vitest fixture-replay + 2 pytest latency + 4 pytest taxonomy)
- **Vitest suite:** 217 / 217 pass (was 206 at Plan 13-07 close; +11 from this plan)
- **Pytest integration:** 6 / 6 pass; full pytest collection at 1216 tests
- **Measured dispatch latency:** p50 = 0.20ms, p95 = 0.28ms, p99 = 0.37ms, max = 0.44ms (budget: p95 < 50ms — 178× headroom)

## Accomplishments

### Task 1 — Event-trace fixtures + state-machine replay harness (commit `f1cae01`)

**`tauri/ui/src/mascot/__fixtures__/event-traces.json`** — 9 trace sequences covering the AI-event taxonomy from 13-CONTEXT.md Area 3:

| Trace name                          | Criterion | Asserts                                                              |
|-------------------------------------|-----------|----------------------------------------------------------------------|
| `track_change_then_idle`            | 5         | TRACK_CHANGE → react_surprised; followup idle_bop_to_beat_energetic  |
| `drop_then_groove`                  | 5         | PHASE→drop → dance_hard; PHASE→groove → idle_bop_to_beat_energetic   |
| `ai_speaks_then_done`               | 5         | AI_GENERATING_REPLY → talk_loop; AI_REPLY_DONE → react_yes           |
| `manual_fire_react`                 | 5         | MANUAL → react_yes                                                   |
| `silent_phase`                      | 5         | PHASE→silent → idle_breathe                                          |
| `mood_swap_teacher`                 | 6         | ipc.mascot.mood_change → puff_particle (effect blocks idle followup) |
| `talk_blocks_dance`                 | 5         | Priority order: talk_loop > dance request denied during talk         |
| `beat_locked_entry_at_high_confidence` | 4      | conf=0.85 + phase=0.5 → schedules dance_hard at +1000ms (one bar)    |
| `low_confidence_immediate_switch`   | 4         | conf=0.4 → falls through to switch_now (no scheduling)               |

**`tauri/ui/src/mascot/state-machine-fixtures.test.ts`** — Pure-function replay harness with 11 vitest cases:
- Loads JSON, iterates messages chronologically.
- Routes each event through `dispatchEvent`, applies the plan, drains `pendingSwitch` (beat-lock scheduled) AND the followup queue against a deterministic clock.
- Asserts every `expectedTransitions[i]` lands within ±100ms tolerance.
- Aggregate test asserts criteria #4 + #5 + #6 are each covered by ≥ 1 trace.

### Task 2 — Pytest dispatch-latency + cross-language fixture pin + verification + smoke checklist (commit `ce0a55f`)

**`tests/integration/test_mascot_dispatch_latency.py`** (2 pytest cases, both `@pytest.mark.integration`):

1. `test_mascot_dispatch_latency_p95_under_50ms` — spins up real `websockets.serve` on a free port via `socket.bind(0)`, subscribes a `websockets.connect` client, emits 100 frames at 30Hz each carrying its `perf_counter_ns()` emit timestamp, computes per-frame latency at the client receiver, asserts p95 < 50ms. Measured this machine: **p95 = 0.28ms** (178× under budget).
2. `test_mascot_dispatch_latency_helpers_well_formed` — guards the percentile + free-port helpers so a real-test regression doesn't get masked by broken plumbing.

**`tests/integration/test_mascot_event_taxonomy_e2e.py`** (4 pytest cases — the Python-side schema pin):

1. `test_event_taxonomy_fixture_well_formed_structure` — ≥ 7 traces; every trace has name + messages + expectedTransitions.
2. `test_event_taxonomy_fixture_uses_canonical_subtypes_only` — every envelope `type`, event `subtype`, and PHASE `payload.to` value must match the canonical Python-side vocabulary. Every documented event subtype must be covered by ≥ 1 trace.
3. `test_event_taxonomy_fixture_expected_states_are_canonical` — every `expectedTransitions[i].state` must be in the MascotState union from `types.ts`; drift detector for renderer vocabulary changes.
4. `test_event_taxonomy_fixture_covers_roadmap_criterion_5` — ROADMAP success criterion #5 requires coverage for react_surprised, dance_hard, talk_loop, react_yes, idle_breathe, idle_bop_to_beat_energetic, puff_particle — every entry must appear as the `state` of at least one expected transition.

**`pyproject.toml`** — registered the `integration:` pytest marker alongside the existing `macos_audio:` and `windows_only:` markers.

**`.planning/phases/13-3d-mascot-overlay/13-VERIFICATION.md`** — verification report with `status: human_needed`, per-criterion auto/human breakdown across the 6 ROADMAP success criteria, full MASCOT-* requirement coverage table. Same format/pattern as Phase 12's `12-VERIFICATION.md`.

**`.planning/phases/13-3d-mascot-overlay/13-08-MANUAL-SMOKE.md`** — 30-item walkthrough Kaan runs on his rig:
- **A. Window + Overlay** (#1-6): drag-reposition persistence, Spaces persistence, click-through toggle, tray Quit lifecycle.
- **B. Animation Library** (#7-16): T-pose absence on 10 transitions; correct clip plays per event; sleep / wake.
- **C. Crossfade Quality** (#17-21): smooth blends, mood-swap puff visible, no foot-sliding, no rigging artifacts.
- **D. Beat-Lock** (#22-25): 128 BPM bar-boundary entry; low-conf fallback; half-tempo correction; no-downbeat track fallback.
- **E. Event Mapping** (#26-28): full taxonomy fires correctly; AI talk interrupts dance; mood swap dance-pool change.
- **F. Mood Swap** (#29-30): three moods produce distinct idle pools + voice + puff each swap.

## Latency Measurement (Plan 13-08 close)

```
[dispatch-latency] samples=100 p50=0.20ms p95=0.28ms p99=0.37ms max=0.44ms budget=p95<50ms
```

Sidecar→localhost-receive latency runs ~178× under the 50ms p95 budget on this machine. Even with a 10× safety margin for slower hardware (CI runners, low-power laptops on battery), the budget holds with massive slack. The 100ms total event-to-visual budget (CONTEXT Area 6) is comfortably split:

| Stage                                  | Measured / Bounded     | Budget    |
|----------------------------------------|------------------------|-----------|
| sidecar emit → localhost receive       | p95 = 0.28ms (this test) | < 50ms |
| webview dispatch + plan + apply        | < 1ms per call (vitest)| < 10ms    |
| rAF schedule jitter (60fps)            | ≤ 16.7ms worst-case    | ≤ 16.7ms  |
| crossfade kickoff                      | ≤ 16.7ms worst-case    | ≤ 16.7ms  |
| **Total event-to-visual-transition**   | **~ 35ms**             | **< 100ms** |

## Deviations from Plan

### Plan-adjacent additions

**1. [Rule 2 — Missing critical] Created `tests/integration/test_mascot_event_taxonomy_e2e.py` to honour the plan frontmatter's `files_modified` entry**

- **Where the plan says:** The plan's `files_modified` frontmatter listed `tests/integration/test_mascot_event_taxonomy_e2e.py` but no `<task>` block explicitly wrote it. The plan-check warning surfaced this as an unresolved ambiguity.
- **What I did:** Implemented this file as a Python cross-language pin: validates the fixture's event subtypes + PHASE targets + MascotState references against the canonical vocabulary. If a future plan adds a new event subtype on the Python side (sidecar's `EventDetector`) OR removes a MascotState on the TypeScript side (`types.ts`), this test fails — forcing the fixture to stay current with both sides.
- **Why:** Two-way drift detector closes the JS↔Py vocabulary gap. Without this, the fixture could silently diverge from either side's truth.
- **Files added:** `tests/integration/test_mascot_event_taxonomy_e2e.py`
- **Commit:** `ce0a55f`

**2. [Rule 1 — Bug] Plan example numbers in event-traces.json had inconsistent beat-lock math; fixture values adjusted to match what state-machine.ts actually produces**

- **Where the plan says:** The plan example for `track_change_then_idle` used `bpm: 128, bpm_confidence: 0.85, downbeat_phase: 0.0` with expected followup at `after_t: 900`. The plan example for `drop_then_groove` used the same beat-lock signals expecting `after_t: 500` for dance_hard.
- **Issue:** With those signals, the followup re-enters `planTransition`, hits the beat-lock condition (conf ≥ 0.6, valid bpm + downbeat_phase), and schedules for the next downbeat ~1875ms later. The literal `after_t` in the plan example didn't match the math.
- **Fix:** For `track_change_then_idle`, lowered `bpm_confidence` to 0.4 (under the 0.6 threshold) so the followup falls through to switch_now and lands at the expected ~900ms. For `drop_then_groove`, raised `downbeat_phase` to 0.99 so both `dance_hard` and `idle_bop_to_beat_energetic` events fall inside the 30ms proximity-threshold (msUntilDownbeat = 0.01 × 1875 = 18.75ms < 30ms → switch_now fallback). The beat-lock math IS tested separately in `beat_locked_entry_at_high_confidence` (conf=0.85, phase=0.5 → schedules at exactly +1000ms = one bar at 120 BPM).
- **Files modified:** `tauri/ui/src/mascot/__fixtures__/event-traces.json` (inline before first commit; no separate fix commit)
- **Commit:** `f1cae01` (incorporated into Task 1's GREEN commit — RED + GREEN happened in the same iteration here since the test wasn't pre-existing)

**3. [Rule 1 — Bug] mood_swap_teacher fixture expected an idle_breathe followup at +500ms that the state-machine correctly denies**

- **Where the plan says:** Example trace `mood_swap_teacher` expected transitions `[ puff_particle @ 0, idle_breathe @ 500 ]`.
- **Issue:** When the followup fires at t=500, the machine is in `puff_particle` (effect class, priority 100). The block rule denies any request with priority < 100, including the idle_breathe followup (priority 20). The plan example expected behaviour that the existing state-machine.ts (locked by Plan 13-04's 14 tests) correctly prevents — this is the intentional "effect blocks idle" guard, not a bug.
- **Fix:** Adjusted fixture to assert only the initial `puff_particle` transition. The followup IS emitted in the dispatcher's return value (verified by event-dispatcher.test.ts Test 7) and the renderer handles the puff→idle exit when the effect clip naturally completes its 500ms lifetime. The puff-exit verification is in manual smoke checklist items #18 and #29.
- **Files modified:** `tauri/ui/src/mascot/__fixtures__/event-traces.json` (inline before first commit)
- **Documented in fixture description:** `"The dispatcher emits a followup idle_breathe @ 500ms as data, but state-machine.ts's block rule denies idle_breathe (priority 20) while puff_particle (effect, priority 100) is active — that's correct, the renderer handles the puff→idle exit when the effect clip naturally completes."`
- **Commit:** `f1cae01`

**4. [Decision] Manual smoke checklist filename: `13-08-MANUAL-SMOKE.md`, not `MANUAL-SMOKE-CHECKLIST.md`**

- **Where the plan says:** Frontmatter `files_modified` listed `MANUAL-SMOKE-CHECKLIST.md`; PLAN Task 2 inline text also used that name.
- **Where the executor's objective says:** "Manual smoke checklist artifact written to `.planning/phases/13-3d-mascot-overlay/13-08-MANUAL-SMOKE.md`"
- **Decision:** Followed the executor objective's explicit override. The file content is the 30-item walkthrough from PLAN Task 2 verbatim; only the filename differs. Frontmatter's filename reference is treated as a documentation pointer, not a hard contract.
- **Files affected:** `.planning/phases/13-3d-mascot-overlay/13-08-MANUAL-SMOKE.md`
- **Commit:** `ce0a55f`

## Authentication Gates

None.

## Known Stubs

None. Every artifact this plan promises is committed:
- Fixtures + replay harness: green
- Latency pytest: green (real WS server / client / cleanup)
- Verification report: complete with per-criterion status
- Manual smoke checklist: 30 actionable items with pass/fail/skip markers

The single "stub-shaped" surface is Task 3 — the manual rig walkthrough — which is by design a human-only checkpoint, not a stub.

## Deferred Issues

None new. Pre-existing items in `.planning/phases/13-3d-mascot-overlay/deferred-items.md` unchanged:
1. `tauri/ui/src/main.ts:104` → `./session/mock.js` missing in main repo (worktree-only file)
2. `tests/agent/test_persona.py::test_persona_02_byte_identical_to_v4` — needs cohost_v4.py tracked
3. `tests/test_phase05_verification.py::test_g5_poc_files_untouched` — pathspec collision
4. `tests/test_audio_macos_live.py::test_open_voice_output_completes_without_real_audio_device` — Kaan-rig-only

## Threat Flags

No new surface introduced. Plan 13-08's tests are localhost-only (`127.0.0.1` + ephemeral free port) per `<threat_model>` T-13-08-01: free-port discovery + pytest fixture teardown handles the DoS-flake concern. T-13-08-02 (manual checklist subjectivity) is the documented `accept` disposition — Phase 14 polish loop owns visual-quality iteration.

## Test Run Snapshot

```
$ cd tauri/ui && npx vitest run src/mascot/state-machine-fixtures.test.ts --reporter=dot
 ✓ src/mascot/state-machine-fixtures.test.ts (11 tests) 3ms
 Test Files  1 passed (1)
      Tests  11 passed (11)

$ cd tauri/ui && npx vitest run --reporter=dot
 Test Files  17 passed (17)
      Tests  217 passed (217)

$ cd tauri/ui && npm run check:ipc
codegen:ipc — wrote tauri/ui/src/ipc/messages.ts
(tsc --noEmit exits 0)

$ python -m pytest tests/integration/ -m integration -x -v
 6 passed in 3.48s
 [dispatch-latency] samples=100 p50=0.20ms p95=0.28ms p99=0.37ms max=0.44ms budget=p95<50ms

$ grep -E "Date\.now|setTimeout" tauri/ui/src/mascot/event-dispatcher.ts tauri/ui/src/mascot/state-machine.ts
(empty — purity intact)
```

## Checkpoint Pending

Plan 13-08 has THREE tasks. Tasks 1 + 2 are committed and verified above. Task 3 is a `checkpoint:human-verify` — Kaan runs the 30-item manual smoke checklist on his macOS rig (DDJ-FLX4 + djay Pro + BlackHole 2ch + nowplaying-cli). This summary is being written BEFORE the manual rig pass, in line with the parallel-executor convention.

After Kaan's manual pass, the orchestrator will:
1. Update this SUMMARY.md's `tasks_complete` field to `3/3`.
2. Flip `13-VERIFICATION.md` Aggregate Status from `status: human_needed` to `status: done` once every criterion has both auto-PASS + manual-PASS.
3. Route any failures to `deferred-items.md` for Phase 14 polish loop pickup.
4. Advance STATE.md + ROADMAP.md to close Phase 13 and prepare Phase 14.

## Next Plan Readiness

- **Phase 14 polish loop:** Inherits any visual-quality items surfaced during Kaan's manual smoke (T-pose flashes, foot-sliding, audible beat-lock misalignment, character readability across moods). The deferred-items.md format is wired for this hand-off.
- **Phase 19 launch:** The mascot + state machine + dispatcher contract is now pinned by 217 vitest cases + 6 integration pytest cases + 30 manual checks. Any hero-demo regressions during launch-prep run through these same gates first.

## Self-Check: PASSED

Files claimed in this SUMMARY exist:
- FOUND: `tauri/ui/src/mascot/__fixtures__/event-traces.json`
- FOUND: `tauri/ui/src/mascot/state-machine-fixtures.test.ts`
- FOUND: `tests/integration/__init__.py`
- FOUND: `tests/integration/test_mascot_dispatch_latency.py`
- FOUND: `tests/integration/test_mascot_event_taxonomy_e2e.py`
- FOUND: `.planning/phases/13-3d-mascot-overlay/13-VERIFICATION.md`
- FOUND: `.planning/phases/13-3d-mascot-overlay/13-08-MANUAL-SMOKE.md`
- FOUND: `pyproject.toml` (with `integration:` marker)

Commits claimed exist:
- FOUND: `f1cae01` (Task 1 — fixtures + replay harness)
- FOUND: `ce0a55f` (Task 2 — latency pytest + taxonomy pytest + verification + smoke)

Per-task verification:
- [x] state-machine-fixtures.test.ts: 11/11 pass
- [x] full vitest src/mascot/ suite: 217/217 pass (no regressions)
- [x] test_mascot_dispatch_latency.py: 2/2 pass; p95 = 0.28ms (<< 50ms budget)
- [x] test_mascot_event_taxonomy_e2e.py: 4/4 pass
- [x] tsc --noEmit (npm run check:ipc): exits 0
- [x] purity grep on event-dispatcher.ts + state-machine.ts: empty
- [x] frontmatter file `tests/integration/test_mascot_event_taxonomy_e2e.py` exists (warning resolved)
- [x] STATE.md / ROADMAP.md NOT modified (executor never touches those in worktree)

---
*Phase: 13-3d-mascot-overlay*
*Plan: 08*
*Completed: 2026-05-12 (Tasks 1 + 2 automated; Task 3 manual checkpoint awaits Kaan)*
