---
phase: 81-bench-the-validation-instrument
verified: 2026-05-26T00:00:00Z
status: human_needed
score: 4/4 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: none
  note: initial verification
human_verification:
  - test: "Run the bounded live two-study produce step on the funded key: `uv run python -m vibemix bench run --study A` (then `--study B`, `--study no-audio`) and confirm cells record real Gemini output, errored cells park as `{error:...}`, and `SessionMeter.summary()` reports a low single-digit euro-cents cost."
    expected: "bench_run.json is written with real per-cell output (no fabricated cells); any 429/auth/network error parks the cell and the sweep continues; cost is bounded."
    why_human: "Requires the funded GEMINI_API_KEY + a live network call — the offline gate is fixture/fake-client only by design (NEVER-FAKE). PRODUCE-AND-PARK contract: autonomous built the instrument; the real run is the parked KAAN-ACTION."
  - test: "Read the generated review surface (render_review over bench_run.json), judge with your ear which architecture × model 'clicks' vs sounds like slop, and FILL the empty `## VERDICT (Kaan fills this)` section. Feeds GROUND-02's `live_coach` alias + the default architecture."
    expected: "The winning architecture + model is decided by Kaan's ear (Phase-16 rule, the HARD HUMAN GATE). No code path names a winner — the verdict is literally empty until Kaan writes it."
    why_human: "Subjective taste judgment ('real DJ friend in the ear, not a voice assistant') — the project's anti-slop release gate. Cannot be automated; faking it would violate the core NEVER-FAKE contract."
  - test: "Author the final TASTE_RUBRIC wording (the 'what clicked means' reward signal) and replace the FIXED placeholder in `src/vibemix/bench/matrix.py` (marked `# KAAN-ACTION: placeholder taste rubric — final wording is Kaan's IP (Open Q1)`)."
    expected: "The real reward-signal rubric (Kaan's lived-experience IP) replaces the stand-in placeholder; the `with_rubric` taste axis already assembles a distinct prompt, so only the text changes."
    why_human: "The rubric is Kaan's IP / lived-experience reward signal (RESEARCH Open Q1) — autonomous deliberately did NOT author it, parking it as KAAN-ACTION."
---

# Phase 81: BENCH — The Validation Instrument — Verification Report

**Phase Goal:** A multi-dimensional bench (model × grounding × prompting × contexting × lens × taste) on real tracks + automated first-pass eval (groundedness/specificity/mode-fidelity) + a Kaan's-ear review surface. PRODUCE-AND-PARK: build + auto-eval + review surface; the verdict is the HARD HUMAN GATE, never faked.
**Verified:** 2026-05-26
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #   | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 1 (SC1/BENCH-01) | A multi-dimensional bench harness runs model × grounding × prompting × contexting × lens × taste on real tracks and records each cell's output | ✓ VERIFIED | `BenchCell` carries all 6 axes (`cell.py:34-56`); `assemble.build_cell_prompt` composes the REAL seams in verified order — `build_lens_instruction` + `AICoach.build_prompt` + `build_parts_description(secondary_ear=)` + `model_router.resolve` (`assemble.py:68-103`), NOT re-authored prompt text; `STUDY_A` (10 cells), `STUDY_B` (2 model-axis cells), `NO_AUDIO_CELL` defined (`matrix.py:62-126`); `run_study` records a `BenchResult` per cell via an INJECTED client + writes verbatim JSON (`run.py:84-222`); 6 real `.mp3` excerpts under `tests/bench/data/`. Live spot-check: `build_cell_prompt(NO_AUDIO_CELL)` → 0 audio Parts, non-empty body, model resolved to `gemini-3-flash-preview` (router id, not a literal). |
| 2 (SC2/BENCH-02) | An automated first-pass eval scores groundedness (vs DSP facts), specificity, and mode-fidelity per cell — unit-testable on fixtures without the live API | ✓ VERIFIED | `eval.py` groundedness REUSES `_LINTER.check(text, snapshot, mode="debrief")` verbatim (`eval.py:45,131`) — no bespoke atom parser; specificity is deterministic over `NEGATIVE_PHRASES` + a concrete-measure regex (`eval.py:139-154`); lens-fidelity scores per-lens `LENS_ANCHORS` (`eval.py:157-168`). Pure, offline. `score_cell` flags errored cells all-zero. `tests/bench/test_eval.py` green with zero API. |
| 3 (SC3/BENCH-03) | Bench cells are surfaced for Kaan's-ear final judgment via a KAAN-ACTION review surface — the auto-score RANKS, Kaan's ear decides | ✓ VERIFIED | `review.render_review` is a pure JSON→Markdown renderer: ranks by aggregate (`rank_cells`, a SORT), groups by grounding dimension, renders coordinates + 3 auto-scores + prompt + output, ends with the literally-EMPTY `## VERDICT (Kaan fills this)` block (`review.py:37-38,210-214`). Errored cells render `**ERRORED — parked:**` (`review.py:145-148`). Live spot-check confirmed empty-verdict placeholder present, errored parked, byte-identical purity. Grep: NO code path writes a winner (all `winner`/`verdict` hits are docstrings/comments/the empty-heading constant). |
| 4 (SC4) | The bench runs honest-green offline (mocked/fixture cells unit-testable) AND has a documented live e2e path on the funded key — results are never faked | ✓ VERIFIED (offline) / parked (live) | `pytest -q tests/bench/` → 16 passed, 0 xfail (the Plan-01 xfail-strict scaffolds flipped to real-green as planned). The 429 fail-safe verified live: a raising client records `error` set + `output==""` + sweep continues (`run.py:159-169`). `vibemix bench run --study A` documented in `docs/bench.md`; real `genai.Client` built ONLY in the CLI path (`__main__.py:1726`), injected into `run_study`. The LIVE run + verdict are the parked HARD HUMAN GATE (human_verification below) — never faked. |

**Score:** 4/4 truths verified (offline/produce side); the 3 PRODUCE-AND-PARK items are correctly parked as the human gate, not gaps.

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `src/vibemix/bench/cell.py` | BenchCell (6-D) + BenchResult frozen dataclasses | ✓ VERIFIED | Both frozen; BenchResult carries prompt/output/dsp_snapshot/usage/error; `cell` optional for parked fixtures |
| `src/vibemix/bench/matrix.py` | STUDY_A/STUDY_B/NO_AUDIO_CELL + TASTE_RUBRIC placeholder + LENS_ANCHORS | ✓ VERIFIED | TASTE_RUBRIC carries the `# KAAN-ACTION` IP-placeholder marker; no model literal (alias strings only) |
| `src/vibemix/bench/assemble.py` | build_cell_prompt composing real seams | ✓ VERIFIED | Composes `build_lens_instruction`/`AICoach.build_prompt`/`build_parts_description`/`model_router.resolve`; dsp_only appends no audio Part |
| `src/vibemix/bench/fixtures.py` | fixture_state_for(contexting, grounding) | ✓ VERIFIED | Builds a real MusicState + non-empty snapshot |
| `src/vibemix/bench/run.py` | run_study + fail-safe + recorder + SessionMeter feed | ✓ VERIFIED | Injected client; per-cell `except` parks error; `meter.record` fed on success; verbatim JSON |
| `src/vibemix/bench/eval.py` | score_cell (groundedness/specificity/lens_fidelity) rank-only | ✓ VERIFIED | Reuses CitationLinter; no winner/verdict field |
| `src/vibemix/bench/review.py` | render_review → markdown, empty verdict | ✓ VERIFIED | Pure, deterministic, empty VERDICT, errored parked |
| `docs/bench.md` | Produce step + KAAN-ACTION parking | ✓ VERIFIED | 8 KAAN-ACTION mentions; documents offline gate, produce command, cost bound, fail-safe, the 3 parked items |
| `tests/bench/*` + `data/*.mp3` | xfail scaffolds → flipped + fixtures + 6 .mp3 | ✓ VERIFIED | 16 tests green; `_FakeClient`/`_RaisingClient`; 6 excerpts present (outside src/, wheel-excluded) |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| assemble.py | model_router.resolve | `model, tier = resolve(cell.model_path)` | ✓ WIRED | `assemble.py:103`; spot-check resolved a real router id |
| run.py | library/budget SessionMeter | `meter.record(cell.model_path, ...)` | ✓ WIRED | `run.py:115,153` |
| assemble.py | prompts/matrix.py + state/coach.py | build_lens_instruction + build_prompt + build_parts_description | ✓ WIRED | `assemble.py:68,84,91` |
| eval.py | coach/citation_linter.py | `_LINTER.check(..., mode="debrief")` | ✓ WIRED | `eval.py:45,131` — verbatim reuse, no re-implementation |
| eval.py | prompts/negative_dict NEGATIVE_PHRASES | slop penalty | ✓ WIRED | `eval.py:40,148` |
| review.py | eval.py rank_cells | grouped ranked render | ✓ WIRED | `review.py:31,206` |
| __main__.py | bench CLI | argv guard + _run_bench_cli | ✓ WIRED | `__main__.py:203,2311`; `vibemix bench --help` exit 0, no banner |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| No-audio cell: zero audio Parts, populated body, router-resolved model | `build_cell_prompt(NO_AUDIO_CELL)` | 0 audio parts, body>100 chars, model=gemini-3-flash-preview | ✓ PASS |
| 429 fail-safe: error set + empty output + sweep continues | `run_study([cell], client=Raising())` | error set, output="", len=1 | ✓ PASS |
| Errored cell sinks in rank | `score_cell(errored)` | errored=True, aggregate=0.0 | ✓ PASS |
| Empty verdict + errored parked + pure render | `render_review(res,[sc])` ×2 | "Kaan fills this in" present, "ERRORED — parked" present, no winner, byte-identical | ✓ PASS |
| Zero model literals under bench/ | `grep -rn "gemini-" src/vibemix/bench/` | no matches | ✓ PASS |
| No winner code path | grep eval.py/review.py | all hits docstring/comment/empty-heading constant | ✓ PASS |
| bench CLI wired (no banner) | `python -m vibemix bench --help` | exit 0, lists `run` | ✓ PASS |
| Bench suite | `pytest -q tests/bench/` | 16 passed | ✓ PASS |
| Full suite (no regressions) | `pytest -q` | 4523 passed, 26 skipped, 1 xfailed, 4 xpassed | ✓ PASS |

The 1 xfail (budget cost-model, pre-existing 2026-05-25 decision) and 4 xpass (live-hardware on hosted runner) are the carried-in baseline — NOT regressions, per verification notes. The README feature-matrix sync gate did NOT fire.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| BENCH-01 | 81-01, 81-02 | Multi-dimensional bench harness on real tracks records each cell | ✓ SATISFIED | cell/matrix/assemble/run; 6-D matrix expressed; STUDY_A/B + NO_AUDIO_CELL; real seams; offline-green |
| BENCH-02 | 81-01, 81-03 | Automated first-pass eval (groundedness/specificity/mode-fidelity) unit-testable on fixtures | ✓ SATISFIED | eval.py reuses CitationLinter; deterministic specificity + lens-fidelity; zero-API tests green |
| BENCH-03 | 81-01, 81-04 | Bench cells surfaced for Kaan's-ear judgment (KAAN-ACTION review surface) | ✓ SATISFIED (code) | review.py ranked surface + empty verdict; docs/bench.md parks the verdict. The ear-verdict itself is the parked human gate. |

No orphaned requirements — REQUIREMENTS.md maps exactly BENCH-01/02/03 to Phase 81, all claimed across the plans.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| matrix.py | 30 | `# KAAN-ACTION:` placeholder marker (TASTE_RUBRIC) | ℹ️ Info | Intentional, clearly-labeled IP placeholder, not debt; references Open Q1 follow-up; the `with_rubric` axis still assembles a distinct prompt today. NOT a TBD/FIXME/XXX debt marker. |

No `TBD`/`FIXME`/`XXX` debt markers in any phase-modified file. No fabricated cell outputs, no synthesized verdict, no winner-assigning code path — the NEVER-FAKE contract holds.

### Human Verification Required

The PRODUCE-AND-PARK contract is satisfied: autonomous produced the harness + auto-eval + review surface (all offline-green), and the three judgment items are correctly parked as the HARD HUMAN GATE (never faked). These are classified as human verification, NOT gaps:

1. **Live two-study produce run** — `uv run python -m vibemix bench run --study A` (then B / no-audio) on the funded key. Expected: real recorded cells, parked errors, bounded cost. Why human: requires funded key + live network (offline gate is fake-client by design).
2. **Kaan's-ear VERDICT** — read the review surface, decide the winning architecture × model, fill the empty `## VERDICT` section. Why human: subjective anti-slop taste judgment (Phase-16 rule), cannot be automated, faking violates the core contract.
3. **Final TASTE_RUBRIC wording** — replace the FIXED placeholder in `matrix.py` with the real reward-signal rubric (Kaan's IP, Open Q1). Why human: Kaan's lived-experience IP, deliberately not authored by autonomous.

### Gaps Summary

No gaps. All four ROADMAP success criteria and all three requirements (BENCH-01/02/03) are met in the shipped code, verified by reading the source, behavioral spot-checks, and the full green suite (4523 passed / 0 failed, baseline preserved). The harness composes the REAL product seams (not re-authored prompt text), the no-audio cell is correct, the 429 fail-safe parks gracefully without fabricating, the eval reuses the product's CitationLinter and RANKS without deciding, and the review surface renders an empty verdict with no winner-assigning code path. The live run + ear-verdict + taste-rubric wording are the parked PRODUCE-AND-PARK human gate — surfaced for Kaan, never faked.

---

_Verified: 2026-05-26_
_Verifier: Claude (gsd-verifier)_
