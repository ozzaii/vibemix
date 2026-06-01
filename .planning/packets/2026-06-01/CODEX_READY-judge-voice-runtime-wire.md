# CODEX_READY: Judge Voice Runtime Wire

Date: 2026-06-01
Author: Codex
Status: LAND packet, judged-evidence speech slice
Package: Package 8B - Judge Voice Evidence Runtime Wire

## Decision

LAND this slice as `feat(intel): voice transition judge evidence`.

The Vibe Judge can now feed measured verdict evidence into the next
`TRACK_CHANGE` prompt, but only when the Judge actually returns a judged
verdict. Abstains stay quiet and do not create fake score/citation material.

## Files

- `src/vibemix/intel/judge_voice.py`
- `src/vibemix/state/transition_judge_runtime.py`
- `src/vibemix/runtime/coach.py`
- `src/vibemix/state/coach.py`
- `tests/intel/test_judge_voice.py`
- `tests/runtime/test_coach_live_judge_run.py`
- `tests/state/test_coach_judge_voice_prompt.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`
- `.planning/packets/2026-06-01/INDEX.md`
- `.planning/packets/2026-06-01/CODEX_READY-judge-voice-runtime-wire.md`

## What Changed

- `judge_and_record(...)` exposes the grounded Judge citation id as
  `judge:transition@t` through `verdict_citation_id(...)`.
- `_run_live_judge(...)` resolves the live deck-audio frame, runs the Judge, and
  appends a compact `verdict_evidence_line(...)` only for judged verdicts.
- `coach_loop` attaches the line to `ev.extra["judge_evidence_line"]` on the
  corresponding `TRACK_CHANGE` event.
- `AICoach` injects the line into the `TRACK_CHANGE` task with instructions to
  preserve the exact citation and avoid unsupported fader/EQ/deck-control
  causes.
- Master-only, unresolved routing, and unsupported-policy cases abstain. That is
  the correct product behavior until real two-deck evidence exists.

## Evidence

Judge runtime/voice/citation schema:

```text
uv run pytest -q tests/intel/test_judge_voice.py tests/runtime/test_coach_live_judge_run.py tests/state/test_coach_judge_voice_prompt.py tests/state/test_judge_and_record.py tests/state/test_judge_citation_schema_mirror.py
24 passed in 0.28s
```

Anti-slop prompt/filter guard:

```text
uv run pytest -q tests/learn/test_no_speculative_phrase.py tests/prompts/test_negative_dict.py tests/state/test_hype_anti_slop.py tests/state/test_coach_anti_slop.py tests/state/test_event_detector.py
84 passed in 0.35s
```

Citation/grounding guard:

```text
uv run pytest -q tests/state/test_coach_anti_slop.py tests/state/test_hype_anti_slop.py tests/agent/test_citation_strip_emit.py tests/agent/test_dj_cohost_grounding.py tests/agent/test_dj_cohost_linter.py tests/state/test_evidence_registry.py tests/coach/test_citation_linter.py tests/coach/test_citation_zero_orphan_replay.py
108 passed in 1.16s
```

Lint:

```text
uv run ruff check src/vibemix/intel/judge_voice.py src/vibemix/state/transition_judge_runtime.py src/vibemix/runtime/coach.py src/vibemix/state/coach.py tests/intel/test_judge_voice.py tests/runtime/test_coach_live_judge_run.py tests/state/test_coach_judge_voice_prompt.py
All checks passed!
```

Whitespace:

```text
git diff --check -- src/vibemix/intel/judge_voice.py src/vibemix/state/transition_judge_runtime.py src/vibemix/runtime/coach.py src/vibemix/state/coach.py tests/intel/test_judge_voice.py tests/runtime/test_coach_live_judge_run.py tests/state/test_coach_judge_voice_prompt.py
```

## Boundaries

- No broad staging, no commit, and no product-release claim.
- This does not prove the packaged app or a real two-deck live artifact yet.
- The current master-only or unresolved-deck rig can correctly abstain. Do not
  treat abstention as a regression.
- The overpraise clamp for weak Judge scores is a related hold lane, not bundled
  into this packet.

## Next Required Proof

Run a source/Tauri live pass with resolved two-deck audio/routing and a judged
transition:

- Confirm the Judge returns a judged verdict, not abstain.
- Confirm the response artifact includes the exact `[judge:transition@t]`
  evidence line.
- Confirm the spoken reply keeps that citation and does not invent fader, EQ, or
  deck-control causes outside the Judge line.
