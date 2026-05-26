---
phase: 81-bench-the-validation-instrument
plan: 03
subsystem: bench
tags: [bench, eval, groundedness, specificity, lens-fidelity, citation-linter, ranks-never-decides, offline-green, one-mind]

# Dependency graph
requires:
  - phase: 81-bench-the-validation-instrument
    plan: 02
    provides: "BenchCell/BenchResult shapes (cell.py) + LENS_ANCHORS (matrix.py) + the recorded-cell artifact this eval scores"
  - phase: 81-bench-the-validation-instrument
    plan: 01
    provides: "tests/bench/test_eval.py — the 4 xfail-strict BENCH-02 scaffolds this plan flips + _grounded_snapshot pre-verified against the REAL CitationLinter"
provides:
  - "src/vibemix/bench/eval.py — score_cell(result) -> CellScore (groundedness/specificity/lens_fidelity + a SORT-ONLY aggregate) + groundedness/specificity/lens_fidelity scorers + rank_cells (a SORT, never a verdict)"
  - "CellScore frozen value type (the per-cell rank signal Plan 04's review.py renders)"
affects: [81-04-review]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "REUSE-THE-GATE groundedness: eval.py groundedness calls CitationLinter.check(output, dsp_snapshot, mode=debrief) VERBATIM — the linter IS the product's anti-slop gate (Invariant #2), so the bench stays honest to shipped behavior; no bespoke atom parser under bench/ (T-81-08)"
    - "RANKS-NEVER-DECIDES: score_cell/rank_cells produce a sort key only — no winner/verdict/decision field anywhere; the grep gate + frozen dataclass shape enforce (Pitfall 5 / T-81-07). Kaan's ear is BENCH-03"
    - "Errored-cell sink: a 429/failed cell (error set) scores all-zero + errored=True so it sinks in the rank — never silently scored high, never fabricated"
    - "Pure + deterministic scorers: no network, no file I/O, no API — fixture cells score identically every run (the offline honest-green proof)"

key-files:
  created:
    - src/vibemix/bench/eval.py
  modified:
    - tests/bench/test_eval.py
    - .planning/codebase/orphans.csv

key-decisions:
  - "groundedness/specificity/lens_fidelity accept BOTH a real BenchResult AND the test's dict stand-in (defensive _text_of/_snapshot_of/_error_of/_lens_of accessors) — so the Plan-01 dict-shaped _result fixtures flip green without a BenchResult ctor change, and the live runner's BenchResult scores identically"
  - "groundedness mapping is the exact RESEARCH Pattern 2: valid->1.0, no_citations->0.5, else (invalid_atoms/malformed_atom)->0.0; errored->0.0 short-circuits before the linter call"
  - "specificity = 0.3 floor + 0.35*concrete_measure_hits - 0.4*slop_hits, clamped [0,1]; one concrete measure outweighs one slop hit so a sharp line with an incidental ban-word still beats vague slop, but pure slop sinks (deterministic, no pseudo-judge)"
  - "concrete-measure regex is word-bounded (\\b\\d+...\\b over hz/khz/bpm/db/bar/bars/beat/beats/s) so 'second' / 'bars' don't false-match the bare unit"
  - "aggregate weights groundedness 0.5 / specificity 0.25 / lens_fidelity 0.25 — groundedness is the empirical heart (the no-audio cell's groundedness is the milestone question); these tune RANK ORDER only, never a verdict"

requirements-worked: [BENCH-02]

# Metrics
duration: 7min
completed: 2026-05-26
---

# Phase 81 Plan 03: BENCH-02 Automated First-Pass Eval Summary

**Built `src/vibemix/bench/eval.py` as three PURE, deterministic, offline scorers over a recorded `BenchResult` plus a SORT-ONLY ranker. Groundedness REUSES `CitationLinter.check(output, dsp_snapshot, mode="debrief")` VERBATIM (the linter IS the product's anti-slop gate, Invariant #2 — no bespoke atom parser). Specificity is a deterministic `NEGATIVE_PHRASES` penalty + concrete-measure reward; lens-fidelity hits the per-lens `LENS_ANCHORS` vocab. `score_cell` composes all three into a `CellScore` with a weighted-mean `aggregate` for sorting only; `rank_cells` SORTS by aggregate — there is NO winner/verdict/decision anywhere (Pitfall 5 / T-81-07; Kaan's ear is BENCH-03). An errored cell scores all-zero + `errored=True` so it sinks in the rank, never fabricated-high. Flipped the 4 BENCH-02 eval xfail scaffolds to real-green.**

## Performance

- **Duration:** ~7 min
- **Tasks:** 1 (TDD — the RED scaffolds were already in place from Plan 01)
- **Files:** 1 created (`bench/eval.py`) + 2 modified (`test_eval.py` flips, `orphans.csv` baseline)

## Accomplishments

- **`eval.py` — `CellScore`** (frozen value dataclass, mirrors `LintResult`/`BenchCell` convention): `groundedness`/`specificity`/`lens_fidelity` floats + `errored: bool` + a SORT-ONLY `aggregate: float`. Deliberately NO `winner`/`verdict`/`decision` field.
- **`groundedness(result)`** — short-circuits an errored cell to `0.0`, else runs the shared module-level `CitationLinter().check(output, dsp_snapshot, mode="debrief")` (±2.0s offline-appropriate tolerance, RESEARCH A3) and maps `valid->1.0 / no_citations->0.5 / else->0.0`. A grounded `[aud:bpm@0.0]` (present in the snapshot) scores 1.0; a fabricated `[aud:bpm@99.0]` (absent) scores 0.0 — via the REUSED linter, not a re-implementation.
- **`specificity(text)`** — `0.3 + 0.35*concrete_hits - 0.4*slop_hits`, clamped `[0,1]`. `slop_hits` = `NEGATIVE_PHRASES` substring hits; `concrete_hits` = word-bounded `\d+ unit` matches (hz/khz/bpm/db/bar/bars/beat/beats/s). "128 bpm kick is hammering the sub" beats "As an AI, I'm here to help."
- **`lens_fidelity(text, lens)`** — `clamp(LENS_ANCHORS[lens] vocab hits / 2.0)`. A hype-vocab line ("drop is sick, energy is cooking") scores higher under `lens="hype"` than a flat line; unknown lens -> `0.0` (never raises — the eval ranks, it does not gate).
- **`score_cell(result)`** — errored -> `CellScore(0,0,0, errored=True, aggregate=0.0)`; else composes the three + the weighted-mean aggregate (g 0.5 / s 0.25 / lf 0.25). Pure: zero I/O.
- **`rank_cells(scored)`** — `sorted(..., key=aggregate, reverse=True)` with a docstring stating it does NOT decide a winner. A SORT, not a verdict.
- **Dual-shape accessors** (`_text_of`/`_snapshot_of`/`_error_of`/`_lens_of`) — read both a real `BenchResult` (`.output`/`.dsp_snapshot`/`.error`/`.cell.lens`) and the Plan-01 dict stand-in (`["output"]`/`["dsp_snapshot"]`/...), so the dict-shaped test fixtures flip green and the live runner's `BenchResult` scores identically.

## Task Commits

1. **Task 1: eval scorers + ranker + xfail flips + baseline refresh** — `8dd8821` (feat)

## Verification

- `pytest tests/bench/test_eval.py tests/bench/test_no_model_literal.py` -> **6 passed** (the 4 BENCH-02 eval xfails flipped real-green: groundedness valid/fabricated split via the reused linter, specificity concrete>slop, lens-fidelity hype>flat, score_cell has the 3 dims + NO winner/verdict attr)
- `grep -n "winner\|verdict\|decide" src/vibemix/bench/eval.py` -> docstring/comment ONLY (no code path; lines 21/22/57/100/103/104/113/178/204 are all prose stating it does NOT decide)
- `grep -n "CitationLinter" src/vibemix/bench/eval.py` -> present (import + shared instance + the reused `.check` call — reuse, not re-implement); `grep -n "NEGATIVE_PHRASES"` -> present (import + slop penalty)
- `bash scripts/release/check_no_hardcoded_model.sh` -> exit 0; `grep gemini- src/vibemix/bench/` -> NONE (no literal introduced; `test_no_model_literal.py` green)
- score_cell is deterministic on fixture cells (no network/file I/O — verified by the offline test run, zero API)
- Full suite: **4520 passed / 26 skipped / 3 xfailed / 4 xpassed** (the 3 remaining xfails = Plan 04's `test_review.py` render scaffolds + were 4 before incl. the eval — the eval's 4 flipped; the 1 `test_budget` xfail + the 3 review = the +1 budget gate; the 4 xpassed are pre-existing live-hardware markers). Baseline 4519 passed/4 xfailed before this plan's test edits within the same suite run -> net the eval flips, zero new failures.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Orphan-inventory baseline drift from `rank_cells`**
- **Found during:** Task 1 full-suite run
- **Issue:** `tests/scripts/test_orphan_inventory.py::test_orphan_diff_clean_against_committed_baseline` failed — `rank_cells` (the new `bench/eval.py` ranker) registered as a NEW orphan vs the committed `.planning/codebase/orphans.csv` baseline. The static analyzer sees `score_cell`/`groundedness`/`specificity`/`lens_fidelity` as consumed (by `test_eval.py`) but not `rank_cells`, whose consumer is Plan 04's `review.py` (not yet written). This is the documented "intentional new public surface" case — identical to the Plan 02 `bench/run.py` helper case.
- **Fix:** Refreshed the baseline with the documented command `python scripts/integration_audit.py --orphan-inventory > .planning/codebase/orphans.csv` (single-line addition: `rank_cells`).
- **Files modified:** `.planning/codebase/orphans.csv`
- **Commit:** `8dd8821`

No bugs, no missing critical functionality, no architectural changes.

## Known Stubs

None. The three scorers are fully implemented and unit-green. (`rank_cells` is consumed by Plan 04's review renderer — not a stub, an intentional public-surface export staged ahead of its consumer, baselined accordingly.)

## Threat Flags

None. `eval.py` is a pure in-memory transform over recorded `BenchResult`s — no network, no file I/O, no auth path, no schema change (boundary: eval.py -> recorded cells, per the plan's `<threat_model>`). T-81-07 (verdict creep) mitigated: no winner/verdict field, `rank_cells` is a sort with a does-not-decide docstring, grep gate confirms. T-81-08 (groundedness drift) mitigated: `CitationLinter.check` reused verbatim, no bespoke citation resolver under `bench/`.

## Self-Check: PASSED

- `src/vibemix/bench/eval.py` FOUND on disk
- Task commit `8dd8821` FOUND in git log
- `pytest tests/bench/test_eval.py` -> 4 eval tests green; full suite green (4520 passed, zero new failures)
- Grep gates: `CitationLinter`/`NEGATIVE_PHRASES` present (reuse); `winner`/`verdict`/`decide` docstring-only; no model literal

## Next Phase Readiness

- The `CellScore` shape + `rank_cells` sort are the inputs Plan 04's `review.py` renders into the `KAAN-ACTION-BENCH.md` review surface (ranked cells with their auto-scores, errored cells as `ERRORED — parked`, an EMPTY verdict section). BENCH-02 is met (scorers unit-green on fixtures, zero API).
- BENCH-01/02/03 stay Pending in REQUIREMENTS — they close after Plan 04 (review surface) + the parked KAAN-ACTION live two-study run on the funded key + Kaan's ear verdict (the HARD HUMAN GATE, never automated/faked).

---
*Phase: 81-bench-the-validation-instrument*
*Completed: 2026-05-26*
