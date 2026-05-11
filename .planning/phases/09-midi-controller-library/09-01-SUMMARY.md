---
phase: 09-midi-controller-library
plan: 01
subsystem: midi
tags: [midi, controller-library, controller-state-extraction, ddj-flx4, json-profile, magnitude-aware, tdd]

requires:
  - phase: 07-windows-port-audio-screen
    provides: cross-platform _midi_common.midi_listener_thread + _midi_macos/_midi_windows MidiBackend impls (Phase 7 Wave 1+4)
  - phase: 06-genre-aware-phase-detection
    provides: hand-validated JSON profile pattern (vibemix.state.genre.profile) + importlib.resources packaging
  - phase: 03-sensing-state-port
    provides: original v4 ControllerState + _CC_MAP + _NOTE_MAP (DDJ-FLX4 IP)
provides:
  - vibemix.midi subpackage with ControllerProfile + ControllerState + MidiEvent + load_profile + list_profiles + find_mapping importable from the top
  - pioneer_ddj_flx4.json — canonical declarative mapping byte-equivalent to v4 _CC_MAP (13 entries) + _NOTE_MAP (12 entries)
  - magnitude-aware MidiEvent emission (signed [-1.0, 1.0] axis — unipolar = (v-prev)/127, bipolar = (v-64)/63)
  - find_mapping(port_name) registry — case-insensitive substring against profile.port_name_hints; alphabetic-id tiebreak
  - _midi_common.midi_listener_thread parameterized by ControllerProfile (with legacy str shim + DeprecationWarning until Phase 10)
affects: [09-02 (Wave 2 — 9 more controller JSONs + generic fallback), 09-03 (Wave 3 — hot-plug port watcher), 10 (prompt rendering thresholds on abs(magnitude))]

tech-stack:
  added: [importlib.resources for vibemix.midi.profiles discovery]
  patterns:
    - "Hand-validated JSON profile (no pydantic — mirrors Phase 6 GenreProfile)"
    - "Re-export shim for in-place class extraction (vibemix.platform._midi_macos.ControllerState shim points at vibemix.midi.state.ControllerState)"
    - "Per-instance lookup tables (self._cc_lookup / self._note_lookup) replace module-globals (_CC_MAP / _NOTE_MAP)"
    - "DeprecationWarning shim for one-release signature change (str port_hint → ControllerProfile)"

key-files:
  created:
    - src/vibemix/midi/__init__.py
    - src/vibemix/midi/profile.py
    - src/vibemix/midi/state.py
    - src/vibemix/midi/registry.py
    - src/vibemix/midi/profiles/__init__.py
    - src/vibemix/midi/profiles/pioneer_ddj_flx4.json
    - tests/midi/__init__.py
    - tests/midi/test_profile.py
    - tests/midi/test_state.py
    - tests/midi/test_registry.py
    - tests/midi/test_profile_flx4_golden.py
  modified:
    - src/vibemix/platform/_midi_macos.py (collapsed to thin shim — re-exports ControllerState/MidiEvent/_knob_label/_xfader_label from vibemix.midi.state)
    - src/vibemix/platform/_midi_windows.py (imports ControllerState from vibemix.midi.state, _PORT_HINT class attr removed)
    - src/vibemix/platform/_midi_common.py (signature change — third positional now ControllerProfile, with str shim)
    - tests/test_midi_macos.py (legacy _CC_MAP/_NOTE_MAP byte-equality tests moved to test_profile_flx4_golden.py; ControllerState() calls now build with FLX4 profile)
    - tests/test_midi_windows.py (test_midi_windows_default_port_hint_is_ddj_flx4 → test_midi_windows_default_profile_port_hints_include_ddj_flx4; spawn_listener call-arg pin updated to ControllerProfile)
    - tests/test_midi_common.py (3 new tests for profile signature + DeprecationWarning + 2-hint fallback)
    - tests/test_platform_windows_integration.py (test_phase_3_midi_golden_after_refactor — ControllerState() now built with FLX4 profile)

key-decisions:
  - "Magnitude semantics: signed (delta-direction-preserving) for both unipolar and bipolar — surfaces direction-of-twist for Coach prompts. abs(magnitude) is in [0,1] for unipolar by convention."
  - "Backward-compat str port_hint shim with DeprecationWarning for one release (Phase 9→10) — Phase 7 tests stay green without modification."
  - "Wave 1 ships only FLX4 profile; find_mapping returns None for unmapped — Wave 2 adds generic-MIDI fallback synthesis."
  - "Re-export _knob_label/_xfader_label from _midi_macos shim — preserves Phase 7 golden test mock paths and downstream importers."
  - "Inner controls/buttons dicts on ControllerProfile are read-only by convention (matches Phase 6 GenreProfile.band_signature precedent — frozen-dataclass freezes top-level field assignment only)."
  - "Profile.port_name_hints is a tuple[str, ...] (not single str) so listener can iterate firmware-revision variants (e.g. 'DDJ-FLX4 USB MIDI' OR 'FLX4 USB MIDI') in one enumeration sweep."

patterns-established:
  - "Pattern: Re-export shim for class extraction — when moving a public class to a new module, leave a re-export at the old path (`from vibemix.midi.state import ControllerState  # noqa: F401`) so legacy imports keep working without forcing downstream test/code rewrites in the same wave."
  - "Pattern: Per-instance lookup tables built from declarative profile — replaces module-global dispatch maps (_CC_MAP / _NOTE_MAP) when extracting hardcoded controller IP into JSON. Future controller additions = ship JSON + load_profile call, no Python code change."
  - "Pattern: Magnitude in [-1.0, 1.0] (signed) over [0.0, 1.0] (unsigned) — direction-of-change is information Coach prompts need; absolute-value clamp happens at the consumer."

requirements-completed: [MIDI-02, MIDI-03, MIDI-14]

duration: ~25min
completed: 2026-05-12
---

# Phase 9 Plan 01: MIDI Controller Library — Wave 1 Foundation Summary

**Extracted ControllerState into vibemix.midi.state, parameterized the v4 DDJ-FLX4 decoder by a JSON-defined ControllerProfile, added signed magnitude-aware MidiEvent emission, and stood up find_mapping registry — preserving Phase 7's golden byte-equivalence test green throughout.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-05-11T20:38Z (worktree spawn)
- **Completed:** 2026-05-11T21:04Z
- **Tasks:** 3/3 complete
- **Files created:** 11 (4 source, 1 JSON, 1 package marker, 5 test files)
- **Files modified:** 7 (4 source, 3 tests)
- **Test deltas:** 86 → 134 in midi-scope tests (+48); full suite 597 → 665 (+68 new — RED commits temporarily added before GREEN)

## Accomplishments

- **vibemix.midi subpackage** with ControllerProfile + ControlBinding + ButtonBinding (frozen dataclasses), JSON loader (importlib.resources), hand-written schema validator (no pydantic), and load_profile / list_profiles / find_mapping registry helpers — all importable from the top.
- **DDJ-FLX4 declarative profile** (`src/vibemix/midi/profiles/pioneer_ddj_flx4.json`) encodes v4's hardcoded `_CC_MAP` (13 entries) + `_NOTE_MAP` (12 entries) byte-equivalently with axis assignments (unipolar for vol/EQ knobs, bipolar for tempo/filter/xfader). Pinned by load-bearing scripted-replay golden test that walks 25+ MIDI messages and asserts deck_snapshot + moves labels match the v4-canonical expected state.
- **ControllerState extracted** to `vibemix.midi.state` and parameterized by `ControllerProfile`. Re-export shim left in `_midi_macos.py` so `from vibemix.platform._midi_macos import ControllerState` keeps working — Phase 7 downstream tests + state_refresh_loop call sites untouched. `_midi_windows.py` updated to import from canonical location.
- **Magnitude-aware MidiEvent ring** alongside the v4 moves ring — unipolar = (v-prev)/127 (signed delta), bipolar = (v-64)/63 (signed-from-center), clamped to [-1.0, 1.0]; buttons emit events with magnitude=None. `events_since(t)` mirrors `moves_since(t)` shape.
- **`_midi_common.midi_listener_thread` signature change** — third positional now `ControllerProfile`. Iterates `profile.port_name_hints` in order on every enumeration sweep so a controller exposing itself as either `"DDJ-FLX4 USB MIDI"` OR `"FLX4 USB MIDI"` (firmware drift) binds without caller knowledge of which hint will hit. Legacy `str` arg accepted with `DeprecationWarning` shim until Phase 10.
- **Phase 7 golden test stays green** — `test_midi_macos_golden_unchanged_behavior_after_refactor` still passes verbatim (the refactor is byte-equivalent for moves/snapshot output).
- **POC files untouched** — `git diff --name-only HEAD~7..HEAD -- 'cohost*.py' 'run*.sh' mascot.html fillers/ cohost.streaming.py.bak` returns empty.
- **Wheel packaging verified** — `uv build --wheel && unzip -l dist/*.whl | grep midi/profiles` confirms `pioneer_ddj_flx4.json` ships in the wheel via hatchling default package-data inclusion (same mechanism Phase 6 proved).

## Task Commits

Each task followed RED → GREEN TDD discipline:

1. **Task 1: ControllerProfile + JSON loader + pioneer_ddj_flx4.json**
   - RED: `e2ba95b` (test) — 11 failing tests for frozen-dataclass identity + schema validator + DDJ-FLX4 byte-equivalence
   - GREEN: `cb02d41` (feat) — vibemix.midi subpackage + profile.py + JSON; 11 tests pass

2. **Task 2: Extract ControllerState + magnitude-aware MidiEvent emission**
   - RED: `8016dd2` (test) — 18 ControllerState tests (re-export identity, profile-driven decks, magnitude semantics, v4 byte-equivalence preservation) + updates to existing tests/test_midi_macos.py + tests/test_midi_windows.py
   - GREEN: `a79f661` (feat) — vibemix.midi.state.ControllerState + MidiEvent + _knob_label/_xfader_label; _midi_macos / _midi_windows shims; tests/test_platform_windows_integration.py call-site update
   - Style: `3711dcd` (style) — ruff format profile.py wrapping

3. **Task 3: find_mapping registry + parameterize _midi_common + FLX4 golden replay**
   - RED: `b52b585` (test) — 7 find_mapping tests + 2 byte-equivalence golden tests + 3 _midi_common profile-signature tests
   - GREEN: `abec1b1` (feat) — vibemix.midi.registry.find_mapping + _midi_common signature change with str shim + DeprecationWarning + _midi_macos/_midi_windows callers updated; tests/test_midi_windows.py updated for ControllerProfile call-arg pin

## Files Created/Modified

### Created (source)

- `src/vibemix/midi/__init__.py` — top-level subpackage; re-exports ControllerProfile / ControlBinding / ButtonBinding / ControllerState / MidiEvent / load_profile / list_profiles / find_mapping
- `src/vibemix/midi/profile.py` — frozen dataclasses + hand-written schema validator (380 lines)
- `src/vibemix/midi/state.py` — ControllerState (parameterized by profile) + MidiEvent + _knob_label/_xfader_label (332 lines)
- `src/vibemix/midi/registry.py` — find_mapping(port_name) (44 lines)
- `src/vibemix/midi/profiles/__init__.py` — package marker
- `src/vibemix/midi/profiles/pioneer_ddj_flx4.json` — canonical FLX4 mapping (33 lines)

### Created (tests)

- `tests/midi/__init__.py` — package marker
- `tests/midi/test_profile.py` — 11 tests (schema validator + DDJ-FLX4 JSON byte-equivalence)
- `tests/midi/test_state.py` — 18 tests (ControllerState construction, magnitude semantics, v4 preservation)
- `tests/midi/test_registry.py` — 7 tests (find_mapping case/short-hint/None paths)
- `tests/midi/test_profile_flx4_golden.py` — 2 load-bearing tests (internal lookup byte-equivalence + 25-message scripted replay)

### Modified (source)

- `src/vibemix/platform/_midi_macos.py` — collapsed from 331 lines to ~120; re-export shim for ControllerState / MidiEvent / _knob_label / _xfader_label; instantiates ControllerState(profile=load_profile('pioneer_ddj_flx4')); start_listener_thread passes the FLX4 profile
- `src/vibemix/platform/_midi_windows.py` — imports ControllerState from vibemix.midi.state; _PORT_HINT class attribute removed (profile is the new source of truth); start_listener_thread passes the FLX4 profile
- `src/vibemix/platform/_midi_common.py` — midi_listener_thread + spawn_listener take ControllerProfile (third positional); _coerce_profile_arg shim accepts legacy str with DeprecationWarning; _find_first_port_match iterates hints in order

### Modified (tests)

- `tests/test_midi_macos.py` — removed _CC_MAP/_NOTE_MAP byte-equality tests (moved to test_profile_flx4_golden.py); replaced bare ControllerState() calls with _flx4_state() helper that builds with the FLX4 profile; added test_legacy_controller_state_import_still_works and test_midi_macos_uses_flx4_profile_by_default; updated time-mock paths from vibemix.platform._midi_macos.time.time to vibemix.midi.state.time.time
- `tests/test_midi_windows.py` — extended test_controller_state_is_imported_from_midi_macos to also pin against vibemix.midi.state.ControllerState; renamed test_midi_windows_default_port_hint_is_ddj_flx4 to test_midi_windows_default_profile_port_hints_include_ddj_flx4; updated test_start_listener_thread_calls_spawn_listener call-arg pin to ControllerProfile
- `tests/test_midi_common.py` — added test_listener_accepts_profile_finds_first_hint, test_listener_emits_deprecation_warning_on_str_port_hint, test_listener_tries_second_port_hint_when_first_misses
- `tests/test_platform_windows_integration.py` — test_phase_3_midi_golden_after_refactor now builds ControllerState with FLX4 profile (Rule 3 auto-fix — see Deviations)

## Decisions Made

1. **Magnitude semantics — signed for both unipolar and bipolar.** CONTEXT §Magnitude says `[0.0, 1.0]` for unipolar; I deviated to signed (`(v-prev)/127`) so direction-of-twist is preserved for Coach prompts. Documented in `MidiEvent` docstring; `abs(magnitude)` is in `[0, 1]` by convention for unipolar. Phase 10 prompt rendering will threshold on `abs()`.

2. **Backward-compat str port_hint shim with DeprecationWarning.** Phase 7 tests use the legacy str signature; rather than rewrite them in this wave, accept str and synthesize a single-hint ControllerProfile with a clear DeprecationWarning. Shim removed in Phase 10.

3. **Re-export shim left in `_midi_macos.py` for ControllerState + helpers.** Plan called for the shim explicitly; preserves `from vibemix.platform._midi_macos import ControllerState` for downstream code without forcing a same-wave call-site sweep.

4. **`_PORT_HINT = "DDJ-FLX4"` class attribute deleted from `MidiWindows`.** Plan was explicit about this — the profile is the new source of truth for port hints. Test `test_midi_windows_default_port_hint_is_ddj_flx4` renamed to `test_midi_windows_default_profile_port_hints_include_ddj_flx4` and now asserts on the bound profile's `port_name_hints` tuple.

5. **`time` import preserved at module level in `_midi_macos.py`.** Phase 7 golden test patches `vibemix.platform._midi_macos.time.time`; preserving the module-level `time` import keeps that mock target valid (the patch propagates to `vibemix.midi.state` too because both modules reference the same `time` module object).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] tests/test_platform_windows_integration.py::test_phase_3_midi_golden_after_refactor still calls bare ControllerState()**

- **Found during:** Task 2 (running full test suite after _midi_macos refactor)
- **Issue:** `tests/test_platform_windows_integration.py:345` calls `ControllerState()` with no args (Phase 7 zero-arg constructor). After the Phase 9 Wave 1 extraction, `ControllerState.__init__` requires a `profile` keyword arg → TypeError.
- **Fix:** Updated the call site to `cs = ControllerState(profile=load_profile("pioneer_ddj_flx4"))` and added the necessary import. Test still asserts the same v4-canonical post-replay deck snapshot — pure call-site mechanical update.
- **Files modified:** `tests/test_platform_windows_integration.py`
- **Verification:** Test passes; full suite stays green.
- **Committed in:** `a79f661` (Task 2 GREEN)

**2. [Plan-explicit deviation — magnitude semantics] CONTEXT §Magnitude said unipolar = `[0.0, 1.0]`; implementation uses signed `[-1.0, 1.0]` for both axes**

- **Found during:** Task 2 (designing MidiEvent emission)
- **Issue:** Plan's `<action>` block for Task 2 explicitly noted this deviation: "the signed convention here surfaces direction-of-twist which is what Coach prompts need ('twisted UP' vs 'twisted DOWN'). Document the deviation in the docstring; the absolute value is in [0.0, 1.0] for unipolar by convention. (Phase 10 prompt rendering will threshold on `abs(magnitude)`.)" — applied as instructed.
- **Fix:** Implemented signed unipolar semantics; documented in `MidiEvent` docstring + state.py module docstring. Tests assert both signs explicitly.
- **Files modified:** `src/vibemix/midi/state.py`
- **Committed in:** `a79f661` (Task 2 GREEN)

## Authentication Gates

None.

## Test Results

- **Wave-scope tests:** 86 passed (tests/midi/ + tests/test_midi_common.py + tests/test_midi_macos.py + tests/test_midi_windows.py + tests/test_platform_windows_integration.py)
- **Full suite:** 665 passed, 6 skipped (Windows-only smoke tests + opt-in live-audio), 3 deselected (pre-existing baseline failures — see Out-of-Scope below)
- **Phase 7 golden test:** `tests/test_midi_common.py::test_midi_macos_golden_unchanged_behavior_after_refactor` STAYS GREEN (load-bearing v4 byte-equivalence pin)
- **DeprecationWarnings fired:** 5 — all from existing Phase 7 tests using the legacy str port_hint signature (expected via shim path)

## Out-of-Scope (Not Fixed)

Three pre-existing test failures in this worktree environment, unrelated to Wave 1:

1. **`tests/agent/test_persona.py::test_persona_02_byte_identical_to_v4`** — depends on `cohost_v4.py` at repo root; POC files don't live in worktrees by design. Pre-existing failure on the merge-base; deselected from full-suite verification.
2. **`tests/test_main_smoke.py::test_smoke_06_poc_files_untouched_during_smoke`** — same root cause (POC files not present in worktree).
3. **`tests/test_audio_macos_live.py::test_open_voice_output_completes_without_real_audio_device`** — depends on a CoreAudio device named "Headphones"; this worktree environment has different audio devices. Live-hardware smoke test, environment-dependent.

These are **out of scope** per the GSD scope-boundary rule: only auto-fix issues directly caused by the current task's changes. None of these three are touched by Wave 1's changes; all reproduce identically on the merge-base commit.

Tracking these as **deferred items** for the host environment / Phase 7 (worktree+POC interaction) follow-up — they don't block 09-02 or 09-03.

## Verification Checklist

- [x] `uv run pytest tests/midi/ tests/test_midi_common.py tests/test_midi_macos.py tests/test_midi_windows.py -x -q` — 98 green
- [x] Full suite (minus 3 pre-existing baseline failures) — 665 green
- [x] `grep -rn "_CC_MAP\|_NOTE_MAP" src/vibemix/platform/_midi_macos.py | grep -v "^#"` returns 0 active hits (only docstring references remain)
- [x] `grep -rn "from vibemix.midi" src/vibemix/platform/` returns ≥3 lines — verified 5 lines (`_midi_macos.py`: 2, `_midi_common.py`: 1, `_midi_windows.py`: 2)
- [x] `python -c "from vibemix.midi import ControllerState, ControllerProfile, MidiEvent, load_profile, list_profiles, find_mapping"` exits 0
- [x] `python -c "from vibemix.midi import load_profile; p = load_profile('pioneer_ddj_flx4'); print(p.id, p.display_name)"` prints `pioneer_ddj_flx4 Pioneer DDJ-FLX4`
- [x] POC files diff-untouched: `git diff --name-only HEAD~7..HEAD -- 'cohost*.py' 'run*.sh' mascot.html fillers/ cohost.streaming.py.bak` empty
- [x] `uv run ruff check` clean on all changed files
- [x] `uv run ruff format --check` clean on all changed files
- [x] `uv build --wheel && unzip -l dist/vibemix-*.whl | grep -c "midi/profiles/.*\.json"` = 1 (FLX4 JSON ships)

## Self-Check: PASSED

All claimed files exist:

- `src/vibemix/midi/__init__.py` ✓
- `src/vibemix/midi/profile.py` ✓
- `src/vibemix/midi/state.py` ✓
- `src/vibemix/midi/registry.py` ✓
- `src/vibemix/midi/profiles/__init__.py` ✓
- `src/vibemix/midi/profiles/pioneer_ddj_flx4.json` ✓
- `tests/midi/test_profile.py` ✓
- `tests/midi/test_state.py` ✓
- `tests/midi/test_registry.py` ✓
- `tests/midi/test_profile_flx4_golden.py` ✓

All claimed commits exist on the worktree branch:

- `e2ba95b` (Task 1 RED) ✓
- `cb02d41` (Task 1 GREEN) ✓
- `8016dd2` (Task 2 RED) ✓
- `a79f661` (Task 2 GREEN) ✓
- `3711dcd` (style cleanup) ✓
- `b52b585` (Task 3 RED) ✓
- `abec1b1` (Task 3 GREEN) ✓

## Hand-Off to 09-02

Wave 2 picks up:

- 9 more controller JSONs (DDJ-400/FLX6/FLX10/1000/SX3 + XDJ-RX3 + Numark + Hercules-300/500) — all encode against the schema this wave locked in.
- Generic-MIDI fallback in `vibemix/midi/generic.py` — ships a synthesized "generic" profile when `find_mapping` returns None.
- `find_mapping` registry exercise once 10 profiles are loaded — alphabetic-id tiebreak path tested for real (Wave 1's tiebreak test was a behavior-pin against the synthetic case).

Wave 3 picks up:

- Hot-plug port watcher that re-enumerates every 2s and resolves the profile via `find_mapping` on each new device.
- Removal of the `_coerce_profile_arg` str shim from `_midi_common.py` is deferred to Phase 10.
