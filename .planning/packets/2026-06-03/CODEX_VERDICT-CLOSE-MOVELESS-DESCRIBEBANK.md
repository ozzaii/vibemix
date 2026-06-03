# CODEX VERDICT - CLOSE-MOVELESS-DESCRIBEBANK

**Item:** CLOSE-MOVELESS-DESCRIBEBANK
**SHA:** `678d7629 fix(runtime): gate moveless track changes`
**Date:** 2026-06-03

## What Landed

- `TRACK_CHANGE` now shares the describe-bank gate with `HEARTBEAT`, `PHASE`, and `LAYER_ARRIVAL`.
- A bare `TRACK_CHANGE` without a grounded voice payload is `silent / describe_bank_only`.
- A `TRACK_CHANGE` carrying `next_suggestion_voice_line` still reaches Sven as `speak / grounded_voice_payload`.
- The next-suggestion receipt now leads with the forward read before the citation-copy and transition caveats.

## By-Eye / Runtime Proof

- Deterministic sim proof: `uv run python scripts/eval/respan_sven_sim.py --gate-only --out /tmp/respan_sven_sim_gate_close_moveless.json`
  - `track_change`: `TRACK_CHANGE -> silent ok`
  - `track_change_with_next`: `TRACK_CHANGE -> speak ok`
  - gate routing: `9/9 matched expectation`
- Real app proof launched current source with meeting-safe audio:
  - `VIBEMIX_DEV_SIDECAR=1 VIBEMIX_LOCAL_TTS=0 VIBEMIX_OUTPUT_DEVICE='Multi-Output Device' uv run python -m vibemix`
  - fresh session: `20260603-223129`
  - ws bus reachable on `127.0.0.1:8765`
  - `ipc.status.tick` showed `voice: muted`
  - `ipc.session.snapshot` showed `cohost_status: IDLE`, `transcript_delta: []`, meters at zero
  - `events.jsonl` had only `session_start`, no idle speech spam
  - app stopped cleanly; `8765` free afterward

## Verification

- `uv run pytest -q tests/runtime/test_speak_gate.py tests/runtime/test_suggestion_voice.py tests/state/test_coach.py::test_task_track_change_includes_grounded_next_suggestion_receipt tests/state/test_coach.py::test_task_transition_opportunity_includes_grounded_next_suggestion_receipt tests/runtime/test_coach.py::test_coach_14_plain_heartbeat_stays_silent tests/runtime/test_coach.py::test_coach_14_plain_phase_stays_silent tests/runtime/test_coach.py::test_coach_15_manual_heartbeat_reaches_model`
- `uv run ruff check src/vibemix/runtime/speak_gate.py src/vibemix/runtime/suggestion_voice.py tests/runtime/test_speak_gate.py tests/runtime/test_suggestion_voice.py scripts/eval/respan_sven_sim.py`
- Citation grounding invariant: `114 passed`
- No speculative phrase / detector invariant: `85 passed`
- Single-writer / one-socket invariant: `107 passed`
- `git diff --check`

## Caveat

`scripts/eval/respan_sven_sim.py` was already an untracked swarm file in this shared tree, so the code commit did not absorb the whole helper. The sim was used for proof, but the committed pins live in tracked runtime tests.
