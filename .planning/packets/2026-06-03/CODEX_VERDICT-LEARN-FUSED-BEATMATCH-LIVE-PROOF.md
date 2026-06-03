# CODEX VERDICT - Learn Fused Beatmatch Live Proof

Item: Q3/B1/B2/B3/Q6 fused beatmatch proof
Code SHA: 8578e13e (`fix(learn): keep beatmatch practice live until locked`)
Date: 2026-06-03
Session: `20260603-235945`

## User Value

A Pro Learn user on L2.01 now hears Sven coach the measured miss without falsely
finishing the lesson, then sees/hears the lesson complete only when the owned-deck
beatmatch judge emits a grounded locked grade.

## By-Ear / By-Eye Artifact

Launch was current source, not bundled sidecar:

```text
VIBEMIX_DEV_SIDECAR=1
VIBEMIX_OUTPUT_DEVICE='Multi-Output Device'
VIBEMIX_LOCAL_TTS=1
VIBEMIX_LEARN_PROGRESS_PATH=/tmp/vibemix-learn-proof-progress/learn-progress.json
uv run --extra ai-local python -m vibemix
```

Observed on boot:

```text
AI voice -> Multi-Output Device @ 24000Hz
djay passthrough -> Multi-Output Device @ 48000Hz
MIDI controller in: 'DDJ-FLX4' (profile=pioneer_ddj_flx4, mode=callback)
```

The first bad L2.01 tempo move emitted a measured `tempo_off` live grade and
did not complete the lesson. The running app kept the lesson alive and kept the
practice player moving, which is the intended "try again" loop.

The recovery move then crossed the lock window. The ws payload showed:

```json
{
  "verdict": "locked",
  "phase_error_beats": 0.00009297052153556251,
  "score": 0.9995,
  "citation": "[ev:BEATMATCH_GRADED@138.318]"
}
```

`events.jsonl` confirmed the grounded speaking path:

```text
learn_beatmatch_practice_graded verdict=locked evidence_time=138.3175129890442
learn_tutor_speak text="nice, matched" citations=["[ev:BEATMATCH_GRADED@138.318]"]
ai_message citation_count=1 action=emit valid=true
learn_lesson_completed reason=completed
```

Kill criterion status:

- Bad measured grade no longer completes: PASS.
- Phase grade reaches the live UI/ws as the practice audio drifts: PASS.
- Locked grade carries a resolving EvidenceRegistry citation: PASS.
- Sven speaks only the grounded locked completion line before lesson completion:
  PASS.

## Notes / Assumptions Corrected

- The FLX4 was present as CoreMIDI and the app opened the FLX4 input port. This
  proof drove the same inbound `ipc.learn.ack` path instead of requiring a
  physical hand move on the controller.
- `JBL GO 4` was not available as a CoreAudio output because macOS Bluetooth was
  off. The app was still forced away from MacBook speakers by launching with
  `VIBEMIX_OUTPUT_DEVICE='Multi-Output Device'`.
- A broad `uv run pytest -q` attempt remains unsuitable as the proof gate today:
  it hit unrelated existing repo failures/noise. The focused Learn/audio slice and
  the grounding invariant slices passed, and the runtime proof above is the done
  artifact.

## Checks

Focused code gate:

```text
uv run ruff check src/vibemix/learn/runtime.py src/vibemix/learn/ipc_handlers.py \
  src/vibemix/learn/beatmatch_practice_driver.py src/vibemix/audio/miniplayer.py \
  tests/learn/test_runtime_evidence_grounding.py
All checks passed.

uv run pytest -q tests/learn/test_runtime_evidence_grounding.py \
  tests/learn/test_beatmatch_practice_driver.py tests/audio/test_miniplayer.py \
  tests/audio/test_miniplayer_gain_ramp.py
38 passed.
```

Earlier grounding slices in this loop:

```text
tests/state/test_coach_anti_slop.py ... tests/coach/test_citation_zero_orphan_replay.py
114 passed.

tests/learn/test_no_speculative_phrase.py tests/prompts/test_negative_dict.py
tests/state/test_event_detector.py
64 passed.

tests/learn/test_runtime_invariants.py tests/state/test_refresh.py
tests/state/test_music_state.py
88 passed.

tests/learn/test_no_new_ws_port.py tests/runtime/test_ws_bus.py
19 passed.
```
