# MIDI Controllers — Reference

vibemix ships with 10 curated controller mappings + a generic-MIDI fallback. The mappings are declarative JSON files in `src/vibemix/midi/profiles/`. The registry auto-detects a connected controller by case-insensitive substring match on the port name, then loads the matching profile.

## Supported Controllers (10)

| Controller | JSON | Verified |
|---|---|---|
| Pioneer DDJ-FLX4 | `pioneer_ddj_flx4.json` | ✅ Live-verified (Kaan's rig) |
| Pioneer DDJ-400 | `pioneer_ddj_400.json` | ⚠ JSON-only (Mixxx mapping basis) |
| Pioneer DDJ-FLX6 | `pioneer_ddj_flx6.json` | ⚠ JSON-only |
| Pioneer DDJ-FLX10 | `pioneer_ddj_flx10.json` | ⚠ JSON-only |
| Pioneer DDJ-1000 | `pioneer_ddj_1000.json` | ⚠ JSON-only |
| Pioneer DDJ-SX3 | `pioneer_ddj_sx3.json` | ⚠ JSON-only |
| Pioneer XDJ-RX3 | `pioneer_xdj_rx3.json` | ⚠ JSON-only |
| Numark Party Mix Live | `numark_party_mix_live.json` | ⚠ JSON-only |
| Hercules Inpulse 300 | `hercules_inpulse_300.json` | ⚠ JSON-only |
| Hercules Inpulse 500 | `hercules_inpulse_500.json` | ⚠ JSON-only |

The 9 "JSON-only" mappings derive from manufacturer MIDI implementation charts + the Mixxx controller-mappings repo (https://github.com/mixxxdj/mixxx/tree/main/res/controllers). They have not been live-tested on real hardware. Phase 16 / 20 / community PRs are the live-verification path. If you own one of these controllers and find a CC layout mismatch, please file an issue with the corrected mapping.

## Magnitude Semantics

EQ knob, channel fader, crossfader, filter, and tempo events emit a `magnitude` field for Coach prompts to render in plain English:

| Magnitude | Coach rendering |
|---|---|
| `\|m\| > 0.7` | "killed", "slammed", "max" |
| `0.4 < \|m\| ≤ 0.7` | "boosted", "cut", "dropped" |
| `0.2 < \|m\| ≤ 0.4` | "tweaked", "nudged" |
| `\|m\| ≤ 0.2` | "slight" |

- **Unipolar** controls (volume, filter): magnitude in `[0.0, 1.0]`.
- **Bipolar** controls (EQ knobs around 12 o'clock): magnitude in `[-1.0, 1.0]`, sign = direction (+ boost, − cut).

## Generic-MIDI Fallback

Any controller whose port name doesn't match a known mapping falls through to `vibemix.midi.generic`. The generic decoder emits positional events:

```python
MidiEvent(kind="generic_cc",   field="cc_0_7",    magnitude=0.5)   # CC #7 on channel 0
MidiEvent(kind="generic_note", field="note_0_60", magnitude=1.0)   # note-on for middle C
```

Coach prompts for unmapped controllers include a system-level reminder: "controller is unmapped — magnitude semantics not available; reactions limited to track audio + screen." The user gets a less semantic experience but vibemix doesn't crash.

## Hot-Plug Detection

`vibemix.midi.watcher.port_watcher_task` polls `mido.get_input_names()` every 2 seconds. On detected change:

- **New port matches a known mapping** → listener thread is restarted with the new profile. Emits a `CONTROLLER_CONNECTED` event into the agent's queue.
- **New port doesn't match** → generic fallback is bound. Emits `CONTROLLER_CONNECTED` with generic profile.
- **Existing port disappears** → emits `CONTROLLER_DISCONNECTED`.

The watcher is started by `MidiMacOS.start_port_watcher` / `MidiWindows.start_port_watcher` from the agent's main loop.

## Adding a New Controller

1. Create `src/vibemix/midi/profiles/<vendor>_<model>.json` mirroring the FLX4 schema.
2. Set `port_name_hints` to the substrings that appear in the controller's port name (case-insensitive). E.g., for the DDJ-FLX4: `["DDJ-FLX4", "FLX4"]`.
3. Fill in `controls` (CC mappings) and `buttons` (note mappings) per channel.
4. Add a golden test in `tests/midi/test_profiles_all_controllers.py`.
5. Add an entry to the table above.

The hand-validator in `vibemix.midi.profile` will reject malformed JSONs at import time — no silent defaults.

## Calibration UX

Phase 11's calibration wizard is the user-facing entry point. It shows the detected controller name, the matched profile (or "generic"), and a button to re-probe / pick a different controller. End users never edit JSONs directly.

## What's Deferred

- Per-controller LED / feedback output (post-v1).
- Auto-mapping wizard (build a custom mapping in-app by wiggling controls) — post-v1.
- Multi-controller simultaneous use (two controllers connected at once) — out of v1.
- Live verification of the 9 JSON-only mappings on real hardware — Phase 16 / 20 / community contributions.
