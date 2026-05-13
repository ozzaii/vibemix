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

A controller profile looks like this — match the shape of any of the existing `src/vibemix/midi/profiles/*.json` files:

```json
{
  "name": "Your Vendor Your Model",
  "slug": "your_vendor_your_model",
  "port_name_substr": "Your Controller MIDI Port",
  "deck_a": {
    "eq_low": {"type": "cc", "control": 38, "channel": 0},
    "eq_mid": {"type": "cc", "control": 39, "channel": 0},
    "eq_high": {"type": "cc", "control": 40, "channel": 0},
    "fader": {"type": "cc", "control": 41, "channel": 0}
  },
  "deck_b": { /* same shape */ },
  "global": {
    "crossfader": {"type": "cc", "control": 99, "channel": 0}
  }
}
```

Fields:

- `name` — display name, what the calibration wizard shows.
- `slug` — kebab-case file basename.
- `port_name_substr` — substring matched against the macOS / Windows MIDI port name for auto-detection.
- `deck_a` / `deck_b` — per-deck control map. The shape is locked by `src/vibemix/midi/profiles/_schema.py` (run `pytest tests/midi/` to confirm).
- `global` — controls not bound to a deck (crossfader, master gain).
- For pads, hot cues, loop tools etc., the curated mappings include them as separate keys. Mirror what the most similar curated controller does.

## Submitting

1. Open a `[controller]` issue first so we don't get duplicates.
2. Fork, drop the JSON in `src/vibemix/midi/profiles/`, add a smoke test in `tests/midi/test_<your_slug>.py` modeled on the existing FLX4 test.
3. Sign off your commits (`git commit -s`) per DCO.
4. PR title: `feat(midi): add <vendor> <model> mapping`.
5. CI auto-merges non-conflicting profile additions once tests are green.

If you don't have time to write the JSON yourself but you own the controller and can send us a MIDI capture (`mido` echo output for every control), open a `new_controller` issue with the capture attached — we'll write the profile.
