# Phase 9: MIDI Controller Library - Context

**Gathered:** 2026-05-11
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous)

<domain>
## Phase Boundary

Build a library of 10 curated DJ controller mappings + a generic-MIDI fallback for unmapped controllers + hot-plug re-enumeration. The Phase 3 `_midi_common.py` listener thread + `ControllerState` decoder + `_midi_macos.py` / `_midi_windows.py` Protocol impls already exist (Phases 3 and 7).

**Scope:** declarative controller mappings (data-shaped — JSON files), a registry that auto-detects controller by port-name substring, magnitude-aware EQ/fader event types, generic positional fallback for unmapped controllers, and a hot-plug poll that re-enumerates MIDI ports every 2 seconds.

**Out of scope:** UI for picking/showing controllers (Phase 11/12), per-controller LED/feedback control (post-v1), per-controller calibration UX (Phase 11 wizard).
</domain>

<decisions>
## Implementation Decisions

### Locked

- **10 controllers** to ship (covers ~70% of consumer DJ market):
  1. Pioneer DDJ-FLX4 (canonical reference — already mapped in `_midi_common.py`)
  2. Pioneer DDJ-400
  3. Pioneer DDJ-FLX6
  4. Pioneer DDJ-FLX10
  5. Pioneer DDJ-1000
  6. Pioneer DDJ-SX3
  7. Pioneer XDJ-RX3
  8. Numark Party Mix Live (Mixtrack family)
  9. Hercules Inpulse 300
  10. Hercules Inpulse 500
- **Mapping format**: declarative JSON in `src/vibemix/midi/controllers/<slug>.json` (e.g. `pioneer_ddj_flx4.json`). Each maps CC numbers + note numbers per channel (deck A/B/C/D) to event types. Frozen schema, hand-validated (no pydantic dep — match Phase 6 profile pattern).
- **Registry**: `src/vibemix/midi/registry.py` — loads all controller JSONs at import time; `find_mapping(port_name)` returns the matching mapping by case-insensitive substring match on the controller's `port_name_hints` array. Generic fallback returned if no match.
- **Magnitude semantics for EQ/fader/tempo events**: delta on a `[-1.0, 1.0]` axis (or `[0.0, 1.0]` for unipolar like volume). Event includes `magnitude` field. Coach prompt rendering interprets thresholds (e.g. `> 0.7` = "killed", `< 0.2` = "slight").
- **Generic fallback** lives in `src/vibemix/midi/generic.py` — any CC becomes `{"type": "GENERIC_CC", "cc": N, "value": V, "channel": ch}`. Coach prompt context for unmapped controllers includes "controller is unmapped — magnitude semantics not available; reactions limited to track audio + screen".
- **Hot-plug**: `_midi_common.py` adds a `port_watcher_task` async loop that polls `mido.get_input_names()` every 2 seconds; on change, emits a `CONTROLLER_CONNECTED` / `CONTROLLER_DISCONNECTED` event into a queue consumed by the agent. Listener thread is restarted with the new port if a known controller appears.
- **Tests**: structural tests on macOS (mock the JSON loading + port enumeration); golden tests verify each of the 10 JSONs decodes correctly against a representative MIDI byte stream. Live testing (real DDJ-FLX4 on Kaan's rig) is the canonical verification — Phase 16 + 20 cover it.

### Claude's Discretion

- Hot-plug poll cadence (locked at 2s per success criterion #4) but exponential backoff if no controllers seen for >60s — defer; not in v1.
- Whether `ControllerState` (currently in `_midi_macos.py`) moves to `_midi_common.py` or `vibemix.midi.state` — Phase 7 deferred this; Phase 9 is the natural extraction point. Move it to `vibemix.midi.state` (cleaner package boundary).
- JSON schema details (exact fields per mapping entry) — pick during planning; aim for thinnest viable.
</decisions>

<code_context>
## Existing Code Insights

- `src/vibemix/platform/_midi_common.py` (108 lines, Phase 7 Wave 1) — cross-platform DDJ-FLX4 listener thread + spawn_listener helper. Currently hardcoded to FLX4's CC/note maps (`_CC_MAP`, `_NOTE_MAP`). Phase 9 generalizes: listener consults a mapping passed in.
- `src/vibemix/platform/_midi_macos.py` — has the original `ControllerState` class with v4-verbatim DDJ-FLX4 decoder. Phase 9 extracts ControllerState into `vibemix.midi.state` and parameterizes the decoder by mapping.
- `src/vibemix/platform/_midi_windows.py` (Phase 7 Wave 3) — thin wrapper that imports ControllerState from `_midi_macos`. Will need a one-line import update post-Phase-9.
- `cohost_v4.py` POC reference — has the full FLX4 decoder body that Phase 3 ported verbatim. Use this for the JSON schema seed.
</code_context>

<specifics>
## Specific Ideas

1. **Schema for `pioneer_ddj_flx4.json`** (model for the other 9):
```json
{
  "id": "pioneer_ddj_flx4",
  "display_name": "Pioneer DDJ-FLX4",
  "port_name_hints": ["DDJ-FLX4", "FLX4"],
  "decks": ["A", "B"],
  "controls": {
    "eq_high_a": {"type": "cc", "channel": 0, "cc": 7, "axis": "unipolar"},
    "eq_mid_a":  {"type": "cc", "channel": 0, "cc": 11, "axis": "unipolar"},
    ...
  },
  "buttons": {
    "play_a": {"type": "note", "channel": 0, "note": 11},
    ...
  }
}
```
2. **Magnitude rendering threshold**: in the Coach prompt module (Phase 10's territory but the registry should expose the constant): `MAGNITUDE_KILLED = 0.7`, `MAGNITUDE_SLIGHT = 0.2`.
3. **Hot-plug event emission** through the existing `state.controller_connected_at` field (or add `controller_event` ring) — keep MusicState writes single-writer.

</specifics>

<deferred>
## Deferred Ideas

- **Per-controller LED/feedback control** (post-v1).
- **Auto-mapping wizard** (Phase 11 calibration step — UX-heavy).
- **Multi-controller simultaneous use** (DDJ-FLX4 + Numark Mixtrack at once) — out of v1.
- **Controller-specific genre presets** (e.g., FLX4 with techno-tuned thresholds) — out of v1.
- **Live test on actual hardware** for all 10 — Kaan only owns FLX4. Phase 16 + 20 cover what's available; the other 9 ship "verified by JSON" only. README docs the user expectation.
</deferred>
