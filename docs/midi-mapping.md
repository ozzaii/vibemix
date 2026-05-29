# MIDI mapping guide

vibemix ships with curated mappings for 10 controllers. If yours isn't on the list, the generic positional fallback will pick up CCs and notes, but vibemix won't know whether CC 38 is your low-EQ or your hot-cue. This guide shows how to calibrate.

## Two paths

1. **Generic fallback (zero work).** Plug in your controller, launch vibemix, run through the calibration wizard. It probes a few CCs and infers rough positions. Works well enough that the AI sees you're "moving the high EQ" without knowing exactly which knob. Good enough for casual sets.

2. **Curated mapping (one JSON file).** Drop a JSON profile under `src/vibemix/midi/profiles/<your-controller-slug>.json` and vibemix knows the meaning of every knob, fader, and pad on your controller. Best feel, opens a clean contribution path.

## Extracting CC and note IDs from your controller

You need a MIDI monitor. On macOS the simplest is `mido`'s built-in echo:

```bash
source .venv/bin/activate
python -m mido.ports  # lists connected MIDI ports
python -c "import mido; \
  port = mido.open_input('YOUR CONTROLLER NAME'); \
  print([msg for msg in port])"
```

Wiggle each control. The terminal prints messages like:

```
control_change channel=0 control=38 value=64
note_on channel=0 note=0x18 velocity=127
```

Write down which control number corresponds to which physical control (low EQ left, hot cue 1, jog wheel, etc.). On Windows use [MIDI-OX](http://www.midiox.com/) or any similar monitor.

## JSON schema

Profile JSONs validate against `src/vibemix/midi/profile.py::_parse_profile` (hand-rolled validator; no `jsonschema` in the live decode path — consistent with the project-wide ban on pydantic). A controller profile looks like this — match the shape of any of the existing `src/vibemix/midi/profiles/*.json` files (`pioneer_ddj_flx4.json` is the canonical reference):

```json
{
  "id": "pioneer_ddj_flx4",
  "display_name": "Pioneer DDJ-FLX4",
  "port_name_hints": ["DDJ-FLX4", "FLX4"],
  "decks": ["A", "B"],
  "controls": {
    "vol_a":    {"kind": "cc", "channel": 0, "cc": 19, "axis": "unipolar", "deck": "A",  "field": "vol"},
    "filter_a": {"kind": "cc", "channel": 6, "cc": 23, "axis": "bipolar",  "deck": "A",  "field": "filter"},
    "xfader":   {"kind": "cc", "channel": 6, "cc": 31, "axis": "bipolar",  "deck": null, "field": "xfader"},
    "jog_a":    {"kind": "cc", "channel": 0, "cc": 33, "axis": "relative", "deck": "A",  "field": "jog"}
  },
  "buttons": {
    "play_a": {"kind": "play", "channel": 0, "note": 11, "deck": "A"},
    "sync_a": {"kind": "sync", "channel": 0, "note": 96, "deck": "A"}
  },
  "notes": "Optional human description — e.g. 'sourced from controller hardware sniff 2026-04-12'."
}
```

Fields (validated by `_parse_profile`):

- `id` — snake_case profile ID; doubles as the JSON filename stem (e.g. `pioneer_ddj_flx4.json`).
- `display_name` — what the calibration wizard + README grid show.
- `port_name_hints` — **non-empty list** of substrings matched against `mido.get_input_names()` output for auto-detection (FLX4 reports as `"DDJ-FLX4"` on macOS and `"FLX4"` on Windows — list both).
- `decks` — list of deck IDs the controller exposes (typically `["A", "B"]`; some four-deck units use `["A", "B", "C", "D"]`).
- `controls` — continuous-value bindings (faders, knobs, jog wheels, EQs, filters, crossfader). Each value carries `kind: "cc"` (today the only supported `kind`), `channel` (0-15), `cc` (CC number 0-127), `axis` (`unipolar` / `bipolar` / `relative` — affects how the magnitude is normalized), `deck` (deck ID from `decks` or `null` for global controls), and `field` (semantic field name — `vol` / `eq_low` / `eq_mid` / `eq_hi` / `tempo` / `filter` / `xfader` / `jog` etc.). Use `relative` for encoder-style controls that emit ticks around center, such as jog wheels reporting 63/65 instead of an absolute position.
- `buttons` — note-message bindings (play, cue, sync, hot cues, loop tools, jog touch). Each value carries `kind` (the semantic event — `play` / `cue` / `sync` / `jog_touch` / `loop_in` / `loop_out`), `channel`, `note` (note number 0-127), and `deck`.
- `notes` — optional one-line string surfaced in diagnostics + the contributor PR review.

To extract real values from your controller, follow the `mido` echo recipe in the "Extracting CC and note IDs" section above. Once you have the (channel, CC) and (channel, note) tuples for every physical control, fill them into the template and run `uv run pytest tests/midi/ -q` to validate.

## Submitting

1. Open a `[controller]` issue first so we don't get duplicates.
2. Fork, drop the JSON in `src/vibemix/midi/profiles/`, add a smoke test in `tests/midi/test_<your_slug>.py` modeled on the existing FLX4 test.
3. Sign off your commits (`git commit -s`) per DCO.
4. PR title: `feat(midi): add <vendor> <model> mapping`.
5. CI auto-merges non-conflicting profile additions once tests are green.

If you don't have time to write the JSON yourself but you own the controller and can send us a MIDI capture (`mido` echo output for every control), open a `new_controller` issue with the capture attached — we'll write the profile.
