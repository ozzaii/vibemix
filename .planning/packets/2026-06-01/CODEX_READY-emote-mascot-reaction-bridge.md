# CODEX_READY: Emote Mascot Reaction Bridge

Date: 2026-06-01
Author: Codex
Status: LAND packet, source-wired mascot reaction slice
Package: Package 8C - Mascot Emote Reaction Bridge

## Decision

LAND this slice as `feat(mascot): bridge cohost emotes to reactions`.

The source path is now wired end-to-end for model control tags that are safe to
use: a co-host response may include a whitelisted `[emote:*]` tag, the spoken
text is stripped before TTS/transcript logging, `MusicState` receives the latest
reaction intent plus a monotonically increasing sequence number, `ws_bus.py`
emits both fields in the 30Hz snapshot, and the production Tauri mascot consumes
a fresh sequence exactly once.

## Files

- `src/vibemix/agent/emote_parser.py`
- `src/vibemix/agent/dj_cohost.py`
- `src/vibemix/state/music_state.py`
- `src/vibemix/runtime/ws_bus.py`
- `tauri/ui/src/mascot/index.ts`
- `tauri/ui/src/mascot/reaction-intent.ts`
- `tauri/ui/src/mascot/reaction-intent.test.ts`
- `tests/agent/test_emote_parser.py`
- `tests/agent/test_dj_cohost.py`
- `tests/e2e/test_seam_p31__ws_bus.py`

Observed adjacent dirty proof file:

- `tests/runtime/test_ws_bus_snapshot.py` was included in sanity checks because
  it is dirty in the same snapshot area, but it is not part of Package 8C's
  Include list.

## What Changed

- `emote_parser.py` defines the Python whitelist and strips complete
  `[emote:name]` tags from speech text. Unknown complete tags are removed from
  speech but are not returned as mascot intents.
- `has_emote_tag(...)` was added during this verification pass after Codex found
  a leak shape: unknown complete tags were stripped from `spoken_text` but the
  replay buffer could still hold the raw tag when no whitelisted intent existed.
- `DJCoHostAgent.llm_node` strips emote tags on streaming chunks and on
  post-stream replay paths. It only writes `last_reaction_intent` and increments
  `last_reaction_intent_seq` when the turn was actually emitted/bypassed and
  produced non-empty spoken text.
- `MusicState` carries `last_reaction_intent_seq` beside
  `last_reaction_intent`.
- `ws_bus.py` emits `reaction_intent` and `reaction_intent_seq` in the mascot
  snapshot frame.
- `selectReactionIntent(...)` accepts only production mascot reactions with a
  finite numeric sequence newer than the last consumed sequence.
- `mascot/index.ts` maps a selected intent to an existing mascot state, switches
  immediately, and schedules a short settle-back follow-up.

## Source Evidence

- `src/vibemix/agent/emote_parser.py:65` parses whitelisted tags;
  `src/vibemix/agent/emote_parser.py:80` detects complete control tags;
  `src/vibemix/agent/emote_parser.py:85` strips all complete lowercase emote
  tags from returned text.
- `src/vibemix/agent/dj_cohost.py:2733` and
  `src/vibemix/agent/dj_cohost.py:2754` strip tags from streaming TTS chunks.
- `src/vibemix/agent/dj_cohost.py:2954` computes stripped spoken text;
  `src/vibemix/agent/dj_cohost.py:2956` collapses replay buffers whenever any
  complete emote tag was present, including unknown tags.
- `src/vibemix/agent/dj_cohost.py:3187` gates mascot state writes to
  emitted/bypassed, non-empty spoken turns; `src/vibemix/agent/dj_cohost.py:3190`
  writes the state and `src/vibemix/agent/dj_cohost.py:3195` logs the event.
- `src/vibemix/state/music_state.py:172` stores the current intent and
  `src/vibemix/state/music_state.py:173` stores its sequence.
- `src/vibemix/runtime/ws_bus.py:989` and
  `src/vibemix/runtime/ws_bus.py:990` put both fields on the live snapshot.
- `tauri/ui/src/mascot/reaction-intent.ts:21` selects only fresh whitelisted
  snapshot intents.
- `tauri/ui/src/mascot/index.ts:228` consumes that selector in the production
  mascot websocket handler.

## Verification

Compile:

```text
uv run python -m py_compile src/vibemix/agent/dj_cohost.py src/vibemix/agent/emote_parser.py src/vibemix/state/music_state.py src/vibemix/runtime/ws_bus.py
```

Backend behavior:

```text
uv run pytest -q tests/agent/test_emote_parser.py tests/agent/test_dj_cohost.py::test_llm_node_strips_emote_tags_and_sets_mascot_intent tests/agent/test_dj_cohost.py::test_llm_node_strips_unknown_emote_tags_without_mascot_intent tests/agent/test_dj_cohost_streaming_pipe.py tests/e2e/test_seam_p31__ws_bus.py
43 passed in 1.16s
```

Shared co-host/ws snapshot sanity:

```text
uv run pytest -q tests/agent/test_dj_cohost.py::test_llm_node_logs_ai_message_observability_with_moves tests/agent/test_dj_cohost.py::test_llm_node_ai_message_uses_prompt_time_mixer_snapshot tests/agent/test_dj_cohost.py::test_llm_node_strips_emote_tags_and_sets_mascot_intent tests/agent/test_dj_cohost.py::test_llm_node_strips_unknown_emote_tags_without_mascot_intent tests/runtime/test_ws_bus_snapshot.py
13 passed in 1.11s
```

Lint:

```text
uv run ruff check src/vibemix/agent/emote_parser.py src/vibemix/agent/dj_cohost.py src/vibemix/state/music_state.py src/vibemix/runtime/ws_bus.py tests/agent/test_emote_parser.py tests/agent/test_dj_cohost.py tests/e2e/test_seam_p31__ws_bus.py tests/runtime/test_ws_bus_snapshot.py
All checks passed!
```

Frontend:

```text
npm --prefix tauri/ui test -- src/mascot/reaction-intent.test.ts src/mascot/event-dispatcher.test.ts
22 passed
```

Build:

```text
npm --prefix tauri/ui run build
vite built the mascot bundle successfully.
```

Whitespace:

```text
git diff --check -- src/vibemix/agent/emote_parser.py src/vibemix/agent/dj_cohost.py src/vibemix/state/music_state.py src/vibemix/runtime/ws_bus.py tauri/ui/src/mascot/index.ts tauri/ui/src/mascot/reaction-intent.ts tauri/ui/src/mascot/reaction-intent.test.ts tests/agent/test_emote_parser.py tests/agent/test_dj_cohost.py tests/e2e/test_seam_p31__ws_bus.py tests/runtime/test_ws_bus_snapshot.py
```

Live status:

```text
vibemix_dev.sidecar_status -> ws_reachable=false, GEMINI_API_KEY present
```

## Boundaries

- No broad staging, no commit, and no product-release claim.
- This packet proves source wiring and focused tests, not a packaged-app visual
  run. The current websocket bus was not reachable during verification.
- The model is not allowed to invent arbitrary mascot commands: both Python and
  TypeScript whitelist the allowed reaction names.
- Unknown complete emote tags are now stripped from speech without firing the
  mascot.
- This package does not change Viber/library chat behavior. It only affects live
  co-host output that contains explicit `[emote:*]` control tags.

## Next Required Proof

Before final product acceptance, run the current source app or packaged app and
force one live co-host response containing a whitelisted `[emote:*]` marker.
Confirm in the session artifacts that the spoken/transcript text contains no
raw tag, the snapshot increments `reaction_intent_seq`, and the mascot visibly
fires the mapped reaction once.
