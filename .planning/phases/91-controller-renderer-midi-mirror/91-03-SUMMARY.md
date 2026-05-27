---
phase: 91-controller-renderer-midi-mirror
plan: 03
subsystem: learn
tags: [learn, midi-mirror, ipc, ws-bus, port-watcher, threading-lock, render-01, render-02, 30hz-cadence]

# Dependency graph
requires:
  - "91-01 (LearnControllerDetected + LearnMidiPosition wrappers in vibemix.ui_bus.learn_messages)"
  - "91-02 (5 Python test files + 14 TS test stubs; this plan flips 4 Python skip → green)"
provides:
  - "vibemix.learn subpackage (2 files): __init__.py exports MidiMirror; midi_mirror.py is the sole writer of ipc.learn.midi_position envelopes"
  - "MidiMirror class: 30 Hz delta-coalesced position snapshotter + thread-safe controller_detected queue"
  - "ws_broadcast accepts midi_mirror=None kwarg; 30 Hz tick gains drain-then-snapshot block AFTER mascot emit, BEFORE existing ipc.session.snapshot block — strict ordering pinned by per-tick test assertion"
  - "__main__.main(): instantiates ONE MidiMirror, layers bind_profile/queue_controller_detected/unbind on top of the existing single-state port_watcher callback, threads midi_mirror into ws_broadcast(...)"
  - "Backend half of P91 is COMPLETE — Plans 04 (Rust shell) + 05 (TS webview) can subscribe to the wire stream now"
affects: [91-04, 91-05, 91-06, 91-07, 92, 93, 94, 95, 96]

# Tech tracking
tech-stack:
  added: []  # No new dependencies — pure additive Python code on existing deps (mido, websockets, dataclasses, threading)
  patterns:
    - "Cross-thread async-safe queue via threading.Lock + locked copy+clear (drain_pending_detected) — uniform with ControllerState's state.py:144 lock primitive, lock window microseconds, never held across await"
    - "Layered port_watcher callback: handle_port_change_single_state retained (single-state in-place mutation invariant) + MidiMirror lifecycle hooks (bind/enqueue/unbind) layered on top — no replace, only compose"
    - "30 Hz tick per-iteration error isolation: each new step (drain / per-envelope emit / snapshot / pos emit) in its own try/except logging '[learn * err]' to stderr — matches the existing per-loop error-isolation pattern from CLAUDE.md §Architecture (a loop failure never wedges the loop)"
    - "Drain-then-snapshot strict ordering inside a single 30 Hz tick: controller_detected envelopes from the queue hit the wire BEFORE any midi_position from the same iteration — pinned by per-tick test assertion that 'frame following controller_detected MUST be midi_position'"
    - "Test harness pattern for 30 Hz cadence: monkey-patch websockets.serve with AsyncMock + asyncio.sleep with tick-counting fast-forward + fake LongLivedClient that records sent payloads — canonical to test_mood_change_envelope.py and now extended to count both mascot frames and learn frames for cadence + ordering pins"

key-files:
  created:
    - "src/vibemix/learn/__init__.py — package marker, exports MidiMirror"
    - "src/vibemix/learn/midi_mirror.py — MidiMirror class (332 lines; sole writer of ipc.learn.midi_position; thread-safe controller_detected queue)"
    - ".planning/phases/91-controller-renderer-midi-mirror/91-03-SUMMARY.md"
    - ".planning/phases/91-controller-renderer-midi-mirror/deferred-items.md (out-of-scope failures from Plan 91-01 capabilities snapshot drift + concurrent-session work-in-flight)"
  modified:
    - "src/vibemix/runtime/ws_bus.py — ws_broadcast gains midi_mirror=None kwarg; 30 Hz tick gains drain-then-snapshot block between mascot emit and existing snapshot/status blocks; all guards isolated per-step"
    - "src/vibemix/__main__.py — MidiMirror instantiated after MidiMacOS; layered port_watcher on_change callback wires bind_profile + queue_controller_detected + unbind; midi_mirror=midi_mirror threaded into ws_broadcast(...); '-> midi_mirror wired' breadcrumb"
    - "tests/runtime/test_ws_broadcast_30hz_under_learn_load.py — Plan 02 stub body replaced with a real harness (cadence ±5% pin + per-tick drain-then-snapshot ordering assertion)"

key-decisions:
  - "MidiMirror snapshot() returns None when no profile is bound (defensive — a None profile means 'no schema to read'). bind_profile() resets the delta cache so the FIRST snapshot after bind always emits a fresh full frame ('fill the freshly-rendered SVG with current state' — pinned by test_first_frame_after_bind)"
  - "Cross-boundary contract: ALL ipc.learn.* emits leave through the SAME ws_broadcast 30 Hz tick (Invariant #4 — no second WS listener). The port_watcher callback ENQUEUES via queue_controller_detected and NEVER calls _send_all directly (that closure is not reachable from outside ws_broadcast). The mirror's queue lock is microseconds wide, never held across an await — a future Rust-direct midir caller or daemon-thread caller works without rework"
  - "Per-tick drain ordering: drain BEFORE snapshot every tick, unconditionally (drain_pending_detected() returns [] when empty — cheap). Order is significant: on a plug-in tick, the controller_detected envelope MUST reach the wire before the FIRST midi_position envelope for that controller — the test asserts this byte-offset relationship in the sent_payloads stream"
  - "Layered port_watcher callback (not replace): __main__'s _on_midi_port_change calls handle_port_change_single_state(holder, event) FIRST (preserves existing mark_connected/mark_disconnected + listener-thread restart behavior), THEN layers MidiMirror's lifecycle (bind_profile + queue on connect; queue + unbind on disconnect). Order matters within the MidiMirror layer: bind BEFORE enqueue on connect (so snapshot() reads a bound profile when it next fires); enqueue BEFORE unbind on disconnect (so envelope payload is well-formed before profile clears)"
  - "Per-step error isolation in ws_broadcast: 4 distinct try/except blocks ([learn drain err] / [learn detected emit err] / [learn snapshot err] / [learn pos emit err]). Matches the per-loop pattern already in this file (a learn-side fault never touches the mascot path above or the ipc.session.snapshot path below — invariant: the 30 Hz cadence holds even if MidiMirror raises)"

patterns-established:
  - "Single-writer Learn envelopes (Invariant #1 extension): MidiMirror is the SOLE writer of ipc.learn.midi_position; the port_watcher callback enqueues the SOLE source of ipc.learn.controller_detected. Both go through ws_broadcast's _send_all closure — no other emit path exists today"
  - "Backward-compat via default=None kwarg: ws_broadcast(midi_mirror=None) preserves the ~10 existing test callers and the test_mood_change_envelope.py::test_ws_broadcast_snapshot_includes_new_phase_13_fields integration test (verified green post-change). Future kwarg additions to ws_broadcast should follow this default-None pattern"
  - "Stub-to-real test promotion (Plan 02 → Plan 03 contract): the Plan 02 stub used `raise pytest.skip.Exception(...)` after the importorskip gate; Plan 03 replaces the stub body with a real harness following the canonical async ws test pattern. The test acceptance criteria are now positive (passes) rather than just collectable (skip)"

requirements-completed: [RENDER-01, RENDER-02]  # Phase requirements per 91-03 PLAN frontmatter

# Metrics
duration: 15min
completed: 2026-05-28
---

# Phase 91 Plan 03: Controller Renderer + MIDI Mirror — Python Backend Summary

**MidiMirror class + ws_broadcast wiring + __main__ port_watcher layering — the engine that turns a physical MIDI knob twist into a wire frame the Learn webview can consume, riding the existing 30 Hz tick on the SAME ws:8765 socket (Invariants #1 + #4 preserved).**

## Performance

- **Duration:** ~15 min (2026-05-28T12:12:35Z → ~12:27Z)
- **Tasks:** 2 atomic task commits + this metadata commit
- **Files created:** 3 (2 source + 1 deferred-items + this SUMMARY)
- **Files modified:** 3 (`ws_bus.py`, `__main__.py`, `test_ws_broadcast_30hz_under_learn_load.py`)
- **Tests flipped SKIP→PASS:** 4 (3 in `test_midi_mirror_unit.py` + 1 in `test_ws_broadcast_30hz_under_learn_load.py`)

## Accomplishments

- **`MidiMirror` class shipped** (`src/vibemix/learn/midi_mirror.py`, 332 lines) — the sole writer of `ipc.learn.midi_position` envelopes. 6 public methods (`bind_profile`, `unbind`, `snapshot`, `controller_detected`, `queue_controller_detected`, `drain_pending_detected`) + 1 internal helper (`_read_current_positions`). Reads (read-only) `ControllerState.deck_snapshot()` via the existing `state.py:144` lock; writes nothing back. Thread-safe queue under `threading.Lock` so the port_watcher callback (asyncio main loop) and a future daemon-thread or Rust-direct caller all work without rework.
- **`ws_broadcast` accepts `midi_mirror=None` kwarg** (`src/vibemix/runtime/ws_bus.py`) — backward-compat preserved (verified by `test_ws_broadcast_snapshot_includes_new_phase_13_fields` green post-change). The 30 Hz tick gains a drain-then-snapshot block AFTER the mascot emit and BEFORE the existing ipc.session.snapshot block. Strict ordering: drain queue (1 try/except per envelope), then pull snapshot (1 try/except), then emit position (1 try/except) — 4 distinct error-isolated steps so a learn-side fault never touches the mascot path or the cadence loop.
- **`__main__.main()` wires the lifecycle** (`src/vibemix/__main__.py`) — instantiates ONE `MidiMirror` after `MidiMacOS()`, prints `-> midi_mirror wired` to stderr, layers `bind_profile` / `queue_controller_detected` / `unbind` on top of the existing `handle_port_change_single_state` callback (no replace; the single-state in-place mutation is preserved). Threads `midi_mirror=midi_mirror` into the `asyncio.create_task(ws_broadcast(...))` call.
- **All 4 previously-skipped Python tests flip from SKIP → PASS** — `test_no_emit_when_steady`, `test_first_frame_after_bind`, `test_delta_emit_when_one_field_changes` (`tests/learn/test_midi_mirror_unit.py`); `test_30hz_cadence_holds_with_midi_mirror_kwarg` (`tests/runtime/test_ws_broadcast_30hz_under_learn_load.py`). The Plan 02 stub body was replaced with a real harness following the canonical `test_mood_change_envelope.py` async-ws test pattern.
- **All 5 grep gates stay green** — `test_no_new_ws_port.py` (Invariant #4), `test_no_pioneer_brand_marks.py` (Apache-clean), `test_controller_detected_roundtrip` + `test_controller_detected_rejects_missing_field` + `test_midi_position_roundtrip` + `test_midi_position_rejects_out_of_range` (Plan 01's envelope parity tests).
- **No regression in existing tests** — full `tests/runtime/` + `tests/test_main_smoke.py` runs 299 passed; wider suite (excluding e2e + concurrent-session-affected dirs) runs 4450 passed with 8 failures ALL pre-existing and unrelated to Plan 03 (capability snapshot drift from Plan 91-01 + 6 audit/repo/scripts/sidecar failures from other sessions' uncommitted work — see `deferred-items.md`).

## Task Commits

Each task was committed atomically by named paths only (concurrent-session discipline — never `git add -A`):

1. **Task 1: Create `vibemix.learn` subpackage with `MidiMirror`** — `63d5c7f2` (feat) — 2 new files (`src/vibemix/learn/__init__.py` + `src/vibemix/learn/midi_mirror.py`). Verify: 3 MidiMirror unit tests + the `test_no_new_ws_port` grep gate all PASS.
2. **Task 2: Wire MidiMirror into `ws_broadcast` + `__main__.main()`** — `e572a8a7` (feat) — 3 named files modified (`ws_bus.py`, `__main__.py`, `test_ws_broadcast_30hz_under_learn_load.py`). Verify: ws_broadcast accepts `midi_mirror` kwarg; drain precedes snapshot in the tick; cadence ±5% holds; existing mood envelope test stays green.

## Files Created

### Source (2 files)

- `src/vibemix/learn/__init__.py` (24 lines) — package marker; one-line re-export of `MidiMirror`; module docstring naming RENDER-01 + RENDER-02 + Invariant #1 + Invariant #4.
- `src/vibemix/learn/midi_mirror.py` (315 lines) — the `MidiMirror` class. SPDX header + threading-discipline docstring naming the cross-thread queue contract + the 4 cardinal invariants (single-writer, one-socket, trust-existing-listener, no-mido-listener-here). 6 public methods + 1 internal `_read_current_positions` helper that consumes `ControllerState.deck_snapshot()` (the documented `{deck_letter: {field: int, ...}, "xfader": int, "connected": bool}` shape) and produces the wire-shape dict `{"<field>:<deck>": int}` per RESEARCH §Pattern 2.

### Documentation (2 files)

- `.planning/phases/91-controller-renderer-midi-mirror/91-03-SUMMARY.md` — this file.
- `.planning/phases/91-controller-renderer-midi-mirror/deferred-items.md` — out-of-scope failures discovered during the wider regression run (capability snapshot drift from Plan 91-01 + 6 audit/repo/scripts/sidecar failures from concurrent-session uncommitted work).

## Files Modified

### Source (2 files)

- `src/vibemix/runtime/ws_bus.py` — additive only:
  - `ws_broadcast` signature: added `midi_mirror=None` as the last keyword-only parameter (the kwarg is `Any | None`; default `None` preserves backward-compat for the ~10 existing test callers).
  - 30 Hz tick body: AFTER the existing mascot dead-drop block (~line 573) and BEFORE the existing `tick += 1` snapshot block (~line 578), inserted a `if midi_mirror is not None:` block that:
    1. **Drain step:** `midi_mirror.drain_pending_detected()` (try/except → `[]` on exception, logged `[learn drain err]`); iterate the returned list and `await _send_all(envelope)` for each (try/except per envelope, logged `[learn detected emit err]`).
    2. **Snapshot step:** `midi_mirror.snapshot()` (try/except → `None` on exception, logged `[learn snapshot err]`); if non-None, `await _send_all(pos_frame)` (try/except, logged `[learn pos emit err]`).
  - The drain step executes UNCONDITIONALLY each tick (cheap when the queue is empty — `[]` short-circuit). The strict drain-before-snapshot order is the wire contract (controller_detected MUST precede midi_position for the same plug-in tick).

- `src/vibemix/__main__.py` — additive only:
  - After `midi_macos = MidiMacOS()` line: `from vibemix.learn.midi_mirror import MidiMirror; midi_mirror = MidiMirror(controller_state=midi_macos.controller_state); print("-> midi_mirror wired", file=sys.stderr)`.
  - Before the existing `midi_macos.start_port_watcher(midi_watcher_stop)` call: built a `ListenerHolder` + `_on_midi_port_change` wrapper that calls `handle_port_change_single_state(holder, event)` FIRST (preserves the single-state lifecycle), THEN layers `midi_mirror.bind_profile(profile) + midi_mirror.queue_controller_detected(connected=True, ...)` on `('connected', ...)` events; `midi_mirror.queue_controller_detected(connected=False, ...) + midi_mirror.unbind()` on `('disconnected', ...)` events. Order within the MidiMirror layer matters: bind BEFORE enqueue (snapshot reads a bound profile next call); enqueue BEFORE unbind (envelope payload well-formed).
  - In the existing `asyncio.create_task(ws_broadcast(...))` call: appended `midi_mirror=midi_mirror` as the last kwarg.

### Tests (1 file)

- `tests/runtime/test_ws_broadcast_30hz_under_learn_load.py` — Plan 02 stub body replaced with a real harness following the canonical async-ws pattern in `tests/ui_bus/test_mood_change_envelope.py`:
  - Monkey-patches `vibemix.runtime.ws_bus.websockets.serve` with `AsyncMock(return_value=mock_server)`.
  - Monkey-patches `vibemix.runtime.ws_bus.asyncio.sleep` with a tick-counting fast-forward (stops `stop_event` after exactly 100 calls).
  - Builds a `LongLivedClient` that records every `send(payload)` call into `sent_payloads`.
  - Drives `ws_broadcast(fake_levels, state, manual_trigger, stop_event, midi_mirror=midi_mirror_stub)` for ~100 ticks under `asyncio.wait_for(timeout=5.0)`.
  - Asserts mascot_emits within ±5% of 100 (cadence pin — RESEARCH §Assumption A1).
  - Asserts per-tick drain-then-snapshot order: on the tick where the (single, queued-once-on-call-50) `controller_detected` envelope is drained, the very next frame in `sent_payloads` MUST be a `midi_position` envelope (proves the drain block runs synchronously through the snapshot block before yielding to `asyncio.sleep`).

## Decisions Made

- **MidiMirror is sync-only by design** — every public method is a sync call, no `async def`. The thread-safe queue uses `threading.Lock` (microseconds-wide locked append + locked copy+clear), never held across an `await`. This is the LOAD-BEARING decision: a sync API means the port_watcher callback (which `_safe_invoke` runs either sync or as a coroutine — see `watcher.py:110`) stays sync, which keeps the cross-boundary contract simple. A future Rust-direct `midir` caller can call `queue_controller_detected` from any thread without `asyncio.run_coroutine_threadsafe`-style plumbing. The 30 Hz tick is the SOLE consumer (drain + snapshot) and runs on the asyncio main loop where the `await _send_all(...)` calls live; that's the only async surface needed.
- **First-frame-after-bind emit contract** — `bind_profile()` always resets `self._last_positions = {}`, so the next `snapshot()` call returns a non-None envelope. This is the "fill the freshly-rendered SVG with current state" guarantee — without it, the SVG would mount but every knob/fader stays at its default visual position until the user touches one. Pinned by `test_first_frame_after_bind`.
- **Order matters in the port_watcher callback** — connect: `bind_profile(profile)` BEFORE `queue_controller_detected(connected=True, ...)`; disconnect: `queue_controller_detected(connected=False, ...)` BEFORE `unbind()`. Connect: bind first so subsequent snapshot() calls in `ws_broadcast` see the bound profile. Disconnect: enqueue first so the envelope payload's `controller_id` / `display_name` are still well-formed before `unbind()` clears `self._profile`. The plan §behavior spells both orderings out explicitly; the test stack does not pin them (those are implementation details of the wiring, not visible at the wire level) but they're documented in the docstrings and inline comments for the next session.
- **30 Hz drain ordering is part of the wire contract, NOT just an implementation detail** — within a single tick, the controller_detected envelope MUST reach the wire BEFORE any midi_position envelope from the same tick, so the webview sees "controller appeared" before it sees position data for that controller. Pinned by the new ordering assertion in `test_30hz_cadence_holds_with_midi_mirror_kwarg`: the frame at index `detected_idx + 1` MUST be `ipc.learn.midi_position` (proves drain runs synchronously through snapshot before yielding to `asyncio.sleep`). This is the test that would catch a future refactor that re-orders the two blocks.
- **The grep gate in `test_no_new_ws_port.py` scans for the LITERAL substring `websockets.serve`** — including in docstrings, since the gate ignores only lines whose `lstrip()` starts with `#`. My initial draft of `midi_mirror.py` mentioned the substring in three docstring contexts (the "no second `websockets.serve`" Invariant #4 framing). The gate tripped on those literal mentions. **Auto-fixed (Rule 3)** by rewording the docstrings to "no second WS listener bound here" — same meaning, no forbidden substring. The fix landed in the same Task 1 commit (no separate fix-up).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking Issue] Grep gate (`test_no_new_ws_port.py`) trips on docstring mentions of `websockets.serve`**

- **Found during:** Task 1 verify command — first run after writing `midi_mirror.py` + `__init__.py`.
- **Issue:** The Plan 02 grep gate (`tests/learn/test_no_new_ws_port.py`) walks `src/vibemix/learn/**/*.py` for the LITERAL substring `websockets.serve` outside lines that `lstrip().startswith("#")`. The plan's `<action>` block told me to "name the threading discipline" and "Invariant #4 statements" in the module docstring — and the cleanest framing of Invariant #4 IS "no second `websockets.serve`". My draft docstrings tripped the gate in 3 places (the `__init__.py` package docstring, the `midi_mirror.py` module docstring, and the `MidiMirror` class docstring §"One socket (Invariant #4)").
- **Fix:** Reworded all 3 sites from `no second ``websockets.serve``` → `no second WS listener bound here` / `no second WS listener`. Same semantic content, no forbidden substring.
- **Files modified:** `src/vibemix/learn/__init__.py`, `src/vibemix/learn/midi_mirror.py`.
- **Verification:** `pytest tests/learn/test_no_new_ws_port.py tests/learn/test_midi_mirror_unit.py` exits 0 with all 4 tests PASSED.
- **Committed in:** `63d5c7f2` (Task 1 atomic commit — the fix landed before the commit).

**2. [Rule 1 - Bug] Plan 02's `test_30hz_cadence_holds_with_midi_mirror_kwarg` test stub had `raise pytest.skip.Exception(...)` placeholder that needed to be replaced**

- **Found during:** Task 2 (the plan's `<verify>` block runs the test and expects PASSED).
- **Issue:** Plan 02 shipped a stub that "documents the contract via the assertion below; the assertion itself never runs because the early-skip above gates the body". The stub raised `pytest.skip.Exception("Plan 91-03 fills in the harness body...")`. The Plan 02 SUMMARY explicitly hands this to Plan 03 ("Plans 04 / 05 / 06 / 07 [...] depends on Plans 03+04+05 first" + "the plan executor for Plan 03 fills this in"). So this is NOT a deviation per se — it's a Plan 02 → Plan 03 hand-off contract — but it required me to write substantive test code (~150 lines of harness) that the plan's `<action>` block did not pre-specify in detail.
- **Fix:** Replaced the stub body with a real harness following the canonical `tests/ui_bus/test_mood_change_envelope.py::test_ws_broadcast_snapshot_includes_new_phase_13_fields` pattern. Added (a) tick-counting fast-forward `asyncio.sleep` patch that stops after exactly 100 ticks, (b) fake `LongLivedClient` that records every `send(payload)` call, (c) fake `MidiMirror` stub that returns a constant position frame every tick and a single queued envelope on call 50 (so the LongLivedClient is reliably connected by then), (d) cadence assertion mascot_emits within ±5% of 100, (e) per-tick drain-then-snapshot ordering assertion (frame after `controller_detected` MUST be `midi_position`).
- **Files modified:** `tests/runtime/test_ws_broadcast_30hz_under_learn_load.py`.
- **Verification:** `pytest tests/runtime/test_ws_broadcast_30hz_under_learn_load.py -v` exits 0 PASSED in 0.38 s.
- **Committed in:** `e572a8a7` (Task 2 atomic commit — same unit as the wiring it tests).

**3. [Rule 1 - Bug] First-pass cadence test asserted global ordering across all ticks (wrong) instead of per-tick ordering (correct)**

- **Found during:** First test run of the harness in Task 2.
- **Issue:** My initial harness asserted `detected_idx < first_position_idx` — global ordering: the first `controller_detected` in the wire stream must precede the first `midi_position`. This is WRONG. The Plan 03 invariant is **per-tick** ordering: on the tick where a detected envelope is drained, the position frame from THAT SAME TICK comes after it. Since the snapshot stub returns a constant frame every tick (no delta suppression), midi_position frames flow on every tick — they precede the controller_detected that's queued at tick 50. The first failed run reported `detected at index 117 but first midi_position at index 1` — exactly the right behavior, my assertion shape was wrong.
- **Fix:** Rewrote the ordering assertion to check the frame at `detected_idx + 1` is `midi_position` (per-tick adjacency — the drain block runs synchronously through the snapshot block before `asyncio.sleep` yields, so the two emits MUST be consecutive in `sent_payloads`).
- **Files modified:** `tests/runtime/test_ws_broadcast_30hz_under_learn_load.py`.
- **Verification:** Test now PASSED.
- **Committed in:** `e572a8a7` (Task 2 atomic commit — caught and fixed in the same edit cycle before the commit).

---

**Total deviations:** 3 auto-fixed (1 Rule 3 - Blocking Issue, 2 Rule 1 - Bug). None changed plan scope. All 3 were caught + fixed within the same task's edit-test loop before the task commit landed.

## Issues Encountered

- **Wider-suite pre-existing failures:** the post-Task-2 wider regression run reported 8 failures across `tests/audit/`, `tests/repo/`, `tests/scripts/`, `tests/security/`, `tests/sidecar/`. All 8 are pre-existing and unrelated to Plan 03's named files — verified by inspecting the failure traces and the changeset. Two of them (`test_capability_snapshot.py` x2) trace to Plan 91-01's `capabilities/default.json` edit that did not regenerate `SNAPSHOT.json`. The other 6 trace to concurrent-session work-in-flight on `live-tuning-or-brain` (other sessions have uncommitted modifications to `src/vibemix/agent/`, `src/vibemix/intel/`, `src/vibemix/prompts/`, and the audit/orphan baselines). Logged to `.planning/phases/91-controller-renderer-midi-mirror/deferred-items.md` per executor §SCOPE BOUNDARY.
- **No git deletions in any task commit** (verified via `git diff --diff-filter=D --name-only HEAD~1 HEAD` after each commit). Concurrent-session named-path staging discipline upheld.

## Threat Flags

No new security-relevant surface introduced. The 2 envelopes ride the existing `127.0.0.1:8765` loopback ws bus (Invariant #4 preserved — verified by the green `test_no_new_ws_port` grep gate); both envelopes are validated by the shared `_VALIDATOR` (Plan 01's `additionalProperties:false` at envelope + payload, `minLength:1` on string identifiers, `0..127` integer bound on `positions` values). The Plan 03 `<threat_model>` mitigations are all implemented:

- **T-91-03-01 (Tampering, single-writer regression):** MidiMirror never imports `MusicState`; never assigns into `controller_state`. Grep gate `git grep "controller_state\\.[a-z_]+\\s*=" src/vibemix/learn/midi_mirror.py` returns 0.
- **T-91-03-02 (DoS, snapshot blocks 30 Hz tick):** `deck_snapshot()` is already lock-guarded for short reads (state.py:144); `_read_current_positions` does one snapshot + an in-memory dict equality compare (sub-millisecond). Verified by the cadence pin (`test_30hz_cadence_holds_with_midi_mirror_kwarg`) — 100 ticks within ±5%.
- **T-91-03-03 (Tampering, MidiMirror mutates ControllerState):** code-review pinned by the absence of `controller_state.<attr> = ...` lines in the file; my draft has zero such lines.
- **T-91-03-04 (DoS, queue grows unbounded):** the queue is drained every 30 Hz tick (33 ms cadence); plug/unplug events are user-driven (≤1/s in normal use). No bound needed at P91 scale.
- **T-91-03-SC (Tampering, package installs):** accepted — ZERO new packages installed (Plan 03 is pure additive Python code on existing deps mido / websockets / dataclasses / threading).

## Next Phase Readiness

- **Plan 04 (Rust shell — `learn_window.rs` + `main.rs` registration)** unblocked — backend wire stream is now live. A `cargo tauri dev` build that spawns the existing sidecar will see the `-> midi_mirror wired` stderr breadcrumb at startup, and the Tauri `WebviewWindowBuilder` can open `learn.html` against an existing producer.
- **Plan 05 (TS LearnWindow renderer + FLX4 + _generic SVGs)** unblocked — the webview can `new WebSocket("ws://127.0.0.1:8765")` and receive `ipc.learn.controller_detected` + `ipc.learn.midi_position` frames. The wire shapes are pinned by Plan 01's schema (count parity green) and Plan 03's MidiMirror implementation (`_read_current_positions` produces the `<field>:<deck>` wire convention).
- **Plan 06 (9 non-FLX4 controller SVGs)** unblocked — same wire contract; the per-controller SVG just needs a matching `data-control-id` per the existing `midi/profiles/<id>.json` field bindings.
- **Plan 07 (Kaan ear-pass)** depends on Plans 04+05 first.
- **§LEARN-LATENCY-CONTINGENCY KAAN-ACTION** still queued — the latency gate (`tauri/ui/tests/learn/highlight-latency.test.ts`) runs in Plan 05; if P95 > 80 ms the Rust-direct `midir` listener contingency fires. Not in scope for Plan 03.
- **Capability SNAPSHOT.json drift** (logged in `deferred-items.md`) — flagged for Plan 91-04 (which already touches the Tauri capability surface) OR a Plan 01 fix-up commit. Plan 03 itself doesn't touch `capabilities/`.

## Self-Check: PASSED

- `src/vibemix/learn/__init__.py` exists + exports `MidiMirror` ✓
- `src/vibemix/learn/midi_mirror.py` exists + is 315 lines with SPDX header + module docstring naming RENDER-01/02 + Invariants #1 + #4 ✓
- `from vibemix.learn import MidiMirror` works ✓
- `from vibemix.learn.midi_mirror import MidiMirror` works ✓
- Both import paths refer to the same class object ✓
- `MidiMirror` exposes 6 named methods (`bind_profile`, `unbind`, `snapshot`, `controller_detected`, `queue_controller_detected`, `drain_pending_detected`) + `_read_current_positions` internal helper ✓
- `MidiMirror(controller_state=<fake>).snapshot()` returns `None` when no profile is bound ✓
- 2-queue / 1-drain round-trip returns 2-element list; next drain returns `[]` ✓
- `_detected_lock` is a `threading.Lock` instance ✓
- `ws_broadcast` signature contains `midi_mirror` parameter with default `None` ✓
- In `ws_bus.py`: byte-offset of `drain_pending_detected` (28062) < byte-offset of `midi_mirror.snapshot()` (28513) ✓
- `__main__.py` AST parses cleanly ✓
- `git grep "MidiMirror(controller_state=" src/vibemix/__main__.py` returns 1 match ✓
- `git grep "midi_mirror=midi_mirror" src/vibemix/__main__.py` returns 1 match ✓
- `git grep "queue_controller_detected" src/vibemix/__main__.py` returns 2 matches (connect + disconnect) ✓
- `git grep "drain_pending_detected" src/vibemix/runtime/ws_bus.py` returns 1 match ✓
- `git grep "bind_profile" src/vibemix/__main__.py` returns 2 matches (`bind_profile(profile)` + `from vibemix...` comment line) ✓
- `git grep "-> midi_mirror wired" src/vibemix/__main__.py` returns 1 match ✓
- `git grep "websockets.serve" src/vibemix/learn/` returns 0 matches ✓
- `git grep -E "open_input|set_callback" src/vibemix/learn/midi_mirror.py` returns 0 matches ✓
- All 9 backend tests pass: `pytest tests/learn/ tests/ipc/test_learn_envelope_parity.py tests/runtime/test_ws_broadcast_30hz_under_learn_load.py -v` exits 0 with 9 PASSED ✓
- Plan §verification end-to-end demo prints exactly: `None`, `True`, `None`, `True`, `True`, `True` ✓
- Existing `test_ws_broadcast_snapshot_includes_new_phase_13_fields` integration test stays green (backward-compat preserved via `midi_mirror=None` default) ✓
- `pytest tests/runtime/ tests/test_main_smoke.py -q` reports 299 passed ✓
- Wider suite (excluding e2e + concurrent-session-affected dirs) reports 4450 passed; 8 failures all pre-existing + logged to `deferred-items.md` ✓
- Two task commits exist:
  - `63d5c7f2` feat(91-03): land MidiMirror — 30 Hz delta-coalesced position snapshot + thread-safe controller_detected queue ✓
  - `e572a8a7` feat(91-03): wire MidiMirror into ws_broadcast 30 Hz tick + __main__ port_watcher ✓
- No git deletions in any task commit ✓ (verified via `git diff --diff-filter=D --name-only HEAD~1 HEAD` after each commit — empty both times)
- 0 modifications to shared files outside the 3 named files (`ws_bus.py`, `__main__.py`, `test_ws_broadcast_30hz_under_learn_load.py`) — `messages.schema.json`, `vite.config.ts`, `capabilities/default.json`, `learn_messages.py`, `ui_bus/__init__.py` all untouched ✓

---
*Phase: 91-controller-renderer-midi-mirror*
*Plan: 03*
*Completed: 2026-05-28*
