# CODEX_READY: Beatmatch Judge Honesty Boundary

Date: 2026-06-01
Author: Codex
Package: 8 - Beatmatch Judge Honesty Boundary
Decision: LAND
Suggested commit: `fix(learn): keep beatmatching unmastered until live producer`

## Summary

This package is ready to land as the Learn beatmatch honesty boundary.

The owned-deck Beatmatch Judge and recognizer branch are future-ready and tested:
a cited, non-abstain, tempo-matched, phase-locked `BEATMATCH_GRADED` event credits
beatmatching. But the production app still has no live emitter that calls the
grader or fires that event. Therefore the Earned Wall must not promise or display
Beatmatch Mastered yet.

This package keeps that boundary honest: `beatmatching.live_creditable` is false,
stale stored beatmatch mastery is masked at compute time, and the wall says
"Mastered isn't live-graded for this skill" instead of pretending there are live
demos the product cannot observe.

## Files In Package

- `src/vibemix/learn/beatmatch_judge.py`
- `src/vibemix/learn/skill_recognizer.py`
- `src/vibemix/learn/skill_tree.py`
- `tests/learn/test_judge_credits_beatmatch.py`
- `tests/learn/test_creditability_drift.py`
- `tests/learn/test_skill_wall_what_remains.py`

Review context, not staged by this dirty package:

- `src/vibemix/audio/grid.py`
- `src/vibemix/audio/miniplayer.py`
- `tests/audio/test_grid.py`
- `tests/audio/test_miniplayer.py`
- `tests/learn/test_beatmatch_judge.py`
- `tests/repo/test_live_reality_pins.py`

## LAND Criteria

- The Beatmatch Judge can still grade exact owned-deck tempo/phase state.
- The recognizer credits beatmatching only on a cited locked `BEATMATCH_GRADED` event.
- Abstain, tempo-off, drifting, trainwreck, uncited, and not-yet-Competent cases credit nothing.
- The manifest and recognizer agree that beatmatching is currently not product-live-creditable.
- Stored/stale beatmatch mastery does not render as Mastered while no production emitter exists.
- The reality pin fails if a production beatmatch emitter appears, forcing this boundary to be revisited.

## Source Evidence

### Future-ready owned-deck judge

- `src/vibemix/learn/beatmatch_judge.py:63-80` defines `BeatmatchGrade`, including
  abstain, tempo match, phase lock, verdict, and score.
- `src/vibemix/learn/beatmatch_judge.py:83-142` grades owned-deck beatmatch state
  from exact grids and deck state, with stopped-deck abstain, octave-folded tempo,
  modular phase error, lock/drift/trainwreck verdicts, and multiplicative score.
- `src/vibemix/learn/beatmatch_judge.py:145-167` exports the canonical event-extra
  shape for a future `BEATMATCH_GRADED` producer and explicitly says a future
  owned-deck practice loop must emit it with a matching citation.

### Recognizer branch stays strict

- `src/vibemix/learn/skill_recognizer.py:94-105` declares beatmatching as the sole
  honest-uncreditable v11 skill because no production loop emits `BEATMATCH_GRADED`.
- `src/vibemix/learn/skill_recognizer.py:154-171` resolves `BEATMATCH_GRADED` to
  `beatmatching` only when not abstaining and both `tempo_matched` and `phase_locked`
  are true.
- `src/vibemix/learn/skill_recognizer.py:199-288` credits only cited live events,
  requires explicit event time for live registry matching, dedups by event/time, and
  reports credit only if `record_live_demo` actually advances the count.

### Earned Wall honesty boundary

- `src/vibemix/learn/skill_tree.py:92-104` defines `SkillSpec.live_creditable` as
  the production-live-Mastered path switch.
- `src/vibemix/learn/skill_tree.py:143-151` sets `beatmatching` to
  `live_creditable=False` until the production `BEATMATCH_GRADED` emitter ships.
- `src/vibemix/learn/skill_tree.py:291-356` masks stored `mastered=True` unless
  the skill is live-creditable, and clears `first_mastered_at` when masked.
- `src/vibemix/learn/skill_tree.py:359-386` emits honest `what_remains` copy:
  uncreditable competent skills state the live-grade limit instead of promising
  demo countdowns.
- `src/vibemix/learn/skill_tree.py:438-505` keeps `record_live_demo` as the pure,
  Competent-gated live-demo writer for skills that can actually be credited.

### Reality pin for missing producer

- `tests/repo/test_live_reality_pins.py:126-141` asserts no production
  `src/vibemix` file calls `grade_beatmatch` or `grade_to_event_extra`.
- `tests/repo/test_live_reality_pins.py:144-156` asserts no production module
  imports `beatmatch_judge`.
- `tests/repo/test_live_reality_pins.py:159-178` asserts the consumer branch exists,
  proving the current state is a starved consumer, not a deleted feature.
- `tests/repo/test_live_reality_pins.py:181-200` proves the emitter-call detector
  is non-vacuous.

## Test Evidence

### Judge And Consumer Proof

Command:

```bash
uv run pytest -q tests/audio/test_grid.py tests/audio/test_miniplayer.py tests/learn/test_beatmatch_judge.py tests/learn/test_judge_credits_beatmatch.py
```

Result:

```text
28 passed in 0.30s
```

Coverage highlights:

- `tests/learn/test_beatmatch_judge.py` verifies beat-phase wrap, octave folding,
  locked grade, tempo-off, stopped-deck abstain, drifting, and recoverable-late math.
- `tests/learn/test_judge_credits_beatmatch.py:70-78` verifies a cited locked grade
  credits beatmatching.
- `tests/learn/test_judge_credits_beatmatch.py:80-124` verifies trainwreck, drifting,
  tempo-off, abstain, and uncited locked grades credit nothing.
- `tests/learn/test_judge_credits_beatmatch.py:127-134` verifies Beatmatch credit
  requires Competent first.
- `tests/learn/test_judge_credits_beatmatch.py:137-171` verifies real judge output
  can flow through `grade_to_event_extra` into the recognizer, and a real trainwreck
  grade still credits nothing.

### Honesty Boundary Proof

Command:

```bash
uv run pytest -q tests/learn/test_creditability_drift.py tests/learn/test_skill_wall_what_remains.py tests/learn/test_judge_credits_beatmatch.py tests/repo/test_live_reality_pins.py
```

Result:

```text
24 passed in 1.01s
```

Coverage highlights:

- `tests/learn/test_creditability_drift.py:17-34` pins the manifest's
  `live_creditable=False` set to the recognizer's honest-uncreditable set:
  currently exactly `beatmatching`.
- `tests/learn/test_skill_wall_what_remains.py:78-87` verifies competent
  beatmatching says no live-grade path yet.
- `tests/learn/test_skill_wall_what_remains.py:89-103` verifies stale stored
  beatmatch mastery is not displayed as Mastered.
- `tests/learn/test_skill_wall_what_remains.py:106-126` verifies truly Mastered
  creditable skills have no remaining-copy and the wall copy avoids hype tokens.

### Frontend Wall And Lint Proof

Command:

```bash
npm --prefix tauri/ui test -- tests/learn/test_skill_wall.spec.ts tests/learn/skill-tree-a11y.spec.ts
```

Result:

```text
Test Files  2 passed (2)
Tests       14 passed (14)
```

Command:

```bash
uv run ruff check src/vibemix/learn/beatmatch_judge.py src/vibemix/learn/skill_recognizer.py src/vibemix/learn/skill_tree.py tests/learn/test_judge_credits_beatmatch.py tests/learn/test_creditability_drift.py tests/learn/test_skill_wall_what_remains.py
```

Result:

```text
All checks passed!
```

Command:

```bash
git diff --check -- src/vibemix/learn/beatmatch_judge.py src/vibemix/learn/skill_recognizer.py src/vibemix/learn/skill_tree.py tests/learn/test_judge_credits_beatmatch.py tests/learn/test_creditability_drift.py tests/learn/test_skill_wall_what_remains.py
```

Result: passed with no output.

## Boundaries

- This package does not wire the live practice-loop producer.
- This package does not run or claim Course 3 full routed-audio proof.
- This package does not run GSD or the excluded beginner-path suites.
- Beatmatch can be marked live-creditable only after a production owned-deck loop
  emits cited `BEATMATCH_GRADED` events. When that happens, retire or rewrite the
  reality pin and flip the wall copy back to the ordinary cited-demo countdown.

## Verdict

LAND as `fix(learn): keep beatmatching unmastered until live producer`.
