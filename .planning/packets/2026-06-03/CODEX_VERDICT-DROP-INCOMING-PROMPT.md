# CODEX VERDICT - DROP-INCOMING-PROMPT

Item: CODEX_READY-DROP-INCOMING-PROMPT
Code SHA: 23116ff3 (`feat(sven): ground incoming drop prompts`)
Date: 2026-06-03

## Result

Landed. Sven's full prompt can now see a trusted incoming-drop ETA only while the
live session lens is active, and the refresh loop writes a citable `cue` receipt
for the predicted drop before the prompt exposes the marker. No drop reaction was
enabled and `VIBEMIX_DROP_CALL` remains untouched.

## What Changed

- Added `next_drop_section(...)` beside `predict_drop_in_sec(...)` without
  changing the existing ETA-only signature.
- Added `MusicState.predicted_drop_cue_id` as the last registered cue anchor for
  the incoming drop.
- Extended `state.refresh._tick_once(...)` to:
  - compute sections once for the audible deck's track;
  - write `EvidenceRegistry.write("cue", <track:drop@start>, <set_seconds>)`;
  - dedupe the drop cue across ticks and against the Course 3 phrase anchor when
    both refer to the same drop.
- Extended `AICoach.evidence_line(...)` full path only:
  - `drop_incoming[eta@8s]`
  - `drop_cue_anchor=track-1:drop@64.0`

## By-Eye / Runtime Artifact

Meeting-safe current-source app was launched with:

```bash
VIBEMIX_DEV_SIDECAR=1 VIBEMIX_LOCAL_TTS=0 VIBEMIX_OUTPUT_DEVICE='Multi-Output Device' uv run python -m vibemix
```

Runtime session: `20260603-214338`.

Observed over the live bus:

- `ws://127.0.0.1:8765` reachable.
- `ipc.session.snapshot` frames flowing.
- `cohost_status="IDLE"`, `music.rms=0`, `drop_pred_bars=null`.
- `transcript_delta=[]`; no Sven speech spam.
- `ipc.status.tick` in `ui.log`: `gemini="ok"`, `livekit="ok"`, `voice="muted"`.

The local rig was idle, so no physical DJ drop was available to prove by ear in
this pass. To avoid pretending, I also ran a runtime-shaped `_tick_once(...)`
proof through the same refresh and prompt code path:

```text
predicted_drop_in_sec= 8.0
predicted_drop_cue_id= track-1:drop@64.0
cue_snapshot= {'track-1:drop@64.0': (108.0,)}
has_drop_marker= True
has_drop_anchor= True
```

This proof also caught and fixed a same-tick duplicate receipt when Course 3's
phrase anchor and the incoming-drop anchor pointed at the same cue.

## Verification

```text
uv run pytest -q tests/state/test_refresh.py tests/state/test_coach_course3_confidence_gate.py tests/state/test_drop_predict.py tests/state/test_coach.py tests/state/test_music_state.py
193 passed

uv run pytest -q tests/state/test_coach_anti_slop.py tests/state/test_hype_anti_slop.py tests/agent/test_citation_strip_emit.py tests/agent/test_dj_cohost_grounding.py tests/agent/test_dj_cohost_linter.py tests/state/test_evidence_registry.py tests/coach/test_citation_linter.py tests/coach/test_citation_zero_orphan_replay.py
114 passed

uv run pytest -q tests/learn/test_no_speculative_phrase.py tests/prompts/test_negative_dict.py tests/state/test_hype_anti_slop.py tests/state/test_coach_anti_slop.py tests/state/test_event_detector.py
85 passed

uv run pytest -q tests/learn/test_runtime_invariants.py tests/state/test_refresh.py tests/state/test_music_state.py
88 passed

uv run ruff check src/vibemix/state/drop_predict.py src/vibemix/state/music_state.py src/vibemix/state/refresh.py src/vibemix/state/prompt_builder.py tests/state/test_drop_predict.py tests/state/test_coach_course3_confidence_gate.py tests/state/test_music_state.py tests/state/test_refresh.py
All checks passed.

git diff --check -- <touched paths>
clean
```

## Assumptions / Caveats

- The packet's suggested loop-local `_prev_drop_cue_id` would not persist across
  `_tick_once(...)` calls at current HEAD, so I used a nullable `MusicState`
  field instead.
- The by-ear drop proof still needs a real deck track with a trusted drop inside
  the 32s horizon; this pass verified the live app was safe/quiet and the
  deterministic refresh/prompt path produced the grounded receipt.
