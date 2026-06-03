# CODEX VERDICT — DECK-ATTRIBUTION-NONMIDI-LEG

**Item:** Deck attribution non-MIDI leg so next-song receipts have a seed on master-only / no-MIDI rigs  
**SHA:** `b1322c09 fix(deck-state): seed receipts from nowplaying playback`  
**Date:** 2026-06-03

## What Landed

- Added a nowplaying playback fallback in `DeckPoller._build_decks` when controller-derived
  `derive_audible_deck(...)` returns no A/B side.
- The fallback requires a DJ-app nowplaying source, a nonempty title, finite active playback
  position, and `playback_rate > 0.05`.
- It seeds a nominal side with confidence `0.5`, enough for seed/context visibility but below
  `DECK_CITE_MIN_CONF=0.6`.
- Bounded websocket/status context now carries `audible_deck_source`,
  `nowplaying_playback`, and `resolved_side_rule` so the UI / prompt path can see the
  provenance.

## User Value

A Free user on a master-only or connected-but-no-MIDI rig can now get a next-song receipt seed
from the real OS nowplaying playback row instead of an empty `decks:{}` collapse.

## Proof

By source/test:

- `uv run pytest -q tests/state/test_deck_poller.py tests/state/test_deck_context.py::test_deck_source_context_renders_nowplaying_playback_provenance tests/state/test_deck_context.py::test_deck_source_context_renders_source_status_without_deck_rows tests/runtime/test_ws_bus_snapshot.py tests/runtime/test_suggestion.py::test_resolve_seed_context_withholds_target_when_audible_side_is_uncertain`
  - `43 passed`
- `uv run pytest -q tests/state/test_deck_poller.py tests/state/test_deck_context.py tests/runtime/test_suggestion.py tests/runtime/test_ws_bus_snapshot.py`
  - `241 passed`
- `uv run pytest -q tests/state/test_refresh.py tests/runtime/test_ws_bus_deck_state.py`
  - `89 passed`
- `uv run ruff check src/vibemix/state/deck_poller.py src/vibemix/state/deck_context.py src/vibemix/runtime/ws_bus.py tests/state/test_deck_poller.py tests/state/test_deck_context.py`
  - passed

By-eye / live-app:

- Relaunched the current-source app meeting-safe with:
  `VIBEMIX_LOCAL_TTS=0 VIBEMIX_DEV_SIDECAR=1 VIBEMIX_OUTPUT_DEVICE='Multi-Output Device'`.
- The websocket bus was reachable on `127.0.0.1:8765`; status tick reported
  `voice=muted`, `gemini=ok`, `livekit=ok`, `midi=1`.
- The app was idle during proof (`track:null`, `bpm:null`, meter values zero), so there was no
  live nowplaying row to light. The live proof is therefore limited to "current source launches
  safely and stays idle"; the deck-row/pill visual proof remains pending the user playing a real
  DJ-app track.

## Packet Corrections / Assumptions

- I did **not** apply the packet's implied citable confidence promotion through the XML floor.
  The fallback remains `0.5`, deliberately below `DECK_CITE_MIN_CONF`, so it can seed Viber/pill
  receipts without turning into a spoken `[deck:A]` claim.
- This is not per-deck audio proof on a 2ch master rig. It is a grounded nowplaying playback
  seed for the one audible nowplaying title.
