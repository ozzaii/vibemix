# CODEX VERDICT — SVEN-AUTO-EVENT-SPAM

Item: user-reported Sven/TTS stutter/spam during live run after credits were depleted/restored.

Code SHA: ed3d1786 `fix(cohost): slow automatic phrase turns`

## What Changed

- Genre-chain events now pass through `EventDetector._cooldown_ok(...)` before reaching
  the co-host. This restores the shared cross-event floor for detectors such as
  `KICK_DENSITY_SHIFT`, `KICK_SWAP`, and `PHRASE_BOUNDARY`.
- `PHRASE_BOUNDARY` cooldown moved from `24.0` to `48.0` seconds. At ~154 BPM the
  old value let 16-bar boundaries offer a speech turn about every 25 seconds; the
  new value keeps phrase reads alive but prevents every boundary from becoming a
  Sven opportunity.

## Why

Latest sidecar evidence before the fix showed automatic LLM turns queued too tightly:

- `20260603-194926/events.jsonl`: `KICK_DENSITY_SHIFT` at `t=23.832`, then
  `PHRASE_BOUNDARY` at `t=33.279` (9.4s later), then phrase boundaries at
  `t=57.952` and `t=82.923`.
- Each turn attached 60s of audio and hit Gemini `429 RESOURCE_EXHAUSTED` while
  credits were depleted. After credits were restored, the same path would start
  producing audible speech unless the model self-abstained.

## Proof

Focused tests:

- `uv run pytest -q tests/state/test_event_detector.py tests/state/detectors/test_phrase_boundary.py tests/audio/test_constants.py`
  - `65 passed`
- `uv run pytest -q tests/state/test_coach_anti_slop.py tests/state/test_hype_anti_slop.py tests/agent/test_citation_strip_emit.py tests/agent/test_dj_cohost_grounding.py tests/agent/test_dj_cohost_linter.py tests/state/test_evidence_registry.py tests/coach/test_citation_linter.py tests/coach/test_citation_zero_orphan_replay.py`
  - `114 passed`
- `uv run pytest -q tests/learn/test_no_speculative_phrase.py tests/prompts/test_negative_dict.py tests/state/test_hype_anti_slop.py tests/state/test_coach_anti_slop.py tests/state/test_event_detector.py`
  - `85 passed`
- `uv run pytest -q tests/learn/test_runtime_invariants.py tests/state/test_refresh.py tests/state/test_music_state.py`
  - `85 passed`
- `uv run ruff check src/vibemix/state/event_detector.py src/vibemix/audio/constants.py tests/state/test_event_detector.py tests/state/detectors/test_phrase_boundary.py tests/audio/test_constants.py`
  - `All checks passed`
- `git diff --check -- ...touched paths...`
  - clean

Runtime by-eye proof, meeting-safe:

- Booted current source with `VIBEMIX_DEV_SIDECAR=1 VIBEMIX_LOCAL_TTS=0 VIBEMIX_OUTPUT_DEVICE='Multi-Output Device' uv run python -m vibemix`.
- Session: `20260603-203137`.
- Stdout confirmed:
  - `-> djay passthrough -> Multi-Output Device @ 48000Hz`
  - `-> AI voice output muted (no local TTS); stream not opened`
  - `-> AgentSession headless (no Room); audio out muted (no local TTS)`
  - `-> mascot bus on ws://127.0.0.1:8765`
- `ws_observe(seconds=5)` saw the live bus and `ipc.status.tick` reported
  `voice:"muted"` with `transcript_delta:[]`.
- `events.jsonl` contained only `session_start`; no LLM invocation, no TTS.
- Stopped cleanly with `TOTAL €0.0000`; `sidecar_status` confirmed the bus closed.

## Assumptions

- By-ear speech was intentionally not exercised because Kaan was in a meeting and
  asked not to route Sven to MacBook speakers. The proof used muted TTS plus the
  configured `Multi-Output Device` path.
- This fix does not mute user/manual turns. It only restores the shared automatic
  event floor and slows phrase-boundary cadence.
