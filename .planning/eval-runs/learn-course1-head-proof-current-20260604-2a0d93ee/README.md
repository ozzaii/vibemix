# Learn Course-1 Current-HEAD Bus Proof - 2026-06-04

Current head when consolidated: `845d202382ab75dc56cdcf489b5c497abccb5738`

Capture heads:

- `l103_eq_current_bus.json`: `a3e7dc0b45efea7ff640be78ddc0847f9a852b0c`
- `l114_eq_exemplars_current_bus.json`: `a3e7dc0b45efea7ff640be78ddc0847f9a852b0c`
- `l113_waveform_current_bus.json`: `a3e7dc0b45efea7ff640be78ddc0847f9a852b0c`
- `l201_grade_auto_advance_current_bus.json`: `2a0d93eebb314e3227bcc4995b1b9d4e19930709`

Learn/audio diff from first capture to consolidated head: `[]`

Checks:

- L1.03 EQ-audio bus: `True`
- L1.14 three EQ exemplars: `True`
- L1.13 waveform with breakdown cue: `True`
- L2.01 cited grade auto-advance: `True`

Result: `True`

This is by-bus proof. It records live websocket envelopes for the player, waveform, tutor, grade, completion, and advance paths from current source with `VIBEMIX_DEV_SIDECAR=1` and isolated Learn progress files. It does not claim human ear confirmation.
