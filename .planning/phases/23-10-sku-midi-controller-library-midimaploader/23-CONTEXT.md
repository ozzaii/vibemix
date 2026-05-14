# Phase 23: 10-SKU MIDI Controller Library + MidiMapLoader - Context

**Gathered:** 2026-05-14
**Status:** Ready for planning
**Mode:** Auto-generated (gsd-autonomous fully — auto-accepted recommended decisions)

<domain>
## Phase Boundary

vibemix understands EQ/fader/jog/cue events on the 10 most-popular bedroom-DJ controllers — universal grounding spine across every DJ app. `MidiMapLoader` class replaces hardcoded `_CC_MAP`/`_NOTE_MAP` dicts with JSON-per-SKU registry. DDJ-FLX4 Sync note disambiguation (`0x60` vs `0x58`) resolved via 5-min mido sniff with Kaan + hardware Day-1.

**Critical scope boundary:** First task of phase = DDJ-FLX4 Sync note 5-min mido sniff (per STATE outstanding-todo). 9 other SKUs ship "verified" where Kaan can sniff with hardware, "inferred from Mixxx XML" where not — JSON honestly flagged either way (Pitfall 24). Generic-MIDI fallback "observes, classifies conservatively, never invents" — never auto-assigns role inference past 5 min observation.

</domain>

<decisions>
## Implementation Decisions

### MidiMapLoader Architecture (LOCKED — per ROADMAP success criteria)
- `MidiMapLoader` class lives in `src/vibemix/midi/loader.py`.
- Loads JSON-per-SKU from `src/vibemix/midi/library/<sku>.json`.
- Replaces hardcoded `_CC_MAP`/`_NOTE_MAP` dicts in `cohost_v4.py` POC port — refactor MUST pass Phase 9 FLX4 byte-equivalent golden replay (regression gate).
- JSON schema: `vendor`, `model`, `usb_name_pattern`, `verified` (bool), `cc_map`, `note_map`, `value_ranges`, `notes`.

### DDJ-FLX4 Sync Disambiguation (LOCKED — per Pitfall 25 + STATE outstanding-todo)
- 5-min mido sniff with Kaan present + DDJ-FLX4 hardware on Day-1 of phase.
- Resolves `0x60` (cohost_v4 inferred) vs `0x58` (Mixxx canonical).
- BOTH candidates documented in JSON with `verified=true` if both fire on different sync paths; sniff log committed to `.planning/phases/23-.../FLX4-SNIFF.md`.

### 10-SKU Coverage (LOCKED — per success criteria + Pitfall 24)
- 10 SKUs:
  - Pioneer DDJ-FLX4 (verified Day-1)
  - Pioneer DDJ-400 (verified if hardware available; else `inferred` from Mixxx)
  - Pioneer DDJ-FLX6
  - Pioneer DDJ-FLX10
  - Pioneer DDJ-SX3
  - Pioneer XDJ-RX3
  - Hercules DJControl Inpulse 300
  - Hercules DJControl Inpulse 500
  - Numark Party Mix Live
  - Numark Mixstream Pro+
- `verified` vs `inferred` flag in each JSON honestly reflects sniff status (Pitfall 24 — telemetry surfaces flag in events.jsonl).

### Community Sniff Tooling (LOCKED — per success criteria)
- `scripts/sniff_controller.py` standalone tool: captures CC + note + value-range over N seconds; emits draft JSON for PR submission.
- Documented in `CONTRIBUTING.md` (Phase 26 references this — controller-mapping path).
- PR review checklist in `CONTRIBUTING.md` requires `verified=true` + sniff log artifact.

### Generic-MIDI Fallback (LOCKED — per success criteria)
- "Observes, classifies conservatively, never invents."
- Logs raw activity in `events.jsonl` (`midi_observed` event with raw bytes).
- NEVER auto-assigns role inference past 5 min observation.
- Tells user "I see MIDI activity but don't know your controller — sniff it via Settings → MIDI for me to learn it" (UI surface stays minimal in v2.0).

### Magnitude-Aware Capture (Claude's Discretion within constraint)
- MIDI-14 carry-forward: delta semantic ("small high boost" vs "kill the lows") preserved per JSON value-range metadata.
- Threshold tuning per controller in `value_ranges` field.

### POC Port-From (LOCKED — per CLAUDE.md POC rule)
- Canonical baseline: `cohost_v4.py` `ControllerState` + `_CC_MAP`/`_NOTE_MAP` (per memory `project_v4_canonical_baseline`).
- POC files remain reference-only — DO NOT modify `cohost_v4.py`, `cohost_v3.py`, `cohost_lk.py`, `cohost_v2.py`, `cohost.py`.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `cohost_v4.py` `ControllerState` + `_CC_MAP` + `_NOTE_MAP` — port-from reference (DO NOT modify).
- `src/vibemix/midi/controller_state.py` — Phase 9 FLX4 verified ControllerState (refactor target).
- Phase 9 byte-equivalent golden replay tests in `tests/midi/` — must stay green after MidiMapLoader refactor.
- Mixxx XML controller mapping repository (public reference) — source of `inferred` mappings for 9 non-FLX4 SKUs.

### Established Patterns
- `mido` + `python-rtmidi` MIDI ingest layer (Phase 9).
- Hot-plug re-enumeration every 2s (MIDI-01).
- `events.jsonl` audit trail for every MIDI event.
- USB device-name pattern matching for auto-detect (MIDI-02).

### Integration Points
- `MidiMapLoader.load(controller_name) -> ControllerMap` consumed by `ControllerState.__init__`.
- `EventDetector` MIX_MOVE detection consumes `ControllerState.recent_moves` ring (12s window).
- Settings → MIDI tab surfaces controller list + sniff button (CDJ Whisper v5 primitives).
- `scripts/sniff_controller.py` standalone — no IPC, just file in / JSON out.

</code_context>

<specifics>
## Specific Ideas

- Wave 0 (Day-1): DDJ-FLX4 Sync 5-min sniff with Kaan + hardware → FLX4-SNIFF.md verdict.
- Wave 1: MidiMapLoader class + JSON schema lock + Phase 9 byte-equivalent regression gate.
- Wave 2: 10 SKU JSON files committed (verified or inferred, honestly flagged).
- Wave 3: `scripts/sniff_controller.py` standalone tool + CONTRIBUTING.md PR path docs.
- Wave 4: Generic-MIDI fallback + 5-min observation gate + events.jsonl `midi_observed` audit.

</specifics>

<deferred>
## Deferred Ideas

- ML-based controller auto-classification (v2.x — heuristic name-pattern in v2.0).
- User-defined custom maps via in-app UI editor (v2.x — sniff tool produces JSON for now, user hand-edits).
- Real-time map hot-reload during session (v2.x — restart required in v2.0).
- DDJ-1000, Numark Mixtrack Pro FX, Reloop Beatpad — defer to v2.0.1 community PRs (10-SKU LOCKED for v2.0).
- MIDI-out feedback to controller LEDs (v2.x — read-only in v2.0).
</deferred>

---

*Phase: 23-10-sku-midi-controller-library-midimaploader*
*Context gathered: 2026-05-14 (smart discuss, fully autonomous)*
