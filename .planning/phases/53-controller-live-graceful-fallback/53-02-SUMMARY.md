# 53-02 SUMMARY — Wire hot-plug watcher into the live session + disconnect/reconnect proof (BRINGUP-03)

status: complete
phase: 53-controller-live-graceful-fallback
plan: 02
wave: 2
depends_on: [53-01]

## What was built

Wave 2 closed the BRINGUP-03 live-wiring gap: the hot-plug watcher (which
existed and was unit-tested but was **never spawned** by `__main__`) now runs in
the live session, on a single-state callback that mutates the ControllerState
the consumers already hold. Two small source touches + three test files + a
guard test + a macos_audio live recipe.

### Task 1 — Single-state hot-plug callback (option B — no rebuild divergence)
- **`src/vibemix/platform/_midi_common.py`:** ADDED
  `handle_port_change_single_state(holder, event)` (parallel to the existing
  rebuild `handle_port_change`, which is **unchanged**). On connect it calls
  `holder.controller_state.mark_connected(port)` — NO `ControllerState()`
  rebuild — and spawns a fresh listener feeding the SAME state object. On
  disconnect it is identical to the rebuild path (stop listener +
  `mark_disconnected()` which clears the rings via Plan 01 + clear bound_port).
  Diff is purely additive (68 insertions, 0 deletions).
- **`src/vibemix/platform/_midi_macos.py`:** `start_port_watcher` default
  callback (when `on_change is None`) is now the single-state one; the
  `on_change` override path is preserved for tests. Holder is still seeded from
  `self.controller_state` and retained as `self._watcher_holder`.
- **Why:** `__main__` passes `midi_macos.controller_state` ONCE to
  `ws_broadcast` + `state_refresh_loop`; those loops read off that captured
  object. A rebuild-on-connect would leave consumers reading the stale old
  object forever (the capture-once-then-rebuild divergence). In-place mutation
  keeps the single object live across unplug/replug — no consumer signature
  change.
- **Carveout (documented):** single-state keeps the original FLX4 profile across
  replug (no re-profiling). Correct for the single-FLX4 BRINGUP-03 target; the
  rebuild path remains for the future multi-controller case.

### Task 2 — Disconnect→reconnect integration through the production callback
- **New:** `tests/midi/test_disconnect_reconnect.py`. Drives the REAL
  single-state callback connected→disconnected→connected on a real FLX4
  ControllerState (spawn_listener stubbed). Asserts on disconnect:
  `is_connected()` False, `moves_since(0)==[]`, `events_since(0)==[]`,
  `bound_port` None, **`id(controller_state)` unchanged** (not rebuilt), no
  raise. On reconnect: connected True, same object id, decode resumes. Plus a
  churn test (rapid alternation) and disconnect-for-other-port no-op.

### Task 3 — Watcher + single-state callback composed (the seam `__main__` runs)
- **New:** `tests/midi/test_watcher_callback_integration.py`. Runs the REAL
  `port_watcher_task` with the REAL single-state callback over a scripted
  `[FLX4]→[]→[FLX4]` mido (reusing `_make_scripted_mido` + `_patch_watcher_sleep`
  from `test_watcher.py`). Asserts the transition sequence
  `connected→disconnected→connected`, a move injected post-connect is cleared on
  the disconnect sweep (Plan 01 ring-clear), final state connected with a fresh
  ring, and `asyncio.run` completes with no propagated exception.

### Task 4 — Wire the watcher into the live session + cleanup (the BRINGUP-03 unlock)
- **`src/vibemix/__main__.py`:** right after the static listener, added
  `midi_watcher_stop = asyncio.Event()` + `midi_watcher_task =
  midi_macos.start_port_watcher(midi_watcher_stop)` (default single-state
  callback, seeded from `midi_macos.controller_state` — the SAME object passed
  to the consumers). In the finally block: `midi_watcher_stop.set()` right after
  `midi_stop.set()`, and `midi_watcher_task` appended to `cleanup_tasks` (so it
  is cancelled + awaited). AST parses; runtime smoke confirmed the watcher
  spawns under the running loop and the holder shares `m.controller_state`.
- **New guard:** `tests/test_main_midi_wiring.py` (source-level, mirrors Phase
  52's input-path assertion): asserts `__main__` spawns `start_port_watcher`,
  uses a dedicated `asyncio.Event` (`midi_watcher_stop`), sets it in the finally
  block, has the watcher task in `cleanup_tasks`, and that `MidiMacOS` exposes
  `start_port_watcher`. Prevents silent regression of the live wiring.

### Task 5 — macos_audio live-drive recipe for Kaan-action sign-off
- **New:** `tests/test_midi_macos_live.py` — `pytestmark` skipif non-darwin +
  one `@pytest.mark.macos_audio` test. Resolves a real plugged FLX4 to
  `pioneer_ddj_flx4`; skips cleanly when absent. The docstring is the explicit
  LIVE-DRIVE RECIPE: plug → run → tap ws://127.0.0.1:8765 → move controls →
  MID-SET unplug (no crash, no error spam, `connected:false`, no stale moves) →
  replug (rebind + decode resumes) → boot-with-controller-absent (clean startup,
  quiet retries). Excluded from the default suite (opt-in marker); the physical
  drive is Kaan-action.

## Verification (real numbers)
- Plan 53-02 targeted suite (`test_midi_common` + `test_disconnect_reconnect` +
  `test_watcher_callback_integration` + `test_main_midi_wiring`): **24 passed**.
- `tests/midi/` full: 262 passed.
- `__main__.py` AST: AST_OK. `grep start_port_watcher` → spawn site (line 874);
  `grep midi_watcher_stop.set()` → cleanup site (line 946).
- `_midi_common.py` diff: single-state callback ADDED (68 insertions, 0
  deletions) — existing rebuild `handle_port_change` unchanged.
- Full default suite: green (recorded in phase verification).

## Commits (5 atomic)
1. `feat(53-02): single-state hot-plug callback — no rebuild divergence on replug (BRINGUP-03)`
2. `test(53-02): disconnect->reconnect integration via single-state callback — no stale moves, no crash, rebind works (BRINGUP-03)`
3. `test(53-02): port_watcher_task + single-state callback composed — FLX4 connect/disconnect/reconnect, no crash (BRINGUP-03)`
4. `feat(53-02): wire hot-plug watcher into live session + cleanup — BRINGUP-03 fallback now runs`
5. `test(53-02): macos_audio FLX4 live-drive recipe for Kaan-action sign-off (BRINGUP-03)`

## Self-Check: PASSED
