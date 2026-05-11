---
phase: 09-midi-controller-library
plan: rollup
type: summary
status: complete
completed_at: 2026-05-12
requirements_covered:
  - MIDI-01   # Hot-plug re-enumeration every 2 seconds
  - MIDI-02   # Auto-detect via port-name substring matching
  - MIDI-03   # Magnitude-aware EQ/fader events with delta semantics
  - MIDI-04   # 10 curated controller mappings (FLX4 + 9 more)
  - MIDI-05   # ControllerProfile JSON schema with hand-validator
  - MIDI-06   # ControllerState extracted to vibemix.midi.state
  - MIDI-07   # Generic-MIDI fallback for unmapped controllers
  - MIDI-08   # Listener thread parameterized by ControllerProfile
  - MIDI-09   # CONTROLLER_CONNECTED / CONTROLLER_DISCONNECTED events
  - MIDI-10   # Pioneer DDJ-FLX4 canonical golden test preserved
  - MIDI-11   # 9 additional Pioneer + Numark + Hercules mappings (JSON-only)
  - MIDI-12   # find_mapping_or_generic — never returns None
  - MIDI-13   # Listener restart on hot-plug without losing audio state
  - MIDI-14   # MidiEvent dataclass with magnitude rendering thresholds
wave_commits:
  - abec1b1   # Wave 1: registry + listener parameterized + FLX4 golden
  - cfd6a2c   # Wave 2: 9 controllers + generic + hot-plug watcher
  - (this commit)   # Wave 3: docs + SUMMARY + STATE/ROADMAP advance
test_count: 839
test_delta: "+214 vs Phase 8 baseline (625 → 839)"
---

# Phase 9 — MIDI Controller Library — Summary

**Verdict:** All 4 ROADMAP success criteria PASS. Phase 9 shipped — 10 controller mappings + generic fallback + hot-plug re-enumeration. Live-verified for DDJ-FLX4; 9 other mappings JSON-only (Mixxx-derived) pending Phase 16/20 + community PRs.

## What Phase 9 Delivered

**Production code (`src/vibemix/midi/`)** — new package:
- `profile.py` — `ControllerProfile` dataclass + `load_profile(path)` hand-validator (no pydantic dep; matches Phase 6 GenreProfile pattern). Schema: `id`, `display_name`, `port_name_hints`, `decks`, `controls` (CC→event), `buttons` (note→event), optional `notes` (JSON-only verification flag).
- `state.py` — `ControllerState` extracted from `_midi_macos.py`. Magnitude-aware `MidiEvent(kind, field, magnitude)` ring; bipolar EQ in `[-1.0, 1.0]`; unipolar volume/filter in `[0.0, 1.0]`.
- `registry.py` — `find_mapping(port_name)` case-insensitive substring match against `port_name_hints` for all 10 profiles.
- `generic.py` — generic-MIDI fallback profile + `find_mapping_or_generic(port_name)` (never returns None). Positional decoder emits `MidiEvent(kind="generic_cc"|"generic_note", field="cc_<ch>_<cc>"|"note_<ch>_<n>", magnitude=v)` for any unmapped controller.
- `watcher.py` — `port_watcher_task` async coroutine polling `mido.get_input_names()` every 2 seconds. `handle_port_change` restarts listener thread with new profile on detected connect; emits `CONTROLLER_CONNECTED` / `CONTROLLER_DISCONNECTED` into agent's event queue.
- `profiles/` (10 JSONs): `pioneer_ddj_flx4.json`, `pioneer_ddj_400.json`, `pioneer_ddj_flx6.json`, `pioneer_ddj_flx10.json`, `pioneer_ddj_1000.json`, `pioneer_ddj_sx3.json`, `pioneer_xdj_rx3.json`, `numark_party_mix_live.json`, `hercules_inpulse_300.json`, `hercules_inpulse_500.json`.

**Production code refactored:**
- `src/vibemix/platform/_midi_common.py` — listener thread now accepts a `ControllerProfile` argument (was hardcoded to FLX4 CC/note maps). `ListenerHolder` class manages restartable listener thread for hot-plug. `handle_port_change` is the production hot-plug glue.
- `src/vibemix/platform/_midi_macos.py` — `ControllerState` moved out to `vibemix.midi.state` (re-exports for backwards compat). `start_port_watcher` exposes the watcher task.
- `src/vibemix/platform/_midi_windows.py` — import updated to source `ControllerState` from `vibemix.midi.state`. `start_port_watcher` mirrors MacOS.

**Tests (839 total, +214 vs Phase 8's 625 baseline):**
- `tests/midi/test_profile.py` — profile loader + hand-validator (15 tests)
- `tests/midi/test_state.py` — ControllerState + magnitude-aware MidiEvent (24 tests)
- `tests/midi/test_registry.py` — find_mapping substring matching (12 tests)
- `tests/midi/test_profile_flx4_golden.py` — byte-equivalent v4 FLX4 replay (3 tests; the Phase 7 + 09-01 canary)
- `tests/midi/test_profiles_all_controllers.py` — 10 per-controller golden tests
- `tests/midi/test_generic_fallback.py` — positional fallback decode (~30 tests)
- `tests/midi/test_watcher.py` — port_watcher_task + handle_port_change + listener restart (~20 tests)

**Docs:**
- `docs/midi-controllers.md` — controller table (verification status), magnitude semantics rendering thresholds, generic fallback contract, hot-plug behavior, adding-a-new-controller recipe.

## Architecture Decisions Pinned

1. **JSON-declarative mapping format** — matches Phase 6 GenreProfile pattern. Hand-validated at import time; no pydantic dep (Critical Constraint 6).
2. **`ControllerState` extracted to `vibemix.midi.state`** — Phase 7's "Claude's Discretion" deferral is closed. Both `_midi_macos.py` and `_midi_windows.py` now import from the canonical location. Phase 7's golden FLX4 byte-equivalence test (`test_midi_macos_golden_unchanged_behavior_after_refactor`) stays green.
3. **Generic fallback is mandatory** — `find_mapping_or_generic` never returns `None`. Any controller "works" even if unmapped; Coach prompts get a magnitude-semantics-unavailable system reminder.
4. **Hot-plug poll cadence = 2 seconds** — matches ROADMAP success criterion #4 exactly. Single-shot watcher coroutine, not exponential backoff (deferred).
5. **9 controller JSONs ship "verified by JSON only"** — Kaan owns FLX4 only. The 9 others derive from manufacturer charts + Mixxx mappings (https://github.com/mixxxdj/mixxx). `notes` field flags "Wave 2 — JSON-only verified" for transparency. Phase 16 + 20 + community PRs cover live verification.
6. **Magnitude rendering thresholds expose `MAGNITUDE_KILLED = 0.7` / `MAGNITUDE_SLIGHT = 0.2`** — Phase 10's prompt module consumes these for Coach-mode narration. Coach: "you killed the lows on deck A" if `magnitude > 0.7`, "slight high boost" if `magnitude < 0.2`.
7. **Listener restart on hot-plug uses `ListenerHolder` pattern** — fresh `ControllerState` per restart (not in-place profile swap). Simpler; thread lifecycle is per-port-bind.

## ROADMAP Success Criteria → Acceptance Gates

| # | Criterion | Status |
|---|-----------|--------|
| 1 | All 10 controllers auto-detect on plug-in via name matching | ✅ PASS — `find_mapping(port_name)` covered by per-controller golden tests; FLX4 + 9 JSON-only |
| 2 | Magnitude-aware EQ events fire with delta semantic | ✅ PASS — `MidiEvent(magnitude=...)` ring; bipolar [-1.0, 1.0] / unipolar [0.0, 1.0]; thresholds exposed |
| 3 | Generic-MIDI fallback ingests unmapped controllers; reactions grounded | ✅ PASS — `find_mapping_or_generic` never None; positional events emit; ~30 fallback tests green |
| 4 | Hot-plug surfaces "controller connected" within 2 seconds | ✅ PASS — `port_watcher_task` 2s poll; `handle_port_change` restarts listener; `CONTROLLER_CONNECTED` event |

## Test Count Delta

- Phase 8 baseline: 625 tests
- Phase 9 final: 839 tests (+214)
- Failed: 1 (pre-existing CoreAudio environmental — deferred to deferred-items.md entry #3)
- Skipped: 6 (windows_only + macos_audio opt-in)

## Deferred to Future Phases

- **Live verification of 9 JSON-only mappings** — Phase 16 + Phase 20 + community PRs.
- **Per-controller LED / feedback output** — post-v1.
- **Auto-mapping wizard** (wiggle-to-map UX) — Phase 11 + post-v1.
- **Multi-controller simultaneous use** — out of v1.
- **Controller-specific genre presets** — out of v1.

## What's Next

**Phase 10 — Prompt Template Matrix (6 cells + Anti-Slop)**: 6 prompt templates (Beginner / Intermediate / Pro × Hype-man / Coach) with the full anti-slop stack: negative dictionary, `TurnHistory` anti-repetition ring, `<silence/>` short-circuit, describe-before-infer anchoring, past-tense framing, reaction throttle, Coach scorecard at session end.
