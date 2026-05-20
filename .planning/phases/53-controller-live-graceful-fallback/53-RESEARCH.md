# Phase 53: Controller Live + Graceful Fallback — Research

**Researched:** 2026-05-21
**Verified against:** HEAD `258e934` (live `src/vibemix/` tree, this session)
**Mode:** Orchestrator-grounded inline research (autonomous `fully`). Every claim below was read off the live source, not assumed.

> **Scope reminder (from 53-CONTEXT.md):** the MIDI subsystem (`src/vibemix/midi/` + `src/vibemix/platform/_midi_*.py`) **already exists** and is heavily unit-tested. This phase does NOT rebuild it. It (a) closes the live-wiring gap so hot-plug detection actually runs in a real session, (b) hardens the disconnect path so no stale state leaks, and (c) pins FLX4 decode + disconnect→reconnect deterministically. Covers **BRINGUP-03**.

---

## Question 1 — The dual-map question: which dir is canonical for LIVE BINDING vs the MIDI-CC map?

**Answer: `midi/profiles/*.json` is canonical for BOTH live binding AND live decode. `midi/controllers/*.json` (via `MidiMapLoader`) is a separate, parallel semantic-map registry that is NOT wired into the live session path at all — it is dead code on the live runtime.**

Verified live:

| Concern | Canonical source | Evidence (read off HEAD) |
|---|---|---|
| **Port → profile binding** (which controller is this?) | `midi/profiles/*.json` via `profile.py` (`load_profile`/`list_profiles`) | `registry.find_mapping(port_name)` (registry.py:23) iterates `list_profiles()` and substring-matches `profile.port_name_hints`. `find_mapping_or_generic` (registry.py:45) falls back to `make_generic_profile()`. The watcher calls `find_mapping_or_generic` (watcher.py:90). |
| **Live MIDI decode** (CC/note → deck/field/event) | `midi/profiles/*.json` → `ControllerState` lookup tables | `ControllerState.__init__` (state.py:172-177) builds `_cc_lookup`/`_note_lookup` **from `profile.controls` / `profile.buttons`** (i.e. from the bound `ControllerProfile`, which came from `profiles/`). `handle_msg` (state.py:252) reads only those two tables. |
| **What `__main__` actually loads** | `profiles/pioneer_ddj_flx4.json` | `MidiMacOS.__init__` (`_midi_macos.py:110`): `ControllerState(profile=load_profile("pioneer_ddj_flx4"))`. `start_listener_thread` (`:148`) passes `load_profile("pioneer_ddj_flx4")` to `spawn_listener`. **Both go through `profiles/`, never `controllers/`.** |
| **`controllers/*.json` + `MidiMapLoader`** | `map_loader.py` | `MidiMapLoader` (map_loader.py:54) discovers `controllers/*.json`, validates against `schema.json`, exposes `load`/`lookup`. **Grep confirms `MidiMapLoader` / `map_loader` is imported NOWHERE in `src/vibemix/` outside its own module + `tests/midi/test_map_loader.py`.** It is a parallel registry not used by the live decode or binding path. |

**Resolution for the planner:** the live path is `profiles/` end-to-end. Do NOT switch the live binding/decode to `controllers/` and do NOT "reconcile" the two dirs in this phase — that is out of scope and risks regressing the golden FLX4 decode. The phase asserts the live path uses `profiles/` (a guard test that pins `__main__`/`MidiMacOS` resolves the FLX4 via `find_mapping`/`load_profile` against `profiles/`), and explicitly documents that `controllers/`+`MidiMapLoader` is a separate, currently-unwired registry (note it; do not delete it — deletion is a separate scope decision).

> Naming detail: the two FLX4 files differ in id/shape — `profiles/pioneer_ddj_flx4.json` is a `ControllerProfile` (port_name_hints + controls + buttons, decoded by `ControllerState`); `controllers/ddj-flx4.json` is a `MidiMapLoader` map (vendor/model/controls→semantic). They are NOT duplicates of the same schema; they serve different (and currently disjoint) consumers.

---

## Question 2 — Is the hot-plug watcher actually wired into the live session? (the real BRINGUP-03 gap)

**Answer: NO. `port_watcher_task` + `handle_port_change` + `ListenerHolder` + `start_port_watcher` all exist and are unit-tested, but `__main__.py` never calls `start_port_watcher`. The live session today spawns ONLY the static FLX4 listener thread. Mid-session unplug/replug does nothing — there is no detection seam running. This is the central wiring gap the phase must close.**

Verified live (`__main__.py` MIDI region, lines 861-932):
```
861  # --- MIDI daemon thread (Phase 3) ---
862  midi_stop = threading.Event()
863  midi_thread = midi_macos.start_listener_thread(midi_stop)   # static FLX4 listener ONLY
...
932  midi_stop.set()                                              # shutdown
```
- `start_listener_thread` (`_midi_macos.py:123`) → `_midi_common.spawn_listener(self.controller_state, stop_event, load_profile("pioneer_ddj_flx4"), mido)`. This is a self-retrying enumerate-open-poll loop (`_midi_common.midi_listener_thread`): on disconnect it just loops back to "no port match → sleep 2s → retry" (it keeps `controller_state` as-is, never marks disconnected, never clears moves).
- **`grep -n "start_port_watcher\|port_watcher\|watcher" src/vibemix/__main__.py` → ZERO hits.** The watcher is never started in the live path.
- The intended production wiring is documented but unbuilt: `start_port_watcher` (`_midi_macos.py:152`) builds a `ListenerHolder` + `functools.partial(handle_port_change, holder)` and `create_task(port_watcher_task(...))`. The docstring says "wired by Phase 4 `__main__.py`" — but it was never wired.

**Consequence on real hardware (why this is a live bug, not theoretical):** with only the static listener, an unplug mid-session leaves `controller_state.is_connected()` stuck `True` and the last `_moves`/`_events` ring intact — so a reaction firing right after unplug can still read stale "B_filter: flat→killed" moves that physically can no longer be happening. The session does NOT crash (the listener loop's outer `try/except` swallows the port-gone exception and retries), but it does NOT degrade cleanly either: stale moves leak, and `is_connected()` lies. CONTEXT requires both "no crash" AND "no stale moves leaking" AND "is_connected reflects reality".

**Plan to close it (minimal, mirrors the documented design):**
1. In `__main__.py`, after `start_listener_thread`, also spawn the watcher via `midi_macos.start_port_watcher(midi_watcher_stop, on_change=<single-state callback>)` (`midi_watcher_stop` is an `asyncio.Event` — the watcher is async, runs on the event loop alongside the other 6 tasks). Register the returned `asyncio.Task` in `cleanup_tasks` (it is cancelled in the existing `finally` loop, refs `__main__.py:932-948`) AND set `midi_watcher_stop.set()` alongside `midi_stop.set()` so the watcher exits cooperatively. Note the dual stop signals: `midi_stop` is a `threading.Event` (listener thread); `midi_watcher_stop` is an `asyncio.Event` (watcher task). Do NOT conflate.
2. **Decide the holder ownership (the correctness trap).** Verified at HEAD: `state_refresh_loop` (refresh.py:494) and `ws_broadcast` (ws_bus.py:192) each take `controller_state` as a parameter and `__main__` passes `midi_macos.controller_state` **once at task-spawn** (`:873`, `:883`). The loops then read `.deck_snapshot()` / `.moves_since()` off that **captured object** (refresh.py:428/463, ws_bus.py:159). But the documented `handle_port_change` REBUILDS `holder.controller_state` on every connect (a fresh object, _midi_common.py:239) — so after a rebind, the captured original and the holder's rebuilt object diverge, and the loops keep reading the dead original. **This capture-once-then-rebuild divergence is the load-bearing design decision.** Two fixes:
   - **(B, RECOMMENDED for BRINGUP-03) Single-state in-place mutate.** Keep ONE `ControllerState` for the whole session (the one `__main__` already captured + passed to both loops). On connect/disconnect, mutate it in place — `mark_connected(port)` / `mark_disconnected()` (which now clears the ring, Q3) — instead of rebuilding. Concretely: add a single-state callback path (a `handle_port_change`-style callback that does NOT rebuild, or a `start_port_watcher(rebuild=False)` mode) so the captured object stays the live one. This avoids the divergence entirely with ZERO change to the two consumer signatures or their tests. Kaan's setup is a SINGLE FLX4 — the multi-controller "different binding shape per device" rebuild generality is not exercised, so its loss is irrelevant for this phase. **Lowest-risk, smallest diff — pick this.**
   - **(A, fallback if multi-controller hot-swap is later needed) Holder-as-source-of-truth indirection.** Have `MidiMacOS` own the holder and reassign `self.controller_state = holder.controller_state` on rebuild, then make the consumers read `.controller_state` LATE (per-tick) off the shared `midi_macos`/holder rather than binding it once. This preserves rebuild generality but ripples into the `ws_broadcast` / `state_refresh_loop` signatures and their tests. **Only if (B) proves insufficient.**
3. Whichever ownership model, the disconnect path must **clear the moves/events ring** (see Q3) so no stale moves leak.

> Autonomous-`fully` resolution: go with **(B)** — single-state in-place mutate. It is the smallest diff, requires no consumer-signature changes (both loops already hold the one state object), and fully satisfies the observable contract for Kaan's single-FLX4 target. Document the choice in the SUMMARY. The observable contract either way: after unplug, `is_connected()==False` and `moves_since(0)==[]`; after replug, `is_connected()==True` and decode resumes on the SAME state object the loops read.

---

## Question 3 — On disconnect, does `ControllerState` clear stale moves? (the hardening gap)

**Answer: NO. `mark_disconnected()` (state.py:184-189) clears ONLY the `_connected` flag. It does NOT clear `_moves` or `_events`. The 12s ring trim is time-based, so right after an unplug the last up-to-12s of moves are still returned by `moves_since(t)` — stale moves leak into reactions. CONTEXT explicitly forbids this.**

Verified live:
- `mark_disconnected` (state.py:184): `with self._lock: self._connected = False`. Nothing else.
- `_moves` / `_events` are only trimmed by the 12s cutoff in `_record_move` (state.py:202-205) / `_record_event` (state.py:232-234) — i.e. only on the NEXT recorded event. After unplug there are no new events, so the rings sit frozen with up-to-12s of pre-unplug moves.
- `moves_since(t)` (state.py:380) returns `[(now - mt, label) for mt, label in self._moves if mt > t]` — it will happily return those frozen stale moves for up to 12s after the controller is gone.
- Existing test `tests/midi/test_state.py::test_mark_disconnected_clears_connected_flag` only asserts the flag — there is **no test that the rings are cleared on disconnect** (this is the coverage GAP, not profile loading).

**Plan to close it (minimal, additive):**
- Extend `mark_disconnected()` to also clear the rings under the lock: `self._moves.clear(); self._events.clear()`. This is the cleanest "degrade cleanly, no stale moves" guarantee. (Keep `deck`/`xfader` as-is or reset to defaults — recommended: leave deck values, since `deck_snapshot()` already carries `connected=False` so consumers can gate on it; clearing the *moves/events rings* is the load-bearing part because that is what reactions read. Resetting deck to defaults is optional polish; the must-have is the rings + flag.)
- This is a 2-line source change to a tested method; the new test asserts the rings clear (Q5 below).

> Verify the existing FLX4 golden decode tests still pass after this change — `mark_disconnected` is not called by `handle_msg`, so the golden path (`test_profile_flx4_golden.py`, `test_state.py` byte-equivalence) is untouched. Clearing rings only happens on the disconnect callback.

---

## Question 4 — Is FLX4 decode + the unknown-controller path already proven, or is there a gap?

**Answer: FLX4 binding + a golden decode exist (`test_profile_flx4_golden.py`, `test_state.py` byte-equivalence) and the unknown→generic binding is tested at the watcher level (`test_watcher.py::test_port_watcher_emits_generic_for_unknown_port`). The gap is an END-TO-END deterministic decode assertion for the live-shaped FLX4 stream AND a disconnect→reconnect-mid-session integration test that drives the production callback. Profile loading is already covered — do NOT re-test it.**

Verified live test surface:
- `tests/midi/test_profile_flx4_golden.py` — golden decode of FLX4 (already covers decode shape).
- `tests/midi/test_state.py` — byte-equivalence of `_moves`/`moves_since`/`deck_snapshot`, `mark_disconnected` flag, dedup/12s-trim. Decode of individual CC/note covered.
- `tests/midi/test_watcher.py` — connected-on-first-sweep (resolves `pioneer_ddj_flx4` profile), disconnected-on-disappear, generic-for-unknown, no-re-emit, port-swap, stop_event, swallows callback + get_input_names exceptions, async callback. **Watcher is well-covered in isolation.**
- `tests/test_midi_common.py` — `handle_port_change` connect-swaps-to-known, connect-swaps-to-generic-for-unknown, marks-disconnected-on-disconnect, disconnect-for-other-port-noop, repeat-connect-noop. **The callback is covered in isolation too.**
- `tests/midi/test_profiles_all_controllers.py` — every curated profile loads/validates. `tests/midi/test_registry.py`, `test_generic_fallback.py`, `test_map_loader.py`, `test_sniff_controller.py`, `tests/wizard/test_step3_controller.py` — registry/generic/map/sniff/wizard surfaces.

**The GAPS (what this phase adds — not re-tests):**
1. **End-to-end FLX4 synthetic-stream decode** through the *listener path*: feed a realistic sequence of FLX4 CC/note `mido`-shaped messages (deck-select implied by channel, crossfader CC, tempo CC, EQ knobs, jog touch, play/cue pads — all read from `profiles/pioneer_ddj_flx4.json`) into `ControllerState.handle_msg` (or via the `_midi_common` listener loop with a fake mido port) and assert `deck_snapshot()` + `moves_since(0)` + `events_since(0)` reflect the right deck/field/magnitude. The existing golden test pins specific values; the new test proves a *live-shaped multi-control sequence* decodes coherently (the "prove FLX4 decode deterministically" CONTEXT requirement).
2. **Disconnect→reconnect mid-session integration** driving the PRODUCTION callback: wire a `ListenerHolder` + `handle_port_change` (the real callback), feed it `('connected', FLX4, profile)` → record some moves → `('disconnected', FLX4)` → assert `is_connected()==False` AND `moves_since(0)==[]` (stale moves gone, Q3 fix) AND no exception → `('connected', FLX4, profile)` again → assert rebind works (`is_connected()==True`, decode resumes, fresh ring). This is the deterministic proxy for Kaan's physical unplug/replug.
3. **Watcher→callback wired together** (one level up from the isolated tests): drive `port_watcher_task` with a scripted fake mido `[FLX4] → [] → [FLX4]` and the REAL `handle_port_change` as `on_change`, asserting the holder's controller_state goes connected→disconnected(ring cleared)→reconnected across the sweeps, no raise. This proves the watcher + callback compose (the seam that `__main__` will actually run).
4. **`__main__` live-wiring guard**: a test (or a focused assertion) that `__main__`'s MIDI region spawns the watcher (not just the static listener) and registers its stop event in cleanup — so the wiring can't silently regress. Pragmatic shape: assert `start_port_watcher` is referenced in `__main__.py` MIDI region + the watcher stop event is set in the `finally` cleanup (source-level grep-style assertion, mirroring how `test_sample_rate_guard.py` pins the input-path call site in Phase 52).
5. **Unknown-controller graceful path end-to-end**: a test that an unknown port name binds to the generic profile via `find_mapping_or_generic` and that `ControllerState(profile=generic)` decodes a CC into a positional `generic_cc` event without raising (the `_handle_generic` path) — confirming "unknown controller doesn't crash, gets generic". (Registry-level generic fallback is tested; the end-to-end "bind generic → decode a message → no crash" assertion is the additive gap.)

---

## Question 5 — Windows parity: does `_midi_windows` need the same wiring?

**Answer: `_midi_windows.py` already mirrors `_midi_macos.py` (it has `start_port_watcher` + the same `handle_port_change` wiring at lines 158-195). The `__main__.py` live path is macOS-only (`MidiMacOS()` at :533, imported from `platform`); the Windows backend (`MidiWindows`) is selected in `platform/__init__.py:61`. The live-wiring fix in `__main__` is platform-agnostic IF it goes through the backend's `start_port_watcher` (both backends expose it).**

Verified:
- `_midi_windows.py:158` `start_port_watcher` + `:191` `functools.partial(_midi_common.handle_port_change, holder)` — same shape as macOS.
- `_midi_common.handle_port_change` / `ListenerHolder` are cross-platform (in `_midi_common`, imported by both backends).
- `platform/__init__.py` selects `MidiMacOS` vs `MidiWindows` per-OS; `__main__.py` imports `MidiMacOS` directly (`:100`) — the live path is the macOS one (Kaan's Mac is the BRINGUP-03 target).

**Plan:** wire the watcher in `__main__` through `midi_macos.start_port_watcher(...)` (the macOS live path — Kaan's target). The Windows backend already has the symmetric method, so a future Windows `__main__` path (or a unified backend selection) inherits the same callback wiring for free. The phase's deterministic tests are platform-agnostic (they drive `handle_port_change` + `port_watcher_task` with fake mido, no real device) — they cover both backends' shared callback. **No Windows-specific live wiring is in scope for this phase** (Kaan's FLX4 on Mac is the real-hardware target; Windows live is covered by the shared deterministic tests + the existing `_midi_windows` mirror). Note this carveout in the plan.

---

## Validation Architecture

> Required section — drives `53-VALIDATION.md` (Nyquist). All commands runnable from repo root.

### Test framework
- **pytest 7.x** (`pyproject.toml [tool.pytest.ini_options]`, `addopts = "-ra --strict-markers"`).
- Quick run: `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q <files>` (or `uv run pytest -q <files>`).
- Full suite: `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q`.
- Opt-in markers used here: `macos_audio` (real FLX4 + real session — Kaan-action live drive recipe). The deterministic tests run in the DEFAULT suite (no real device — fake mido + direct `handle_msg`/callback drive).

### What is automatable (engineering, default suite)
| Behavior | Requirement | Test type | Command |
|---|---|---|---|
| Live path binds + decodes FLX4 via `profiles/` (not `controllers/`); `find_mapping("DDJ-FLX4 …")` → `pioneer_ddj_flx4`; `MidiMacOS.controller_state` profile id is `pioneer_ddj_flx4` | BRINGUP-03 | unit | `pytest -q tests/midi/test_live_binding_profiles_canonical.py` |
| FLX4 live-shaped synthetic stream (deck select / xfader / tempo / EQ / jog / play / cue) decodes into correct `deck_snapshot()` + `moves_since` + `events_since` | BRINGUP-03 | unit | `pytest -q tests/midi/test_flx4_synthetic_decode.py` |
| `mark_disconnected()` clears `_moves` + `_events` rings (no stale moves leak) AND clears `_connected` | BRINGUP-03 | unit | `pytest -q tests/midi/test_state.py -k disconnect` |
| `handle_port_change` disconnect path: `is_connected()==False`, `moves_since(0)==[]`, no raise; reconnect rebinds + decode resumes with a fresh ring | BRINGUP-03 | integration (callback) | `pytest -q tests/midi/test_disconnect_reconnect.py` |
| `port_watcher_task` + REAL `handle_port_change` composed: scripted `[FLX4]→[]→[FLX4]` drives connected→disconnected(ring cleared)→reconnected, no raise | BRINGUP-03 | integration | `pytest -q tests/midi/test_watcher_callback_integration.py` |
| Unknown controller binds to generic profile and decodes a CC into a `generic_cc` event without crash | BRINGUP-03 | unit | `pytest -q tests/midi/test_generic_fallback.py -k decode` (or new file) |
| `__main__` MIDI region spawns the watcher (`start_port_watcher`) and sets its stop event in cleanup — live wiring can't silently regress | BRINGUP-03 | unit (source assertion) | `pytest -q tests/test_main_midi_wiring.py` |
| Full suite still green (no golden-FLX4 / byte-equivalence regression) | all | suite | `PYTHONPATH=src python3 -m pytest -q` |

### What is manual / Kaan-action (real hardware — autonomous carveout)
| Behavior | Requirement | Why manual | Instructions |
|---|---|---|---|
| Real FLX4 plugged in → jog/crossfader/knob/pad moves register on the bus/UI during a live session | BRINGUP-03 (SC1) | needs the physical controller + eyes on UI | Plug FLX4; run `uv run python -m vibemix`; tap `ws://127.0.0.1:8765`; move jog/crossfader/knobs → confirm controller moves surface. Runnable recipe shipped as a `macos_audio`-marked live test docstring. |
| Mid-set unplug → app keeps running on audio alone, no crash; replug → rebinds | BRINGUP-03 (SC2/SC3) | needs physical unplug/replug | During the live session above, unplug the FLX4 → confirm app keeps running, no MIDI errors flood the log, `connected:false` on the bus; replug → confirm decode resumes. (Per `project_phase_16_kaan_dj_testing`.) |
| Boot with controller absent → full session on audio alone, no MIDI-related log errors | BRINGUP-03 (SC3) | needs a real boot without device | Start `uv run python -m vibemix` with no controller plugged → confirm clean startup, listener retries quietly, no error spam. |

### Sampling rate
- After every task commit: run that task's quick command.
- After every wave: run the full default suite.
- Before verify: full default suite green; the `macos_audio` live drive (FLX4 in Kaan's hands) is Kaan-action and recorded as deferred.

---

## Pitfalls (verified, must respect)
1. **Do NOT rebuild the MIDI subsystem.** `registry`, `watcher`, `state`, `profile`, `generic`, `_midi_common`, the per-OS backends all exist and are tested. This phase WIRES + HARDENS + TESTS the gaps.
2. **The live-wiring gap is the core deliverable** — `__main__` never starts `start_port_watcher`. Wiring it is the BRINGUP-03 unlock; everything else is hardening + proof.
3. **Controller-state divergence trap** — `handle_port_change` rebuilds `holder.controller_state` on connect; the live consumers (`ws_broadcast`, `state_refresh_loop`) capture `midi_macos.controller_state` once at task-spawn. After a rebind they read the stale original. Fix the ownership (recommended: shared holder / read `.controller_state` late; fallback: single-state in-place mutate). This is the subtle correctness bug, not a cosmetic one.
4. **`mark_disconnected` must clear the rings** — today it only clears the flag, so up to 12s of stale moves leak post-unplug. CONTEXT forbids stale moves in reactions.
5. **`profiles/` is canonical, `controllers/`+`MidiMapLoader` is unwired** — do not switch the live path to `controllers/`, do not "reconcile" the dirs, do not delete `controllers/` (separate scope). Just pin the live path uses `profiles/` and note the parallel registry.
6. **Golden FLX4 decode is immutable** — `test_profile_flx4_golden.py` + `test_state.py` byte-equivalence must stay green. The disconnect-ring-clear change is to `mark_disconnected` (not on the decode path), so the golden path is untouched — verify it.
7. **Watcher is async, listener is a thread** — `start_port_watcher` returns an `asyncio.Task` on the event loop (its stop is an `asyncio.Event`); `start_listener_thread` is a daemon thread (its stop is a `threading.Event`). The `__main__` cleanup must handle BOTH stop signals. Don't conflate the two stop events.
8. **No real device in the default suite** — every deterministic test uses fake mido (`SimpleNamespace` with `get_input_names`/`open_input`) or direct `handle_msg`/`handle_port_change` calls. The real FLX4 drive is `macos_audio`-marked + Kaan-action.
9. **Windows parity is free at the callback level** — `_midi_windows` already mirrors the watcher wiring; the deterministic tests drive the shared `_midi_common` callback, covering both. No Windows-specific live `__main__` wiring in scope.

---

## RESEARCH COMPLETE
