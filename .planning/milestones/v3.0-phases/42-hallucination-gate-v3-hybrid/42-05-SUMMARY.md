---
phase: 42-hallucination-gate-v3-hybrid
plan: 05
subsystem: release-cut / hallucination-gate
tags: [GATE-08, P85, decision-log, hybrid-gate, v3.0]
status: complete
date_started: 2026-05-16
date_completed: 2026-05-16
duration_minutes: 15
tasks_total: 2
tasks_completed: 2
requirements_completed: [GATE-08]
dependency_graph:
  requires:
    - "Plan 42-03 (GATE-05 / GATE-07): scripts/release/check_ear_test.sh + eval/EAR-TEST-PROTOCOL.md"
    - "Plan 42-04 (GATE-06): scripts/release/check_gate.sh + cut_release.sh Gate-2b wiring + P85 reminder removal"
    - "Phase 27-04: eval/THRESHOLD-LOCK.md autonomous-signed (kaan_signed: autonomous_phase27)"
    - "Phase 39-08: tests/repo/test_phase_16_override_expiry.py (v2.1 expiry enforcer — deleted by this plan)"
  provides:
    - ".planning/decisions/P85-OVERRIDE-RETIRED.md — formal Decision Log entry"
    - "tests/repo/test_gate_42_hybrid_in_force.py — positive-assertion contract pinning v3.0 hybrid in force"
    - "STATE.md annotation marking the override RETIRED with cross-reference"
  affects:
    - "scripts/launch/cut_release.sh (read-only assertion target)"
    - "scripts/release/check_gate.sh (read-only assertion target)"
    - "scripts/release/check_ear_test.sh (read-only assertion target)"
    - "tests/repo/test_cut_release_invokes_check_gate.py (retired 42-04 plan-boundary sanity)"
tech_stack:
  added: []
  patterns:
    - "Decision Log entry pattern at .planning/decisions/ — formal retirement-of-override doc"
    - "Positive-assertion test replacing expiry-clock test (inverse pinning)"
    - "Grep hygiene — scope every grep to specific PATH constants; filter comment-only lines"
key_files:
  created:
    - ".planning/decisions/P85-OVERRIDE-RETIRED.md"
    - "tests/repo/test_gate_42_hybrid_in_force.py"
  modified:
    - ".planning/STATE.md (1 line annotation)"
    - "tests/repo/test_cut_release_invokes_check_gate.py (retired 1 sanity test + 1 unused constant + 2 docstring lines)"
    - ".planning/phases/42-hallucination-gate-v3-hybrid/deferred-items.md (1 entry added)"
  deleted:
    - "tests/repo/test_phase_16_override_expiry.py (the v2.1 P85 expiry-clock enforcer; full retirement)"
decisions:
  - "Decision Log entry preserved the STATE.md Phase 16 line (annotated RETIRED) rather than deleting it — audit trail visibility outweighs cleanliness"
  - "Retired the 42-04 plan-boundary sanity test (`test_p85_test_file_not_yet_deleted_in_this_plan`) inline as part of Task 2 commit — its docstring explicitly hands the retirement off to 42-05"
  - "Strict-spec test assertions over tolerant-glob fallback — once Plan 42-04 merged into local main and was pulled into worktree, all 10 tests passed without spec relaxation"
metrics:
  duration_minutes: 15
  commits: 2
  tests_added: 10
  tests_deleted: 4
  tests_retired_inline: 1
  files_created: 2
  files_modified: 3
  files_deleted: 1
---

# Phase 42 Plan 05: P85 Override Retirement Summary

**One-liner:** Formally retired v2.1's P85 autonomous-only override — Decision
Log entry + STATE.md annotation + replaced expiry-clock enforcer
(`test_phase_16_override_expiry.py`) with positive-assertion contract
(`test_gate_42_hybrid_in_force.py`, 10 tests) pinning the v3.0 hybrid gate
(Phase 42 / GATE-06+GATE-05+GATE-07) is wired into the release cut.

---

## Status

`complete` — 2 tasks shipped, 10 new tests pass, full PLAN verification block
green, only out-of-scope pre-existing README drift remains.

## Commits

| Task | Commit | Subject |
|------|--------|---------|
| 1 | `3c2daa5` | `docs(42-05): retire P85 override + delete expiry test + annotate STATE.md` |
| 2 | `3f8e99a` | `test(42-05): pin v3.0 hybrid gate in force + retire 42-04 plan-boundary sanity` |

## Test Counts

| Bucket | Count | Source |
|--------|-------|--------|
| New tests added | 10 | `tests/repo/test_gate_42_hybrid_in_force.py` |
| Tests deleted | 4 | `tests/repo/test_phase_16_override_expiry.py` (full file) |
| Tests retired inline | 1 | `test_p85_test_file_not_yet_deleted_in_this_plan` in `test_cut_release_invokes_check_gate.py` |
| PLAN verification block pass | 19 / 19 | hybrid + g5 poc + bundle id |
| Full `tests/repo/` pass | 200 / 201 | 1 pre-existing failure (out of scope — README feature-matrix drift) |

## What Shipped

### `.planning/decisions/P85-OVERRIDE-RETIRED.md`

New Decision Log entry. Five canonical sections:

- **Status** — RETIRED (replaced by v3.0 hybrid gate).
- **History** — three v2.1-era enforcement mechanisms cited (Pitfall P85,
  expiry test, cut_release.sh reminders).
- **Replacement** — full wiring inventory: `check_gate.sh` (Plan 42-04),
  `check_ear_test.sh` (Plan 42-03), `EAR-TEST-PROTOCOL.md` (Plan 42-03),
  `cut_release.sh` Gate-2b (Plan 42-04).
- **Audit Trail** — `eval/THRESHOLD-LOCK.md` autonomous-signed,
  Phase 39-08 reminder enforcement, `v2.1-MILESTONE-AUDIT.md` close,
  this Plan 42-05 retirement entry.
- **What Changes** — explicit DELETED / ADDED / ANNOTATED checklist.
- **Anti-Feature Carveout** — locks the hybrid design as final for v3.0; do
  NOT propose a more-aggressive autonomous judge under cover of cleanup.

### `.planning/STATE.md`

Single-line annotation. Original:

> **Phase 16 ear-test memory override accepted for v2.1 only** — Phase 27 autonomous proxy gate substituted. Override EXPIRES post-v2.1 (P85 enforced in Phase 39-08). v2.2 must re-route hallucination-gate strategy.

Replaced with:

> **Phase 16 ear-test memory override [RETIRED post-v2.1]** — replaced by v3.0 hybrid gate (Phase 42). See .planning/decisions/P85-OVERRIDE-RETIRED.md. Phase 27 autonomous proxy = fast lane; Kaan ear-test = slow lane (release-cut Gate 2b veto).

Line preserved (annotate-not-delete) per the audit-trail convention.

### `tests/repo/test_phase_16_override_expiry.py` (deleted)

Full file deletion. Its 4 assertions were tied to v2.1 expiry-clock state that
no longer exists (override formally retired). `.pyc` shadow also removed
(`find ... -delete` one-liner handled both).

### `tests/repo/test_gate_42_hybrid_in_force.py` (new — 10 tests)

The positive-assertion replacement. Every assertion is scoped to specific PATH
constants declared at module top to prevent self-invalidation from docstring
tokens (`[P85]`, `Phase 16 override`, `OVERRIDE_*`). Comment-only line filter
via `re.match(r'^\s*#', line)`.

| # | Test | What it pins |
|---|------|--------------|
| 1 | `test_cut_release_invokes_check_gate_at_gate_2b` | `[Gate 2b]` + `check_gate.sh` both appear in cut_release.sh |
| 2 | `test_check_gate_reads_nightly_eval_runs` | `check_gate.sh` references `.planning/eval-runs` |
| 3 | `test_check_gate_invokes_ear_test_gate` | `check_gate.sh` invokes `check_ear_test.sh` (slow-lane chain) |
| 4 | `test_check_gate_sh_is_executable` | `check_gate.sh` has +x bit |
| 5 | `test_no_override_constants_remain_in_release_scripts` | No `OVERRIDE_*` / `OVERRIDE =` / `OVERRIDE:` on non-comment lines in `scripts/launch/*.sh` + `scripts/release/*.sh` |
| 6 | `test_no_p85_reminder_in_cut_release_echo_lines` | No `[P85]` / `Phase 16 override cleanup reminder` / `Phase 16 ear-test memory override` on echo lines of cut_release.sh |
| 7 | `test_cut_release_success_path_references_gate_06` | `[GATE-06]` appears after `ALL GATES PASS` marker in cut_release.sh body |
| 8 | `test_decision_log_entry_exists_and_cites_p85` | Decision Log entry exists and contains all of: P85, RETIRED, check_gate.sh, check_ear_test.sh |
| 9 | `test_state_md_phase_16_line_is_annotated_retired` | STATE.md Phase 16 line carries RETIRED + cross-reference path `P85-OVERRIDE-RETIRED.md` |
| 10 | `test_expiry_test_file_actually_deleted` | `tests/repo/test_phase_16_override_expiry.py` is gone (catches future revert) |

### `tests/repo/test_cut_release_invokes_check_gate.py` (retired 1 sanity test)

Plan 42-04 wrote a plan-boundary sanity test
(`test_p85_test_file_not_yet_deleted_in_this_plan`) asserting the expiry test
file still existed at 42-04's commit time. Its docstring explicitly handed the
deletion off to Plan 42-05:

> "Sanity that Plan 42-04 did NOT delete tests/repo/test_phase_16_override_expiry.py — that retirement is Plan 42-05's job."

After 42-05 deletes the expiry file, the sanity test self-fails. Retired inline
in this plan: function deleted + unused `PHASE_16_OVERRIDE_TEST` constant
deleted + comment block + docstring updated to point at the inverse pin in
`test_gate_42_hybrid_in_force.py`. This is the literal plan-boundary handoff;
the docstring of the original test even names 42-05 as the retiring party.

## Deviations from Plan

### [Rule 1 - Bug] Retire 42-04 plan-boundary sanity test inline (within Task 2)

- **Found during:** Task 2 verification (`python3 -m pytest tests/repo/ -q`)
- **Issue:** After merging local `main` (which now contains 42-04 at
  `c204318`) into the worktree, two tests failed:
    1. `tests/repo/test_cut_release_invokes_check_gate.py::test_p85_test_file_not_yet_deleted_in_this_plan`
       — 42-04's plan-boundary sanity that the expiry file still existed.
    2. `tests/repo/test_readme_feature_matrix_sync.py::test_readme_feature_matrix_in_sync`
       — pre-existing README drift, unrelated to 42-05.
- **Fix (1):** Surgically removed the sanity test function + the now-unused
  `PHASE_16_OVERRIDE_TEST` constant + updated the file's module-docstring
  bullet. Per the sanity test's own docstring, the deletion is Plan 42-05's
  job — this is the literal plan-boundary handoff.
- **Fix (2):** Logged the README drift to
  `.planning/phases/42-hallucination-gate-v3-hybrid/deferred-items.md` and
  left it alone (SCOPE BOUNDARY rule — pre-existing failure in an unrelated
  file is out of scope; Plan 42-05 touches neither `README.md` nor
  `scripts/launch/sync_feature_matrix.py`).
- **Files modified:** `tests/repo/test_cut_release_invokes_check_gate.py`,
  `.planning/phases/42-hallucination-gate-v3-hybrid/deferred-items.md`
- **Commit:** `3f8e99a` (folded into Task 2 commit since the fix is part of
  the same plan-boundary handoff)

### [Process - Worktree absolute-path drift]

- **Found during:** Initial Task 1 staging
- **Issue:** First-pass Write/Edit calls used absolute paths rooted at the
  main repo (`/Users/ozai/projects/dj-set-ai/...`) — these resolved INSIDE
  the main repo, not the worktree (#3099 absolute-path safety class). A
  `cd /Users/ozai/projects/dj-set-ai` in a Bash call then drifted cwd onto
  `main`, where `git add` would have staged on the protected `main` branch.
  Caught by the pre-commit HEAD assertion (`FATAL: HEAD on protected ref`).
- **Fix:** Reset main repo (unstage + checkout HEAD + rm stray decision
  file), re-applied every Write/Edit using the **worktree's** absolute path
  (`/Users/ozai/projects/dj-set-ai/.claude/worktrees/agent-ae22a3d629c578daa/...`).
- **Outcome:** No data lost (the unstaged work on main was reverted before
  any commit landed). Task 1 then committed cleanly on the worktree branch.
- **Files affected:** none (the cleanup was complete before the commit)
- **Lesson:** When writing into a Claude Code worktree, derive every
  absolute path from `git rev-parse --show-toplevel` run INSIDE the
  worktree — never from an outer-context path.

## Notes

- **Dependency on 42-04 (Wave 3) was honored by mid-execution merge.** Plan
  42-05's `depends_on: [04]` and `wave: 4` were already locked in the
  frontmatter; the orchestrator merged 42-04 into local `main` between my
  initial worktree-merge (`2be1634`) and Task 2 verification, and I pulled
  it into the worktree (`git merge main --no-edit` produced commit
  `c5bde88`). All 10 hybrid-in-force tests pass post-merge.

- **No threat flags introduced.** The plan only touches Decision Log + STATE.md
  + repo-level tests — zero network surface, zero new auth path, zero new
  filesystem trust boundary.

- **No new stubs introduced.** Plan output is documentation + test assertions;
  no UI surface, no data source wired.

- **All five success criteria green:**
    1. Decision Log entry with all five canonical sections — ✅
    2. Expiry test file fully deleted (`.py` + `.pyc` shadow) — ✅
    3. 10 positive-assertion tests in `test_gate_42_hybrid_in_force.py` — ✅
    4. STATE.md Phase 16 line annotated RETIRED with cross-reference — ✅
    5. Grep hygiene observed (no self-invalidation from token leakage) — ✅

## Self-Check: PASSED

- `.planning/decisions/P85-OVERRIDE-RETIRED.md` exists — FOUND
- `tests/repo/test_gate_42_hybrid_in_force.py` exists — FOUND
- `tests/repo/test_phase_16_override_expiry.py` deleted — CONFIRMED GONE
- `.planning/STATE.md` carries `RETIRED` annotation + `P85-OVERRIDE-RETIRED.md`
  cross-reference — VERIFIED via grep
- Commit `3c2daa5` (Task 1) on worktree branch — FOUND in `git log`
- Commit `3f8e99a` (Task 2) on worktree branch — FOUND in `git log`
- Plan verification block (Decision Log existence + expiry file absence +
  hybrid test + g5 poc + bundle id + STATE.md cross-reference) — all green
- 10 / 10 hybrid-in-force tests pass
- 200 / 201 full `tests/repo/` pass (1 out-of-scope pre-existing failure
  logged to deferred-items.md)
