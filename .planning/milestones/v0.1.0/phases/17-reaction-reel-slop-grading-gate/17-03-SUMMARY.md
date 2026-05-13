---
phase: 17-reaction-reel-slop-grading-gate
plan: 17-03
subsystem: testing
tags: [aggregator, pass-fail-verdict, report-generation, integration-test, atomic-writes, slop-gate]

# Dependency graph
requires:
  - phase: 17-reaction-reel-slop-grading-gate
    plan: 17-02
    provides: scripts/reaction_reel/grade.py producer of <session>/grades/<rater>.jsonl + grades.key.json
  - phase: 17-reaction-reel-slop-grading-gate
    plan: 17-01
    provides: 17-RUBRIC.md pass thresholds (≥4.0 AND zero 1-2) + tie-breaker band semantics
provides:
  - scripts/reaction_reel/analyze.py — aggregator CLI (load grades → verdict → report.md + scores.csv)
  - Exit codes 0/1/2/3 → PASS/FAIL/INCOMPLETE/PASS_TIE_BREAKER_NEEDED for CI / iteration-loop triggers
  - Schema strictness: malformed grade records logged WARNING + skipped (T-17-03-01 mitigation)
  - Atomic file writes (tmp + os.replace) preserve previous output on mid-write failure
  - Pure functions for report + CSV with injectable `now` for deterministic tests
affects:
  - Phase 17 close gate (VERIFY-02) — analyzer is now operational end-to-end
  - 17-ITERATION-LOOP.md re-entry trigger: report.md `verdict: FAIL` is the mechanical signal
  - scripts/reaction_reel/grade.py: producer schema completed with `graded_at_iso` (Rule 2 fix)

# Tech tracking
tech-stack:
  added: []  # stdlib-only (argparse, csv, io, json, logging, os, statistics, tempfile, datetime)
  patterns:
    - "Verdict-as-exit-code (0/1/2/3) — CI-friendly gate signal for iteration loop trigger"
    - "Pure-function rendering (build_report_md / build_scores_csv) with injectable `now` for determinism"
    - "Atomic write (tmp + os.replace) mirrors grade.py's per-line fsync — defense against half-flushed audit trail"
    - "Schema strictness with WARNING logs — malformed records visible to operator, not silently dropped"
    - "Tie-breaker band (avg ∈ [3.95, 4.05] AND >25% 3-scores) → distinct exit code 3 for Kaan-decision escalation"

key-files:
  created:
    - scripts/reaction_reel/analyze.py
    - tests/reaction_reel/test_analyze.py
    - tests/reaction_reel/test_pipeline.py
  modified:
    - scripts/reaction_reel/__init__.py  # docstring updated to advertise both shipped scripts
    - scripts/reaction_reel/grade.py     # Rule 2 fix — added graded_at_iso to locked schema + writer
    - tests/reaction_reel/test_grade.py  # 3 fixtures updated to include graded_at_iso

key-decisions:
  - "Verdict-to-exit-code 1:1 mapping (0/1/2/3) — lets shell / CI pin re-entry condition mechanically without parsing report.md"
  - "graded_at_iso added to grade.py's locked schema (Rule 2 fix) — closes the gap between 17-RUBRIC.md §3 and Plan 17-02's writer; analyze.py's T-17-03-02 repudiation mitigation now operational"
  - "INCOMPLETE wins over PASS/FAIL when raters_present < 4 OR any rater skipped reactions — verdict order intentionally guards against false-PASS on partial data"
  - "Tie-breaker triggers on >25% 3-scores AND avg ∈ [3.95, 4.05] — verbatim from 17-RUBRIC.md §5; exit code 3 distinguishes from clean PASS for Kaan escalation"
  - "Schema validation is defense-in-depth — grade.py already enforces on write, analyze.py re-validates on read so corrupt JSONL never silently inflates the verdict"
  - "Atomic write via tempfile.mkstemp + os.replace (not append + fsync like grade.py) — full-file rewrite needs tmp-then-rename to preserve previous output on failure"

patterns-established:
  - "Pattern: verdict-as-exit-code — encode rubric gates as CLI exit codes so the iteration loop document can pin re-entry conditions in shell"
  - "Pattern: WARNING-and-skip schema validation — operator sees malformed records via stderr without crashing the analyzer"
  - "Pattern: pure-function report rendering with injectable `now` — keeps tests deterministic; production passes None and uses UTC now"

requirements-completed: []  # VERIFY-02 stays gated on the full Phase 17 close (autonomous deliverables complete; human grading + reel capture remain).

# Metrics
duration: ~14min
completed: 2026-05-13
---

# Phase 17 Plan 03: Reaction-Reel Slop Grading Aggregator Summary

**`scripts/reaction_reel/analyze.py` — turns N rater JSONL files into a pass/fail verdict + report.md + scores.csv with the locked rubric encoded as CLI exit codes (0=PASS, 1=FAIL, 2=INCOMPLETE, 3=PASS_TIE_BREAKER_NEEDED) so the iteration loop trigger is mechanical, not eyeballed.**

## Performance

- **Duration:** ~14 min (RED → GREEN → integration → SUMMARY)
- **Started:** 2026-05-13T15:30:00Z
- **Completed:** 2026-05-13T15:44:00Z
- **Tasks:** 2 (Task 1: analyzer + 14 unit tests; Task 2: integration test + Rule 2 fix)
- **Commits:** 3 (RED + GREEN + integration)
- **Tests added:** 20 (14 unit + 6 integration); full reaction_reel suite at 33 passing
- **Regression check:** tests/recording/ + tests/ui_bus/ + tests/runtime/ + tests/prompts/ → 329 passed, no regressions

## Accomplishments

- **Verdict logic encodes 17-RUBRIC.md §5 verbatim.** `compute_verdict()` returns one of `PASS`, `FAIL`, `INCOMPLETE`, `PASS_TIE_BREAKER_NEEDED` plus a metrics dict carrying everything report/CSV rendering needs (score_counts, per_rater breakdown, per_reaction_graders, incomplete_raters, low_records, three_pct, in_tie_band).
- **Exit codes mirror verdicts** — `EXIT_PASS=0`, `EXIT_FAIL=1`, `EXIT_INCOMPLETE=2`, `EXIT_TIE_BREAKER=3`. The iteration loop document (17-ITERATION-LOOP.md) can now reference `analyze.py exit == 1` as the Phase 10 re-entry trigger without parsing markdown.
- **Schema validation is defense-in-depth.** `validate_record()` re-checks every JSONL line against the 11-field locked schema (strict-bool, score in 1..5, slop_flag enum). Malformed records are logged at WARNING and skipped — they never silently inflate the verdict (T-17-03-01).
- **Atomic file writes.** `_atomic_write_text()` does tmp + `os.replace` so a mid-write OSError leaves the previous `report.md` / `scores.csv` intact. Test 14 pins this invariant by injecting an `os.replace` failure and verifying the pre-existing report content survives.
- **Report renders for the operator + the iteration loop.** Summary table (total reactions / raters present / average / 1-5 distribution), per-rater breakdown table, "All 1-2 ratings" enumeration joined with `grades.key.json` for reaction_text, score distribution histogram, iteration guidance section (worst rater + top-5 worst reactions when FAIL/TIE_BREAKER), and methodology citing 17-RUBRIC.md verbatim.
- **scores.csv has 12 locked columns** — reaction_id, rater, score, grounded, timely, unique, personality_fit, slop_flag, comment, would_clip, graded_at_iso, reaction_text. One row per (reaction × rater). reaction_text joined from grades.key.json so external spreadsheet review needs no second file.
- **Tie-breaker logic distinguishes from clean PASS.** When avg lands in `[3.95, 4.05]` AND ≥26% of records are score==3, verdict becomes `PASS_TIE_BREAKER_NEEDED` (exit 3) — flags Kaan's manual ship-vs-iterate decision per 17-RUBRIC.md §5.
- **End-to-end integration test pins the full pipeline.** `test_pipeline.py` synthesizes a recordings dir + drives `grade.py` (one test uses real `grade.main()` with mocked stdin, others use `write_grade` directly) and runs `analyze.analyze_session` — verifying PASS / FAIL / INCOMPLETE verdicts, the 1-2 enumeration with reaction_text join, the anti-slop dictionary linkage, and the POC-untouched invariant.

## Task Commits

1. **Task 1a (RED): 14 failing tests for analyzer** — `2a29d95`
2. **Task 1b (GREEN): scripts/reaction_reel/analyze.py + __init__.py docstring** — `32fe98e`
3. **Task 2: integration test + Rule 2 fix to grade.py** — `a1b322e`

## Files Created

- `scripts/reaction_reel/analyze.py` — 906 LOC. Public API: `analyze_session`, `compute_verdict`, `enumerate_low_scores`, `build_report_md`, `build_scores_csv`, `load_all_grades`, `load_grades_key`, `validate_record`, `main`. Constants `EXIT_PASS / EXIT_FAIL / EXIT_INCOMPLETE / EXIT_TIE_BREAKER`, `PASS_AVG_THRESHOLD = 4.0`, `TIE_BREAKER_BAND = 0.05`, `TIE_BREAKER_THREE_PCT = 0.25`, `EXPECTED_RATERS = 4`, `VALID_RATERS`, `SLOP_FLAGS`.
- `tests/reaction_reel/test_analyze.py` — 627 LOC. 14 unit tests covering PASS / FAIL (via avg / via single 2 / via single 1) / INCOMPLETE (missing rater / partial grading) / PASS_TIE_BREAKER_NEEDED / empty input / per-rater breakdown / 1-2 enumeration with reaction_text join / malformed records WARNING+skip / scores.csv shape / build_report_md determinism / atomic write contract.
- `tests/reaction_reel/test_pipeline.py` — 453 LOC. 6 integration tests covering full PASS / FAIL-via-2-score / INCOMPLETE / real grade.main() via mocked stdin / anti-slop dictionary linkage / POC-untouched invariant.

## Files Modified

- `scripts/reaction_reel/__init__.py` — docstring updated to advertise both shipped scripts (was "Plan 17-02 ships grade.py only"; now reflects 17-02 + 17-03 shipped pipeline).
- `scripts/reaction_reel/grade.py` — Rule 2 fix: added `graded_at_iso` to the locked schema (`_REQUIRED_FIELDS`) and to the dict built in `_prompt_grade_for_reaction` (ISO-8601 UTC timestamp at submission). The field was missing from Plan 17-02 but is required by 17-RUBRIC.md §3 and is the anchor for threat T-17-03-02 (Repudiation).
- `tests/reaction_reel/test_grade.py` — 3 fixture dicts in tests 7, 8, 10 now include `graded_at_iso: "2026-05-13T14:00:00+00:00"` to satisfy the completed schema.

## Decisions Made

- **`graded_at_iso` lives on grade.py (producer), not analyze.py (consumer).** Plan 17-02 missed the field but 17-RUBRIC.md §3 already locked it. Adding it server-side keeps the audit trail honest at write-time; analyze.py validates as defense-in-depth.
- **INCOMPLETE wins over FAIL when raters/coverage short.** A 3-rater PASS would be FALSE PASS — the gate requires all 4 raters because anti-blindness depends on the full rater roster (CONTEXT Area 1 + 17-RUBRIC.md §5).
- **Pure functions for rendering with injectable `now`.** `build_report_md` and `build_scores_csv` are stateless string builders; production calls them via `analyze_session` (which fills in UTC now), tests inject `datetime(2026, 5, 13, 14, 0, 0)` for deterministic output assertions.
- **Atomic write via `tempfile.mkstemp` in the destination dir.** Same-FS rename guarantee from `os.replace` only holds when src and dst are on the same filesystem — `mkstemp(dir=path.parent)` enforces that.
- **`load_grades_key` swallows JSON decode errors → empty dict.** Per T-17-03-04 mitigation: malformed `grades.key.json` is a UX degradation (empty reaction_text in CSV), not a crash. The verdict computation never references the key — only the renderer does.

## Deviations from Plan

### Rule 2 — Auto-add missing critical functionality

**1. `graded_at_iso` added to grade.py's locked schema**
- **Found during:** Task 2 integration test (real `grade.main()` flow).
- **Issue:** 17-RUBRIC.md §3 lists `graded_at_iso` as a required grade-record field. Plan 17-02 omitted it from `_REQUIRED_FIELDS` and from the dict built by `_prompt_grade_for_reaction`. analyze.py (this plan) correctly required the field per the rubric and threat T-17-03-02 (Repudiation needs a per-record timestamp). Real `grade.main()` was writing records without it → every record got WARNING-skipped by analyze.py.
- **Fix:** added the field to grade.py's schema and writer; the timestamp is `datetime.now(timezone.utc).replace(microsecond=0).isoformat()` at submission time. Updated 3 grade-dict fixtures in `test_grade.py` (tests 7, 8, 10) to satisfy the completed schema.
- **Files modified:** `scripts/reaction_reel/grade.py`, `tests/reaction_reel/test_grade.py`.
- **Commit:** `a1b322e`.

No other deviations — analyzer implementation followed plan §interfaces verbatim.

## Issues Encountered

- **Worktree branch was at Phase 6 close** (`6e6dd9f`) while `main` carried Plan 17-01 / 17-02 commits — merged `main` into the worktree branch (clean merge, no conflicts) before reading Plan 17-03. Same pattern as Plan 17-02 SUMMARY documented.
- **Initial Write tool call used an absolute path resolving to the main repo** (protocol 0b in the executor docs). Caught immediately on `git status --short` returning empty in the worktree, fixed by re-writing the file inside the worktree path; the stray file in the main repo was deleted before any commit happened.
- **No `synthetic_session` conftest fixture** as the Plan 17-03 spec referenced — Plan 17-02 inlined `_build_session` in `test_grade.py` rather than extracting to conftest. Plan 17-03 integration test inlines its own `_build_synthetic_session` + `_populated_grades` + `_write_synthetic_grades` helpers for module independence; reusing across `test_grade.py` and `test_pipeline.py` would be a refactor outside this plan's scope.

## User Setup Required

None. `scripts/reaction_reel/analyze.py` is stdlib-only and runs against any directory containing `<session>/grades/<rater>.jsonl` files written by `grade.py`. Phase 17 close still requires Kaan to:

1. Record the actual 30-min reel (Plan 17-01 territory — capture protocol documented).
2. Run `python -m scripts.reaction_reel.grade <session> <rater>` for each of 4 raters (Plan 17-02 CLI).
3. Run `python -m scripts.reaction_reel.analyze <session>` (this plan) → produces `<session>/grades/report.md` + `scores.csv` + the verdict; exit code 0/1/2/3 drives 17-ITERATION-LOOP.md re-entry.

## Next Phase Readiness

- **Phase 17 autonomous deliverables complete.** Rubric (17-01) + Capture Protocol (17-01) + Iteration Loop doc (17-01) + grade.py CLI (17-02) + analyze.py CLI (17-03) all shipped. The only Phase 17 close requirement is the *human* gate: capture the reel + grade × 4 + verify analyze.py reports PASS. Per CONTEXT §Area 5, verification status for Phase 17 will be `human_needed` on completion of these artifacts.
- **17-ITERATION-LOOP.md trigger is now mechanical.** It can reference `analyze.py exit 1` as the FAIL signal that re-enters Phase 10 (prompt template matrix) — no human verdict-parsing required.
- **No downstream plans in Phase 17.** Plan 17-03 is the last plan; Phase 17 closes via human gating once the actual grading completes.

## TDD Gate Compliance

- ✅ RED gate — commit `2a29d95` (`test(17-03): ...`) added 14 failing tests for analyze.py; verified `ModuleNotFoundError` for all 14 before implementation.
- ✅ GREEN gate — commit `32fe98e` (`feat(17-03): ...`) implemented analyze.py; all 14 unit tests passed first run.
- ✅ Integration GREEN — commit `a1b322e` (`feat(17-03): ...`) added test_pipeline.py (6 tests) and the Rule 2 fix needed to bridge grade.py ↔ analyze.py; full reaction_reel suite at 33 passing.
- ✅ No REFACTOR commit needed — GREEN code shipped with docstrings, edge-case handling, and threat-model wiring in place. The Rule 2 fix to grade.py is a producer-side schema completion, not a refactor of analyze.py.

## Self-Check: PASSED

- Files exist:
  - `scripts/reaction_reel/analyze.py` ✅
  - `tests/reaction_reel/test_analyze.py` ✅
  - `tests/reaction_reel/test_pipeline.py` ✅
- Commits exist:
  - `2a29d95` ✅ (test: 14 failing tests)
  - `32fe98e` ✅ (feat: analyze.py implementation)
  - `a1b322e` ✅ (feat: integration test + Rule 2 fix)
- Acceptance criteria automation:
  - `python -c "from scripts.reaction_reel.analyze import main, analyze_session, compute_verdict, build_report_md, build_scores_csv, enumerate_low_scores, load_all_grades, load_grades_key"` → ok ✅
  - `python -m pytest tests/reaction_reel/test_analyze.py -v` → 14 passed ✅
  - `python -m pytest tests/reaction_reel/test_pipeline.py -v` → 6 passed ✅
  - `python -m pytest tests/reaction_reel/ -q` → 33 passed ✅
  - `python -m pytest tests/recording/ tests/ui_bus/ tests/runtime/ tests/prompts/ -q` → 329 passed (no regressions) ✅
  - `grep -q "PASS_AVG_THRESHOLD = 4.0" scripts/reaction_reel/analyze.py` ✅
  - `grep -c "EXIT_PASS\|EXIT_FAIL\|EXIT_INCOMPLETE\|EXIT_TIE_BREAKER" scripts/reaction_reel/analyze.py` → 22 (≥4) ✅
  - `grep -q "TIE_BREAKER" scripts/reaction_reel/analyze.py` ✅
  - `grep -c "from scripts.reaction_reel" tests/reaction_reel/test_pipeline.py` → 2 ✅
  - `grep -c "NEGATIVE_PHRASES" tests/reaction_reel/test_pipeline.py` → 7 (≥1) ✅
- POC untouched: `git diff --stat main..HEAD` shows only scripts/reaction_reel/* + tests/reaction_reel/* + a 3-line fixture update; no cohost*.py / mascot.html / mocks/ touched ✅
- IPC schema count unchanged: `git diff main..HEAD` shows no tauri/ or src/vibemix/ipc/ changes ✅

---
*Phase: 17-reaction-reel-slop-grading-gate*
*Completed: 2026-05-13*
