---
phase: 81-bench-the-validation-instrument
plan: 01
subsystem: testing
tags: [bench, eval, xfail-strict, fixtures, citation-linter, model-router, offline-green]

# Dependency graph
requires:
  - phase: 80-ground
    provides: "build_parts_description(secondary_ear=) framing the grounding axis bench cells exercise"
  - phase: 79-lens
    provides: "build_lens_instruction + LENS_TO_MODE_MOOD — the lens axis the assembler composes"
  - phase: 78-perceive
    provides: "MusicState trajectory_narrative/detected_genre fields — the contexting axis fixtures"
provides:
  - "tests/bench/ offline test package: _FakeClient + _RaisingClient fixtures (zero network), bench_data_dir (env-overridable), real MusicState + grounded EvidenceRegistry snapshot builders"
  - "6 charter .mp3 excerpts in-repo under tests/bench/data/ (outside src/, wheel-excluded)"
  - "14 xfail-strict scaffolds pinning BENCH-01 (assemble/run), BENCH-02 (eval), BENCH-03 (review) — flip in Plans 02/03/04"
  - "bench-scoped model-literal guard (real-green; bench/ NOT allowlisted)"
affects: [81-02-harness, 81-03-eval, 81-04-review]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Inject-the-client offline-green: _FakeClient.models is self, generate_content returns SimpleNamespace(text, usage_metadata) — zero API"
    - "Nyquist xfail(strict=True) safety net: each acceptance criterion fails today (clean ImportError), flips real-green when its plan lands; an early pass xpasses → HARD failure"
    - "Real-fixture grounding: build a real MusicState + EvidenceRegistry snapshot, not ad-hoc dicts, so the linter's additive gating exercises real paths"

key-files:
  created:
    - tests/bench/__init__.py
    - tests/bench/conftest.py
    - tests/bench/data/.gitkeep
    - tests/bench/data/*.mp3 (6 excerpts)
    - tests/bench/test_assemble.py
    - tests/bench/test_run_fake.py
    - tests/bench/test_eval.py
    - tests/bench/test_review.py
    - tests/bench/test_no_model_literal.py
  modified: []

key-decisions:
  - "Copied 6 charter excerpts (t1..t6), not all 8 — matches the plan's named charter set; t7/t8 (solardo/gobang) deferred to the real run if Kaan wants the fuller set"
  - "The canned _FakeClient line cites [aud:bpm@0.0] and the snapshot builder writes aud/bpm@0.0 + aud/sub@0.0 — pre-verified against the REAL CitationLinter so the eval grounded/fabricated contract flips real-green in Plan 03 with no fixture churn"
  - "test_no_model_literal.py imports the existing tests/repo gate's _ALLOWLIST/_MODEL_LITERAL_RE rather than re-declaring the regex — single source of truth; asserts bench/ is NOT allowlisted"
  - "test_eval/test_review use a dict {output, dsp_snapshot} stand-in for the not-yet-built BenchResult ctor where the scorer only reads those two fields, and the real BenchResult where the field set matters (errored cell)"

patterns-established:
  - "Pattern 1: xfail reason names the flipping plan (Plan 02/03/04) so the scaffold's lifecycle is self-documenting"
  - "Pattern 2: bench guard re-uses repo guard logic via import, never a copied regex"

requirements-completed: [BENCH-01, BENCH-02, BENCH-03]

# Metrics
duration: 13min
completed: 2026-05-26
---

# Phase 81 Plan 01: BENCH Wave-0 Safety Net Summary

**Installed the offline honest-green gate for Phase 81 BEFORE any `bench/` source: 14 xfail-strict scaffolds pinning every BENCH-01/02/03 acceptance criterion (flip in Plans 02/03/04), a zero-network `_FakeClient`/`_RaisingClient` + real `MusicState`/snapshot fixture suite, 6 in-repo `.mp3` excerpts, and a real-green bench-scoped model-literal guard.**

## Performance

- **Duration:** ~13 min (incl. one 250s full-suite run)
- **Started:** 2026-05-26T02:44:28Z
- **Completed:** 2026-05-26T02:52:15Z
- **Tasks:** 2
- **Files modified:** 11 created (9 source/data + 2 .mp3-set entries counted as one group), 0 src/ change

## Accomplishments
- `tests/bench/conftest.py`: `_FakeClient` (canned cited line `that 303 line opened up [aud:bpm@0.0]` + synthetic `usage_metadata` 1900/40/1940/0, `.models is self`, no network), `_RaisingClient` (fake 429 to drive Plan 02's fail-safe), `bench_data_dir` (honors `VIBEMIX_BENCH_DATA_DIR`), and `build_snapshot_state`/`build_trajectory_state` building a REAL `MusicState` + a populated `EvidenceRegistry` snapshot.
- 6 charter `.mp3` excerpts copied from `/tmp/truthtest` into `tests/bench/data/` — in-repo (tracked, not gitignored), outside `src/` so hatchling's `packages=["src/vibemix"]` auto-excludes them from the wheel.
- 14 `xfail(strict=True)` scaffolds: `test_assemble.py` (4 — hype-lens reuse, the no-audio `dsp_only` cell, structured-vs-generic, model-via-router) + `test_run_fake.py` (3 — zero-network sweep, the 429 fail-safe, usage capture) flip in Plan 02; `test_eval.py` (4 — groundedness/specificity/lens-fidelity/score-ranks-not-decides) flips in Plan 03; `test_review.py` (3 — empty VERDICT, errored→parked, ranked render) flips in Plan 04.
- `test_no_model_literal.py` real-green: walks `src/vibemix/bench/` (absent today → vacuous pass), reuses the `tests/repo` gate's regex + allowlist, asserts `bench/` is NOT allowlisted.

## Task Commits

1. **Task 1: Fixtures + in-repo .mp3 data + the offline _FakeClient** — `43933a1` (test)
2. **Task 2: xfail-strict scaffolds for BENCH-01/02/03 + the bench model-literal guard** — `fd89b23` (test)

## Files Created/Modified
- `tests/bench/__init__.py` — package marker + Nyquist-net rationale docstring
- `tests/bench/conftest.py` — `_FakeClient`/`_RaisingClient`, `bench_data_dir`, real `MusicState`+snapshot builders
- `tests/bench/data/.gitkeep` + `t1..t6_*.mp3` — the 6 charter excerpts (wheel-excluded)
- `tests/bench/test_assemble.py` — BENCH-01 cell-assembly scaffolds (incl. the no-audio cell)
- `tests/bench/test_run_fake.py` — BENCH-01 fake-client sweep + fail-safe scaffolds
- `tests/bench/test_eval.py` — BENCH-02 groundedness/specificity/lens-fidelity scaffolds
- `tests/bench/test_review.py` — BENCH-03 review-render scaffolds (empty verdict)
- `tests/bench/test_no_model_literal.py` — bench-scoped model-literal guard (real-green)

## Decisions Made
- See `key-decisions` frontmatter. Headline: the canned `[aud:bpm@0.0]` line + the `aud/bpm@0.0` snapshot write were chosen so the grounded/fabricated eval contract was pre-validated against the REAL `CitationLinter` (verified: grounded→`valid`, fabricated→`invalid_atoms`) — Plan 03's `groundedness` scorer flips real-green with no fixture churn.
- 6 excerpts (t1..t6), not 8 — the plan named the t1..t6 charter set; t7/t8 stay in `/tmp/truthtest` and can join the real run on demand.

## Deviations from Plan
None - plan executed exactly as written. No bugs, no missing critical functionality, no blocking issues, no architectural changes. No `src/vibemix/` file touched (correct for a Wave-0 scaffold plan). Zero packages installed.

## Issues Encountered
None. The `.mp3` excerpts confirmed not-gitignored (so they track in-repo for reproducibility); the offline fixture + real-linter grounding contract verified before committing.

## Known Stubs
None. The `dict` stand-in in `test_eval.py`/`test_review.py` for the not-yet-built `BenchResult` is intentional and scoped — it carries only the `{output, dsp_snapshot}` fields the scorer reads; the real `BenchResult` ctor is used where its full field set matters (the errored-cell render). Plan 02 lands the real ctor and the scaffolds flip.

## Self-Check: PASSED
- 8 created test/source files all FOUND on disk
- 6 `.mp3` excerpts present in `tests/bench/data/`
- Both task commits FOUND in git log (`43933a1`, `fd89b23`)

## Next Phase Readiness
- The offline gate is locked: Plan 02 (harness) flips the 7 assemble/run scaffolds, Plan 03 (eval) flips the 4 eval scaffolds, Plan 04 (review) flips the 3 review scaffolds. A silent early-pass in any of them xpasses → HARD failure, so the harness/eval/review are spec'd by their tests, never faked.
- The `.mp3` excerpts are in-repo + env-overridable, so the documented real run (`uv run python -m vibemix bench run --study A`) is reproducible.
- KAAN-ACTION (parked, soft): the live two-study run on the funded key + BENCH-03's ear verdict — neither blocks the autonomous merge; the offline gate is the honest-green proof.

---
*Phase: 81-bench-the-validation-instrument*
*Completed: 2026-05-26*
