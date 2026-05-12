---
phase: 12-live-session-ui-settings-panel
plan: 02
subsystem: runtime
tags: [python, runtime, ipc, session, settings, config-store, asyncio, jsonschema]

# Dependency graph
requires:
  - phase: 12-live-session-ui-settings-panel
    plan: 01
    provides: ipc.* schema additions — SessionSnapshot / SessionMute / SettingsSet / SettingsGet / SettingsState / StatusRecheck / IpcError dataclasses + jsonschema validator
  - phase: 11-tauri-shell-calibration-wizard
    plan: 04
    provides: WizardBus + handler-registration pattern + ws_bus 127.0.0.1:8765 lifecycle (re-used as IpcBus alias by SessionLoop)
provides:
  - src/vibemix/runtime/config_store.py — JSON-backed sidecar settings store (superset of Phase 11 schema; preserves unknown top-level keys; atomic os.replace write)
  - src/vibemix/runtime/settings.py — SettingsApplier 7-field dispatch matrix routing ipc.settings.set to runtime hooks + persist
  - src/vibemix/runtime/session_loop.py — SessionLoop class registering 4 ipc.* handlers + 30Hz ipc.session.snapshot emitter + transcript ring + MIDI events delta drain
  - src/vibemix/__main__.py — --session flag dispatches to run_session standalone (default unchanged — full main() runtime)
  - src/vibemix/runtime/__init__.py — re-exports SessionLoop/run_session + WizardLoop/run_wizard alongside Phase 4 surface
  - src/vibemix/runtime/ws_bus.py — IpcBus alias of WizardBus for neutral session-side reads
  - tests/runtime/test_config_store.py — 23 tests covering round-trip + atomic write + OS path resolution + Phase 11 superset preservation
  - tests/runtime/test_settings_apply.py — 23 tests covering the full 7-field dispatch matrix (happy/missing-hook/invalid-value) + persistence verification
  - tests/runtime/test_session_loop.py — 18 tests covering handler registration, mute toggle + PlaybackQueue.clear, settings get/set ack flow, status recheck, snapshot shape (both present and missing MusicState), validation wrapper, full run lifecycle
affects:
  - 12-03 (renderer components — consumes ipc.session.snapshot shape; can now spawn `vibemix --session` against a real Python WS bus)
  - 12-04 (glue plan — replaces None hook refs in SettingsApplier with real cascade/event_detector/audio_core/genre_loader refs from main(); unifies --session and default dispatch)
  - 12-05 (Settings drawer — sends ipc.settings.set; SettingsApplier is the receiving surface and already handles every field in the discriminator union)

# Tech tracking
tech-stack:
  added: []  # no new dependencies — pure stdlib + existing jsonschema/asyncio
  patterns:
    - Optional-hook injection (Protocol-typed) — SettingsApplier and SessionLoop ship structurally before 12-04 wires real cascade/audio/event_detector refs
    - WizardBus/IpcBus class re-use — the bus has the same dispatch surface in both wizard and session modes; the Tauri shell spawns one process at a time, so a single class is correct
    - Transcript-delta drain pattern — internal 200-entry deque + per-snapshot unsent slice keeps payload small while the renderer maintains its own append buffer
    - MusicState-absent fallback emits cohost_status=IDLE + grounded=false (the schema rejects "warming_up", so we cannot use that label; grounded=false IS the renderer's "cohost surface offline" signal)
    - PlaybackQueue.clear() called duck-typed — the real method lands in 12-04 when SessionLoop wires into main(); Wave 2 ships the call site against a None ref
    - Atomic config write (tmp + os.replace) preserves unknown top-level keys so the Rust shell's tauri-plugin-store wrapper (`first_run_state`) survives a sidecar save

# Outcome
status: completed
shipped:
  - src/vibemix/runtime/config_store.py (250 lines incl. docs)
  - src/vibemix/runtime/settings.py (210 lines incl. docs)
  - src/vibemix/runtime/session_loop.py (420 lines incl. docs)
  - src/vibemix/__main__.py (+18 lines — --session flag + dispatch branch + docstring)
  - src/vibemix/runtime/__init__.py (+5 lines — SessionLoop/WizardLoop/run_session/run_wizard re-exports)
  - src/vibemix/runtime/ws_bus.py (+6 lines — IpcBus alias)
  - tests/runtime/test_config_store.py (220 lines, 23 tests)
  - tests/runtime/test_settings_apply.py (280 lines, 23 tests)
  - tests/runtime/test_session_loop.py (430 lines, 18 tests)
  - tests/runtime/test_ws_bus.py (PKG-05 surface assertion updated for new exports)

tests:
  runtime_suite: 136 / 136 pass (was 72 baseline; +64 new Wave-2 tests)
  ipc_suite: 26 / 26 pass (no regressions)
  ui_bus_suite: 23 / 23 pass (no regressions)
  wizard_suite: 24 / 24 pass (no regressions)
  smoke_suite: 20 / 20 pass (cli_entry default-path preserved via --session opt-in)
  schema_drift_gate: green (26 == 26 oneOf vs wrapper-count parity)
  poc_files: untouched (0 lines diff against cohost_v*.py / mocks/ / mascot.html in this plan)
  pre_existing_failure: tests/test_phase05_verification.py::test_g5_poc_files_untouched (mascot.html modified by commit 398f788, predates Phase 12 — unrelated to 12-02)

# Deviations from plan
- **`__main__.py` dispatch.** The plan text shows
    `if args.wizard: run_wizard else: run_session`
  as the new entry shape, which would make `python -m vibemix` (no flag)
  route to the standalone SessionLoop and break the Phase 4/5 full live
  runtime + the SMOKE-02 GEMINI_API_KEY exit test. Shipped instead as an
  additive `--session` flag — default behavior is unchanged
  (`cli_entry([])` still invokes `main()`), and `--session` opts into the
  standalone IPC surface. 12-04 will unify the two paths when it wires
  SessionLoop into `main()`.

- **`cohost_status` fallback when MusicState is absent.** The plan
  preamble suggests `cohost_status="warming_up"` as the Wave-2 fallback;
  the schema enum is `["LISTENING", "TALKING", "IDLE"]` (no
  `warming_up`). Shipped `IDLE` + `grounded=false` instead — the renderer
  already treats `grounded=false` as "cohost offline / not yet wired".

- **PlaybackQueue.clear().** Plan requires SessionLoop to call
  `playback_queue.clear()` on mute. The real `PlaybackQueue` in
  `src/vibemix/audio/buffers.py` has no `clear()` method yet (v4's
  `PlaybackQueueAudioOutput.clear_buffer` is a no-op stub). Shipped
  duck-typed call site only — the real method lands in 12-04 when the
  audio surface is wired in. Tests use a `MagicMock(spec=["clear"])`
  fake.

- **Genre apply on missing loader.** Plan-text "Genre apply: reload …
  loader" implies failure when the loader ref is None. Shipped instead
  as `persist + soft warn + return success` so a settings drawer change
  in Wave-2 standalone mode is not lost on restart. A logger.warning
  flags the deferred reload. SettingsApplier returns `(True, None)` on
  this path with the warning visible via the standard logger.

# Handoffs

## 12-03 (renderer components — already shipping in parallel)
- The renderer can now spawn `vibemix --session` against a real Python
  WS bus to drive component fixtures off live IPC. Snapshot shape +
  settings.state shape are exactly the wire payload — no mock JSON
  needed in vitest beyond what 12-01 ships.
- `cohost_status="IDLE"` + `grounded=false` is the wire-true signal for
  "cohost not yet wired / warming up". Renderer should treat this
  identically to the no-MusicState state from a developer-mode launch.

## 12-04 (glue plan — wave 3)
1. **Wire SettingsApplier refs from `main()`.** Pass the live
   `DJCoHostAgent` (cascade_agent), `EventDetector`, `audio_backend`
   (audio_core), and `genre_profile_loader` (Phase 6) into a single
   `SettingsApplier(...)` constructed in `main()`. The TODO comments in
   `settings.py` mark each hook site. Each cascade/event-detector/audio
   class needs a small adapter method matching the Protocol signature
   (`set_voice`, `set_mode`, `restart_output`, `set_mic_gating_profile`).
2. **Wire SessionLoop into `main()`.** Construct the WizardBus before
   any cascade work (currently `ws_broadcast` opens a `websockets.serve`
   at the same port — these will conflict; pick ONE bus). Pass the live
   `MusicState`, `Levels`, `PlaybackQueue`, and
   `MidiMacOS.controller_state` into `SessionLoop(...)`. Replace
   `ws_broadcast` with `SessionLoop.run` (or merge the mascot 30Hz
   payload into `ipc.session.snapshot`).
3. **Make `PlaybackQueue.clear()` real.** Add a 5-line method to
   `src/vibemix/audio/buffers.py` that takes `self._lock` then resets
   `self._buffer = bytearray()`. SessionLoop already calls this; the
   only test churn is the buffers unit test.
4. **Unify `__main__` dispatch.** With SessionLoop merged into main(),
   delete the `--session` flag (or keep it as a no-op alias) and route
   the default path through the unified surface. SMOKE-02 still needs
   to fail-fast on missing `GEMINI_API_KEY` — gate that check on
   "cascade mode" rather than on the dispatch shape.
5. **MIDI events on the snapshot.** `ControllerState.recent_moves`
   currently emits `(age, label)` tuples. SessionLoop's MIDI delta only
   tracks "new since last snapshot" by list-length — replace with a
   monotonic event index or rotation-aware ring read once Phase 3's
   real `ControllerState` is in the loop.

## 12-05 (settings drawer)
- Every settings.set field is wired end-to-end through SettingsApplier;
  the drawer can POST `{field, value}` for any of the 7 fields and
  receive either a fresh `ipc.settings.state` (success) or an
  `ipc.error` envelope (failure). No further sidecar work required for
  the drawer's transport layer.

# Commits
- 10d8634 feat(12-02): config_store + tests
- d16ea63 feat(12-02): SettingsApplier + tests
- 7fd9610 feat(12-02): SessionLoop + __main__ dispatch + tests
