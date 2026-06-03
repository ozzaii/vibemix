# CODEX VERDICT — NOVELTY-SPEAK-GATE

**Item:** NOVELTY-SPEAK-GATE
**Code SHA:** `63f560ef` (`fix(runtime): silence repeated speak-gate events`)
**Date:** 2026-06-03
**Result:** LANDED

## User Value

A live Sven user now gets fewer repeated stale reads: when the same grounded event
fingerprint has already produced an emitted line, the runtime treats the next match as
`silent / repeat_of_recent` before it asks the model to rephrase.

## What Changed

- Added `event_speak_fingerprint(ev)` in `runtime/speak_gate.py`, built from grounded event
  inputs available before generation.
- Added `recent_fingerprints` to `decide_speak_gate`; human/manual triggers still override.
- Added a small emitted-event fingerprint ring on `DJCoHostAgent`, populated beside
  `_record_said(...)` after actual audience text emits.
- Threaded the agent fingerprint snapshot through `coach_loop`, and clear it on
  `TRACK_CHANGE`.

## Proof

Focused deterministic proof:

- `uv run pytest -q tests/runtime/test_speak_gate.py tests/runtime/test_coach.py tests/runtime/test_coach_cancel_wiring.py`
  - `40 passed`
- `uv run pytest -q tests/agent/test_dj_cohost.py::test_agent_03_initial_state tests/agent/test_dj_cohost.py::test_record_said_uses_event_fired_set_seconds_when_provided tests/agent/test_dj_cohost.py::test_record_said_legacy_fallback_uses_live_state_set_seconds tests/agent/test_dj_cohost.py::test_record_said_records_event_speak_fingerprint tests/agent/test_dj_cohost.py::test_track_change_record_said_resets_event_speak_fingerprints tests/agent/test_dj_cohost.py::test_llm_node_threads_event_fired_set_seconds_to_record_said`
  - `6 passed`
- `uv run ruff check src/vibemix/runtime/speak_gate.py src/vibemix/runtime/coach.py src/vibemix/agent/dj_cohost.py tests/runtime/test_speak_gate.py tests/runtime/test_coach.py tests/runtime/conftest.py tests/agent/test_dj_cohost.py`
  - `All checks passed!`
- `git diff --check`
  - clean

Grounding / invariant floor from this landing loop:

- Citation grounding suite: `114 passed`
- No-speculative-phrase / detector suite: `85 passed`
- Single-writer / one-socket suite: `107 passed`

By-eye live app artifact:

- Launched current source with meeting-safe audio:
  - `VIBEMIX_DEV_SIDECAR=1 VIBEMIX_LOCAL_TTS=0 VIBEMIX_OUTPUT_DEVICE='Multi-Output Device' uv run python -m vibemix`
- Session: `20260603-224414`
- `ipc.session.snapshot`: websocket reachable, meters zero, `track:null`,
  `cohost_status:"IDLE"`, `transcript_delta:[]`, `drop_pred_bars:null`.
- `ipc.status.tick`: `livekit:"ok"`, `gemini:"ok"`, `midi:0`, `screen:"unavailable"`,
  `voice:"muted"`.
- `events.jsonl`: only `session_start`; no idle transcript spam.
- Process stopped cleanly; `lsof -nP -iTCP:8765 -sTCP:LISTEN` returned no listener.

## Caveats

- I did not invent a live debug event injector. The app currently has no wired debug IPC for
  forcing a repeated PHASE through the live websocket path, so the `repeat_of_recent` proof is
  the real `coach_loop` deterministic path, not a synthetic live-bus event.
- A full `tests/agent/test_dj_cohost.py` run still has two unrelated stale audio-context
  golden failures around deck-audio prompt span/token expectations. The novelty-owned agent
  pins pass.
