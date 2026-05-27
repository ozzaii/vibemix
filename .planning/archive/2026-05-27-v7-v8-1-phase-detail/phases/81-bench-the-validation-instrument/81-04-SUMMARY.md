---
phase: 81-bench-the-validation-instrument
plan: 04
subsystem: bench
tags: [bench, review, kaan-action, hard-human-gate, empty-verdict, ranks-never-decides, errored-parked, offline-green, one-mind, docs]

# Dependency graph
requires:
  - phase: 81-bench-the-validation-instrument
    plan: 03
    provides: "score_cell / rank_cells / CellScore (eval.py) — the per-cell rank signal this review surface renders"
  - phase: 81-bench-the-validation-instrument
    plan: 02
    provides: "BenchResult / BenchCell (cell.py) — the recorded-cell shape rendered; bench run CLI documented in docs/bench.md"
  - phase: 81-bench-the-validation-instrument
    plan: 01
    provides: "tests/bench/test_review.py — the 3 xfail-strict BENCH-03 render scaffolds this plan flips real-green"
provides:
  - "src/vibemix/bench/review.py — render_review(results, scores) -> str: a PURE JSON->Markdown renderer; ranked (via rank_cells), grouped by grounding dimension, EMPTY verdict, errored cells parked"
  - "docs/bench.md — the documented produce-and-park contract: offline gate + the bounded fail-safe produce command + the review surface + the 3 parked KAAN-ACTION items"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "PRODUCE-AND-PARK / the hard human gate: render_review emits a literally-EMPTY `## VERDICT (Kaan fills this)` block — NO code path writes a winner, picks an architecture, or synthesizes a verdict (Pitfall 5 / T-81-09). The auto-rank is a SORT; Kaan's ear is the verdict (BENCH-03)."
    - "Errored-cell parking (cardinal-sin guard): a cell with `error` set renders `**ERRORED — parked:** {error}`, never a fabricated output line (T-81-10). Mirrors the eval's errored-sink."
    - "Pure + deterministic render: render_review has no clock / randomness / file I/O — same inputs -> byte-identical Markdown; the CALLER writes the artifact (precedent runtime/soak.py)."
    - "Privacy path-scrub: prompts + outputs are scrubbed via the Telegram-bridge `strip_leaks` before rendering — the surface emits scores + prompts + outputs, never a key or a personal track path (T-81-11)."

key-files:
  created:
    - src/vibemix/bench/review.py
    - docs/bench.md
  modified:
    - src/vibemix/bench/cell.py
    - tests/bench/test_review.py

key-decisions:
  - "BenchResult.cell made OPTIONAL (defaulted to None, moved after dsp_snapshot): the Plan-01 review scaffolds construct BenchResult WITHOUT a cell (TypeError before this) — a parked/fixture result must render without a synthetic cell. The live runner always populates it; review renders the 6-D coordinates row only when cell is not None. Field reorder is safe — run.py constructs by keyword."
  - "Group by the grounding dimension (dsp_only / audio+dsp / …): grounding is the milestone's empirical axis ('which architecture clicks'), so grouping by it lets Kaan read the architecture contrast at a glance. Deterministic group order (sorted label). A no-cell result falls under '(uncategorized)'."
  - "render_review accepts BOTH a positional `scores` list (the common path — [score_cell(r) for r in results]) AND a dict keyed by result — matches the test's list usage + a future keyed call without an API change."
  - "Reworded one docstring line so the literal `winner:` token does not appear anywhere in review.py — keeps the acceptance grep-gate (`grep -in winner:`) cleanly empty in code; the remaining `winner` mentions are prose stating it NEVER writes one."
  - "docs/bench.md groups the produce-and-park contract into 6 sections matching docs/library.md's tone; cross-references 81-VALIDATION.md's Manual-Only rows so the 3 KAAN-ACTION items have a single canonical home."

requirements-worked: [BENCH-01, BENCH-02, BENCH-03]

# Metrics
duration: 9min
completed: 2026-05-26
---

# Phase 81 Plan 04: BENCH-03 Review Surface + docs/bench.md Summary

**Built `src/vibemix/bench/review.py` — `render_review(results, scores) -> str`, a PURE JSON→Markdown renderer that lays the recorded bench cells out for Kaan's ear. It ranks each grounding-dimension group by auto-score (via `rank_cells`, a SORT), renders every cell's 6-D coordinates + the three auto-scores + the assembled prompt + the recorded output, and ends with a literally-EMPTY `## VERDICT (Kaan fills this)` block. THE HARD HUMAN GATE is honored: no code path writes a winner, picks an architecture, or synthesizes a verdict (Pitfall 5 / T-81-09). An errored cell renders `**ERRORED — parked:** {error}`, never fabricated output (T-81-10); prompts + outputs are path-scrubbed via `strip_leaks` (T-81-11). The render is pure + deterministic — same inputs → byte-identical Markdown, no I/O. Wrote `docs/bench.md` documenting the produce-and-park contract: the offline honest-green gate (`pytest tests/bench/`, zero API), the bounded fail-safe produce command (`uv run python -m vibemix bench run --study A`), the review surface, and the three parked KAAN-ACTION items (the real run, Kaan's-ear verdict, the taste-rubric wording). Flipped the 3 BENCH-03 review xfail scaffolds to real-green. This closes Phase 81's CODE deliverables.**

## Performance

- **Duration:** ~9 min
- **Tasks:** 2 (Task 1 review.py — TDD, RED scaffolds in place from Plan 01; Task 2 docs/bench.md)
- **Files:** 2 created (`bench/review.py`, `docs/bench.md`) + 2 modified (`bench/cell.py` cell-optional, `tests/bench/test_review.py` xfail flips)

## Accomplishments

- **`review.py` — `render_review(results, scores) -> str`** — a pure JSON→Markdown transform. Pairs each result with its score (positional list or keyed dict), groups by the grounding dimension, sorts each group strongest-first via `rank_cells`, and renders per cell: rank, 6-D coordinates (only when a cell is recorded), the three auto-scores + the SORT-ONLY aggregate (labelled "rank signal, not a verdict"), the truncated+scrubbed prompt, and the scrubbed output.
- **The hard human gate** — the surface ends with the EXACT empty block: `## VERDICT (Kaan fills this)` + `> _Kaan fills this in — the auto-rank is a sort, not a decision._`. No code path writes a winner (grep-gate clean: `grep -in "winner:"` empty in code).
- **Errored-cell parking** — `result.error is not None` → `**ERRORED — parked:** {error}` (scrubbed), no output line; never fabricated.
- **Privacy** — prompts/outputs scrubbed via the Telegram-bridge `strip_leaks` (absolute paths / `~/...` → `[path]`); the renderer emits no key.
- **`docs/bench.md`** — 6 sections matching `docs/library.md`'s idiom: What it is (the matrix + two studies + no-audio cell), the Offline gate, the produce step (KAAN-ACTION, cost-bounded + fail-safe), the review surface, and an explicit KAAN-ACTION section naming all three parked items; states plainly "autonomous produces + ranks; Kaan decides; nothing is faked".
- **Flipped the 3 BENCH-03 review xfails** (`test_verdict_section_present_but_empty`, `test_errored_cell_renders_as_parked`, `test_render_ranks_and_groups`) to real-green.

## Task Commits

1. **Task 1: review.py — ranked KAAN-ACTION render, empty verdict + cell-optional + xfail flips** — `e659429` (feat)
2. **Task 2: docs/bench.md — produce step + KAAN-ACTION parking** — `738920b` (docs)

## Verification

- `pytest tests/bench/test_review.py tests/bench/test_no_model_literal.py -x` → **5 passed** (the 3 BENCH-03 review xfails flipped real-green + the 2 literal-guards stay green).
- `grep -in "winner:" src/vibemix/bench/review.py` → **empty** (no winner-assigning line in code); `grep -in "the winner is"` → empty. The remaining `winner` mentions are docstring prose stating it NEVER writes one (Pitfall 5 / T-81-09 enforced).
- Empty-verdict block present + path-scrub verified live: a `/Users/ozai/Music/secret.mp3` prompt rendered as `[path]`; `## VERDICT (Kaan fills this)` + the placeholder present; an errored cell rendered `ERRORED — parked`.
- Purity verified: two `render_review(...)` calls on identical inputs → byte-identical Markdown (no clock / randomness / I/O).
- `test -f docs/bench.md && grep -c "KAAN-ACTION" docs/bench.md` → **8**; `grep -q "bench run"` → present (matches the Plan-02 CLI `vibemix bench run --study A`).
- `bash scripts/release/check_no_hardcoded_model.sh` path: `tests/bench/test_no_model_literal.py` green — no literal introduced under `bench/`.
- Orphan inventory: `tests/scripts/test_orphan_inventory.py` green — `render_review` is consumed by `test_review.py`, not flagged as a new orphan (no baseline edit needed, unlike Plan 03's `rank_cells`).
- **Full suite:** `4523 passed / 26 skipped / 1 xfailed / 4 xpassed` (was 4520 passed / 3 xfailed before this plan — the 3 BENCH-03 review xfails flipped to passed, 4520→4523; the 1 remaining xfail = the pre-existing `test_budget` gate; the 4 xpassed = pre-existing live-hardware markers). Zero new failures.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `BenchResult.cell` made optional so the Plan-01 review scaffolds construct**
- **Found during:** Task 1 (first run of the review test scaffolds)
- **Issue:** `BenchResult.cell` was a required positional field (Plan 02), but the Plan-01 `test_review.py` scaffolds construct `BenchResult(prompt=..., output=..., dsp_snapshot=..., usage=..., error=...)` WITHOUT a `cell` — raising `TypeError: missing 1 required positional argument: 'cell'`. A parked / fixture result legitimately has no 6-D coordinate to record, and the test contract (Plan 01) expects this.
- **Fix:** Defaulted `cell: BenchCell | None = None` and moved it after `dsp_snapshot` (so it sits with the other defaulted fields). The live runner (`run.py`) always passes `cell=cell` by keyword — the field reorder is safe (no positional construction anywhere). `render_review` renders the coordinates row only when `cell is not None`.
- **Files modified:** `src/vibemix/bench/cell.py`
- **Commit:** `e659429`

No bugs, no missing critical functionality, no architectural changes.

## Known Stubs

None. `render_review` is fully implemented and unit-green. (The `TASTE_RUBRIC` placeholder in `bench/matrix.py` is an INTENTIONAL parked KAAN-ACTION — Kaan's IP, documented in `docs/bench.md` + `81-VALIDATION.md`, not an engineering gap.)

## Threat Flags

None. `review.py` is a pure in-memory JSON→Markdown transform over recorded cells + scores — no network, no API, no auth path, no schema change; the caller owns the file write (boundary per the plan's `<threat_model>`). T-81-09 (verdict creep / a winner-naming surface) mitigated: the VERDICT section is literally empty, no code path writes a winner, the grep gate is clean in code. T-81-10 (fabricated errored cell) mitigated: errored cells render `ERRORED — parked`, asserted in `test_review.py`. T-81-11 (key / personal-path leak) mitigated: prompts/outputs scrubbed via `strip_leaks`, no key emitted.

## Self-Check: PASSED

- `src/vibemix/bench/review.py` FOUND on disk
- `docs/bench.md` FOUND on disk
- Task commit `e659429` FOUND in git log
- Task commit `738920b` FOUND in git log
- `pytest tests/bench/test_review.py` → 3 review tests green; full suite green (4523 passed, zero new failures)
- Grep gates: `winner:` empty in code; `KAAN-ACTION` ×8 in docs/bench.md; no model literal under bench/

## Next Phase Readiness

- **BENCH-01/02/03 CODE is complete** — the harness (Plan 02), the eval (Plan 03), and the review surface (this plan) are all offline-green with zero API. Phase 81's engineering deliverables close here.
- **The HARD HUMAN GATE rides forward as KAAN-ACTION** (never automated, never faked — documented in `docs/bench.md` + `81-VALIDATION.md`): (1) the bounded real two-study run on the funded key (`vibemix bench run --study A`); (2) Kaan's-ear VERDICT — which architecture + model wins (feeds GROUND-02's `live_coach` alias + the default architecture as a follow-up); (3) the final `TASTE_RUBRIC` wording (Kaan's IP).
- Acting on the verdict (setting `live_coach` to the winning model, making the winning architecture the default) is a follow-up after Kaan judges — out of this phase by design.

---
*Phase: 81-bench-the-validation-instrument*
*Completed: 2026-05-26*
