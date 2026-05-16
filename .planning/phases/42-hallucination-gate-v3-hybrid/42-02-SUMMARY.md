---
phase: 42-hallucination-gate-v3-hybrid
plan: 02
subsystem: eval
tags: [eval, threshold, recalibration, audit-log, ci-gate, tolerance-band, gate-04]
requires:
  - Phase 27-01 (scripts/eval/replay_harness.py + eval_report.json shape)
  - Phase 27-04 (eval/THRESHOLD-LOCK.md frontmatter + threshold_lock.py parser)
  - Plan 42-01 (eval/corpus/sessions/ scaffold + manifest contract)
provides:
  - GATE-04 recalibration driver (scripts/eval/recalibrate_thresholds.py)
  - ±0.10 inclusive tolerance band over (f1, substance, cited_cosine, bypass)
  - Append-only audit trail (eval/THRESHOLD-RECALIBRATION-LOG.md)
  - --check-only CI mode gating corpus size + log freshness
  - .github/workflows/eval.yml extension on schedule + workflow_dispatch
affects:
  - .github/workflows/eval.yml (new freshness-gate step)
  - Plan 42-03 (check_gate.sh — reads nightly proxy scorecards alongside)
  - Phase 27 re-tuning protocol (programmatically enforced no-auto-mutate)
tech-stack:
  added: []
  patterns:
    - "±0.10 tolerance band with float-representation epsilon (1e-9) so the boundary 0.70-0.80 case classifies inclusively under IEEE-754 drift"
    - "Append-only audit-log writer that seeds the markdown file on first use"
    - "ISO8601 header regex + schema_example filter for log-freshness gate (placeholder never satisfies)"
    - "subprocess-isolated replay_harness invocation with optional in-process runner injection for hermetic unit tests"
    - "--check-only fast lane that skips the replay harness entirely (no Gemini calls in CI)"
key-files:
  created:
    - scripts/eval/recalibrate_thresholds.py
    - eval/THRESHOLD-RECALIBRATION-LOG.md
    - tests/eval/test_recalibrate_thresholds.py
    - tests/eval/test_check_real_corpus_mode.py
  modified:
    - .github/workflows/eval.yml
decisions:
  - "Inclusive boundary at |delta|=0.10 chosen per the plan's test_compute_delta_on_boundary contract; added _TOLERANCE_FLOAT_EPS=1e-9 to absorb IEEE-754 drift on the 0.70-0.80 case (8e-17 representation error)."
  - "schema_example seed entry is explicitly filtered by _latest_audit_entry_at so the seed cannot satisfy the 30-day freshness gate on its own."
  - "subprocess invocation of replay_harness preferred over direct import — process isolation insulates the recalibration parser from harness import-time side effects; in-process runner injection retained for hermetic unit tests."
  - "Aggregate verdict is conjunctive (any single metric out of band promotes the whole run to out_of_tolerance)."
metrics:
  duration: "~50 minutes"
  completed: 2026-05-16
  tasks: 2
  files: 5
  tests_added: 28
---

# Phase 42 Plan 02: Threshold Recalibration Tooling + ±0.10 Tolerance Band + eval.yml --check-real-corpus Summary

Shipped the GATE-04 recalibration tooling that drives the existing 2-judge eval (Phase 27) against the real-corpus session WAVs, computes the inclusive ±0.10 tolerance band over the four locked metrics, appends a structured audit entry, and either exits 0 (in band) or 1 (out of band, `RECALIBRATION_REQUIRED`). The CI workflow now carries a `--check-only` step that fails when the corpus has fewer than 6 populated sessions or the audit log carries no entry within the last 30 days.

## Objective

Per CONTEXT D-GATE-04, build the recalibration surface that lets the locked Phase 27 thresholds (f1≥0.80, substance≥0.65, cited-cosine≥0.40, bypass≤0.15, per-genre F1≥0.70) be tested against real-corpus WAVs once Kaan discharges GATE-03 — without ever auto-editing `eval/THRESHOLD-LOCK.md`. Phase 27's re-tuning protocol forbids autonomous re-signing; this plan codes that prohibition into the recalibration driver itself.

## Tasks Completed

### Task 1: recalibrate_thresholds.py + audit log seed + tolerance-band tests

**Commit:** `e6d358a`

**Files created:**

- `scripts/eval/recalibrate_thresholds.py` — recalibration driver. CLI surface exposes `--corpus`, `--judges`, `--lock-path`, `--log-path`, `--dry-run`, `--check-only`. Five exported callables: `main`, `measure_against_corpus`, `compute_delta`, `aggregate_verdict`, plus the `RECALIBRATION_TOLERANCE = 0.10` constant. `measure_against_corpus` invokes the existing replay harness via subprocess (process isolation for T-42-02-03 mitigation against `responses/*.txt` content leak), parses `eval_report.json` for numeric fields only, returns aggregate + per-session + per-genre breakdowns. `compute_delta` is the load-bearing tolerance-band primitive — measured minus locked, with absolute-value comparison against `RECALIBRATION_TOLERANCE + _TOLERANCE_FLOAT_EPS` (the epsilon absorbs the 8e-17 IEEE-754 drift on `0.70 - 0.80`). `append_audit_entry` writes append-only; seeds the markdown file when missing. `_run_recalibration` ties everything together, returning exit codes 0 (in band), 1 (out of band + `RECALIBRATION_REQUIRED` stderr), 2 (corpus too small or harness fault).

- `eval/THRESHOLD-RECALIBRATION-LOG.md` — seed audit-trail markdown file. Documents the purpose, cross-references, entry schema, and ships with one `verdict=schema_example` placeholder timestamped `1970-01-01T00:00:00Z`. The schema_example sentinel is filtered out by `_latest_audit_entry_at` so it can never satisfy the 30-day freshness gate alone — fresh-clone state correctly fails the `--check-only` gate until a real recalibration entry lands.

- `tests/eval/test_recalibrate_thresholds.py` — 19 unit tests covering:
  - `compute_delta` for in-tolerance (`0.83 vs 0.80`), negative-in-tolerance (`0.75 vs 0.80`), inclusive-boundary (`0.70 vs 0.80` and `0.90 vs 0.80`), and out-of-band (`0.65 vs 0.80`) cases.
  - `aggregate_verdict` conjunction (any single metric out of band → corpus out of band).
  - `format_audit_entry` schema fidelity (ISO8601 timestamp, all four metrics in measured/locked/delta blocks, per-genre line, `action: none` for in-tolerance vs `RECALIBRATION_REQUIRED` for out-of-tolerance).
  - `append_audit_entry` append-only invariant (3 sequential writes preserve header + all prior entries in order; missing file is seeded automatically).
  - `test_script_never_writes_to_lock_file` — full out-of-tolerance recalibration run with a stub runner; md5 of `THRESHOLD-LOCK.md` pinned before/after the run (T-42-02-01 mitigation).
  - `main` exit codes: corpus too small → 2; dry-run with full corpus → 0; `--check-only` empty corpus → 1; `--check-only` stale log → 1; `--check-only` fresh both → 0; `--check-only` schema_example-only → 1.
  - Header-regex resilience (skips malformed lines without crashing).
  - `RECALIBRATION_TOLERANCE` constant + callable surface pinned.

**Verify:** `uv run pytest tests/eval/test_recalibrate_thresholds.py -q --no-header` → `19 passed`.

**Done:** ≥7 tests pass (actual: 19), `recalibrate_thresholds.py --dry-run --corpus eval/corpus/sessions` exits 2 (corpus too small — placeholder dirs without `input.wav` don't count), audit log carries the schema block.

### Task 2: Extend .github/workflows/eval.yml with --check-real-corpus mode + workflow test

**Commit:** `e6caeab`

**Files modified/created:**

- `.github/workflows/eval.yml` — new step `Real-corpus calibration freshness gate (Phase 42 GATE-04)` inserted after the nightly-canary replay-harness step and before the post-scorecard step. Gated on `github.event_name == 'schedule' || github.event_name == 'workflow_dispatch'` — never on `pull_request` (PR mode uses VCR cassettes, not real-corpus). Invokes `uv run python -m scripts.eval.recalibrate_thresholds --corpus eval/corpus/sessions --check-only --lock-path eval/THRESHOLD-LOCK.md --log-path eval/THRESHOLD-RECALIBRATION-LOG.md`. Quoted step name (colon inside parens) to keep YAML parse-safe per Phase 27-04 precedent.

- `tests/eval/test_check_real_corpus_mode.py` — 9 tests covering:
  - YAML parses via `yaml.safe_load`.
  - Step with name matching the regex `Real-corpus calibration freshness gate` exists (exactly one).
  - `if` expression contains both `schedule` and `workflow_dispatch` but NOT `pull_request`.
  - `run` body invokes `recalibrate_thresholds` + `--check-only` + explicit `--lock-path` / `--log-path`.
  - Step ordering: canary < gate < post-scorecard.
  - Subprocess CLI tests: small corpus → exit 1 + `fewer than 6 sessions`; stale log (empty) → exit 1 + freshness reason; old entry (45 days) → exit 1 + `stale recalibration log`; fresh both → exit 0 + `CHECK_REAL_CORPUS_OK`.

**Verify:** `uv run pytest tests/eval/test_check_real_corpus_mode.py -q --no-header && uv run python -c "import yaml; yaml.safe_load(open('.github/workflows/eval.yml'))" && echo OK` → `9 passed` + `OK`.

**Done:** ≥6 workflow tests pass (actual: 9), eval.yml still YAML-parses, new step lives between nightly-canary and post-scorecard, `--check-only` invocation exits as designed for all three coverage paths.

## Verification Results

| Plan verification step | Status |
|---|---|
| `uv run pytest tests/eval/test_recalibrate_thresholds.py tests/eval/test_check_real_corpus_mode.py -q` | 28 passed |
| `uv run pytest tests/eval/ -q --no-header` (Phase 27 regression) | 169 passed, 1 pre-existing failure (see Deviations) |
| THRESHOLD-LOCK.md md5 before/after run with synthetic out-of-tolerance corpus | `37addcfe45c9553a7efbf61714a48feb` unchanged (pinned by `test_script_never_writes_to_lock_file`) |
| `yq '.jobs.eval.steps[].name' .github/workflows/eval.yml \| grep "Real-corpus"` (Python equivalent) | `Real-corpus calibration freshness gate (Phase 42 GATE-04)` |
| `grep -E "verdict=(in_tolerance\|out_of_tolerance\|schema_example)" eval/THRESHOLD-RECALIBRATION-LOG.md` | `### 1970-01-01T00:00:00Z — verdict=schema_example` |

## Success Criteria

- [x] `scripts/eval/recalibrate_thresholds.py` shipped with ±0.10 tolerance band + audit log writer + `--check-only` mode
- [x] `eval/THRESHOLD-RECALIBRATION-LOG.md` seeded with schema block
- [x] `.github/workflows/eval.yml` extended with the real-corpus freshness gate (schedule + dispatch only, not PR)
- [x] ≥13 new tests pass across 2 test files (actual: 28)
- [x] THRESHOLD-LOCK.md never auto-mutated — verified by md5 + by explicit test (`test_script_never_writes_to_lock_file`)
- [x] Phase 27 eval baseline untouched (169 prior tests still pass)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] Floating-point boundary drift breaks inclusive ±0.10 band**

- **Found during:** Task 1, running the unit test suite for the first time.
- **Issue:** `compute_delta(0.70, 0.80)` produces `delta = -0.10000000000000009` under CPython 3.12 IEEE-754 doubles (representation error of ~8e-17). The plan's `test_compute_delta_on_boundary` requires `|±0.10|` to classify inclusively as `in_tolerance`, but `abs(-0.10000000000000009) > 0.10` flipped the verdict to `out_of_tolerance`.
- **Fix:** Added `_TOLERANCE_FLOAT_EPS = 1e-9` constant and changed the band comparison to `abs(delta) <= RECALIBRATION_TOLERANCE + _TOLERANCE_FLOAT_EPS`. The epsilon is 10⁸ × larger than the actual drift, so it cleanly classifies boundary cases without admitting anything meaningfully out of band. Documented in module docstring + inline comment.
- **Files modified:** `scripts/eval/recalibrate_thresholds.py`.
- **Commit:** `e6d358a` (included in Task 1).

### Pre-existing Out-of-Scope Failure

- **Test:** `tests/eval/test_corpus_diversity_gate.py::test_each_session_has_events_jsonl_file`
- **Status:** Already documented in `.planning/phases/42-hallucination-gate-v3-hybrid/deferred-items.md` as a Plan 42-01 deferral. Failure pre-dates Plan 42-02 — closure path is Kaan's GATE-03 corpus-acquisition discharge runbook. Out of scope for this plan.

## Threat Surface

| Threat ID | Disposition | Implementation |
|---|---|---|
| T-42-02-01 (autonomous lock edit) | mitigate | `test_script_never_writes_to_lock_file` pins md5 invariance after full out-of-tolerance run; script's only LOCK_PATH operation is read-only `parse_threshold_lock_frontmatter`. |
| T-42-02-02 (audit log mutation) | mitigate | `append_audit_entry` uses append-only file mode (`"a"`); `test_append_audit_entry_is_append_only` pins 3-entry sequential append preserves header + ordering. |
| T-42-02-03 (response-text disclosure) | mitigate | `_parse_eval_report` actively `pop`s forbidden response-text fields and only reads numeric metrics; subprocess invocation isolates the harness's stdout from the parser. |
| T-42-02-04 (timestamp spoofing) | accept | Single-machine `datetime.now(timezone.utc)`; no signing required for internal audit. |
| T-42-02-05 (replay-cost DoS) | mitigate | `--check-only` skips replay_harness entirely; full recalibration is operator-discharged (nightly canary only). |

## Self-Check: PASSED

**File existence:**
- `scripts/eval/recalibrate_thresholds.py` — FOUND
- `eval/THRESHOLD-RECALIBRATION-LOG.md` — FOUND
- `tests/eval/test_recalibrate_thresholds.py` — FOUND
- `tests/eval/test_check_real_corpus_mode.py` — FOUND
- `.github/workflows/eval.yml` — FOUND (modified)

**Commit existence:**
- `e6d358a` — FOUND (Task 1: recalibrate_thresholds.py + ±0.10 tolerance band + audit log seed)
- `e6caeab` — FOUND (Task 2: extend eval.yml + workflow tests)

**Test execution:** 28 new tests pass (19 + 9); 169 Phase 27 prior tests still pass; 1 pre-existing failure documented in deferred-items.md is out of scope.
