# FLX4 BlackHole 16ch Deck-B Routing Probe

Date: 2026-06-01

Source session:
`~/Library/Application Support/vibemix/recordings/20260601-203332/`

Runtime command:

```bash
VIBEMIX_DEV_SIDECAR=1 \
VIBEMIX_INPUT_DEVICE="BlackHole 16ch" \
VIBEMIX_INPUT_CHANNELS=4 \
VIBEMIX_DECK_AUDIO_CHANNELS="A=0,1;B=2,3" \
VIBEMIX_DECK_VISION=0 \
PYTHONUNBUFFERED=1 \
uv run python -m vibemix
```

Result:

- Source runtime opened `BlackHole 16ch @ 48000Hz (4ch)`.
- Rekordbox UI showed two decks playing, but Vibemix captured only the first deck pair.
- Trace count over the run:
  - `deck_audio_capture=A_active+B_silent`: 240
  - `deck_audio_capture=A_active+B_active`: 0
  - `B_active`: 0
  - nonzero `B_rms`: 0
  - `deck_audio_support=no_deck_route`: 240
- The cohost emitted one broad sound-description line and stripped one later candidate; no deck-B causal claim was allowed.

Interpretation:

Vibemix can open the 16-channel device and process a 4-channel deck map, but the live Rekordbox/Multi-Output routing is not feeding Deck B into BlackHole channels `2,3`. This is a rig-routing/setup blocker, not evidence that the cohost should claim Deck B. The app correctly remains in `no_deck_route` / `A_active+B_silent` proof state.

Next useful check:

Change Rekordbox audio output routing so Deck 1 sends to BlackHole channels `0,1` and Deck 2 sends to BlackHole channels `2,3`, then rerun this exact command. Acceptance is at least one trace window with `deck_audio_capture=A_active+B_active` and nonzero `B_rms`.
