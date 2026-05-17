---
phase: 43-visual-ship-lock
plan: 01
subsystem: ui-audit
tags: [visual-ship-lock, ui-audit, gsd-ui-checker, gsd-ui-auditor, tier-1-surfaces, cdj-whisper, frontend-enforcement]

# Dependency graph
requires:
  - phase: 14-cdj-whisper-flip
    provides: tokens.css v5 (locked CDJ Whisper visual contract — --amber-*, --glow-faint, --silk-* token family)
  - phase: 12-session-window
    provides: tauri/ui/src/session/* (Tier-1 surface entry — SessionLayout.ts + components/*.ts)
provides:
  - scripts/launch/run_ui_audit.py audit driver (Tier-1 surface allowlist + UI-REVIEW skeleton writer)
  - .planning/phases/43-visual-ship-lock/UI-REVIEW-INDEX.md (4-surface inventory + closure-plan ownership map)
  - .planning/phases/43-visual-ship-lock/UI-REVIEW-session.md (3 HIGH + 3 MEDIUM + 2 LOW seed findings for the session window)
  - tests/launch/test_ui_audit_driver.py (5 pinning tests — allowlist, skeleton, rejection, dry-run, listing)
affects: [43-02 (session + mascot-overlay closure), 43-03 (wizard + calibration closure), 43-04 (meter rebuild closes H-03)]

# Tech tracking
tech-stack:
  added: []  # stdlib-only; no new deps
  patterns:
    - "Audit driver as markdown-skeleton writer + invariant gate (NOT a runner — paired agents invoked interactively by closure plans)"
    - "Append-only audit-loop log table per surface (iteration / agent / verdict / files_changed / notes)"
    - "Severity rubric (HIGH=blocks ship, MEDIUM=strongly-recommended-fix, LOW=nice-to-have) shared across all 4 Tier-1 surfaces"
    - "Filename contract: UI-REVIEW-<surface>.md verbatim (closure plans grep these names)"

key-files:
  created:
    - scripts/launch/run_ui_audit.py
    - scripts/launch/__init__.py
    - tests/launch/__init__.py
    - tests/launch/test_ui_audit_driver.py
    - .planning/phases/43-visual-ship-lock/UI-REVIEW-INDEX.md
    - .planning/phases/43-visual-ship-lock/UI-REVIEW-session.md
  modified: []

key-decisions:
  - "Driver is its own plan (43-01) rather than folded into 43-02..04 — matches CONTEXT §VIS-01 Claude's-discretion default; lets closure plans depend on a stable filename contract that already has a CI-green skeleton."
  - "Driver is subprocess-free during --dry-run — paired agents (gsd-ui-checker + gsd-ui-auditor) run interactively from closure plans via the Task tool. Test 4 monkeypatches subprocess.run/Popen/os.system to AssertionError to pin this contract."
  - "Seed audit uses real findings from direct source-read of tauri/ui/src/session/{SessionLayout,components/*}.ts — NOT fabricated. 3 HIGH findings discovered: rocker:hover lacks --glow-faint, titlebar:hover lacks --glow-faint, meter renders smooth-gradient instead of hardware-LED-strip."
  - "H-03 (meter rebuild) tracked HIGH-against-43-02 even though VIS-03 owner is 43-04 — session surface CANNOT pass audit while meter renders as web-app gradient. Cross-link explicit in the finding entry + cross-references section."

patterns-established:
  - "Audit-loop log table per UI-REVIEW-<surface>.md is append-only; closure iterations add rows, never delete history"
  - "Closure contract per surface = (a) every HIGH closed inline as `_(closed iteration N)_`, (b) final log row verdict=PASS, (c) closure plan SUMMARY cross-references audit file + closing iteration"
  - "Driver --list (no args) is the discovery surface for the 4-surface inventory; uses sorted iteration so output is stable"
  - "scripts.launch package is importable via sys.path.insert + scripts.launch.<module> (mirrors tests/scripts/test_grey_area_log.py)"

requirements-completed: [VIS-01]

# Metrics
duration: 28min
completed: 2026-05-16
---

# Phase 43 Plan 01: UI Audit Driver + First Audit Run (session surface) Summary

**Tier-1 audit driver ships with a 4-surface allowlist + UI-REVIEW skeleton writer, and the session surface gets its first real audit pass — 3 HIGH findings (rocker hover gap, titlebar hover gap, meter gradient vs hardware-LED-strip) that gate the 43-02 closure plan.**

## Performance

- **Duration:** 28 min
- **Started:** 2026-05-16T15:59:00Z
- **Completed:** 2026-05-16T16:27:42Z
- **Tasks:** 2/2
- **Files created:** 6

## Accomplishments

- Tier-1 audit driver (`scripts/launch/run_ui_audit.py`) lands with the four CONTEXT §VIS-01 surfaces locked in `TIER1_SURFACES` — session / mascot-overlay / wizard / calibration. Closure plans 43-02 / 43-03 can now grep the stable filename contract.
- 5-test contract pinning the driver: allowlist match, skeleton-sections match, unknown-surface rejection with exit 2, subprocess-free dry-run (monkeypatched assertion), and `--list` listing all 4 surfaces + owner plans.
- `UI-REVIEW-INDEX.md` documents the 4-surface inventory, closure-plan ownership, audit-loop methodology block-quoted from CONTEXT §VIS-01, severity buckets, CDJ Whisper baseline references, and the closure contract.
- `UI-REVIEW-session.md` carries the first real audit pass on the session window — **3 HIGH findings** (2 hover-coverage gaps + 1 meter-render-vs-hardware-LED-strip mismatch), **3 MEDIUM** (typography + density + hover-state inconsistency), **2 LOW** (rgba token migration + dead breakpoint). Plan 43-02 runs iteration 1+ against this seed list.

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): UI audit driver contract test suite** — `4798e0f` (test — RED gate)
2. **Task 1 (GREEN): UI audit driver implementation** — `b946c46` (feat — GREEN gate; 5/5 tests passing)
3. **Task 2: UI-REVIEW-INDEX + session seed audit** — `a0832ca` (docs)

_TDD cycle on Task 1 produced 2 commits (test → feat); Task 2 is a single docs commit per plan spec._

## Files Created/Modified

### Created
- `scripts/launch/__init__.py` — makes `scripts.launch` an importable package (precedent: `scripts/__init__.py` already in place; tests/scripts/test_grey_area_log.py uses the same `sys.path.insert + from scripts.<mod>` pattern).
- `scripts/launch/run_ui_audit.py` — driver: `TIER1_SURFACES` (4-entry allowlist), `write_audit_skeleton(surface, phase_dir, force_rewrite=False) -> Path`, `main(argv)` CLI with `--list` / `--surface` / `--phase-dir` / `--dry-run` / `--force-rewrite`. stdlib-only.
- `tests/launch/__init__.py` — pytest package marker.
- `tests/launch/test_ui_audit_driver.py` — 5 contract tests (allowlist set, skeleton sections, unknown-surface rejection, dry-run subprocess-absent, listing surfaces+owners).
- `.planning/phases/43-visual-ship-lock/UI-REVIEW-INDEX.md` — Tier-1 surface table, audit-loop methodology, severity rubric, CDJ Whisper references, closure contract.
- `.planning/phases/43-visual-ship-lock/UI-REVIEW-session.md` — first real audit pass on the session window (3 HIGH / 3 MEDIUM / 2 LOW + iteration-0 seed-log row + cross-refs to 43-02 / 43-04).

### Modified
None.

## Decisions Made

- **Folded vs separate driver plan** — kept separate (CONTEXT §VIS-01 default). Closure plans 43-02 / 43-03 depend on stable filenames + a working skeleton; a separate 43-01 lets them depend on a green artifact rather than co-evolving with their own audit churn.
- **Driver does NOT subprocess agents during dry-run** — paired audit agents (`gsd-ui-checker`, `gsd-ui-auditor`) are invoked interactively by closure plans via the Task tool. Test 4 hard-pins this contract via monkeypatch on `subprocess.run` / `subprocess.Popen` / `os.system`.
- **Tracked the meter-rebuild finding (H-03) under the session surface** even though its owner is 43-04 (VIS-03), because the session surface cannot pass audit while the meter renders as a web-app gradient. Cross-link in the finding entry + a dedicated Cross-references section makes the dependency explicit.
- **Findings are seeded from a direct source read, not fabricated** — Task 2 instruction explicit. The 3 HIGH findings came from reading `rocker.ts:70`, `titlebar.ts:154`, and `meter.ts:34-164` against `mocks/vibemix-direction-final.html` + `mocks/vibemix-app-ui.html`. Each finding carries an explicit `<file>:<line>` reference.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Test 2 asserted `### Audit Loop Log` (h3) but skeleton used `## Audit Loop Log` (h2)**
- **Found during:** Task 1 GREEN phase — first pytest run failed on `test_write_audit_skeleton_emits_canonical_sections` with `assert '### Audit Loop Log' in text`.
- **Issue:** Initial skeleton header was `## Audit Loop Log` (h2 — same level as Methodology and Findings); tests pinned `### Audit Loop Log` (h3 nested under an `## Audit Loop` h2). Plan's Task 2 sample-INDEX structure implies h3 (a sub-section under an h2 `## Audit Loop` parent), so the test was right and the skeleton was wrong.
- **Fix:** Added a `## Audit Loop` h2 parent + nested `### Audit Loop Log` h3 in `_render_skeleton`. Re-ran tests — 5/5 green.
- **Files modified:** `scripts/launch/run_ui_audit.py`
- **Committed in:** `b946c46` (rolled into the same GREEN commit as the initial implementation)

**2. [Rule 3 - Blocking] cwd-drift discovered during initial commit attempt**
- **Found during:** Task 1 RED commit — the worktree environment's cwd (`/Users/ozai/projects/dj-set-ai/.claude/worktrees/agent-a50c6ca225f024e29/`) was masked by `cd /Users/ozai/projects/dj-set-ai/` calls in Bash, which actually traversed into the MAIN repo's working tree. First three file writes (and one staged `git add`) landed on main, not the worktree.
- **Issue:** The orchestrator runs Bash calls in a sandboxed cwd that *resets* per call; the Read tool's prior file paths were absolute and (in cases) pointed at the main repo path. The pre-commit `if [ -f .git ]` worktree-detector guard saw `.git` as a directory in `/Users/ozai/projects/dj-set-ai/` and refused to run the worktree branch assertion, surfacing the protected-ref FATAL.
- **Fix:** Reset main's staged paths (no commit had been made yet); deleted the misplaced files from `/Users/ozai/projects/dj-set-ai/{scripts/launch/__init__.py,tests/launch/*}`; re-created all files under the canonical worktree path `/Users/ozai/projects/dj-set-ai/.claude/worktrees/agent-a50c6ca225f024e29/`; switched to `git -C <worktree>` for all git ops + absolute paths rooted in the worktree directory for all Write/Edit tool calls.
- **Files modified:** N/A — recovery deleted files that should never have existed on main.
- **Committed in:** all three plan commits (`4798e0f`, `b946c46`, `a0832ca`) landed cleanly on `worktree-agent-a50c6ca225f024e29` after the recovery.
- **Note:** this is the exact #3097 / cwd-drift scenario referenced in the executor's protocol. The pre-commit safety assertions caught it before any commit landed on a protected ref.

## Threat-model coverage

| Threat ID    | Disposition | How addressed                                                                                                                                                  |
| ------------ | ----------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| T-43-01-01   | mitigate    | Audit-loop log is append-only with `iteration / agent / verdict / files_changed / notes` columns; closure plans 43-02 / 43-03 append rows but never delete.    |
| T-43-01-02   | mitigate    | Every finding carries an explicit `<file>:<line>` reference + remediation owner plan; re-running `grep` against the production source verifies each closure.    |
| T-43-01-03   | accept      | Tier-1 surface paths are repo-public source-code paths; no secrets in the audit markdown.                                                                       |

## Verification

```
$ uv run pytest tests/launch/test_ui_audit_driver.py -q --no-header
.....                                                                    [100%]
5 passed in 0.01s

$ uv run pytest tests/launch/ -q --no-header
.....                                                                    [100%]
5 passed in 0.01s

$ uv run python scripts/launch/run_ui_audit.py --list
Tier-1 surfaces (CONTEXT §VIS-01)
=================================
  calibration  ...  owner_plan  : 43-03
  mascot-overlay  ...  owner_plan  : 43-02
  session  ...  owner_plan  : 43-02
  wizard  ...  owner_plan  : 43-03

$ grep -qE "^## Surface: session" UI-REVIEW-session.md \
    && grep -qE "^### HIGH findings" UI-REVIEW-session.md \
    && grep -cE "^## Tier-1 Surfaces" UI-REVIEW-INDEX.md | grep -q "^1$" \
    && grep -qE "session.*43-02" UI-REVIEW-INDEX.md \
    && echo OK
OK
```

Counts confirmed: 3 HIGH + 3 MEDIUM + 2 LOW findings; 1 iteration-0 seed log row; 22 cross-references to 43-02 + 43-04.

## Cross-references for downstream plans

- **43-02 (Wave A polish — session + mascot-overlay closure):** consumes
  `UI-REVIEW-session.md` HIGH list. Runs `gsd-ui-checker` + `gsd-ui-auditor`
  iteration 1+ against the surface; closes H-01, H-02, and most MEDIUM /
  LOW findings; seeds `UI-REVIEW-mascot-overlay.md` via the driver.
- **43-03 (Wave A polish — wizard + calibration closure):** uses the same
  driver pattern to seed `UI-REVIEW-wizard.md` + `UI-REVIEW-calibration.md`,
  then runs the paired agent loop.
- **43-04 (VIS-03 meter rebuild):** closes H-03 (meter gradient → hardware
  LED-strip + amber peak-hold). 43-02 cannot ship until 43-04 lands.

## Self-Check: PASSED

- [x] `scripts/launch/run_ui_audit.py` exists in worktree
- [x] `scripts/launch/__init__.py` exists in worktree
- [x] `tests/launch/__init__.py` exists in worktree
- [x] `tests/launch/test_ui_audit_driver.py` exists in worktree
- [x] `.planning/phases/43-visual-ship-lock/UI-REVIEW-INDEX.md` exists in worktree
- [x] `.planning/phases/43-visual-ship-lock/UI-REVIEW-session.md` exists in worktree
- [x] Commit `4798e0f` (test RED) exists on `worktree-agent-a50c6ca225f024e29`
- [x] Commit `b946c46` (feat GREEN) exists on `worktree-agent-a50c6ca225f024e29`
- [x] Commit `a0832ca` (docs INDEX + seed) exists on `worktree-agent-a50c6ca225f024e29`
- [x] All 5 driver tests pass; tests/launch/ stays green
