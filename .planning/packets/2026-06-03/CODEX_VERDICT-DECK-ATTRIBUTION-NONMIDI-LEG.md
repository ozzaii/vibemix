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

---

## 2026-06-04 Refresh Wire Follow-Up

**Item:** Deck attribution non-MIDI leg, refresh writer half  
**SHA:** `d84144e9 fix(state): lift nowplaying playback into audible deck`

### What Landed

- `state/refresh.py` now reads `deck_source.source_snapshot()` before assigning
  `MusicState.audible_deck`.
- If controller-derived attribution and verified deck-pair audio both return `none`, refresh
  accepts the poller's `nowplaying_playback` provenance as a nominal A/B side at
  `NOWPLAYING_PLAYBACK_CONF=0.5`.
- The fallback requires `resolved_side_rule=nominal_nowplaying_seed_not_physical_deck_proof`.
  It still stays below `DECK_CITE_MIN_CONF`, so it can lift `audible_track_confidence` to the
  TRACK_CHANGE floor without minting citable `key:`/`track:` evidence.

### User Value

On FLX4 / no-MIDI-motion / master-only rigs, Sven and the pill can now treat an actively
playing DJ-app nowplaying title as real live context instead of leaving the live state stuck at
`audible_deck=none`.

### Proof

Code/test:

- `uv run pytest -q tests/state/test_refresh.py::test_tick_uses_nowplaying_playback_deck_status_when_controller_silent tests/state/test_refresh.py::test_tick_refuses_unverified_deck_audio_fallback_when_controller_silent tests/state/test_refresh.py::test_tick_writes_audible_deck_and_track tests/state/test_deck_poller.py::test_nowplaying_playback_seeds_deck_when_controller_has_no_midi_motion`
  - `4 passed`
- `uv run pytest -q tests/state/test_refresh.py tests/state/test_refresh_deck.py tests/state/test_deck_poller.py tests/state/test_deck_context.py tests/runtime/test_speak_gate.py tests/runtime/test_suggestion_voice.py`
  - `288 passed`
- `uv run pytest -q tests/state/test_event_detector.py tests/state/test_hype_anti_slop.py tests/state/test_coach_anti_slop.py tests/coach/test_citation_linter.py tests/state/test_evidence_registry.py`
  - `115 passed`
- `uv run ruff check src/vibemix/state/refresh.py tests/state/test_refresh.py`
  - passed
- `uv run ruff format --check src/vibemix/state/refresh.py tests/state/test_refresh.py`
  - passed

Live source / by-eye:

- Relaunched current source with `VIBEMIX_DEV_SIDECAR=1`, `VIBEMIX_LOCAL_TTS=0`,
  `VIBEMIX_INPUT_DEVICE=eqMac`, and `VIBEMIX_OUTPUT_DEVICE=Multi-Output`.
- Startup log confirmed `AI voice output muted`, `MOSS local TTS is disabled`, FLX4 MIDI input
  selected, and output/passthrough routed to `Multi-Output Device`.
- Websocket status showed `midi_device=DDJ-FLX4`, `midi_activity=connected_no_midi_traffic`,
  `voice=muted`, `capture_device=eqMac Export`.
- Session snapshots showed `music.rms=0.0`, `music.peak=0.0`, `track=null`, `bpm=null`,
  `cohost_status=IDLE`.

### Remaining Live Blocker

By-ear proof did **not** fire because the current capture route is silent: `eqMac Export` is
reading zero music. The code path is pinned by tests and loaded in a fresh muted source run, but
the rig still needs Rekordbox/FLX4 audio routed into the capture loopback before a real
TRACK_CHANGE / pill / Sven receipt can occur.
