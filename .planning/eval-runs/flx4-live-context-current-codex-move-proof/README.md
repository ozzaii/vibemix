# FLX4 live move and guard proof

Date: 2026-06-01, Europe/Istanbul.

This packet records a source-runtime proof from the live Rekordbox + DDJ-FLX4 +
BlackHole 16ch rig. It is intentionally narrow: it proves the app consumed live
audio/controller context and protected the co-host from one bad live claim. It
does not prove separate Deck A/B audio capture or correct transition judging.

## Runtime under test

Command:

```sh
VIBEMIX_DEV_SIDECAR=1 \
VIBEMIX_INPUT_DEVICE="BlackHole 16ch" \
VIBEMIX_DECK_AUDIO_CHANNELS=auto \
VIBEMIX_DECK_VISION=0 \
PYTHONUNBUFFERED=1 \
uv run python -m vibemix
```

Session:

```text
/Users/ozai/Library/Application Support/vibemix/recordings/20260601-200842/
```

Session window:

```text
started_at_iso=2026-06-01T20:08:42.808+03:00
ended_at_iso=2026-06-01T20:17:42.930+03:00
duration_s=540.121
crashed=false
```

Important startup facts from the runtime console:

- TTS was MOSS-local only: no cloud TTS fallback.
- Brain model was Gemini direct: `gemini-3.5-flash`.
- FLX4 controller profile loaded: `pioneer_ddj_flx4`.
- Audio input opened as `BlackHole 16ch @ 48000Hz (2ch)`.
- Screen vision was disabled by default.
- Websocket bus was live on `127.0.0.1:8765`.

## Files in this packet

- `live_context_proof.json`: first live-context proof during user movement.
- `live_context_active.json`: later active live-context proof.
- `live_context_active_digest.json`: compact digest of the later proof.
- `session_event_digest.jsonl`: selected `events.jsonl` rows for event, LLM,
  AI-message, and live-claim-guard evidence.
- `session_trace_digest.jsonl`: selected `trace.jsonl` rows for MIDI movement,
  emitted events, skipped deck-audio parts, and live-evidence changes.
- `direct_midi_callback.jsonl` and `direct_midi_active.jsonl`: standalone MIDI
  sniffer windows. Both happened to catch quiet or contended windows.

## What this proves

The app heard live master audio and observed the controller posture:

- `live_context_active.json` reported `ok=true`, `frames_seen=4`,
  `audible=true`, `deck=mix`, `phase=peak`, `music=0.156`.
- `deck_mixer.connected=true` with both sides visible:
  `A(vol=127 low=84 mid=77 hi=74 play=false)` and
  `B(vol=127 low=0 mid=79 hi=77 play=true)`.
- The app reported two-deck route support from controller posture:
  `deck_audio_context[...] routing=A=dominant(0.70) B=dominant(0.70)
  support=two_deck_route`.

The runtime consumed real controller moves and used them in live evidence:

- `session_trace_digest.jsonl` contains `MIDI` move rows such as
  `B_low: max->boost`, `B_low: boost->flat`, `B_low: killed->deep-cut`,
  `B_hi: flat->boost`, `A_mid: flat->boost`, and xfader moves.
- `session_event_digest.jsonl` contains `MIX_MOVE` events and `llm_invoke`
  rows with recent moves and grounding refs.
- The app emitted live events while audible, including `MIX_MOVE`, `PHASE`,
  and `HEARTBEAT`.

The live-claim guard protected the product from one bad co-host claim:

- At `t=96.508`, `live_claim_guard` fired with
  `policy=mixer_contradiction`, `reason=low_kill_not_in_mixer_state`,
  `action=strip`.
- The raw model text claimed the DJ killed deck B lows too aggressively for a
  transition.
- The guard corrected that to: `I can't tell from this live proof whether the
  control caused that.`
- The corresponding `ai_message` row at `t=96.510` has
  `stop_reason=strip`, `message_chars=0`, and `citation.action=strip`, so the
  bad claim did not reach MOSS or the transcript as spoken output.

The co-host eventually spoke two sound-only observations:

- `0016_201558`, `stop_reason=emit`, `message_chars=198`.
- `0019_201730`, `stop_reason=emit`, `message_chars=198`.
- Both were grounded sound reads, not transition or deck-identity claims.

Important open follow-up: both emitted messages still carried a bracketed
evidence atom in the assistant message, for example
`[mix:deck_audio_support=two_deck_route]` and
`[mix:audio_delta=onset_density_fell_31pct_clear]`. This source process was
already running while other sessions were landing commits, so treat this as a
live re-check item rather than a final current-HEAD verdict: restart from the
latest HEAD and verify whether evidence atoms are removed from the actual MOSS
speech path while remaining available in logs/receipts.

## What this does not prove

Deck identity and transition quality remain unproven:

- `readiness.ready=false`, diagnosis `missing_physical_proof`.
- `deck_state_resolved=false`, `deck_state_pair_resolved=false`, and no citable
  track IDs were available.
- Library cache was missing: `~/.cache/vibemix/library.pkl` was not present.
- Now Playing was blocked by a non-DJ owner: `com.apple.webkit.gpu`.
- Screen vision was disabled.

Separate Deck A/B audio remains unproven:

- `deck_audio_separation_context` says the device had 16 input channels but the
  runtime opened only 2 channels.
- Current capture was `P1_global_mix`.
- `deckA_audio=not_captured`, `deckB_audio=not_captured`,
  `per_deck_audio=not_attached`, `isolated_decks=false`.
- `trace.jsonl` repeatedly logged `deck_audio_parts_skipped` with
  `reason=no_deck_audio_buffers`.

Brain reliability was poor in this run:

- Most AI turns ended with Gemini `503 Service Unavailable` or playout timeout.
- Because MOSS is the only TTS source and Gemini returned no usable text, the
  co-host was mostly silent for the right reason: no fake fallback.
- Session cost was EUR 0.0148 with 50.6% cache hit rate.

Standalone MIDI sniffer caveat:

- The app runtime logged MIDI movement, but the separate callback sniffer files
  in this packet caught zero frames. Treat those files as quiet-window evidence,
  not as proof that the FLX4 was inactive.

## Product consequence

Safe claims after this run:

- VibeMix can hear the current master output from BlackHole 16ch.
- VibeMix can see FLX4 controller posture and runtime MIDI movements.
- VibeMix can put those moves into grounded prompt context.
- The live-claim guard can strip a bad mixer-causality claim before speech.

Unsafe claims after this run:

- Do not claim isolated Deck A/B audio.
- Do not claim resolved Deck A/B track identity.
- Do not claim transition, blend, switch, handoff, or timing quality from this
  proof.
- Do not claim the co-host is reliably speaking while Gemini is returning 503s.
- Do not claim citation atoms are safely out of speech until a fresh current-HEAD
  MOSS run proves it.
