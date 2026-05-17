---
phase: 45-external-discharge-public-rc-publish
plan: 04
subsystem: release
tags: [release, audit, ship-13, decision-report, telemetry, t-plus-30, gh-cli, bravoh-healthz, ear-test, hermetic-fixtures]

# Dependency graph
requires:
  - phase: 42-hybrid-hallucination-gate
    provides: ear-test-logs/*.json schema (D-GATE-05; consumed by audit's ear-test source)
  - phase: 42-hybrid-hallucination-gate
    provides: scripts/release/check_ear_test.sh (audit's evidence-source-3 pattern reused)
  - phase: 44-launch-positioning-and-pre-stage
    provides: launch-rotation.md (audit cites it as the catastrophic-pause rotation doc)

provides:
  - "SHIP-V1-DECISION audit script — at T+30 pre-fills `.planning/decisions/v3.0-SHIP-V1-DECISION.md` from 4 evidence sources (GH releases telemetry, Bravoh /vibemix/healthz uptime, ear-test logs, GH issues) so Kaan only signs off on the 3-way verdict (cut v1.0.0 / cycle v3.0.0-rc2 / pause)"
  - "Canonical SHIP-V1-DECISION-TEMPLATE.md schema — 4 H3 evidence sections, 5-row Kaan-discharge rubric (Downloads / Uptime / Slop / Crash / Anti-slop), 3-way decision checkbox, sign-off block"
  - "5 synthetic-telemetry fixtures (gh_releases.json + healthz_uptime.csv + gh_issues.json + 2 ear_test_log_*.json) — hermetic CI mode never hits real GH or Bravoh"
  - "T-45-04-{01..05} threat mitigations: numeric-only substitution (no markdown injection), zero ear-test free_form leak, _generated_by provenance comment, read-only gh argv list, atomic tempfile+os.replace write"
  - "Plan 45-06 §SHIP-13 runbook ready to cite literal T+30 invocation (--live + --bravoh-healthz-stats-url)"

affects: [45-06-kaan-action-legal-runbooks, future-v3.x-bake-cycles, SHIP-13-discharge]

# Tech tracking
tech-stack:
  added:
    - "argparse + dataclass-free dict aggregation pattern for release-tooling Python scripts"
    - "stdlib-only --live HTTP path (urllib.request) — zero new runtime deps"
  patterns:
    - "Fixture-first hermetic-mode + --live env-gating (mirrors check_bravoh_org_ready.sh + post_discord_launch.py dry-run defaults from Phase 44)"
    - "Atomic write via tempfile.mkstemp + os.replace (mirrors Phase 27 sign-manifest pattern)"
    - "Audit-provenance HTML comment in generated reports (T-45-04-03; new pattern for v3.x decision-of-record docs)"

key-files:
  created:
    - "scripts/release/audit_ship_v1_decision.py (610 lines — argparse CLI + 4 fixture/live loaders + aggregate + render + atomic write + gh CLI preflight)"
    - "docs/SHIP-V1-DECISION-TEMPLATE.md (68 lines — locked schema for decision report)"
    - "tests/release/__init__.py (pytest discovery)"
    - "tests/release/test_audit_ship_v1_decision.py (665 lines — 20 pin tests, hermetic by default)"
    - "tests/release/fixtures/synthetic_telemetry/gh_releases.json (synthetic 231 downloads, 142 DMG + 89 MSI)"
    - "tests/release/fixtures/synthetic_telemetry/healthz_uptime.csv (15 rows, 14 ok + 1 fail = 93.33% uptime)"
    - "tests/release/fixtures/synthetic_telemetry/gh_issues.json (7 issues; 2 crash-labelled)"
    - "tests/release/fixtures/synthetic_telemetry/ear_test_log_1.json (techno, clean)"
    - "tests/release/fixtures/synthetic_telemetry/ear_test_log_2.json (hard_tek, felt_slop=true + felt_late=true)"
    - "tests/release/fixtures/synthetic_telemetry/.gitkeep (dir present at Task 1 RED)"
  modified: []

key-decisions:
  - "Audit pre-fills evidence sections + 4 of 5 rubric rows; Kaan manually fills the 5th (Anti-slop community reports) + the 3-way decision checkbox at T+30. Audit NEVER decides — auto-cycle is explicitly out per CONTEXT §SHIP-V1-DECISION."
  - "Hermetic-by-default: --fixtures dir is the CI mode; --live is the T+30 Kaan-discharge mode. Zero real network in test suite (20/20 tests are subprocess.run-monkeypatched + urllib-monkeypatched)."
  - "Stdlib-only --live HTTP: urllib.request for Bravoh healthz, gh CLI subprocess for GH. No new runtime deps (no requests / httpx pulled in just for one one-shot audit script)."
  - "Bravoh healthz dual fallback: --bravoh-healthz-stats-url URL preferred; --bravoh-healthz-csv path fallback. Plan 45-06 §SHIP-13 runbook picks one based on whatever the Bravoh team's healthz cron exposes."
  - "VIBEMIX_AUDIT_DATE_OVERRIDE env enables byte-deterministic re-runs in CI (Test 12 + Test 20)."
  - "Plan 42-06 privacy contract preserved: ear-test free_form text + session_id + signed_at NEVER appear in the rendered decision report — only aggregate counts (felt_slop count, felt_scripted count, genres_csv)."

patterns-established:
  - "Hermetic fixture mode + --live env-gating pattern for release-audit Python scripts (reusable for future v3.x SHIP-V2-DECISION + v4 audits)"
  - "Audit-provenance HTML comment (_generated_by:) — surfaces in rendered docs to prove the audit ran (vs. Kaan hand-filling). T-45-04-03 mitigation pattern."
  - "Read-only gh subprocess argv list — never include --method POST/PATCH/DELETE; T-45-04-05 mitigation pattern reusable for future release-tooling that touches GH."

requirements-completed: [SHIP-13]

# Metrics
duration: 28min
completed: 2026-05-17
---

# Phase 45 Plan 04: SHIP-V1-DECISION Audit Script + Template + Synthetic-Telemetry Fixtures Summary

**Python audit script that at T+30 pre-fills the v3.0 SHIP-V1-DECISION report from 4 evidence sources (GH releases, Bravoh healthz, ear-test logs, GH issues) — Kaan signs off on the 3-way verdict instead of hand-collating data from 4 dashboards.**

## Performance

- **Duration:** ~28 min
- **Started:** 2026-05-17T07:40:24Z
- **Completed:** 2026-05-17T08:09:00Z (approx)
- **Tasks:** 3 (all auto, all TDD)
- **Files created:** 10 (template + audit + 5 fixtures + tests + __init__ + .gitkeep)
- **Files modified:** 0 (all-new surface)
- **Tests:** 20/20 GREEN

## Accomplishments

- Canonical `docs/SHIP-V1-DECISION-TEMPLATE.md` shipped — locked structure with 4 evidence sections + 5-row Kaan-discharge rubric + 3-way decision checkbox + Kaan sign-off block. Both audit script AND Plan 45-06 §SHIP-13 runbook cite this schema.
- `scripts/release/audit_ship_v1_decision.py` (610 lines) operates in two modes:
  1. **Fixture mode** (CI / dev): `--fixtures DIR` reads 5 synthetic JSON/CSV files; zero network.
  2. **--live mode** (T+30 Kaan-discharge): `gh` subprocess for GH releases + issues, stdlib `urllib.request` for Bravoh `/vibemix/healthz/stats`, with CSV fallback. Requires `GITHUB_TOKEN` env; exits 2 with documented stderr otherwise.
- 5 synthetic-telemetry fixtures land hermetic CI runs in <0.5s — including a deliberately-bad-uptime scenario (93.33%) + a flagged ear-test (felt_slop=true) so the rubric "Current" cells exercise the failure path.
- 20-test pin contract covers template schema, RED/GREEN boundary, fixture aggregation, --live subprocess argv, URL→CSV fallback chain, GH Actions notice annotation, atomic tempfile-replace write, and re-run idempotency.
- Threat-model mitigations T-45-04-01 through T-45-04-05 all enforced via tests + code (numeric-only substitution, ear-test PII never leaked, `_generated_by:` provenance comment, read-only gh argv, atomic write).
- Plan 45-06 §SHIP-13 runbook has a literal T+30 invocation ready to embed verbatim.

## Task Commits

Each task was committed atomically on `plan-45-04` feature branch (off `main` at f1700db / post-45-05-merge 198f30c):

1. **Task 1 (RED):** test(45-04): pin SHIP-V1-DECISION-TEMPLATE.md schema + fixtures dir — `c822baa`
   - Authored template + 20 pin tests (Tests 1-7 GREEN at RED gate; Tests 8-20 FAIL until script lands).
2. **Task 2 (GREEN-fixture+live):** feat(45-04): audit_ship_v1_decision.py fixture-mode + template pre-fill + 5 synthetic fixtures — `c3185ab`
   - Authored audit script (argparse, fixture loaders, --live loaders, aggregate, render, atomic write) + 5 synthetic fixtures.
   - 18/20 tests GREEN after first run; 2 test-vs-script alignment fixes (gh argv-detection + ::notice prefix).
3. **Task 3 (GREEN-polish):** feat(45-04): --live gh preflight + friendly install error (Rule 2 — correctness) — `8838f55`
   - Added `_require_gh_cli()` preflight: `--live` without `gh` on PATH surfaces a single-line install error instead of opaque FileNotFoundError. Updated Tests 16+17+20 subprocess stubs to answer `gh --version`.

**Plan metadata commit (this SUMMARY + state):** will land in the final merge below.

_Note: Plan 45-04 is a 3-task TDD plan. RED gate (`c822baa`) + GREEN gates (`c3185ab` + `8838f55`) preserved in commit-order; `git log` shows the canonical test → feat progression._

## Files Created/Modified

- `docs/SHIP-V1-DECISION-TEMPLATE.md` — canonical decision schema (locked structure; reordering breaks audit + §SHIP-13 runbook).
- `scripts/release/audit_ship_v1_decision.py` — argparse CLI + fixture/live loaders + aggregate + render + atomic write.
- `tests/release/__init__.py` — pytest discovery anchor.
- `tests/release/test_audit_ship_v1_decision.py` — 20 pin tests, hermetic by default.
- `tests/release/fixtures/synthetic_telemetry/gh_releases.json` — synthetic v3.0.0-rc1 release with 2 assets (231 aggregate downloads).
- `tests/release/fixtures/synthetic_telemetry/healthz_uptime.csv` — 15 rows demonstrating 93.33% (RED-zone) uptime.
- `tests/release/fixtures/synthetic_telemetry/gh_issues.json` — 7 issues with 2 crash-labelled (1 open + 1 closed).
- `tests/release/fixtures/synthetic_telemetry/ear_test_log_1.json` — techno session, all slop flags false.
- `tests/release/fixtures/synthetic_telemetry/ear_test_log_2.json` — hard_tek session, felt_slop=true + felt_late=true.
- `tests/release/fixtures/synthetic_telemetry/.gitkeep` — dir presence anchor (Task 1 RED).

## Decisions Made

- **Hermetic-first audit:** CI mode is `--fixtures DIR`, NOT `--live`. The `--live` mode is a Kaan-discharge convenience for T+30; all 20 tests run in fixture mode so PR CI never costs a gh API call or a Bravoh server probe. This mirrors the Phase 44 `check_bravoh_org_ready.sh` pattern (network calls behind `--live` flag, dry-run default).
- **Stdlib-only --live HTTP:** Bravoh healthz uses `urllib.request` not `httpx` / `requests`. No new runtime dep just for one one-shot audit script. The gh CLI is already a Kaan-machine prerequisite per `gh release create` in §SHIP-03.
- **VIBEMIX_AUDIT_DATE_OVERRIDE env for determinism:** Test 12 + Test 20 pin byte-identical re-runs by freezing the audit timestamp. Without this knob, the `_generated_by:` provenance comment + bake-window arithmetic would vary across runs.
- **Audit pre-fills evidence + 4 of 5 rubric "Current" cells; rest is manual:** The Anti-slop community reports row stays `<manual>` because community reports come from Discord / GH discussions / Twitter — not from a single auditable source. Plan 45-06 §SHIP-13 runbook documents the manual fill step.
- **Privacy contract (Plan 42-06):** The audit ONLY emits aggregate counts from ear-test logs (felt_slop count, felt_scripted count, genres covered). The free_form text + session_id + signed_at fields are read by the aggregator but NEVER substituted into the rendered report. Verified: `grep -c "Felt grounded\|breakdown section felt generic" rendered-output → 0`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Template `<audit_date>` placeholder was not in the substitution map**

- **Found during:** Manual `<verification>` step after Task 2 GREEN — first rendered output showed `Bake window: 2026-05-03T08:00:00Z → <audit_date> (13 days)` with the placeholder left literal.
- **Issue:** Template skeleton uses `<YYYY-MM-DD>` for "Audit date:" header AND `<audit_date>` in the "Bake window:" line. My render code substituted the first but not the second.
- **Fix:** Added `text.replace("<audit_date>", audit_date_str)` in `render_report()` + added `<audit_date>` to Test 11's `forbidden_in_evidence` list so the bug can never regress.
- **Files modified:** `scripts/release/audit_ship_v1_decision.py`, `tests/release/test_audit_ship_v1_decision.py`
- **Verification:** Re-ran fixture-mode render; bake-window line now shows `2026-05-03T08:00:00Z → 2026-05-17 (13 days)`.
- **Committed in:** `c3185ab` (Task 2 GREEN commit — caught + fixed before commit landed).

**2. [Rule 2 - Missing Critical] `--live` mode lacked a gh-CLI preflight; opaque FileNotFoundError if `gh` not on PATH**

- **Found during:** Task 3 (code review of --live failure path).
- **Issue:** First-time Kaan-discharge user without `gh` installed would get `FileNotFoundError: [Errno 2] No such file or directory: 'gh'` deep in subprocess. Tracebacks like that are an anti-slop violation in their own right.
- **Fix:** Added `_require_gh_cli()` preflight that runs `gh --version`; surfaces a single-line friendly error with install instructions if the binary is missing. Tests 16/17/20 subprocess.run stubs updated to answer `gh --version` so monkeypatched runs never hit a real PATH.
- **Files modified:** `scripts/release/audit_ship_v1_decision.py`, `tests/release/test_audit_ship_v1_decision.py`
- **Verification:** 20/20 tests still GREEN after the change; manual `--live` invocation without `gh` exits 2 with the documented message.
- **Committed in:** `8838f55` (Task 3 commit — landed as the dedicated polish atomic).

**3. [Out-of-scope inclusion] Parallel-agent files (Plan 45-01) included in Task 2 commit**

- **Found during:** Task 2 GREEN commit — staging area was shared with the parallel Plan 45-01 agent operating in the same working directory (no worktree isolation between Wave-1 plans in this run).
- **Issue:** My explicit `git add` of MY files also picked up `scripts/dist/install_vm_matrix.{json,sh}` + `tests/install/test_install_vm_matrix.py` that the 45-01 agent had staged but not yet committed.
- **Fix:** Per `<scope_boundary>` — left the spurious files in the commit rather than `git rm` them (which would have deleted them from 45-01's disk). Plan 45-01 will merge ITS branch with identical-content blobs; git will detect duplicate content + merge cleanly. Logged here for traceability.
- **Files affected:** None of MY surface (audit script + template + fixtures + tests).
- **Verification:** `git show c3185ab` shows the 3 extra 45-01 files alongside MY 5 fixture files + audit script + test changes. All 45-01 files are byte-identical to commit 60113e0 (45-01 RED) so the eventual 45-01 → main merge will be a no-op for those paths.
- **Note:** This is a CI-pipeline-architecture issue (parallel agents in shared cwd), not a scope-creep issue. Filed for Phase 45 post-mortem; see "Issues Encountered".

---

**Total deviations:** 3 (1 Rule 1 bug, 1 Rule 2 missing-critical, 1 parallel-staging artifact)
**Impact on plan:** Both auto-fixes (Rule 1 + Rule 2) were necessary for correctness. The Rule 1 fix landed inline in Task 2; the Rule 2 fix is exactly what Task 3 was scoped to deliver. Parallel-staging artifact is benign — no rework needed.

## Issues Encountered

- **Parallel agents in shared cwd corrupt staging:** During Task 1, the parallel Plan 45-05 agent in the same `/Users/ozai/projects/dj-set-ai` working directory ran `git checkout main` between my Write tool calls and my `git add` invocation. My on-disk files were wiped + had to be recreated; my first feature-branch checkpoint commit captured 45-01's index entries with MY commit message (rolled back via `git branch -D plan-45-04`; redone cleanly). The fix-forward pattern that worked: atomic shell-multi-command `mkdir + git add + git commit` in one Bash call to minimize the staging-race window. For future Phase 45 parallel-wave plans, the orchestrator should either (a) spawn agents in worktrees (`Agent(isolation="worktree")`) or (b) serialize plans within a wave instead of parallelizing them in shared cwd.
- **No real network calls in tests** — all `--live` mode tests use `monkeypatch.setattr(mod.subprocess, "run", ...)` + `monkeypatch.setattr(mod.urllib.request, "urlopen", ...)`. Run-time: full 20-test suite in 0.48s.

## User Setup Required

None — the audit script ships ready-to-run in fixture mode (CI / dev), and the §SHIP-13 runbook (Plan 45-06 will append) documents the T+30 `--live` invocation. The runbook handles GITHUB_TOKEN provisioning + the optional `--bravoh-healthz-stats-url` choice.

## Plan 45-06 Hand-off

§SHIP-13 runbook should cite the two literal invocations:

**Dev / dry-run (any time):**
```bash
uv run python scripts/release/audit_ship_v1_decision.py \
  --fixtures tests/release/fixtures/synthetic_telemetry/ \
  --output /tmp/decision-test.md
```

**T+30 Kaan-discharge (real):**
```bash
GITHUB_TOKEN=ghp_xxx uv run python scripts/release/audit_ship_v1_decision.py \
  --live \
  --release-tag v3.0.0-rc1 \
  --bravoh-healthz-stats-url https://api.altidus.world/vibemix/healthz/stats \
  --output .planning/decisions/v3.0-SHIP-V1-DECISION.md
```

Then: Kaan reviews the pre-filled report, manually fills the `<manual>` Anti-slop community-reports cell, ticks one of the 3 decision boxes, signs the sign-off line, commits the report to `.planning/decisions/`.

## Next Phase Readiness

- **Wave 1 partial complete (45-04 ✓):** SHIP-13 engineering scaffolding GREEN. Awaiting parallel Wave-1 sibling plans (45-01 install_vm_matrix, 45-02 launch_trigger, 45-03 check_bravoh_server_ready, 45-05 launch-rotation §SHIP-11) which run independently.
- **Wave 2 trigger (45-06):** Once all Wave-1 plans land, Plan 45-06 (KAAN-ACTION-LEGAL §SHIP-01..13 cookbook) can append §SHIP-13 citing this audit's literal invocation.
- **Discharge readiness:** SHIP-13 itself only fires at T+30 of v3.0 bake, which is gated by SHIP-08 (live publish) + the ~14-day bake clock. Engineering side is done; external clock is what we're waiting on.

## Self-Check: PASSED

Verified before this SUMMARY committed:

- [x] `docs/SHIP-V1-DECISION-TEMPLATE.md` exists on disk + in `git show c822baa` tree
- [x] `scripts/release/audit_ship_v1_decision.py` exists on disk + in `git show c3185ab` tree
- [x] All 5 synthetic fixtures exist on disk + in `git show c3185ab` tree
- [x] `tests/release/test_audit_ship_v1_decision.py` exists on disk; 20/20 tests GREEN
- [x] Commits `c822baa` / `c3185ab` / `8838f55` exist in `git log --oneline` and trace test → feat → feat
- [x] Manual `--help` exit code 0; manual `--fixtures … --output /tmp/d.md` exit code 0; manual `--live` (no token) exit code 2 with documented stderr
- [x] Plan 42-06 privacy regression: rendered report contains zero ear-test free_form / session_id substrings (T-45-04-02 mitigation)

---

*Phase: 45-external-discharge-public-rc-publish*
*Plan: 04*
*Completed: 2026-05-17*
