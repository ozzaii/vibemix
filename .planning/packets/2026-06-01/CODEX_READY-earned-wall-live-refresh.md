# CODEX_READY: Earned Wall Live Refresh

Date: 2026-06-01
Author: Codex
Package: 9 - Earned Wall Live Refresh
Decision: LAND
Suggested commit: `fix(learn-runtime): refresh earned wall after live cited credits`

## Summary

This package is ready to land as the backend Earned Wall refresh path.

The live coach loop now has a bounded bridge from cited runtime events to Learn
progress: cited events can advance `LearnProgress`, persist the progress file,
emit an `ipc.learn.progress_state` snapshot so the shell can repaint, and play a
rare fixed-text Mastered unlock line exactly on the not-mastered to mastered
flip.

The honesty boundary is still important. This package proves the backend emit
and fixed-vocal behavior. It does not prove a visible live UI repaint in the
desktop shell, does not wire a `BEATMATCH_GRADED` production producer, and does
not claim Course 3 full routed-audio readiness.

## Files In Package

- `src/vibemix/runtime/coach.py`
- `tests/runtime/test_coach_skill_credit.py`
- `tests/runtime/test_coach_progress_emit.py`
- `tests/learn/test_mastered_vocal_fires_once.py`

Review context, not staged by this package:

- `src/vibemix/learn/mastered_vocal.py`
- `src/vibemix/learn/vocals/mastered_vocals.json`
- `tests/learn/test_no_speculative_phrase.py`
- `tests/prompts/test_negative_dict.py`

## LAND Criteria

- Cited live coach events can credit Learn skills through the existing recognizer.
- Uncited events do not credit and do not speak.
- Credit persists through `save_progress`.
- A successful credit emits `ipc.learn.progress_state` to the UI bus.
- Progress emission is fail-soft and cannot wedge the live coach loop.
- The Mastered unlock vocal uses fixed text through `session.say`, not an LLM turn.
- The Mastered vocal fires exactly once on the mastery flip, not on every credit.
- Beatmatch remains under the Package 8 honesty boundary until a live producer exists.

## Source Evidence

### Cited credit bridge

- `src/vibemix/runtime/coach.py:123-218` implements `_credit_live_skill_demo`.
  It no-ops without registry or progress, computes session time from the live
  `MusicState`, snapshots pre-credit mastered flags, calls
  `skill_recognizer.recognize(...)` with a citation check against
  `EvidenceRegistry.has(...)`, speaks only newly-mastered skills, persists with
  `save_progress(...)`, and catches errors so the loop is not wedged.
- `src/vibemix/runtime/coach.py:286-324` maps a judged transition verdict back
  into the same cited-credit bridge by writing the transition evidence atom and
  then calling `_credit_live_skill_demo(...)`.
- `src/vibemix/runtime/coach.py:619-633` calls `_credit_live_skill_demo(...)` for
  ordinary live events, then calls `_emit_earned_wall_refresh(...)` before the
  normal reaction path.
- `src/vibemix/runtime/coach.py:812-831` passes `learn_progress` and the fixed
  `mastered_speak` hook into the live transition judge path.

### Earned Wall refresh emission

- `src/vibemix/runtime/coach.py:220-254` implements
  `_emit_earned_wall_refresh(...)`. It returns immediately when no skill was
  credited, when progress is absent, or when the bus is absent. Otherwise it
  snapshots `LearnProgress`, builds a `LearnProgressState` envelope with
  `action="snapshot"`, and emits it on the runtime IPC bus.
- `tests/runtime/test_coach_progress_emit.py:62-70` proves a credited skill emits
  one `ipc.learn.progress_state` envelope with the progress snapshot.
- `tests/runtime/test_coach_progress_emit.py:73-91` proves the refresh helper
  stays silent with no credit, no bus, or a snapshot error.

### Fixed Mastered vocal

- `src/vibemix/runtime/coach.py:256-273` builds the Mastered speak hook from
  `session.say(...)`, passes `add_to_chat_ctx=False`, and does not call
  `generate_reply` or any model-backed text path.
- `src/vibemix/runtime/coach.py:443-447` builds the hook once for the coach loop.
- `tests/runtime/test_coach_skill_credit.py:268-281` proves the fixed speak hook
  uses `add_to_chat_ctx=False`.
- `tests/runtime/test_coach_skill_credit.py:284-315` proves the vocal fires on
  the mastery flip and does not repeat on the next cited demo.
- `tests/runtime/test_coach_skill_credit.py:318-335` proves a non-flip credit is
  silent.
- `tests/runtime/test_coach_skill_credit.py:338-353` proves an uncited event never
  speaks.
- `tests/runtime/test_coach_skill_credit.py:356-375` proves a failing speak hook
  cannot block the credit.

## Test Evidence

### Coach Credit And Speech Safety

Command:

```bash
uv run pytest -q tests/runtime/test_coach_skill_credit.py tests/runtime/test_coach_progress_emit.py tests/learn/test_mastered_vocal_fires_once.py tests/learn/test_no_speculative_phrase.py tests/prompts/test_negative_dict.py
```

Result:

```text
41 passed in 0.30s
```

Coverage highlights:

- `tests/runtime/test_coach_skill_credit.py:79-100` proves cited
  `LAYER_ARRIVAL` events credit transitions and persist.
- `tests/runtime/test_coach_skill_credit.py:103-120` proves the same event does
  not credit without citation.
- `tests/runtime/test_coach_skill_credit.py:145-160` proves a broken progress
  object never raises.
- `tests/runtime/test_coach_skill_credit.py:163-185` proves cited `MIX_MOVE`
  credits both `eq_mixing` and `deck_control`.
- `tests/runtime/test_coach_skill_credit.py:187-207` proves an unset
  `set_start_at` self-cancels without losing credit.
- `tests/runtime/test_coach_skill_credit.py:209-230` proves a raising registry
  never raises.
- `tests/runtime/test_coach_skill_credit.py:232-248` proves an unmapped event
  credits nothing.
- `tests/learn/test_mastered_vocal_fires_once.py` keeps the public Mastered line
  fixed, non-speculative, and valid against the JSON fixture.

### Beatmatch Honesty Regression Guard

Command:

```bash
uv run pytest -q tests/learn/test_judge_credits_beatmatch.py tests/learn/test_creditability_drift.py tests/learn/test_skill_wall_what_remains.py tests/runtime/test_coach_skill_credit.py tests/runtime/test_coach_progress_emit.py
```

Result:

```text
37 passed in 0.26s
```

This verifies Package 9 does not smuggle Beatmatch into the live-Mastered path.
Beatmatch remains governed by Package 8: the recognizer branch exists, but the
production app still needs a live cited `BEATMATCH_GRADED` producer before the
Earned Wall can credit it.

### Lint And Diff Hygiene

Command:

```bash
uv run ruff check src/vibemix/runtime/coach.py tests/runtime/test_coach_skill_credit.py tests/runtime/test_coach_progress_emit.py tests/learn/test_mastered_vocal_fires_once.py
```

Result:

```text
All checks passed!
```

Command:

```bash
git diff --check -- src/vibemix/runtime/coach.py tests/runtime/test_coach_skill_credit.py tests/runtime/test_coach_progress_emit.py tests/learn/test_mastered_vocal_fires_once.py
```

Result: passed with no output.

## Boundaries

- This is backend refresh-emission proof, not live desktop repaint proof.
- This package does not wire the future `BEATMATCH_GRADED` production producer.
- This package does not claim Course 3 routed-audio readiness.
- This package does not run GSD or the excluded beginner-path suites.
- Any future change to co-host speech around this path needs the grounding-review
  pass again.

## Verdict

LAND as `fix(learn-runtime): refresh earned wall after live cited credits`.
