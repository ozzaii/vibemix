---
phase: 53
slug: controller-live-graceful-fallback
artifact: VERIFICATION
status: human_needed
requirement: BRINGUP-03
verifier: gsd-code-review (Opus 4.7)
date: 2026-05-21
diff_range: 53f871b..50d06ed
---

# Phase 53 — Goal-Backward Verification

**Status: `human_needed`** — engineering is COMPLETE and all deterministic gates
pass; the only outstanding item is the physical FLX4 plug-in / mid-set
unplug-replug / boot-without-controller drive on Kaan's Mac (SC1/SC2/SC3 live
confirmation). Per the autonomous carveout + [[project_phase_16_kaan_dj_testing]],
hardware-in-Kaan's-hands is a documented Kaan-action surface, NOT a gap. The
engineering deliverable for BRINGUP-03 is shipped and proven.

## Goal (53-CONTEXT)

> Prove the DDJ-FLX4 MIDI path is live during a real session — controller moves
> reach `ControllerState` in real time — AND the app degrades cleanly when the
> controller is unplugged (and rebinds on replug), with no crash, no stale moves,
> no hang. Covers BRINGUP-03.

## Headline gap — CLOSED

**Before Phase 53:** `port_watcher_task` / `start_port_watcher` existed and were
unit-tested, but `__main__` NEVER spawned the watcher. Mid-session unplug/replug
went undetected in a real run, `is_connected()` never flipped, stale moves were
never cleared. The hot-plug machinery was dead code in production.

**After Phase 53:** `__main__.py:874` spawns
`midi_macos.start_port_watcher(midi_watcher_stop)` on the live loop, sharing the
single `controller_state` object, cleaned up in `finally` + `cleanup_tasks`.
Verified by source-level guard `test_main_midi_wiring.py` (6 tests, pass) and the
in-place review above. **The gap that made BRINGUP-03 unverifiable is closed.**

---

## Success criteria

### SC1 — FLX4 moves register live → `human_needed`

- **Synthetic-decode proof (engineering, PASS):** `test_flx4_synthetic_decode.py`
  drives a broad live-shaped stream with the exact ch/cc/note bytes from
  `profiles/pioneer_ddj_flx4.json` through a real `ControllerState`, asserting
  per-deck values, move labels, and typed-event kind/deck/field/magnitude. If a
  real FLX4 emits these bytes, the live decode produces these results.
- **Live binding canonical (PASS):** `test_live_binding_profiles_canonical.py` +
  `test_midi_macos_live.py` (automated half) confirm a real FLX4 port resolves to
  `pioneer_ddj_flx4` via `find_mapping` on the canonical `profiles/` path.
- **Live recipe (Kaan-action):** `test_midi_macos_live.py` docstring steps 1-4 —
  plug, `uv run python -m vibemix`, tap `ws://127.0.0.1:8765`, move
  jog/crossfader/EQ/faders/pads, confirm moves surface. This is the true SC1
  sign-off → `human_needed`, not a gap.

### SC2 — clean unplug (no crash, no stale moves, rebind on replug) → `human_needed`

- **Ring-clear (engineering, PASS):** `mark_disconnected` now clears moves+events
  rings under the lock (`test_state.py::test_mark_disconnected_clears_moves_and_events_rings`).
- **Watcher disconnect path (PASS):** `test_disconnect_reconnect.py` +
  `test_watcher_callback_integration.py` drive the REAL watcher + REAL single-state
  callback through connect→disconnect→reconnect (and a churn loop): on disconnect
  `is_connected()→False`, both rings `==[]`, `bound_port→None`, SAME object
  preserved (`id()` identity), no raise; on reconnect `is_connected()→True`, decode
  resumes on a fresh ring. The composed test runs under real `asyncio.run` with no
  exception propagating.
- **No crash on churn (PASS):** rapid 7-event alternation stays internally
  consistent, never raises.
- **Live recipe (Kaan-action):** steps 5-6 — physical mid-set unplug → app keeps
  running on audio alone, `connected:false` on bus, no MIDI error spam, move list
  empties; replug → rebinds, decode resumes. → `human_needed`.

### SC3 — graceful when absent/unknown at boot → `human_needed` (engineering PASS)

- **Unknown-controller path (PASS):** `test_generic_fallback.py::
  test_unknown_controller_bind_decode_no_crash_end_to_end` —
  `find_mapping_or_generic("Some Random USB MIDI Thing")` → generic_midi profile →
  `ControllerState(generic)` → decode CC + note_on → positional generic events, no
  crash. `find_mapping_or_generic` never returns None (empty/non-str port →
  generic).
- **Absent at boot (PASS):** `start_listener_thread` returns a no-op daemon thread
  when mido is absent; the watcher's enumeration is `try/except → skip` on a
  poisoned/empty backend (no error spam, quiet retries). `test_midi_macos_live.py`
  confirms enumeration failure → `pytest.skip`, never fail.
- **Live recipe (Kaan-action):** step 7 — boot with nothing plugged → clean start,
  quiet retries, plug-mid-session binds + decodes. → `human_needed`.

---

## Validation matrix (53-VALIDATION) — all checks GREEN

| Check | Command | Result |
|-------|---------|--------|
| 53-01-01 disconnect ring-clear | `pytest tests/midi/test_state.py -k disconnect` | PASS |
| 53-01-02 live binding canonical | `pytest tests/midi/test_live_binding_profiles_canonical.py` | PASS |
| 53-01-03 FLX4 synthetic decode | `pytest tests/midi/test_flx4_synthetic_decode.py` | PASS |
| 53-01-04 generic fallback | `pytest tests/midi/test_generic_fallback.py` | PASS |
| 53-02-01 disconnect/reconnect | `pytest tests/midi/test_disconnect_reconnect.py` | PASS |
| 53-02-02 watcher+callback composed | `pytest tests/midi/test_watcher_callback_integration.py` | PASS |
| 53-02-03 main wiring guard | `pytest tests/test_main_midi_wiring.py` | PASS |
| 53-02-04 live recipe (deselected) | `pytest -m macos_audio tests/test_midi_macos_live.py` | SKIP (no device, clean) |

Targeted run: **70 passed, 0 failed** (8 Phase-53 files + `test_watcher.py`).
macos_audio recipe: **1 skipped** (clean, no device). Golden + common:
**15 passed**. Orchestrator-confirmed full suite: **3744 passed, 26 skipped,
0 failed.**

## Untouched invariants (confirmed by `git diff --name-only`)

- Golden FLX4 decode (`tests/midi/test_profile_flx4_golden.py`,
  `tests/test_midi_common.py`) — untouched, 15/15 pass.
- `src/vibemix/midi/profiles/` — untouched.
- `src/vibemix/midi/controllers/` + `src/vibemix/midi/map_loader.py` — untouched
  (and pinned unwired by `test_live_binding_profiles_canonical.py`).
- `src/vibemix/midi/watcher.py` + `registry.py` — NOT modified this phase (the
  enumeration-skip robustness is pre-existing, reviewed and correct).

## Conclusion

Engineering for BRINGUP-03 is COMPLETE: the headline wiring gap is closed, the
disconnect path is hardened (ring-clear), single-state ownership holds across
hot-plug, and the deterministic test surface (decode + disconnect/reconnect +
watcher-composed + wiring guard + unknown-fallback) is real and green. The
remaining SC1/SC2/SC3 live confirmation is the physical FLX4 drive on Kaan's Mac
(recipe in `test_midi_macos_live.py`) — `human_needed`, by design.
