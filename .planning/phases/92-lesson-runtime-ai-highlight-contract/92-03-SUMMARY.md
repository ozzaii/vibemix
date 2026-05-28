---
phase: 92-lesson-runtime-ai-highlight-contract
plan: 03
subsystem: backend
tags: [lesson-runtime, fsm, python-statemachine, learn-state, tutor-prompts, json-fixture, single-writer]

# Dependency graph
requires:
  - "Plan 92-01 (python-statemachine ^3.1.2 dep + 11 ipc.learn.* envelopes + learn_tutor router path)"
  - "Plan 92-02 (test scaffolding — 2 AST gates LIVE + 4 module-skip stubs awaiting this plan)"
  - "Plan 91-03 (src/vibemix/learn/midi_mirror.py + tests/learn/__init__.py)"
provides:
  - "src/vibemix/learn/state.py — LearnState mutable dataclass (6 fields tracking lesson position)"
  - "src/vibemix/learn/runtime.py — LessonRuntime FSM (StateMachine subclass; 8 states / 5 transitions / 1 Hz tick_loop / 5 on_enter_<state> callbacks)"
  - "src/vibemix/learn/curriculum.py — COURSE_FRAMES + LessonMeta + CURRICULUM dispatch (1 entry: L0.00-press-play)"
  - "src/vibemix/learn/prompts.py — build_tutor_system_instruction with 4-forbidden-moves lock LAST for strongest recency"
  - "src/vibemix/learn/transcripts/hello_world/01_press_play.json — hand-authored 1-step lesson fixture"
  - "Single-writer invariant #1 binding for LearnState — AST gate test_runtime_invariants.py stays green"
  - "TONE-04 binding — 4 REQUIRED_LOCK_TOKENS present + lock-is-LAST"
  - "TONE-02 binding — tutor_speak.text VERBATIM from JSON fixture (zero generative writes)"
affects: [92-04, 92-05, 92-06, 92-07]

# Tech tracking
tech-stack:
  added:
    - "No new dependencies — python-statemachine ^3.1.2 already installed by Plan 92-01"
  patterns:
    - "Single-writer FSM: LessonRuntime is the SOLE writer of LearnState; all mutations live inside on_enter_<state> callbacks (Invariant #1 binding); AST gate enforces"
    - "Dual-use guard signature: action_matches(midi, expected=None) accepts BOTH the FSM cond= path (expected read from CURRICULUM) AND the direct-test path (expected passed in) — keeps the test surface small without coupling tests to the full FSM lifecycle"
    - "allow_event_without_transition = True converts a False guard into silent no-op; mirrors the test contract where rt.send('skip') before the 45 s floor must leave state untouched (NOT raise)"
    - "Loop-probe before create_task: asyncio.get_running_loop() check guards the scheduling so synchronous unit tests don't orphan a coroutine + emit pytest RuntimeWarning"
    - "Hand-authored JSON fixture is the SOURCE OF TRUTH for tutor_speak text (TONE-02); LessonRuntime reads text VERBATIM into LearnTutorSpeak envelopes — never LLM-generated at runtime"
    - "Tutor system instruction composition mirrors COACH_CLOSING_BLOCK precedent at prompts/matrix.py:241-251: 4-forbidden-moves lock lands as the FINAL block (strongest recency); 4 REQUIRED_LOCK_TOKENS pinned by AST gate"
    - "LessonRuntime defensive emit pattern: every ipc_router.emit + progress_store call wrapped in try/except so a single envelope failure doesn't wedge the FSM mid-lesson (failures print to stderr; FSM state machine proceeds)"

key-files:
  created:
    - "src/vibemix/learn/state.py (55 lines — LearnState dataclass)"
    - "src/vibemix/learn/curriculum.py (121 lines — COURSE_FRAMES + LessonMeta + CURRICULUM)"
    - "src/vibemix/learn/prompts.py (200 lines — build_tutor_system_instruction + _FORBIDDEN_TUTOR_MOVES_LOCK)"
    - "src/vibemix/learn/runtime.py (575 lines — LessonRuntime FSM)"
    - "src/vibemix/learn/transcripts/hello_world/01_press_play.json (35 lines — hand-authored lesson fixture; addendum 122/200 chars)"
  modified:
    - "src/vibemix/learn/__init__.py (re-exports LearnState / COURSE_FRAMES / CURRICULUM / LessonMeta / LessonRuntime / build_tutor_system_instruction — preserves P91's MidiMirror re-export)"

key-decisions:
  - "LessonRuntime.completed is NOT marked final=True — the load transition lets a freshly-completed runtime re-load a new lesson (the post-skip / post-completion relaunch flow). python-statemachine's trap-state check requires every non-final state to have at least one outgoing transition; load satisfies that. Plan-level guidance said final=True; runtime check made that impossible (Plan deviation Rule 1 — bug)."
  - "action_matches takes BOTH a `midi` arg AND an `expected` arg (defaulting None). When expected is omitted, the function reads from CURRICULUM (the FSM cond= path); when provided, it's used as-is (the direct-test path). Tests call action_matches({...}, expected={...}) directly — only the dual signature satisfies both call surfaces."
  - "allow_event_without_transition = True (StateMachine class attribute). Without this, send('skip') with a failed guard raises TransitionNotAllowed — which the tests don't catch. Setting True makes failed-guard send a silent no-op (state stays put), matching the test contract."
  - "asyncio.get_running_loop() probe BEFORE asyncio.create_task in on_enter_advancing. asyncio.create_task creates the coroutine first and then attempts to schedule, so a failed create_task leaves an unawaited coroutine that pytest warns about. Probing the loop first lets us skip creating the coroutine when no loop is running (synchronous test path)."
  - "_last_was_match flag set in on_ack_action / on_skip transition callbacks (which fire DURING the transition, BEFORE on_enter_<state>). on_enter_advancing reads the flag to set the LearnAdvance reason field (action_matched vs user_skip). Same pattern works for on_enter_completed's complete_lesson reason."
  - "Controller frame degrades to 'a MIDI controller' when find_mapping returns None (unmapped hardware). The frame is informational, not load-bearing — the tutor narration can still proceed without a known device. Live binding always reaches via find_mapping_or_generic, so the None branch only fires in tests that pass an unknown id."
  - "Re-export __init__.py updated incrementally (Task 1 added 4 names, Task 2 added LessonRuntime as 5th). Avoids the import-error gap where Task 1's __init__ would try to import LessonRuntime before runtime.py existed."

patterns-established:
  - "FSM with single-writer dataclass: declare the dataclass as mutable (NOT frozen), enforce sole-writer via AST grep gate, never inside Python typing"
  - "Defensive emit-wrap pattern: every ipc_router.emit call inside on_enter_<state> wrapped in try/except so transient envelope failures don't wedge the FSM"
  - "Loop-probe-before-create-task: asyncio.get_running_loop() check converts test-path scheduling failures into clean no-ops"
  - "Dual-use guard signature: predicates that serve BOTH the FSM cond= path AND direct-test calls accept the expected/baseline as an optional kwarg defaulting to None (then look up from registry when None)"

requirements-completed: [LESSON-01, LESSON-04, LESSON-05, TONE-02, TONE-04]
# Note: LESSON-06 (model_router learn_tutor route) was completed in Plan 92-01; this plan reuses it.

# Metrics
duration: 13min
completed: 2026-05-28
---

# Phase 92 Plan 03: Lesson Runtime + AI Highlight Contract Summary

**LessonRuntime FSM (8 states / 5 transitions / 1 Hz tick_loop / single-writer of LearnState) + LearnState mutable dataclass + CURRICULUM dispatch with 1 hello-world lesson + build_tutor_system_instruction composing 5 fragments with 4-forbidden-moves lock LAST for strongest recency + hand-authored JSON fixture — the Python brain of P92.**

## Performance

- **Duration:** 13 min
- **Started:** 2026-05-28T01:21:28Z
- **Completed:** 2026-05-28T01:34:54Z
- **Tasks:** 2 (plus 1 hot-fix commit)
- **Files created:** 5 (state.py, curriculum.py, prompts.py, runtime.py, 01_press_play.json)
- **Files modified:** 1 (__init__.py re-exports)
- **Lines:** 951 total (state 55 / curriculum 121 / prompts 200 / runtime 575)

## Accomplishments

- **LessonRuntime FSM lands end-to-end.** 8 states + 5 transitions + 1 Hz tick_loop + 6 callback methods. Full lifecycle (load → begin → ack_action → advancing) works synchronously without an event loop; async _finish_when_dwelled scheduled only when a loop runs.
- **Single-writer Invariant #1 binding enforced.** All LearnState writes live inside runtime.py's on_enter_<state> callbacks. The AST gate test_runtime_invariants.py stays green across both task commits.
- **TONE-04 anti-slop lock landed.** _FORBIDDEN_TUTOR_MOVES_LOCK contains all 4 REQUIRED_LOCK_TOKENS (COMPLIMENT / SUMMARIZE / PREVIEW / "CLOSE with an upbeat hook"). The lock lands as the FINAL block of the composed tutor system instruction (strongest-recency rule; mirrors COACH_CLOSING_BLOCK precedent).
- **TONE-02 fixture binding.** Lesson script ships as a hand-authored JSON file. LessonRuntime reads tutor_speak.text VERBATIM into LearnTutorSpeak envelopes — zero generative writes (AST gate test_scripts_are_fixtures.py confirms).
- **7 test files flipped skip → PASS.** test_lesson_runtime_smoke.py (2 tests) + test_advancement_gates.py (5 tests) + test_prompts.py (5 tests) + test_tutor_system_instruction_lock.py (2 tests) = 14 tests now LIVE. AST gates (test_runtime_invariants / test_scripts_are_fixtures / test_no_new_ws_port / test_no_pioneer_brand_marks) stay green.

## Task Commits

1. **Task 1: Land LearnState + Curriculum + Lesson Script + Tutor Prompts** — `7144fd2f` (feat)
   - Creates: state.py, curriculum.py, prompts.py, transcripts/hello_world/01_press_play.json
   - Modifies: __init__.py (re-exports 4 names)
   - Flipped tests: test_prompts.py (5) + test_tutor_system_instruction_lock.py (2)

2. **Task 2: Land LessonRuntime FSM** — `3838e1d9` (feat)
   - Creates: runtime.py (575 lines — FSM + 6 callbacks + tick_loop + defensive emit wraps)
   - Modifies: __init__.py (re-exports LessonRuntime as 5th name)
   - Flipped tests: test_lesson_runtime_smoke.py (2) + test_advancement_gates.py (5)

3. **Hot-fix: docstring grep-gate violation** — `66b50397` (fix)
   - Rephrases runtime.py docstring tokens "open_input" / "set_callback" so CI grep gate (which doesn't strip docstring lines) returns 0 matches.

**Plan metadata commit:** _(landed at end of this section)_

## Files Created/Modified

- `src/vibemix/learn/state.py` — LearnState mutable dataclass (6 fields: current_course_id / current_lesson_id / current_controller_id / current_beat_index / strike_count / lesson_started_at). Mutable on purpose — single-writer invariant enforced statically via AST gate, NOT Python typing.
- `src/vibemix/learn/curriculum.py` — COURSE_FRAMES dict (1 entry: course_0) + LessonMeta frozen dataclass with lazy .script @property (re-reads from disk each access) + CURRICULUM dict (1 entry: L0.00-press-play pointing at hello_world/01_press_play.json). P94/95/96 add the other 35 lessons via this same table.
- `src/vibemix/learn/prompts.py` — build_tutor_system_instruction composes 5 fragments in order: (1) base via build_system_instruction(skill="intermediate", mode="coach", mood="teacher", include_*=False), (2) COURSE_FRAMES[course_id], (3) _controller_frame(controller_id), (4) CURRICULUM[lesson_id].system_instruction_addendum (≤200 chars enforced), (5) _FORBIDDEN_TUTOR_MOVES_LOCK LAST. Unknown course/lesson raises ValueError; >200-char addendum raises ValueError.
- `src/vibemix/learn/runtime.py` — LessonRuntime(StateMachine) — see Architecture below.
- `src/vibemix/learn/transcripts/hello_world/01_press_play.json` — hand-authored fixture (lesson_id=L0.00-press-play, title="press play", 1 tutor_speak beat, 3 hints, expected_action=play button down on deck A). Addendum 122/200 chars; tutor_speak.text 59/280 chars; tts_marker 10/64 chars.
- `src/vibemix/learn/__init__.py` — re-exports 6 names: COURSE_FRAMES / CURRICULUM / LearnState / LessonMeta / LessonRuntime / MidiMirror / build_tutor_system_instruction. P91's MidiMirror re-export preserved.

## Architecture — LessonRuntime FSM

```
States (8):
  idle (initial)
    └── load(lesson_id, course_id, controller_id) ──► loaded
                                                       └── begin() ──► awaiting_action
                                                                        │
  awaiting_action ─── tick_loop @30s + strike_count<3 ──► strike()
                                                          │
                  ┌── ack_action(midi) [cond: action_matches] ──► advancing
                  │                                                │
                  └── skip()           [cond: min_dwell_elapsed]  finish()
                                                                   ▼
  hint_strike_1 ─── tick_loop @30s + strike_count<3 ──► strike()  completed (terminal)
  hint_strike_2 ─── tick_loop @30s + strike_count<3 ──► strike()      │
  hint_strike_3 ─── (no further strike — capped)                       │
       │                                                                ▼
       ├── ack_action(midi) ──► advancing                          load(...) ──► loaded
       └── skip()             ──► advancing                        (post-completion relaunch)
```

**Smoke-test lifecycle emit counts** (verified via mock_ipc_router.emit.call_args_list):

| # | Envelope type | Count | Triggered by |
|---|---------------|-------|--------------|
| 1 | `ipc.learn.lesson_loaded` | 1 | on_enter_loaded |
| 2 | `ipc.learn.highlight` | 1 | on_enter_awaiting_action (amber pulse-ring on play:A) |
| 3 | `ipc.learn.tutor_speak` | 1 | on_enter_awaiting_action calls _emit_tutor_beat(0) |
| 4 | `ipc.learn.advance` | 1 | on_enter_advancing (reason="action_matched") |
|   | **TOTAL** | **4** | |

Synchronous test path stops at `advancing` (no async loop → no `_finish_when_dwelled` scheduling). The live P92-04 path runs in the asyncio loop and completes the chain to `completed` after the 45 s min-dwell + 0.7 s settle.

**learn_tutor model resolution** (P92-01 router entry): `model_router.resolve("learn_tutor")` returns `("gemini-3.5-flash", ServiceTier.STANDARD)`. The model id is NOT hardcoded anywhere in `src/vibemix/learn/`; the CI grep gate `scripts/release/check_no_hardcoded_model.sh src/vibemix/learn/` stays green.

## Decisions Made

1. **Drop `final=True` on `completed` state** (vs the planner-suggested marker). The `load` transition lets a freshly-completed runtime re-load a new lesson (post-skip / post-completion relaunch). python-statemachine rejects a final state with outgoing transitions at class-definition time (`InvalidDefinition: Cannot declare transitions from final state`). Removing `final=True` keeps the relaunch flow; the trap-state check still passes because `load` provides the outgoing edge. Documented in the `completed = State()` comment.

2. **Dual-use guard signature for `action_matches`.** Tests in `test_advancement_gates.py` call `rt.action_matches({...}, expected={...})` directly, but the FSM `cond=` path calls it from the framework with only the user's `midi` kwarg. Solution: `def action_matches(self, midi=None, expected=None, **_kwargs)` — when `expected` is omitted, read from `CURRICULUM[current_lesson_id]`; when supplied, use as-is.

3. **`allow_event_without_transition = True`** at the class level. Without it, `send("skip")` with a failed guard raises `TransitionNotAllowed` — but the tests just call `send("skip")` and expect state to stay put. Setting the flag converts failed-guard send into a silent no-op.

4. **Loop-probe before `create_task`.** `asyncio.create_task` creates the coroutine eagerly then attempts to schedule, so a failed schedule leaves an un-awaited coroutine that pytest warns about. The probe `asyncio.get_running_loop()` raises RuntimeError outside a loop — we catch it and skip the coroutine creation entirely.

5. **`_last_was_match` flag set in transition action callbacks** (`on_ack_action` / `on_skip`) that fire DURING the transition, BEFORE the `on_enter_<state>` callback. This is the cleanest way to pass the trigger reason from a guarded transition into the entry callback without coupling the entry to the event name.

6. **Defensive try/except around every `ipc_router.emit` + `progress_store` call.** A single envelope failure (validation error, network glitch in live path) must not wedge the FSM. Failures print to stderr; FSM state machine proceeds. Documented as a Rule-2 deviation (auto-add critical functionality — robustness for a stateful FSM).

7. **Re-export `__init__.py` updated incrementally.** Task 1 added 4 names; Task 2 added LessonRuntime as the 5th. The alternative (one-shot edit with all 5 names in Task 1) would have caused an import error because `runtime.py` doesn't exist yet in Task 1's commit.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] Dropped `final=True` on `completed` state**
- **Found during:** Task 2 (LessonRuntime instantiation)
- **Issue:** Plan/RESEARCH suggested `completed = State(final=True)` AND `load = idle.to(loaded) | completed.to(loaded)`. python-statemachine rejects this combination at class-definition time: `InvalidDefinition: Cannot declare transitions from final state. Invalid state(s): ['completed']`.
- **Fix:** Removed `final=True`. The trap-state check still passes because `load` provides the outgoing edge from `completed`. Documented in the class attribute comment.
- **Files modified:** `src/vibemix/learn/runtime.py`
- **Verification:** All 7 test files for this plan pass.
- **Committed in:** `3838e1d9` (Task 2 commit)

**2. [Rule 2 — Missing Critical] Loop-probe before `asyncio.create_task` in `on_enter_advancing`**
- **Found during:** Task 2 (`test_lesson_runtime_smoke.py::test_full_lifecycle` first run)
- **Issue:** RESEARCH skeleton used `asyncio.create_task(self._finish_when_dwelled())` with `try/except RuntimeError`. But `create_task` creates the coroutine eagerly THEN attempts to schedule it, so a `RuntimeError` (no running loop in tests) leaves an un-awaited coroutine — pytest emits RuntimeWarning: "coroutine '_finish_when_dwelled' was never awaited".
- **Fix:** Probe with `asyncio.get_running_loop()` FIRST; only call `create_task` when a loop exists. No coroutine created in the test path.
- **Files modified:** `src/vibemix/learn/runtime.py`
- **Verification:** No more RuntimeWarning in pytest output for `test_lesson_runtime_smoke.py`.
- **Committed in:** `3838e1d9` (Task 2 commit)

**3. [Rule 2 — Missing Critical] `allow_event_without_transition = True`**
- **Found during:** Task 2 (`test_advancement_gates.py::test_min_dwell_blocks_skip` first run)
- **Issue:** RESEARCH skeleton didn't mention this flag. Without it, `rt.send("skip")` with a False `min_dwell_elapsed` guard raises `TransitionNotAllowed`. But the test contract is `rt.send("skip"); assert state == "awaiting_action"` — no try/except.
- **Fix:** Set `allow_event_without_transition = True` at the class level. Failed-guard sends now return None silently; state stays put.
- **Files modified:** `src/vibemix/learn/runtime.py`
- **Verification:** All 5 `test_advancement_gates.py` tests pass.
- **Committed in:** `3838e1d9` (Task 2 commit)

**4. [Rule 2 — Missing Critical] Dual-use signature for `action_matches`**
- **Found during:** Task 2 (`test_advancement_gates.py::test_cc_drop_30pct` + `test_button_press` first run)
- **Issue:** RESEARCH `action_matches(self, midi)` reads from `CURRICULUM[current_lesson_id]`. But `test_advancement_gates.py` calls `rt.action_matches({...}, expected={...})` — passing the expected action directly. Without dual-signature support, those tests would have to drive the full FSM lifecycle to load a lesson first.
- **Fix:** `def action_matches(self, midi=None, expected=None, **_kwargs) -> bool` — when `expected` is None (FSM cond= path), read from CURRICULUM; when supplied (direct-test path), use as-is.
- **Files modified:** `src/vibemix/learn/runtime.py`
- **Verification:** All 5 advancement-gate tests pass.
- **Committed in:** `3838e1d9` (Task 2 commit)

**5. [Rule 2 — Missing Critical] Defensive try/except around every emit / progress_store call**
- **Found during:** Task 2 design (preemptively, not test-driven)
- **Issue:** A single envelope validation failure or stale progress store would wedge the FSM mid-lesson. The lesson HUD would then be stuck on a broken state with no recovery path.
- **Fix:** Every `ipc_router.emit` and `progress_store.*` call wrapped in try/except. Failures print bracket-tagged errors to stderr (matches the project's logging convention); FSM state machine proceeds. The `# pragma: no cover` markers note these are defensive paths not exercised by happy-path tests.
- **Files modified:** `src/vibemix/learn/runtime.py`
- **Verification:** All tests pass; no spurious stderr in happy-path test output.
- **Committed in:** `3838e1d9` (Task 2 commit)

**6. [Rule 1 — Bug] Docstring tokens tripped the MIDI-listener grep gate**
- **Found during:** Phase-level validation (VALIDATION.md Check 5)
- **Issue:** `runtime.py` docstring contained the literal substrings `open_input` and `set_callback` inside backticks (documenting what we do NOT do). The CI grep gate `git grep -E "open_input|set_callback" src/vibemix/learn/runtime.py | grep -v -E '^[^:]+:[0-9]+:\s*#'` only strips `#`-prefixed comments, not docstring lines — so the gate showed 2 offenders.
- **Fix:** Rephrased the docstring without using the literal tokens; the underlying invariant (no second MIDI listener) is still documented in plain prose.
- **Files modified:** `src/vibemix/learn/runtime.py`
- **Verification:** `git grep -E "open_input|set_callback" src/vibemix/learn/runtime.py` returns 0 matches; all tests still pass.
- **Committed in:** `66b50397` (separate hot-fix commit)

**7. [Rule 2 — Missing Critical] `runtime.py` line count exceeds RESEARCH's ≤300-line estimate**
- **Found during:** Task 2 final review
- **Issue:** RESEARCH §Pattern 1 estimated runtime.py at ≤300 lines. Actual: 575 lines.
- **Fix:** None — the additional lines are comprehensive docstrings (~150 lines) + defensive emit-wrap try/except blocks (~80 lines) + the dual-use `action_matches` documentation (~30 lines). The non-docstring/non-comment "code+docstring" line count is 423. Trimming would reduce readability and remove safety nets that protect the FSM from envelope-validation transients.
- **Files modified:** N/A — this is a deviation documentation note, not a code change.
- **Verification:** All 22 tests pass; the wc is bookkeeping.
- **Committed in:** N/A

---

**Total deviations:** 7 auto-fixed (1 plan-spec bug — final=True; 5 missing critical — robustness + dual-signature + control flow; 1 line-count deviation note)
**Impact on plan:** All deviations preserve the plan's contracts; tests landed by Plan 92-02 all pass as-is. No scope creep — every deviation closes a robustness gap the plan-time skeleton did not anticipate.

## Issues Encountered

- **`MagicMock` vs `Mock` for `progress_store` in the executor verify-direct script.** First verification run used `Mock()` which doesn't support `__getitem__` — the runtime's `LearnLessonLoaded.make(progress_dots=...)` defensive path treats the MagicMock as iterable. Fixed by using `MagicMock` (matches the actual test pattern in `_make_runtime`). Not a code bug — was an issue with my verify-direct script.

- **python-statemachine `current_state` deprecation warnings.** The library deprecated `current_state` in favor of `configuration`. Tests use `current_state`; we keep using it. Future cleanup (P94+) when the deprecation upgrade is forced.

## Threat Flags

None — every new file extends the threat-model surface the plan anticipated:
- LessonRuntime is the sole writer of LearnState (T-92-03-01 mitigated by AST gate).
- LessonRuntime never writes MusicState/ControllerState (T-92-03-02 mitigated by same gate).
- No generative writes to tutor_speak.text (T-92-03-03 mitigated by test_scripts_are_fixtures.py — passes).
- 4-forbidden-moves lock preserves all 4 required tokens (T-92-03-04 mitigated).
- Lock lands LAST (T-92-03-05 mitigated by `test_lock_is_last_block_for_strongest_recency`).
- tick_loop callbacks are sync emits — no file I/O, no LLM call, no blocking work (T-92-03-06 mitigated by design).
- No hardcoded model literals in `src/vibemix/learn/` (T-92-03-07 mitigated; CI gate green).
- No second MIDI listener (T-92-03-08 mitigated; CI grep gate now returns 0 after docstring hot-fix).

## User Setup Required

None — no external service configuration required. The full plan landed entirely under `src/vibemix/learn/` and is exercised by unit tests via mocked `ipc_router` / `progress_store` / `midi_mirror` / `controller_state`. Live wire-in to `__main__.main()` (the asyncio loop + real ipc_router + real progress_store) is Plan 92-04's job.

## Next Phase Readiness

Plan 92-04 (LessonRuntime wire-in to `__main__.main()` + ProgressStore + persistence) is unblocked:

- `LessonRuntime` is importable + instantiable + all 8 states + 5 transitions + callbacks wired.
- `LearnState` is the mutable single-writer dataclass (Invariant #1 binding stays green when 92-04 adds its `__main__.py` edits, provided those edits ONLY READ `LearnState`).
- `CURRICULUM["L0.00-press-play"]` returns a `LessonMeta` with lazy `.script` property — Plan 92-04's `start_lesson` IPC handler can dispatch on `lesson_id`.
- `build_tutor_system_instruction` is callable — Plan 92-04 / 94 wire the actual LLM emit site (Plan 94 owns the live `generate_content` call that uses this instruction).
- All 7 test files (smoke + advancement + prompts + lock + 4 AST gates) are LIVE and green; Plan 92-04 inherits a stable test surface.

## Self-Check: PASSED

- All 5 files created exist at expected paths (state.py, curriculum.py, prompts.py, runtime.py, JSON fixture).
- All 3 commits exist: `7144fd2f` (Task 1), `3838e1d9` (Task 2), `66b50397` (hot-fix).
- All 22 tests in `tests/learn/` pass (1 skip for `test_progress_persistence.py` — awaits Plan 92-04).
- All 5 phase-level VALIDATION.md checks pass.

---

*Phase: 92-lesson-runtime-ai-highlight-contract*
*Completed: 2026-05-28*
