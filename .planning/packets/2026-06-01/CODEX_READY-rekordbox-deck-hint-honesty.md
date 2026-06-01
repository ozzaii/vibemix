# CODEX_READY: Rekordbox Deck-Hint Honesty Gate

Date: 2026-06-01
Author: Codex
Status: LAND packet, split from the held Deck Audio Controller-Weighted lane
Suggested commit: `fix(audio): reject stale rekordbox deck routing hints`

## Decision

LAND this narrow safety slice.

This is not the full controller-weighted master feature. It only prevents
Vibemix from treating stale Rekordbox external-deck settings as live deck
isolation when the current top-level Rekordbox output is a stereo/internal
master device such as a Multi-Output Device.

## Files

- `src/vibemix/audio/deck_capture.py`
- `src/vibemix/audio/deck_signal.py`
- `tests/audio/test_deck_capture.py`
- `tests/audio/test_deck_signal.py`

Keep out:

- `src/vibemix/midi/state.py`
- `src/vibemix/__main__.py`
- controller-weighted master synthesis
- DROP-call speech/timing files

## What Changed

- `rekordbox_deck_output_routing_hint()` now prefers candidates matching the
  current top-level `audioDeviceManager` output row when Rekordbox exposes one.
- If the current output is stereo/internal master, stale external mixer rows are
  ignored instead of auto-enabling per-deck capture.
- Auto-detected Rekordbox deck pairs stay configured but not consumable until
  both configured deck sides have shown audio at least once.
- `signal_frame_from_capture()` consumes `effective_enabled()` so the Judge and
  downstream executed-mix evidence stay honest-null for unverified auto pairs.
- Manual `VIBEMIX_DECK_AUDIO_CHANNELS=A=...;B=...` maps remain operator-trusted.

## Evidence

Focused source tests:

```text
uv run pytest -q tests/audio/test_deck_capture.py tests/audio/test_deck_signal.py tests/midi/test_state.py tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py
170 passed in 0.62s
```

Focused Ruff:

```text
uv run ruff check src/vibemix/audio/deck_capture.py src/vibemix/audio/deck_signal.py src/vibemix/midi/state.py src/vibemix/__main__.py tests/audio/test_deck_capture.py tests/audio/test_deck_signal.py tests/midi/test_state.py tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py
All checks passed!
```

Staged whitespace gate:

```text
git diff --cached --check
```

## Boundary

This proves an honesty guard, not release-complete deck separation.

The full `feat(audio): weight deck-pair master by controller posture` lane
still requires live proof that controller posture changes the audible
master/citation context. Do not land the remaining dirty MIDI/input-callback or
controller-weighted master hunks under this packet.
