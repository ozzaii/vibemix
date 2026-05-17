---
phase: 42-hallucination-gate-v3-hybrid
plan: 06
subsystem: docs
tags: [eval, hallucination-gate, public-docs, privacy, hybrid-gate, threshold-mirror, redaction]

# Dependency graph
requires:
  - phase: 42-hallucination-gate-v3-hybrid
    provides: corpus scaffolding (42-01), recalibrate_thresholds + audit log (42-02), EAR-TEST-PROTOCOL + schema + check_ear_test.sh (42-03), check_gate.sh + cut_release.sh Gate-2 wire-in (42-04), P85 override retirement decision log (42-05)
  - phase: 27-eval-harness-v2-0-carry-forward-close-out
    provides: THRESHOLD-LOCK.md, replay_harness.py, judge rubrics (judge_pro.md + judge_flash.md), corpus MANIFEST + LICENSES
provides:
  - eval/README.md — public-facing v3.0 hybrid hallucination gate documentation
  - tests/eval/test_eval_readme_public_facing.py — 16 section-coverage + threshold-mirror tests
  - tests/eval/test_eval_readme_redacts_ear_test_content.py — 5 privacy contract tests (3 skip cleanly pre-§GATE-05)
affects: [v3.0-public-release, OSS-contributor-onboarding, threshold-drift-detection, ear-test-privacy]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Public docs mirror locked thresholds verbatim — drift detection via parametrized pytest"
    - "Rubric-leak smoke test self-updates: sentinels derived from first-meaningful-chunk of judge_pro.md + judge_flash.md (no hardcoded prompt strings)"
    - "Privacy contract tests skip-cleanly when source data absent (pre-discharge state) but trigger on every CI run once data lands"

key-files:
  created:
    - eval/README.md
    - tests/eval/test_eval_readme_public_facing.py
    - tests/eval/test_eval_readme_redacts_ear_test_content.py
  modified: []

key-decisions:
  - "Anti-slop manifesto target: cross-link the project root README.md (line 33 — 'A real DJ friend in your ear — no AI slop') rather than create a new docs/ASLOP-MANIFESTO.md file. CONTEXT D-GATE-09 said 'cross-link the manifesto'; existing public surface satisfies that without doc proliferation."
  - "Rubric-leak sentinel derivation: read rubric file → strip YAML frontmatter → skip blank/HTML-comment lines → first ~40 chars of meaningful body. Self-updating against rubric evolution (PLAN's explicit prescription)."
  - "Privacy tests use pytest.skip with informative message when eval/ear-test-logs/ is empty (pre-§GATE-05 state) rather than vacuous-true asserting; this surfaces the discharge gap to the test runner without producing false-green coverage."
  - "Threshold mirror normalization: format locked floats to 2-decimal-place strings (0.4 → 0.40) so the parametrized test catches both numeric drift AND format drift in the README table."

patterns-established:
  - "Public-OSS doc threshold mirror: locked values appear verbatim in both the policy file and the public doc; test loads the policy and asserts presence in the doc per key. Future numeric drift breaks CI."
  - "Sentinel-derived prompt-leak detection: tests derive their leak tokens from the actual rubric files at runtime, removing the hardcoded-sentinel maintenance burden documented in Phase 27."

requirements-completed: [GATE-09]

# Metrics
duration: 7m
completed: 2026-05-16
---

# Phase 42 Plan 06: Public-Facing Eval Documentation Summary

**Public-facing `eval/README.md` for the v3.0 hybrid hallucination gate — documents fast-lane (autonomous proxy 2-judge cross-check) + slow-lane (Kaan ear-test) regime, mirrors 5 locked thresholds verbatim from THRESHOLD-LOCK.md, cross-links protocol + decision log + replay harness, redacts all ear-test session content per `feedback_privacy_scope_narrow`, pinned by 21 new tests across 2 files.**

## Performance

- **Duration:** 7 min (389s)
- **Started:** 2026-05-16T15:25:52Z
- **Completed:** 2026-05-16T15:32:21Z
- **Tasks:** 3 / 3
- **Files created:** 3
- **Files modified:** 0
- **Tests added:** 21 (18 pass + 3 skip-cleanly)

## Accomplishments

- **eval/README.md shipped** — 163 lines (under the 350-line single-page scannability budget), 10 sections per the PLAN structure spec, public-OSS tone, zero Kaan-private content
- **Threshold mirror pinned** — 5 locked values from `eval/THRESHOLD-LOCK.md` appear verbatim in the README's "Threshold Values" table; parametrized test detects drift per key
- **2-judge architecture documented** — names both `judge_pro` (Gemini 3 Pro) + `judge_flash` (Gemini 3 Flash), describes `min()` aggregation collusion mitigation, links rubric bodies in `eval/rubrics/` rather than inlining prompts
- **Ear-test protocol shape documented (content redacted)** — describes 30 min minimum, ≥ 2 genres in 14d window, 4 slop-flag taxonomy; explicit REDACTED statement keeps individual sessions out of public doc
- **Reproducibility one-liner ships** — copy-pasteable `uv sync + pytest tests/eval/ + replay_harness --judges noop` works against synthetic fixtures with zero Gemini API spend
- **History documented** — v2.1 P85 override → v3.0 hybrid transition cross-linked to `.planning/decisions/P85-OVERRIDE-RETIRED.md`
- **Anti-feature carveouts shipped** — no aggressive autonomous judge replacement, no cross-DJ in v3.0, no ear-test gamification
- **Privacy contract enforced by tests** — `free_form` text + `session_id` + `signed_at` from `eval/ear-test-logs/*.json` cannot land in README; test iterates every log file (skips cleanly while §GATE-05 outstanding, fires automatically once Kaan discharges)
- **Rubric leak guard self-updating** — sentinels derived at test-time from `judge_pro.md` + `judge_flash.md` first-meaningful-chunk (no hardcoded prompt strings — removes Phase 27's documented maintenance burden)

## Task Commits

Each task was committed atomically on `worktree-agent-a99aeb07615be4155`:

1. **Task 1: Write eval/README.md public-facing documentation** — `357b5c6` (docs)
2. **Task 2: Section-coverage + threshold-mirror tests for eval/README.md** — `94a777d` (test)
3. **Task 3: Privacy contract test — README cannot leak ear-test log content** — `b628f36` (test)

## Files Created/Modified

- `eval/README.md` (163 lines) — public-facing hybrid hallucination gate doc; mirrors locked thresholds verbatim; cross-links all dependency artifacts from Plans 42-01..05 + Phase 27
- `tests/eval/test_eval_readme_public_facing.py` (219 lines) — 16 tests; parametrized threshold-mirror across 5 keys + section coverage + rubric-leak smoke
- `tests/eval/test_eval_readme_redacts_ear_test_content.py` (182 lines) — 5 tests; iterates ear-test log files, asserts `free_form` / `session_id` / `signed_at` redaction + positive policy assertion + schema-exclusion sanity

## Decisions Made

- **Anti-slop manifesto target = project root README.md** (line 33: "A real DJ friend in your ear — no AI slop"). Did NOT create a new `docs/ASLOP-MANIFESTO.md`. The PLAN's interfaces block said "cross-link to the actual link target verified in Task 1's Bash probe"; the probe found the manifesto statement on the root README, so the worktree-local link `../README.md#what-it-does` is the canonical target.
- **Privacy tests use pytest.skip when no logs exist** (not vacuous-true). Surfaces the §GATE-05 outstanding state in CI output without producing false-positive green coverage; the contract still holds and will fire once data lands.
- **Threshold mirror normalization to 2-decimal-place strings** (`0.4 → "0.40"`). Catches both numeric drift AND README table format drift.
- **Rubric body inlined into README is explicitly forbidden** (per PLAN's "Tone" guidance). Sentinel-derived smoke test enforces this. Rubrics live in `eval/rubrics/` as the single source of truth.

## Deviations from Plan

**Total deviations:** 1 environmental workaround (no code/scope change)

### Environmental Workaround (not a deviation rule)

**1. [Tooling] Write tool absolute-path drift to main repo on Task 1**
- **Found during:** Task 1 (initial `eval/README.md` write)
- **Issue:** The first Write call with an absolute worktree path (`/Users/ozai/projects/dj-set-ai/.claude/worktrees/agent-a99aeb07615be4155/eval/README.md`) reported success but the file landed at the main-repo path (`/Users/ozai/projects/dj-set-ai/eval/README.md`). This is exactly the `#3099` bug flagged in the executor preamble — absolute paths constructed in orchestrator context can silently resolve to the main repo from a worktree.
- **Fix:** Copied the README content to `/tmp`, removed the misplaced file from main repo (`rm` — main repo had no commit risk, file was untracked there), `cp` to the correct worktree path. Subsequent Writes for Tasks 2 + 3 landed correctly without re-occurrence.
- **Files affected:** none — only the intermediate misplaced file at main-repo `eval/README.md` (cleaned up before any commit, never reached main-repo HEAD).
- **Verification:** `git rev-parse --show-toplevel` confirms `worktree-agent-a99aeb07615be4155` root after the cleanup; the Task 1 commit `357b5c6` correctly applies inside the worktree.
- **Impact:** Zero — no scope change, no plan change, no rule triggered. Documented here because the executor preamble specifically asks for #3099-class issues to be surfaced.

## Issues Encountered

- **Write tool absolute-path drift (#3099)** — documented above as environmental workaround. Resolved cleanly with `cp`-based salvage before any commit hit either repo.

## Pre-Existing Out-of-Scope Failures (Deferred)

Per the executor SCOPE BOUNDARY rule, the following pre-existing failures are documented but NOT fixed by this plan:

1. **`tests/eval/test_corpus_diversity_gate.py::test_each_session_has_events_jsonl_file`** — pre-existing failure from Phase 27-03 commit `5a7ee8b`. `eval/corpus/sessions/hard_tek_01/events.jsonl` does not exist because the real corpus WAV + events bundle is a **Kaan-discharge** item (`.planning/KAAN-ACTION-LEGAL.md §GATE-03`). Not 42-06 scope.
2. **LFS pointer drift on `tauri/ui/assets/mascot/animations/*.glb` + `tests/library/fixtures/synthetic_*` files** — pre-existing worktree state, unrelated to eval docs. Not 42-06 scope.

Neither item blocks the GATE-09 plan from completing per its own success criteria.

## Threat Surface Scan

No new threat surface introduced. README is read-only docs + tests are read-only assertions. The PLAN's `<threat_model>` mitigations (T-42-06-01..05) are all covered by the shipped tests:

| Threat ID | Mitigation | Status |
|-----------|------------|--------|
| T-42-06-01 (free_form leak)  | `test_no_free_form_text_in_readme` iterates every log | shipped (skip-cleanly pre-§GATE-05) |
| T-42-06-02 (session_id leak) | `test_no_session_id_specific_anecdotes_in_readme`     | shipped (skip-cleanly pre-§GATE-05) |
| T-42-06-03 (threshold drift) | `test_readme_threshold_values_match_lock_file` × 5    | shipped + passing |
| T-42-06-04 (rubric body leak) | `test_readme_no_inline_rubric_or_prompt_bodies`      | shipped + passing |
| T-42-06-05 (redaction silent) | `test_readme_does_document_redaction_explicitly`     | shipped + passing |

## Verification Results

```
test_eval_readme_public_facing.py            ........ 16 passed
test_eval_readme_redacts_ear_test_content.py  sss..    2 passed, 3 skipped (cleanly — no logs yet)

Full tests/eval/ baseline (excluding pre-existing GATE-03 failure):
212 passed, 5 skipped in 3.31s — zero regressions
```

Plan-named verification block (all OK):

```
[ok] eval/README.md exists
[ok] eval/THRESHOLD-LOCK.md
[ok] eval/EAR-TEST-PROTOCOL.md
[ok] eval/THRESHOLD-RECALIBRATION-LOG.md
[ok] .planning/decisions/P85-OVERRIDE-RETIRED.md
[ok] scripts/release/check_gate.sh
[ok] scripts/release/check_ear_test.sh
[ok] scripts/eval/replay_harness.py
[ok] eval/corpus/MANIFEST.md
[ok] eval/corpus/LICENSES.md
[ok] eval/rubrics
```

## User Setup Required

None — `eval/README.md` is purely additive documentation, no env vars, no service config. The implied OSS-contributor `uv sync` step is already documented in the README itself.

## Next Phase Readiness

**Phase 42 close-out ready.** All 6 plans (42-01 → 42-06) have shipped. Wave 5 was the documentation wave; with this plan landing:

- v3.0 hybrid hallucination gate is engineering-complete
- Public-facing docs are scannable + tested
- Privacy contract is self-enforcing (CI fires the redaction tests once §GATE-05 ear-test logs land)
- Threshold drift is auto-detected on every PR

**Outstanding Kaan-discharge items** (per `.planning/KAAN-ACTION-LEGAL.md`, not 42-06 scope):
- §GATE-01: ack-bank top-up (20/40 → 40/40) one-liner Gemini TTS call (~$0.10)
- §GATE-02: VCR cassette recording one-liner
- §GATE-03: 6 × 30-min DJ session WAVs to LFS + per-session events.jsonl
- §GATE-05: first ear-test session sign-off via debrief toggle

None of these block the v3.0 release-gate scaffolding from being green-buildable; they are the human-loop discharges the autonomous-mode plan was designed to defer per `feedback_autonomous_no_grey_area_pause`.

## Self-Check: PASSED

- [x] `eval/README.md` exists and is committed (`357b5c6`)
- [x] `tests/eval/test_eval_readme_public_facing.py` exists and is committed (`94a777d`)
- [x] `tests/eval/test_eval_readme_redacts_ear_test_content.py` exists and is committed (`b628f36`)
- [x] All 3 commits visible in `git log --oneline`
- [x] No deletions in any commit (verified post-commit deletion check)
- [x] Zero regressions on Phase 27 + 42 baseline (212/212 passing modulo pre-existing §GATE-03 failure)

---
*Phase: 42-hallucination-gate-v3-hybrid*
*Completed: 2026-05-16*
