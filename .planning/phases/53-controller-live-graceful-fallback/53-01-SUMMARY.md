# 53-01 SUMMARY — Controller state hardening + FLX4 decode proof + canonical-binding pin (BRINGUP-03)

status: complete
phase: 53-controller-live-graceful-fallback
plan: 01
wave: 1

## What was built

Wave 1 made the controller-input primitives correct + proven, building on the
already-tested MIDI subsystem (NOT a rebuild). One additive source change + four
test files (two new, two extended).

### Task 1 — `mark_disconnected` clears the moves + events rings (the hardening gap)
- **Source (only edit):** `src/vibemix/midi/state.py::mark_disconnected` — under
  the existing lock, now also `self._moves.clear()` + `self._events.clear()` in
  addition to `self._connected = False`. Docstring updated to state why (the
  rings are 12s-time-trimmed, so without an explicit clear they sit frozen with
  up-to-12s of stale moves after an unplug, readable by `moves_since` /
  `events_since` → a hallucinated reaction grounded on a controller that is
  gone).
- **TDD:** added `test_mark_disconnected_clears_moves_and_events_rings` (RED
  first — proved 3 stale moves survived disconnect before the fix); GREEN after.
  The original `test_mark_disconnected_clears_connected_flag` stays intact.
- **Off the decode path:** `mark_disconnected` is never called by `handle_msg`,
  so the FLX4 golden decode + byte-equivalence are untouched (full suite green).

### Task 2 — Pin live binding/decode canonical on `midi/profiles/` (dual-map resolved)
- **New test:** `tests/midi/test_live_binding_profiles_canonical.py` (no marker).
  - `find_mapping("DDJ-FLX4 USB MIDI").id == "pioneer_ddj_flx4"` (+ second-hint
    "FLX4", + result is in `list_profiles()`).
  - `MidiMacOS().controller_state._profile.id == "pioneer_ddj_flx4"` and it
    decodes a known FLX4 CC (ch0/cc19 → deck A vol).
  - Documents-and-pins that `MidiMapLoader`/`map_loader.py` (the separate
    `controllers/` registry) has **no live-runtime importer** under
    `src/vibemix` (source-level glob assertion; only `map_loader.py` itself
    references it) and is not re-exported from `vibemix.midi`.
- **Resolution:** profiles/ = canonical for live binding + decode;
  controllers/+MidiMapLoader = separate, currently-unwired registry. Not
  switched, not deleted.

### Task 3 — FLX4 synthetic-stream end-to-end decode proof
- **New test:** `tests/midi/test_flx4_synthetic_decode.py` (no marker). Drives a
  live-shaped multi-control stream (vol/eq/tempo/filter CCs + xfader + jog/play/
  cue/sync notes) using the verified ch/cc/note map and asserts `deck_snapshot`
  per-deck values, `moves_since` labels (`A_vol up`, `A_low:…killed`,
  `A_tempo up`, `xfader→full-B`, `A_play→ON`, `B_cue_hit`, `A_sync_hit`), and
  `events_since` kind/deck/field/magnitude (pytest.approx on the bipolar/unipolar
  floats), plus monotonic event ids. Also: deck-B independence, unmapped-CC
  no-op, malformed-message no-raise. Complements (does not duplicate)
  `test_profile_flx4_golden.py`.

### Task 4 — Unknown-controller bind→decode→no-crash end-to-end
- **Extended:** `tests/midi/test_generic_fallback.py` +1 end-to-end test:
  unknown port → `find_mapping_or_generic` → `generic_midi` →
  `ControllerState(generic)` → `handle_msg(CC + note_on)` → positional
  `generic_cc` (`cc_0_42`) + `generic_note` (`note_3_60`) events, moves
  recorded, no raise. Does not duplicate the existing isolated generic-decode
  tests.

## Verification (real numbers)
- Plan 53-01 targeted suite (`test_state` + `test_live_binding_profiles_canonical`
  + `test_flx4_synthetic_decode` + `test_generic_fallback`): **48 passed**.
- `git diff` on `state.py`: ONLY `mark_disconnected` changed (no decode-path edit).
- Ring-clear confirmed inside `mark_disconnected` (state.py:199-200).
- Full default suite: green (golden FLX4 decode + byte-equivalence unaffected).

## Commits (4 atomic)
1. `feat(53-01): mark_disconnected clears moves+events rings — no stale moves leak on unplug (BRINGUP-03)`
2. `test(53-01): pin live binding/decode canonical on midi/profiles (dual-map resolved, BRINGUP-03)`
3. `test(53-01): FLX4 synthetic-stream end-to-end decode proof (BRINGUP-03)`
4. `test(53-01): unknown-controller bind->decode->no-crash end-to-end (BRINGUP-03)`

## Self-Check: PASSED
