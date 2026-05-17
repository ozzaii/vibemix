---
phase: 45-external-discharge-public-rc-publish
plan: 01
subsystem: infra
tags: [tart, vm-matrix, install, onboarding, ship-04, ship-05, autonomous-pre-stage, bash, python3, json]

# Dependency graph
requires:
  - phase: 33-rc1-launch-flow
    provides: onboarding-stopwatch.ts (Phase 33 INSTALL-05 — emits OnboardingTimingEvent with totalMs + per-step durations)
  - phase: 44-launch-prep
    provides: discord_provision.py taxonomy-driven JSON pattern; check_bravoh_org_ready.sh polling-gate shape with discriminating exit codes (0/1/2/3)
provides:
  - tart-based INSTALL-VM matrix runner (scripts/dist/install_vm_matrix.sh) — JSON-driven, dry-run-default, 5 canonical OS rows
  - matrix config file (scripts/dist/install_vm_matrix.json) — single source of truth for macOS 12.3/14/15 + Windows 10/11 rows
  - --check-60s sub-gate with VM-absent autonomous-degraded semantics (BLOCKED_BY=install-vm convention)
  - run.json index format (dist/install-vm-runs/<run-id>/run.json) consumable by Plan 45-04 SHIP-V1-DECISION audit
  - 17 contract tests in tests/install/test_install_vm_matrix.py (zero-network, PATH-shimmed tart)
affects: 45-04-audit-ship-v1-decision, 45-05-cut-release-gates, 45-06-kaan-action-legal-runbook

# Tech tracking
tech-stack:
  added: []  # no new deps — uses python3 + bash + sed + find (already available)
  patterns:
    - "JSON-driven matrix runners (data-not-code expansion path)"
    - "PATH-shimmed external CLIs for zero-network contract tests"
    - "Atomic run.json writes via tempfile + mv"
    - "BLOCKED_BY=<key> stderr convention for cut_release.sh grep"

key-files:
  created:
    - scripts/dist/install_vm_matrix.sh — matrix runner (281 lines)
    - scripts/dist/install_vm_matrix.json — 5-row matrix config (42 lines)
    - tests/install/test_install_vm_matrix.py — 17 pin tests (570 lines)
  modified: []

key-decisions:
  - "VM-absent rows SKIP rather than fail — autonomous-degraded pass under --check-60s when zero VMs present (CONTEXT §INSTALL-VM)"
  - "Dry-run default — no tart invocation without explicit --live (matches discord_provision.py P44-06 ergonomics)"
  - "JSON-driven matrix — adding/removing OS rows is data not code (taxonomy pattern from P44-06 Discord provisioning)"
  - "Exit code triage: 0 ok, 1 gate fail, 2 usage error, 3 external dep missing (matches check_bravoh_org_ready.sh)"
  - "Subshell-capture trick for python3 gate exit code: `echo $?` inside $(...) + grep-extract (|| GATE_RC=$? would assign in subshell, not parent)"

patterns-established:
  - "Pattern: PATH-shimmed external CLI under pytest for zero-network contracts — `tart` shim writes argv to a marker file; tests assert marker absence (dry-run) or presence (live)"
  - "Pattern: JSON-driven matrix loop with python3 heredoc for per-row JSON extraction — avoids jq dependency, vibemix-aligned"
  - "Pattern: Gate-only mode reading the newest run.json by mtime via `find -maxdepth 2 -name run.json -exec stat -f '%m %N' | sort -nr | head -1`"

requirements-completed: [SHIP-04, SHIP-05]

# Metrics
duration: 15min
completed: 2026-05-17
---

# Phase 45 Plan 01: tart-based INSTALL-VM Matrix Runner + 60s Onboarding Gate Summary

**tart-based 5-OS install matrix runner with JSON-driven config, dry-run-default semantics, and a --check-60s sub-gate that fails the cut when any VM exceeded 60s end-to-end onboarding.**

## Performance

- **Duration:** 15 min
- **Started:** 2026-05-17T07:39:07Z
- **Completed:** 2026-05-17T07:54:57Z
- **Tasks:** 3 (all TDD: RED → GREEN → GREEN)
- **Files created:** 3 (install_vm_matrix.sh, install_vm_matrix.json, test_install_vm_matrix.py)
- **Tests:** 17/17 GREEN (zero-network, PATH-shimmed `tart`)

## Accomplishments

- **INSTALL-VM matrix runner ships** — `scripts/dist/install_vm_matrix.sh` walks the 5-row matrix (macOS 12.3/14/15 + Windows 10/11), captures per-row screenshots + onboarding-stopwatch timing dump, writes `dist/install-vm-runs/<run-id>/run.json`.
- **--check-60s sub-gate operational** — Reads the most-recent `run.json`, exits non-zero on any row exceeding `max_onboarding_ms` (default 60000), exits 0 with WARN when all rows are skipped (CONTEXT §INSTALL-VM autonomous-degraded semantics). Plan 45-06 §SHIP-04 runbook can cite `bash install_vm_matrix.sh --check-60s` directly.
- **Zero-network test contract** — `tests/install/test_install_vm_matrix.py` PATH-shims `tart` so the test suite never invokes the real binary; covers dry-run output, --live exit-3-when-tart-absent, image-missing-skip semantics, run.json schema, timing-dump merge, all four --check-60s exit paths, --quiet behaviour.
- **No new deps** — uses python3 + bash + sed + find (already vendored by vibemix's gate scripts).

## Task Commits

Each task was committed atomically (TDD: RED → GREEN-loop → GREEN-check):

1. **Task 1 (RED)** — `60113e0` `test(45-01): pin install_vm_matrix.{sh,json} CLI + schema contract (RED)`
2. **Task 2 (GREEN)** — `27c8c08` `feat(45-01): implement install_vm_matrix.sh JSON-driven dry-run + skip semantics + run.json index (GREEN)`
3. **Task 3 (GREEN)** — `dce8f53` `feat(45-01): --check-60s sub-gate with VM-absent autonomous-degraded semantics`

## Files Created/Modified

- `scripts/dist/install_vm_matrix.sh` — matrix entry point. JSON-driven row loop; per-row `tart clone → run (env VIBEMIX_INSTALL_VM_RUN=1) → screenshot per step → stop`; --check-60s gate-only mode reads newest run.json by mtime; emits `BLOCKED_BY=install-vm` on stderr; --quiet honours stdout-only suppression. Exit codes: 0 ok, 1 gate fail, 2 usage, 3 tart missing.
- `scripts/dist/install_vm_matrix.json` — versioned matrix config. 5 canonical OS rows: macOS Monterey 12.3, Sonoma 14, Sequoia 15, Windows 10, Windows 11. Each row has `tart_image`, `expected_steps` (intro, permissions, output-device, controller, first-reaction), `max_onboarding_ms=60000`.
- `tests/install/test_install_vm_matrix.py` — 17 pin tests. Tests 1-6/6b cover Task 1 schema + CLI contract. Tests 7-11 cover Task 2 dry-run + --live + skip-on-missing-image + run.json schema + timing-dump merge. Tests 12-16 cover Task 3 --check-60s no-runs / all-pass / one-exceeds / all-skipped / --quiet paths.

## Decisions Made

- **VM-absent = autonomous-degraded pass, not block.** When `--check-60s` runs against a run.json where all 5 rows are `status: skipped` (zero VM images present locally), exit 0 with a `[install-vm] WARN — all rows skipped...` line. Reason: CI on a machine without tart images shouldn't block the cut; full discharge is gated by Kaan's §SHIP-04 manual VM walk. CONTEXT §INSTALL-VM is the canonical decision.
- **Dry-run default; --live opt-in.** Default invocation prints `[plan] tart ...` lines without invoking the binary. Test suite asserts `tart` PATH-shim marker file is absent post-default-run. `--live` flag actually invokes. Matches `scripts/dayzero/discord_provision.py` Phase 44-06 ergonomics — every destructive scaffolding script defaults to dry-run.
- **JSON-driven matrix.** Adding a future OS row (e.g., macOS 16 Tahoe) requires editing `install_vm_matrix.json` only — no `.sh` change. Taxonomy-driven pattern lifted from `discord_provision.py` (Phase 44-06 Discord taxonomy JSON).
- **Subshell exit-code capture trick.** Inside `GATE_OUT=$(python3 ... || GATE_RC=$?)` the `||` runs in the command-substitution subshell, so `GATE_RC` is assigned in the subshell and lost. Workaround: append `; echo "__GATE_RC__=$?"` inside the `$(...)`, then parse the trailing `__GATE_RC__=N` token from the captured string. Documented inline.
- **Exit code triage.** 0 = ok, 1 = gate failed, 2 = CLI usage error, 3 = external dep missing (tart binary). Matches `check_bravoh_org_ready.sh` (Phase 44-06) — so Plan 45-06 §SHIP-04 runbook can discriminate "loop and alert" (exit 1) from "install tart first" (exit 3) without re-reading stderr.

## Deviations from Plan

**Total deviations:** 1 minor auto-fix (Rule 3 — Blocking)

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added `dirname` to Test 8's empty-bin allow-list**
- **Found during:** Task 2 (Test 8: `--live without tart on PATH exits 3`)
- **Issue:** Matrix runner header runs `cd "$(dirname "${BASH_SOURCE[0]}")/../.."` before any path validation. With `dirname` stripped from PATH (test simulates a binary-stripped environment), the script failed at line 35 with `dirname: command not found` and exited 2 (matrix JSON not found) instead of 3 (tart absent). The test as originally written would never reach the tart-missing check.
- **Fix:** Added `dirname` to the test's allow-list of essentials symlinked into `tmp_path/empty-bin`. The matrix runner still legitimately needs `dirname` to locate itself; this is correct production behaviour.
- **Files modified:** `tests/install/test_install_vm_matrix.py`
- **Verification:** Test 8 GREEN post-fix; all 17 tests now pass.
- **Committed in:** `27c8c08` (Task 2 GREEN commit)

**Impact on plan:** Trivial test-fixture correction. No production behaviour changed. No scope creep.

## Issues Encountered

- **Parallel-execution branch hijacking (resolved).** Orchestrator's working-directory env pointed to `/Users/ozai/projects/dj-set-ai` (main checkout) instead of the agent's allocated worktree `/Users/ozai/projects/dj-set-ai/.claude/worktrees/agent-ac406198878ff8285`. Earlier in execution, a concurrent agent's commit (45-04 RED) absorbed my staged files. Recovery: switched to the proper worktree (matching the gitStatus branch `worktree-agent-ac406198878ff8285`), recreated the three files there, committed cleanly on the per-agent branch. Working tree's stale `.glb` LFS pointer diffs (known issue per memory `project_v0_1_0_rc1_open_bugs`) were left untouched (out of scope per SCOPE BOUNDARY).

## User Setup Required

None — no external service configuration. The matrix runner is a local discharge tool; SHIP-04 live execution (downloading actual `tart` images, running the 5-VM walk) is Kaan's discharge action documented in Plan 45-06 §SHIP-04 runbook.

## Plan 45-06 §SHIP-04 Hand-off

Plan 45-06's KAAN-ACTION-LEGAL.md §SHIP-04 runbook can cite both:

- **Live discharge:** `bash scripts/dist/install_vm_matrix.sh --live --run-id $(date -u +%Y-%m-%dT%H-%M-%SZ)` — walks all 5 VMs, captures screenshots + per-VM timing JSON, writes `dist/install-vm-runs/<run-id>/run.json`.
- **Gate verification:** `bash scripts/dist/install_vm_matrix.sh --check-60s` — exits 0 if all rows under 60s onboarding, 1 with `BLOCKED_BY=install-vm: row <os>-<version> took <N>ms (max: 60000ms)` on stderr otherwise.

No further engineering needed — both flags are operational as of this plan.

## Self-Check

Verified before SUMMARY commit:

- [x] `scripts/dist/install_vm_matrix.sh` exists (executable, 281 lines, mode 100755).
- [x] `scripts/dist/install_vm_matrix.json` exists (42 lines, 5 rows, version=1).
- [x] `tests/install/test_install_vm_matrix.py` exists (570 lines, 17 tests).
- [x] Commit `60113e0` present in `git log` (Task 1 RED).
- [x] Commit `27c8c08` present in `git log` (Task 2 GREEN).
- [x] Commit `dce8f53` present in `git log` (Task 3 GREEN).
- [x] `bash -n scripts/dist/install_vm_matrix.sh` exits 0.
- [x] `bash scripts/dist/install_vm_matrix.sh --help` exits 0 and prints flag reference.
- [x] `python3 -c 'import json; d=json.load(open("scripts/dist/install_vm_matrix.json")); assert d["version"]==1 and len(d["rows"])==5'` exits 0.
- [x] `bash scripts/dist/install_vm_matrix.sh --check-60s` exits 1 with `no runs found` on stderr (pre-discharge baseline — correct behaviour).
- [x] All 17 tests in `tests/install/test_install_vm_matrix.py` GREEN.

## Self-Check: PASSED

---
*Phase: 45-external-discharge-public-rc-publish*
*Completed: 2026-05-17*
