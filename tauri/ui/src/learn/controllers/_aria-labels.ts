// SPDX-License-Identifier: Apache-2.0
// Phase 91 Plan 05 — Learn-window ARIA label lookup (RENDER-03 binding).
//
// One source of truth for every `<g data-control-id>` aria-label rendered
// across the 11 controller SVGs. Keyed on the SAME `<field>:<deck>` string
// the SVG `data-control-id` carries AND the Python wire-shape uses
// (`src/vibemix/midi/profiles/<id>.json::controls.*.field` +
// `controls.*.deck`, per `_read_current_positions` in
// `src/vibemix/learn/midi_mirror.py`).
//
// Coverage: every (field, deck) pair surfaced by any of the 10 shipped
// MIDI profiles under `src/vibemix/midi/profiles/`. Includes deck variants
// A/B/C/D (DDJ-1000 / DDJ-FLX10 / DDJ-SX3 expose 4 deck channels), the
// non-deck-bound master controls (xfader / filter_fx / tap_tempo), and
// the per-deck transport (play/cue/sync), pitch (tempo), and jog touch
// states (jog_touch).
//
// Style: human-readable, lowercase except the EQ-band abbreviations, no
// vendor brand-marks, no exclamations. Used by parity-gate test
// `tauri/ui/tests/learn/test_aria_labels_present.spec.ts` (the SVGs MUST
// reference these labels verbatim).

export const ARIA_LABELS: Record<string, string> = {
  // Channel faders — vol per deck
  "vol:A": "channel fader, deck A",
  "vol:B": "channel fader, deck B",
  "vol:C": "channel fader, deck C",
  "vol:D": "channel fader, deck D",

  // EQ knobs — HI / MID / LOW per deck
  "eq_hi:A": "EQ-HI knob, deck A",
  "eq_hi:B": "EQ-HI knob, deck B",
  "eq_hi:C": "EQ-HI knob, deck C",
  "eq_hi:D": "EQ-HI knob, deck D",
  "eq_mid:A": "EQ-MID knob, deck A",
  "eq_mid:B": "EQ-MID knob, deck B",
  "eq_mid:C": "EQ-MID knob, deck C",
  "eq_mid:D": "EQ-MID knob, deck D",
  "eq_low:A": "EQ-LOW knob, deck A",
  "eq_low:B": "EQ-LOW knob, deck B",
  "eq_low:C": "EQ-LOW knob, deck C",
  "eq_low:D": "EQ-LOW knob, deck D",

  // Pitch faders per deck (renders the bipolar tempo slider)
  "tempo:A": "pitch fader, deck A",
  "tempo:B": "pitch fader, deck B",
  "tempo:C": "pitch fader, deck C",
  "tempo:D": "pitch fader, deck D",

  // Filter knobs per deck (bipolar — center = bypass)
  "filter:A": "filter knob, deck A",
  "filter:B": "filter knob, deck B",
  "filter:C": "filter knob, deck C",
  "filter:D": "filter knob, deck D",

  // Crossfader — master section, no deck
  xfader: "crossfader",

  // Transport buttons per deck
  "play:A": "play button, deck A",
  "play:B": "play button, deck B",
  "play:C": "play button, deck C",
  "play:D": "play button, deck D",
  "cue:A": "cue button, deck A",
  "cue:B": "cue button, deck B",
  "cue:C": "cue button, deck C",
  "cue:D": "cue button, deck D",
  "sync:A": "sync button, deck A",
  "sync:B": "sync button, deck B",
  "sync:C": "sync button, deck C",
  "sync:D": "sync button, deck D",

  // Jog wheels — touch-detect per deck (FLX4 uses `jog` kind, others
  // `jog_touch` — the wire shape resolves to `jog_touched:<deck>` after
  // ControllerState normalisation, but the static SVG label can use
  // either form — both keys land here.)
  "jog_touch:A": "jog wheel, deck A",
  "jog_touch:B": "jog wheel, deck B",
  "jog_touch:C": "jog wheel, deck C",
  "jog_touch:D": "jog wheel, deck D",
  "jog_touched:A": "jog wheel, deck A",
  "jog_touched:B": "jog wheel, deck B",
  "jog_touched:C": "jog wheel, deck C",
  "jog_touched:D": "jog wheel, deck D",

  // Loop in/out — per deck (DDJ-400 + DDJ-FLX4)
  "loop_in:A": "loop-in button, deck A",
  "loop_in:B": "loop-in button, deck B",
  "loop_out:A": "loop-out button, deck A",
  "loop_out:B": "loop-out button, deck B",

  // Hot-cue pads — labelled per deck (the Wave-2 controllers expose
  // multi-pad arrays; the canonical wire key is just `hotcue:<deck>`
  // because the profile JSONs bind a single hotcue field today).
  "hotcue:A": "hot-cue pads, deck A",
  "hotcue:B": "hot-cue pads, deck B",

  // Master-section extras (Hercules Inpulse 500 + variants)
  filter_fx: "master filter FX",
  tap_tempo: "tap tempo button",
};
