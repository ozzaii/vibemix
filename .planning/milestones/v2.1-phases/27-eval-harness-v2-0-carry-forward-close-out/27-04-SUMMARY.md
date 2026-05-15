---
phase: 27-eval-harness-v2-0-carry-forward-close-out
plan: 04
subsystem: eval-harness
tags: [eval-06, eval-07, eval-08, ci-gate, threshold-lock]
requires:
  - phase: 27
    provides: Plans 27-01 (replay_harness) + 27-02 (judges) + 27-03 (corpus skeleton)
provides:
  - eval/THRESHOLD-LOCK.md autonomous-signed lock with CONTEXT EVAL-06 thresholds
  - scripts/eval/threshold_lock.py parser (yaml.safe_load V5 ASVS) + autonomous_sign
  - .github/workflows/eval.yml GHA workflow (PR + nightly + dispatch)
  - replay_harness --threshold-lock wire-in
  - .planning/eval-runs/ tracking + .gitignore prune rules
affects:
  - All future PRs (gated by eval workflow)
  - Phase 28+ (nightly canary keeps the gate calibrated)
tech-stack:
  added: []
  patterns:
    - "yaml.safe_load gated (NEVER yaml.load — V5 ASVS)"
    - "Autonomous-sign with idempotent re-sign + KAAN-ACTION-LEGAL.md audit append"
    - "PR-mode = Flash only + VCR cassettes ($0); nightly = Pro + Flash + new_episodes (~$1-2/night)"
    - "Pitfall P46 audit grep on every workflow run (no apple/signpath POST/PUT)"
    - "[skip-eval] PR title bypass for docs-only PRs"
requirements-completed:
  - EVAL-06
  - EVAL-07
  - EVAL-08
duration: ~20 min
completed: 2026-05-15
---

# Phase 27 Plan 04: CI Eval Gate + Threshold Lock Summary

**Ships the v2.1 ship-gate. Every PR runs the autonomous-proxy hallucination gate (Flash + cassettes, $0). Every night the Pro+Flash canary refreshes cassettes against real Gemini API. THRESHOLD-LOCK.md autonomous-signed; re-tuning requires re-running both judges first.**

## Performance

- **Duration:** ~20 min
- **Files created:** 5 (threshold-lock + threshold_lock.py + eval.yml + .gitkeep + test_threshold_lock.py)
- **Files modified:** 4 (replay_harness.py + .gitignore + KAAN-ACTION-LEGAL.md + (none more))
- **Tests added:** 11 (97 total in tests/eval/, all passing in 1.44s)

## Accomplishments

- `eval/THRESHOLD-LOCK.md` autonomous-signed with `kaan_signed: autonomous_phase27` + ISO8601 timestamp. CONTEXT EVAL-06 thresholds (f1_min=0.80, substance_min=0.65, cited_cosine_min=0.4, bypass_max=0.15, per_genre_f1_min=0.70). Re-tuning protocol + Pitfall cross-references in the body.
- `scripts/eval/threshold_lock.py`: parser uses `yaml.safe_load` (V5 ASVS), `is_signed()` boolean, `autonomous_sign()` with idempotency + KAAN-ACTION-LEGAL.md audit append. `DEFAULT_THRESHOLDS` constant kept in sync.
- `scripts/eval/replay_harness.py` extended: `--threshold-lock <path>` arg now consumed by `_load_thresholds()` — falls back to DEFAULT_THRESHOLDS when omitted. Empty corpus path also uses the lock.
- `.github/workflows/eval.yml`: PR + nightly cron + workflow_dispatch triggers. PR mode runs `--judges gemini-3-flash` with `VCR_RECORD_MODE=none` (cassettes only). Nightly canary runs `--judges gemini-3-pro,gemini-3-flash` with `VCR_RECORD_MODE=new_episodes` (real API + refreshes cassettes). PR comment via actions/github-script. Nightly commit via vibemix-eval-bot. Pitfall P46 audit grep. AIza scrub on cassettes. Threshold-lowering diff guard.
- `.planning/eval-runs/.gitkeep`: tracked dir for nightly canary scorecards. PR scorecards stay ephemeral (gitignored via `*/scorecard.preview.md`).
- 11 new tests cover the parser, safe_load enforcement (V5 ASVS), signature lifecycle (is_signed + autonomous_sign + idempotency), replay_harness CLI integration, Pitfall cross-reference in the body.

## Task Commits

1. **Task 1+2 combined: threshold-lock + parser + replay_harness wire-in + eval.yml + tests** — `c41c72c` (feat)

## Decisions Made

- **Autonomous sign with `kaan_signed: autonomous_phase27` (not `false` → `true`).** This string is distinguishable from a real signature in audit. The KAAN-ACTION-LEGAL.md Item documents "review when convenient" — explicitly NOT a legal-capacity signature.
- **eval.yml posts to PR via actions/github-script@v7** instead of a custom action. Per RESEARCH §Pattern 6: github-script's built-in `github.rest.issues.createComment` is the well-supported path; no extra deps.
- **Combined Tasks 1+2 into one commit.** The lock file + parser + harness wire-in + workflow + KAAN-ACTION audit + tests are tightly coupled; separating would produce a half-broken intermediate where the workflow references a parser that doesn't exist yet.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - YAML name with colon] eval.yml workflow YAML parse error**
- **Found during:** Task 2 — yaml.safe_load validation of the workflow file
- **Issue:** Initial workflow had `- name: Threshold-lowering diff guard (Pitfall: tampering)` — the colon inside the parenthesized name confused the YAML parser at line 118.
- **Fix:** Quoted the name: `- name: "Threshold-lowering diff guard (Pitfall tampering)"`. Same intent, parse-safe.
- **Files modified:** `.github/workflows/eval.yml`
- **Verification:** `uv run python -c "import yaml; yaml.safe_load(open('.github/workflows/eval.yml'))"` succeeds.
- **Committed in:** `c41c72c`

**Total deviations:** 1 auto-fixed (YAML syntax). **Impact:** No semantic change — workflow runs identically.

## Verification

```bash
# Lock file integrity
test -f eval/THRESHOLD-LOCK.md
grep -q "kaan_signed: autonomous_phase27" eval/THRESHOLD-LOCK.md

# Parser (V5 ASVS — yaml.safe_load)
uv run python -c "from scripts.eval.threshold_lock import parse_threshold_lock_frontmatter, is_signed, DEFAULT_THRESHOLDS; from pathlib import Path; r=parse_threshold_lock_frontmatter(Path('eval/THRESHOLD-LOCK.md')); assert r['thresholds']['f1_min'] == 0.80; assert is_signed(r); assert DEFAULT_THRESHOLDS['per_genre_f1_min'] == 0.70"

# KAAN-ACTION-LEGAL audit entry
grep -q "THRESHOLD-LOCK autonomous-signed" .planning/phases/27-eval-harness-v2-0-carry-forward-close-out/KAAN-ACTION-LEGAL.md

# replay_harness consumes the lock
uv run python -m scripts.eval.replay_harness --corpus tests/eval/fixtures --judges noop --threshold-lock eval/THRESHOLD-LOCK.md --output /tmp/p27-04-final
test -f /tmp/p27-04-final/eval_report.json

# Workflow YAML parses
uv run python -c "import yaml; yaml.safe_load(open('.github/workflows/eval.yml'))"

# All eval tests pass
uv run pytest tests/eval/ -x  # 97 passed in 1.44s
```

## Self-Check: PASSED

- [x] All 9 plan-level success criteria met (with 1 documented Rule 1 deviation for YAML syntax)
- [x] threshold_lock.py uses yaml.safe_load (V5 ASVS verified by test)
- [x] eval.yml workflow YAML parses cleanly
- [x] eval.yml Pitfall P46 audit step grep-asserts no apple/signpath POST/PUT
- [x] PR comment via actions/github-script@v7
- [x] Nightly canary commits via vibemix-eval-bot
- [x] [skip-eval] PR title bypass present
- [x] AIza scrub on cassettes
- [x] Threshold-lowering diff guard

## Next Plan Readiness

**Phase 27 complete.** v2.1 RC eval gate is operational:
- PRs gated by `eval.yml` (Flash + cassettes, $0)
- Nightly canary refreshes cassettes + commits per-run scorecards
- KAAN-ACTION-LEGAL.md tracks the 4 deferred items (cassette recording, Apple/SignPath, ack_bank residual 20, corpus WAV acquisition)

The autonomous-proxy hallucination gate is now the merge gate for every PR in milestone v2.1.
