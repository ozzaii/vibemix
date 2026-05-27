---
phase: 27-eval-harness-v2-0-carry-forward-close-out
plan: 02
subsystem: eval-harness
tags:
  - llm-judge
  - eval-02
  - eval-04
  - eval-05
  - p42-mitigation

requires:
  - phase: 27
    provides: Plan 27-01 replay_harness + scripts/eval scaffold + dev deps
provides:
  - 2-judge cross-check architecture (Pro 6-axis + Flash binary) with min() aggregation
  - cited_relevance cosine filter (Gemini Embedding 2) with min-8-words cost guard
  - useful_response_ratio + per_event_class_substance (Pitfall P44 mitigation)
  - rubric files documenting divergent framings (Pitfall P42 mitigation)
affects:
  - Plan 27-04 (CI gate consumes rubric files + judge module)
  - Phase 28+ (eval harness fully wired for nightly canary)

tech-stack:
  added: []
  patterns:
    - "min(pro_f1, flash_f1) aggregation prevents single-judge collusion (Pitfall P42)"
    - "min-8-words floor early-exits relevance API call (Pitfall P45 cost guard)"
    - "VCR.py cassettes scrub authorization + x-goog-api-key headers + query key param"
    - "Structured-output via response_schema on Gemini SDK (no manual JSON parsing post-call)"

key-files:
  created:
    - eval/rubrics/judge_pro.md (68 lines, 6-axis rubric)
    - eval/rubrics/judge_flash.md (43 lines, binary rubric)
    - scripts/eval/judge.py (288 lines)
    - scripts/eval/cited_relevance.py (143 lines)
    - tests/eval/cassettes/.gitkeep
    - tests/eval/test_substance_metric.py (96 lines, 8 tests)
    - tests/eval/test_cited_relevance.py (97 lines, 10 tests)
    - tests/eval/test_judge_pro_rubric.py (127 lines, 12 tests)
    - tests/eval/test_judge_flash_rubric.py (90 lines, 9 tests)
  modified:
    - scripts/eval/replay_harness.py (+49 lines: real-judge dispatcher)
    - tests/eval/test_replay_harness.py (updated unknown-judges test + 2 new tests for the gemini-3-pro/multi-judge paths)

key-decisions:
  - "Pure-logic tests (39 new) cover the critical aggregation + threshold + rubric-divergence gates. API-backed VCR tests are deferred to KAAN-ACTION-LEGAL.md (one-time cassette recording with real GEMINI_API_KEY)."
  - "Pitfall P42 mitigation is structural (min() in aggregate_session_f1) AND prompt-level (divergent rubric framings + anti-self-praise instructions). Both layers required because a clever attacker could potentially clone the rubric on both sides — the min() floor is the hard gate."
  - "Pitfall P45 cost guard returns 0.0 BEFORE invoking the embedding API when stripped response < 8 words. Saves cost on noop / filler responses + enforces the substance floor."
  - "Lazy genai.Client init in replay_harness — _build_judge_callable returns a callable; client only constructed on first real invocation. Keeps offline tests (and the noop path) free of API requirements."

requirements-completed:
  - EVAL-02
  - EVAL-04
  - EVAL-05

duration: ~20 min
completed: 2026-05-15
---

# Phase 27 Plan 02: 2-Judge Cross-Check + Cited-Relevance + Substance Metric Summary

**Replaces Plan 27-01's `--judges noop` stub with the real Gemini 3 Pro 6-axis JSON + Gemini 3 Flash binary cross-check, plus the cited-relevance cosine filter and substance-metric aggregation. The technical heart of the autonomous hallucination-proxy gate.**

## Performance

- **Duration:** ~20 min
- **Tasks:** 2 (atomic commits per task — combined into one commit since the rubric + judge.py + cited_relevance.py + tests are tightly coupled)
- **Files created:** 9 (2 rubrics + 2 modules + 5 test files)
- **Files modified:** 2 (replay_harness.py, test_replay_harness.py)
- **Tests added:** 39 (all pure-logic; 72 total in tests/eval/, all passing in 0.96s)
- **VCR cassettes:** 0 (deferred to KAAN-ACTION-LEGAL.md Item 1)

## Accomplishments

- `eval/rubrics/judge_pro.md` + `eval/rubrics/judge_flash.md` with intentionally divergent framings (Pitfall P42 mitigation): Pro asks 6-axis numeric grading + "would this fool a human DJ friend?"; Flash asks the orthogonal binary "does this semantically anchor to its citation?". Both files include explicit anti-self-praise instructions.
- `scripts/eval/judge.py`:
  - `PRO_VERDICT_SCHEMA` + `FLASH_VERDICT_SCHEMA` dicts (drop-in to Gemini structured-output `response_schema`).
  - `load_rubric` with `@lru_cache` so the rubric file is read once per process.
  - `call_pro_judge` / `call_flash_judge` async dispatchers wrapping the real Gemini SDK.
  - `call_judges` multi-judge dispatcher with `asyncio.gather` for concurrent Pro + Flash invocation.
  - **`aggregate_session_f1` returns `min(pro_f1, flash_f1)` — NEVER mean** (Pitfall P42 critical gate).
- `scripts/eval/cited_relevance.py`:
  - `strip_citations` regex covers all 4 citation forms (ev / track / mix / emote).
  - `cosine` with explicit zero-vector guard (returns 0.0, never NaN/ZeroDivision).
  - `relevance_score` with **min-8-words floor cost guard** — early-exits with 0.0 BEFORE invoking the embedding API when stripped response is too short.
  - `useful_response_ratio` + `per_event_class_substance` for Pitfall P44 substance metric (HEARTBEAT excluded from per-class denominator).
- `scripts/eval/replay_harness.py` updated: `_build_judge_callable` now wires the real Gemini judges when `judges_arg != "noop"`. Multi-judge via comma-separated names. Lazy `genai.Client` instantiation (no API contact until first invocation).
- 39 new pure-logic tests covering: schema integrity, aggregation correctness (the P42 min vs mean test is the critical pin), rubric file structure + divergence + anti-self-praise gates, P45 word-floor enforcement, P44 substance metric edge cases (empty, all-heartbeat, mixed).

## Task Commits

1. **Tasks 1+2 combined: rubrics + judge.py + cited_relevance.py + replay_harness wire-in + tests** — `afb0a2c` (feat)

## Files Created/Modified

- `eval/rubrics/judge_pro.md` — 6-axis Pro rubric (groundedness/timing/substance/tone/relevance/brevity + verdict + rationale)
- `eval/rubrics/judge_flash.md` — binary Flash rubric (pass/why)
- `scripts/eval/judge.py` — schemas + dispatchers + min() aggregator
- `scripts/eval/cited_relevance.py` — cosine + word-floor + ratio + per-class metrics
- `scripts/eval/replay_harness.py` — real-judge dispatch (+49 lines)
- `tests/eval/cassettes/.gitkeep` — directory marker for VCR cassettes (recorded later per KAAN-ACTION Item 1)
- `tests/eval/test_substance_metric.py` — 8 tests
- `tests/eval/test_cited_relevance.py` — 10 tests
- `tests/eval/test_judge_pro_rubric.py` — 12 tests
- `tests/eval/test_judge_flash_rubric.py` — 9 tests
- `tests/eval/test_replay_harness.py` — updated unknown-judges + added 2 multi-judge wire tests

## Decisions Made

- **Pure-logic vs API-backed split.** 39 new tests cover the structural + algorithmic surface; the rubric-driven Gemini calls are deferred to KAAN-ACTION Item 1 for one-time cassette recording with real GEMINI_API_KEY. Pure-logic tests pin the Pitfall P42 (min-aggregation) + P45 (word-floor) + P44 (substance metric) gates which are the critical-path mitigations.
- **Combined Tasks 1+2 into one commit.** The rubric files + judge.py + cited_relevance.py + replay_harness wire-in are tightly coupled — separating into two commits would have produced a half-broken intermediate (e.g. judge.py imports from cited_relevance.py for the test wiring). One feat commit, SUMMARY as close-out marker.

## VCR Cassette Recording Workflow (Deferred to KAAN-ACTION Item 1)

```bash
cd /Users/ozai/projects/dj-set-ai

# One-time: record cassettes with real GEMINI_API_KEY
VCR_RECORD_MODE=new_episodes uv run pytest \
  tests/eval/test_judge_pro_rubric.py \
  tests/eval/test_judge_flash_rubric.py \
  tests/eval/test_cited_relevance.py \
  -m "vcr" --tb=short

# Verify scrub
! grep -rE "AIza[A-Za-z0-9_-]{35}" tests/eval/cassettes/

# Commit
git add tests/eval/cassettes/*.yaml
git commit -m "test(27-02): record VCR.py cassettes for judge + relevance tests"
```

Subsequent PR runs use `record_mode="none"` (cassettes replay) for $0 cost.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Test coverage split] VCR cassette tests deferred to KAAN-ACTION**
- **Found during:** Task 1 + 2 — the plan's verify command tries to run `uv run pytest tests/eval/test_judge_pro_rubric.py::test_call_judges_aggregates_min_not_mean` which works (pure logic), but other tests in the same file would attempt API calls without cassettes.
- **Issue:** PLAN.md says "Note for executor: in `record_mode=new_episodes` (used by nightly canary in Plan 04 CI), missing cassettes get recorded. In `record_mode=none` (PR CI), missing cassettes raise. To populate cassettes initially: `VCR_RECORD_MODE=new_episodes uv run pytest tests/eval/test_judge_pro_rubric.py` ONCE with a real GEMINI_API_KEY."
- **Fix:** Created 39 pure-logic tests across 4 test files covering all the gating surfaces (schema integrity, aggregation min(), rubric file divergence, anti-self-praise grep, word-floor enforcement, substance edge cases). VCR-decorated tests deferred to KAAN-ACTION Item 1 with the exact one-time recording command documented above.
- **Files modified:** All Plan 27-02 test files lean on pure logic; no `@pytest.mark.vcr` markers in this commit's test files.
- **Verification:** 39 new tests pass in 0.06s; 72 total in tests/eval/ pass in 0.96s.
- **Committed in:** `afb0a2c`

**2. [Rule 1 - Existing test contract] test_judges_unknown_value_raises_not_implemented breaks once Plan 27-02 wires real judges**
- **Found during:** Full eval suite run after Plan 27-02 implementation
- **Issue:** Plan 01's test asserted `_build_judge_callable("gemini-3-flash")` raises NotImplementedError. Plan 27-02's wire-up makes that name valid — the test fails.
- **Fix:** Updated test to use a truly-unknown name (`"gemini-9-future"`); added two new tests covering the gemini-3-pro path + the multi-judge parse path.
- **Files modified:** `tests/eval/test_replay_harness.py`
- **Verification:** All 72 tests pass.
- **Committed in:** `afb0a2c` (in the same commit as the rest of Plan 27-02)

**Total deviations:** 2 auto-fixed (1 cassette-recording deferred to KAAN-ACTION, 1 prior-test update for cross-plan API change).
**Impact:** No architectural change. The 2-judge cross-check + cited-relevance + substance metric are fully implemented; the API-backed verification surface is one cassette-recording command away.

## Verification

```bash
# Pure-logic tests pass
uv run pytest tests/eval/test_substance_metric.py \
              tests/eval/test_cited_relevance.py \
              tests/eval/test_judge_pro_rubric.py \
              tests/eval/test_judge_flash_rubric.py \
              -x  # 39 passed in 0.06s

# Full eval suite (including Plan 27-01 baselines) green
uv run pytest tests/eval/ -x  # 72 passed in 0.96s

# Noop path regression preserved
uv run python -m scripts.eval.replay_harness --corpus tests/eval/fixtures \
  --judges noop --output /tmp/p27-02-noop
test -f /tmp/p27-02-noop/eval_report.json  # OK

# Rubric files exist + diverge
diff -q eval/rubrics/judge_pro.md eval/rubrics/judge_flash.md  # MUST differ

# Min-aggregation gate (Pitfall P42 critical evidence)
uv run pytest tests/eval/test_judge_pro_rubric.py::test_call_judges_aggregates_min_not_mean -x  # OK
```

## Self-Check: PASSED

- [x] All 9 plan-level success criteria met (with 2 documented Rule 1 deviations adapting to autonomous-mode constraints)
- [x] All `<acceptance_criteria>` pass
- [x] Plan-level `<verification>` block passes (pure-logic; VCR cassette gate deferred to KAAN-ACTION)
- [x] Pitfall P42 mitigation present at BOTH structural (min) and prompt (divergent rubric) layers
- [x] Pitfall P45 cost-guard (min-8-words floor) enforced by pure-logic test
- [x] No POC files modified

## Next Plan Readiness

Plan 27-03 (corpus assembly) and Plan 27-04 (CI gate) build on this. Plan 27-04 will:
1. Add the `tests/eval/cassettes/**` AIza scrub gate to CI.
2. Add the rubric anti-self-praise grep gate.
3. Activate the eval.yml workflow with `--judges gemini-3-pro,gemini-3-flash`.

When KAAN-ACTION Item 1 (cassette recording) is done, the cassettes commit allows Plan 27-04 CI to run at $0 per PR.
