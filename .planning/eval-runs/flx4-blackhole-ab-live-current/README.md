# FLX4 / BlackHole A+B Live Probe — 2026-06-01 20:03 +03

Context: Kaan reported Rekordbox was live with Deck A and Deck B on DDJ-FLX4.
This probe was run from the repo on the same Mac without launching the Vibemix
app or binding the websocket bus.

## Audio device enumeration

Observed devices:

- `DDJ-FLX4` — input 2, output 4, 48 kHz
- `BlackHole 16ch` — input/output 16, 48 kHz
- `BlackHole 2ch` — input/output 2, 48 kHz

## Direct audio capture

Short CoreAudio captures showed:

- `BlackHole 16ch`: active only on channels 1-2
  - ch01 `rms=0.06595`, `peak=0.52027`
  - ch02 `rms=0.01608`, `peak=0.12686`
  - ch03-ch16 silent
- `BlackHole 2ch`: silent on both channels
- `DDJ-FLX4` input: effectively silent on both channels

Interpretation: the Mac can hear the master/main signal through BlackHole16,
but this run did not expose independent Deck A/B channel pairs. Do not treat
this as per-deck audio proof.

## MIDI probe

`uv run python scripts/sniff_controller.py --list` showed the input port:

- `DDJ-FLX4`

Two direct sniffs saw no controller frames:

- `uv run python scripts/sniff_controller.py --port DDJ-FLX4 --seconds 8 --mode callback`
  - summary: `frames=0`, `unique_cc=[]`, `unique_notes=[]`
- `uv run python scripts/sniff_controller.py --port DDJ-FLX4 --seconds 12 --mode poll`
  - summary: `frames=0`, `unique_cc=[]`, `unique_notes=[]`

Interpretation: the controller is enumerated, but this proof window did not
observe MIDI motion. Do not let the co-host claim it saw controller moves from
this run.

## Product consequence

This is a HOLD artifact for FLX4/deck-pair/live-move proof:

- master audio is observable
- separate deck lanes are not observable
- direct MIDI motion is not observable in this probe

The correct next product work is an honest routing/motion diagnostic, not a
claim that Deck B or FLX4 moves are grounded.
