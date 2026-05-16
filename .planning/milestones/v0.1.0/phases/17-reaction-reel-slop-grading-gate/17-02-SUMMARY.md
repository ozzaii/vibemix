---
phase: 17-reaction-reel-slop-grading-gate
plan: 17-02
subsystem: testing
tags: [grading, blind-evaluation, slop-detection, cli, anonymization, fisher-yates]

# Dependency graph
requires:
  - phase: 15-recordings-browser
    provides: events.jsonl + session.json shape (RecordingsIndex / VoiceRecorder)
  - phase: 10-prompt-template-matrix
    provides: vibemix.prompts.negative_dict.NEGATIVE_REGEX (slop phrase regex)
provides:
  - scripts/reaction_reel/grade.py — blind-grading CLI for one rater × one session
  - SHA-8 reaction anonymization + grades.key.json mapping for post-grading analysis
  - Deterministic per-rater shuffle (resumable mid-grading via per-line fsync JSONL)
  - Locked-schema GradeRecord validation matching CONTEXT Area 1
affects:
  - Phase 17-03 (analyze.py) will consume <session>/grades/<rater>.jsonl + grades.key.json
  - Phase 17 capture protocol (Plan 17-01) writes the reels grade.py consumes

# Tech tracking
tech-stack:
  added: []  # stdlib-only (argparse, hashlib, json, random, subprocess, platform)
  patterns:
    - Single-source-of-truth re-export — NEGATIVE_REGEX imported, never copied
    - Per-line JSONL + fsync for crash-resumable session state (mirrors recorder.py)
    - Strict bool validation (rejects bool-as-int) to keep schema honest
    - macOS-first CLI with Windows fallback + graceful no-op on Linux (CLAUDE.md platforms)

key-files:
  created:
    - scripts/reaction_reel/__init__.py
    - scripts/reaction_reel/grade.py
    - tests/reaction_reel/__init__.py
    - tests/reaction_reel/test_grade.py
  modified: []

key-decisions:
  - "Per-rater seed = SHA1(rater + session_dir.name)[:8] → random.Random(int(seed,16)).shuffle — deterministic Fisher-Yates per CONTEXT §Specifics"
  - "Anonymization id = SHA1(text + '|' + round(t,3))[:8] — stable across re-runs so analyst can hold a long-lived key file"
  - "Context window inclusive at ±15.0s boundary (covers Plan-15 recorder rounding without dropping at-boundary events)"
  - "Strict bool typing in validate_grade — bool is an int in Python; explicit isinstance(_, bool) check prevents 1/0 sneaking in"
  - "Player command per-OS via shutil.which(afplay) | cmd /c start /MIN /WAIT — never raises; rater can grade by text alone if playback unavailable"
  - "rater_view filters context to {trigger, track_resolved, phase_change, session_start} — keeps the blind contract honest while still giving rater enough to judge timing"

patterns-established:
  - "Pattern: blind-grading view → render reaction_id + mm:ss + transcript + slop_highlights + filtered nearby events; NEVER surface persona/mode/genre/user_level"
  - "Pattern: re-use Phase 10 negative_dict.NEGATIVE_REGEX (test_slop_dictionary_is_imported_not_copied gate prevents future drift)"
  - "Pattern: validate_grade → write_grade pipeline — schema gate is the only entry point to the JSONL; resume reads back the same shape"

requirements-completed: []  # PLAN.md not previously committed; phase frontmatter req VERIFY-02 remains gated on the full Phase 17 close.

# Metrics
duration: 6min
completed: 2026-05-13
---

# Phase 17 Plan 02: Reaction-Reel Blind-Grading CLI Summary

**`scripts/reaction_reel/grade.py` — terminal-only blind-grading harness with SHA-8 reaction anonymization, deterministic per-rater shuffle, resumable JSONL persistence, and a 1-source-of-truth slop dictionary re-export from Phase 10.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-05-13T15:16:59Z
- **Completed:** 2026-05-13T15:22:30Z
- **Tasks:** 2 (RED tests + GREEN implementation)
- **Files created:** 4 (2 source, 2 test)
- **Tests added:** 13 (all green)

## Accomplishments

- `extract_reactions(session_dir)` walks `events.jsonl` for `kind=="ai_text"` events and assembles per-reaction clip cards with a ±15s context window slice.
- `anonymize_reactions(raw, grades_dir=...)` assigns SHA-8 ids and writes `grades/grades.key.json` so the post-grading analyst (Kaan) can de-anonymize without exposing persona/mode/genre/skill to the rater.
- `shuffle_for_rater(...)` produces a deterministic Fisher-Yates permutation seeded on `SHA1(rater + session_dir.name)[:8]`; same rater + same session always lands on the same order so a Ctrl-C mid-grading resumes cleanly.
- `load_existing_grades(rater_jsonl)` + `next_reactions_to_grade(...)` filter the shuffle down to un-graded ids so resume picks up at the right place.
- `slop_highlights(text)` returns the negative-dictionary hits via `vibemix.prompts.negative_dict.NEGATIVE_REGEX` — single source of truth shared with Phase 10's runtime filter (drift gate via `test_slop_dictionary_is_imported_not_copied`).
- `validate_grade(grade)` enforces the Area-1 locked schema: 1-5 score range, strict-bool fields (rejects 1/0 sneaking in), `slop_flag ∈ {none, late, generic, hallucination, repetition, cringe}`, all 10 required fields present and correctly typed.
- `write_grade(rater_jsonl, grade)` appends one validated JSONL line + fsyncs per line so a process kill loses at most the in-flight grade.
- `play_audio(voice_wav)` invokes `afplay` (macOS) or `cmd /c start /MIN /WAIT` (Windows); falls back to text-only mode gracefully on Linux / missing player binary / `FileNotFoundError`.
- `build_rater_view(anonymized)` renders the on-screen card: `reaction_id`, `mm:ss`, transcript, slop highlights, and a filtered nearby-event summary (whitelist: trigger / track_resolved / phase_change / session_start) — explicitly excludes all persona/mode/genre/user_level labels.
- CLI entrypoint: `python -m scripts.reaction_reel.grade <session_dir> <rater>` — argparse-driven, returns 0 on completion / 130 on Ctrl-C / 1 on setup error.

## Task Commits

1. **Task 1: RED — failing tests** — `8b8109e` (test)
2. **Task 2: GREEN — implementation** — `5a3cacc` (feat)

## Files Created

- `scripts/reaction_reel/__init__.py` — package init + docstring covering Plan 17-02 (grade.py) and Plan 17-03 (analyze.py, deferred).
- `scripts/reaction_reel/grade.py` — 538 LOC. The CLI + 11 public functions (extract_reactions, anonymize_reactions, rater_seed, shuffle_for_rater, load_existing_grades, next_reactions_to_grade, slop_highlights, build_rater_view, play_audio, validate_grade, write_grade) + `main(argv)` entrypoint.
- `tests/reaction_reel/__init__.py` — test package init.
- `tests/reaction_reel/test_grade.py` — 13 tests pinning the public API + behavior contracts: extract walks ai_text only, empty-reactions case, sha-8 anonymization + key.json, deterministic per-rater shuffle, resume after partial JSONL, slop highlights via NEGATIVE_REGEX, schema validation, JSONL write + fsync, rater view persona-strip, end-to-end resume flow, play_audio FileNotFoundError graceful path, rater_seed derivation, slop-dict re-export drift gate.

## Decisions Made

All decisions inherited from `17-CONTEXT.md` §Area 3 specifics — no new architectural choices. Implementation details:

- **Context window inclusive at boundary** (`abs(other.t - reaction.t) <= 15.0`): keeps an event at exactly +15.0s from being silently dropped by a `<` predicate. Matches the recorder's t-rounding precision (`round(_, 3)`).
- **Anonymization id `SHA1(text + "|" + round(t,3))[:8]`**: stable across re-runs of the pipeline, so the analyst can hold a long-lived key file even if the recording is re-processed. Collisions (vanishingly rare with SHA-8) get a `[:6] + idx` suffix and continue without crashing.
- **`random.Random(seed_int).shuffle` for Fisher-Yates**: CPython's stdlib `random` uses Mersenne Twister and `shuffle` is documented to be Fisher-Yates. The deterministic-across-Python-versions guarantee holds for CPython 3.11+ where we are.
- **`platform.system()` dispatch + `shutil.which("afplay")` guard**: Linux gets None (no v1 commitment per CLAUDE.md §Platforms = macOS + Windows only). Missing afplay on a macOS dev VM also gets None — falls back to text-only.
- **Strict bool validation**: `isinstance(x, bool)` BEFORE the `isinstance(x, int)` branch — Python treats `True` as `1` so a sloppy "1/0" answer would otherwise pass. The locked schema demands `true/false`.

## Deviations from Plan

**None** — the executor spec listed exactly the deliverables shipped (CLI, anonymization, shuffle, slop dictionary import, schema enforcement, resumable JSONL, 12+ tests, blind-view). Test count exceeded the floor (13 vs 12) by adding the slop-dict re-export drift gate.

## Issues Encountered

- **Worktree was missing the Phase 14/15 + Phase 17 CONTEXT commits**: at startup the worktree branch was at `6e6dd9f` (Phase 6 close) while main was at `f172825` (Phase 17 CONTEXT). Merged `main` into the worktree branch (clean merge, no conflicts) before reading the plan. Not a deviation — required setup.
- **No 17-02-PLAN.md was committed by an upstream planner**: the executor spec carried the plan inline. The implementation followed CONTEXT §Area 3 verbatim, and this SUMMARY records all decisions.
- **Pre-existing unrelated test failures** in `tests/test_main_smoke.py::test_smoke_03_full_wiring` etc. and `tests/agent/test_persona.py::test_persona_02_byte_identical_to_v4` and `tests/test_phase05_verification.py::test_g5_poc_files_untouched`. Confirmed pre-existing via `git stash` + re-run. **Out of scope** per the scope-boundary rule (failures in unrelated files, not caused by this plan's changes).

## User Setup Required

None — `scripts/reaction_reel/grade.py` runs against any vibemix recording session and depends only on stdlib + existing `vibemix.prompts.negative_dict`. Phase 17 close still requires Kaan to:

1. Record the 30-min reel (Plan 17-01 territory).
2. Run `python -m scripts.reaction_reel.grade <session> <rater>` for each of 4 raters.
3. Run `python -m scripts.reaction_reel.analyze <session>` (Plan 17-03 territory) to produce the gate verdict.

## Next Phase Readiness

- Plan 17-03 (`analyze.py`) consumes `<session>/grades/<rater>.jsonl` × N raters + `grades.key.json` and produces the report.md + scores.csv pass/fail verdict. The JSONL shape written by `write_grade` is the input contract — no further coordination needed.
- Plan 17-01 (`17-CAPTURE-PROTOCOL.md`) can reference `python -m scripts.reaction_reel.grade <session> <rater>` as the rater-instruction command verbatim.

## TDD Gate Compliance

- ✅ RED gate — commit `8b8109e` (`test(17-02): ...`) added 13 failing tests; verified `ModuleNotFoundError` for all 13 before implementation.
- ✅ GREEN gate — commit `5a3cacc` (`feat(17-02): ...`) implemented the module; all 13 tests pass.
- ✅ No REFACTOR commit needed — the GREEN code shipped with the production-quality docstrings + edge-case handling in place.

## Self-Check: PASSED

- Files exist:
  - `scripts/reaction_reel/__init__.py` ✅
  - `scripts/reaction_reel/grade.py` ✅
  - `tests/reaction_reel/__init__.py` ✅
  - `tests/reaction_reel/test_grade.py` ✅
- Commits exist:
  - `8b8109e` ✅ (test: failing tests)
  - `5a3cacc` ✅ (feat: implementation)
- Tests green: `PYTHONPATH=src python3 -m pytest tests/reaction_reel/ -q` → `13 passed in 0.08s` ✅
- CLI smoke: `python -m scripts.reaction_reel.grade --help` → exits 0 with usage ✅

---
*Phase: 17-reaction-reel-slop-grading-gate*
*Completed: 2026-05-13*
