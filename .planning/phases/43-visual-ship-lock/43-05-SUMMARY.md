---
phase: 43-visual-ship-lock
plan: 05
subsystem: mascot
tags: [mascot, retarget, mixamo, bundle-size-gate, kaan-discharge, vis-04]

# Dependency graph
requires:
  - phase: 43-visual-ship-lock plan 07 (memory + storyboard doc drift — "DJ bat" → "Neon Rebel")
    provides: locked rig name used verbatim in this plan's runbook + manifest

provides:
  - scripts/mascot/retarget_to_neon_rebel.py — Mixamo → Neon Rebel retarget pipeline scaffold
  - scripts/mascot/check_bundle_size.sh — two-tier mascot bundle size gate (≤25 MB total + 400 KB-1200 KB per-clip)
  - scripts/mascot/MIXAMO-CLIP-SOURCES.md — Kaan's source-clip selection manifest with Pioneer-CDJ-headbob aesthetic guardrails
  - KAAN-ACTION-LEGAL.md §VIS-04 — Kaan-discharge runbook for the Mixamo login + 5 clip downloads + 5 retargets
  - tests/mascot/test_retarget_pipeline.py — 8 sanity tests pinning CLI surface + slot taxonomy + size-band predicate
  - tests/mascot/test_bundle_size_cap.py — 6 sanity tests pinning the wrapper's existence + delegation + per-clip band + manifest contents

affects:
  - 43-06 (mood pool runtime validation runs against placeholders today; flips to real retargets after §VIS-04 discharge)
  - Phase 45 v3.0 ship-cut gate (visual ship lock blocks on real retargets landing)
  - 43-09 future appends to KAAN-ACTION-LEGAL.md (§VIS-04 sits between §GATE-05 and the next future §VIS-* section; canonical block format preserved)

# Tech tracking
tech-stack:
  added:
    - subprocess-based gltf-pipeline (npm) draco compression shell-out (Python wrapper)
    - bash two-tier gate pattern (delegate + per-clip enforcement) — reuses existing Phase 31 25 MB cap as Tier 1
  patterns:
    - "scaffold + runbook split" — CI ships invokable script with NotImplementedError on the load-bearing step, paired with a KAAN-ACTION-LEGAL.md §-section documenting the discharge protocol. Lets Kaan close the gap without the autonomous agent attempting an Adobe-account-gated operation.
    - "two-tier size gate" — delegate to existing total-budget gate, layer per-clip band check on top (rejects both over-compressed and under-compressed outputs in one pass)
    - "dataclass slot taxonomy" — frozen SlotMapping dataclass tuple drives both --dry-run output and argparse --slot choices; single source of truth.

key-files:
  created:
    - scripts/mascot/__init__.py
    - scripts/mascot/retarget_to_neon_rebel.py
    - scripts/mascot/check_bundle_size.sh
    - scripts/mascot/MIXAMO-CLIP-SOURCES.md
    - tests/mascot/__init__.py
    - tests/mascot/test_retarget_pipeline.py
    - tests/mascot/test_bundle_size_cap.py
  modified:
    - KAAN-ACTION-LEGAL.md (appended §VIS-04 section, 114 lines added)

decisions:
  - "Slot mapping: ship the 5 vibemix slot filenames (prep_settle / prep_head_turn_left / prep_head_turn_right / prep_lean_in_hyped / prep_lean_in_neutral) matching the existing placeholders in tauri/ui/assets/mascot/animations/ — NOT new public/mascot/ paths. Preserves manifest.json + asset-loader.ts `s.startsWith('prep_')` convention."
  - "Output dir default: tauri/ui/assets/mascot/animations/ (matches existing placeholder placement) rather than tauri/ui/public/mascot/ (which CONTEXT named, but no files exist there)."
  - "Retarget implementation: intentionally NotImplementedError + exit code 3 in this plan. Two implementation paths (pygltflib OR blender headless) documented in §VIS-04 — Kaan picks at discharge time based on whether the Mixamo skinned-mesh remap fits in pygltflib's surface."
  - "Tier 2 placeholder state: bundle gate exit 2 is the expected state today (placeholders are 44-56 KB, below the 400 KB floor). The non-zero exit is the mechanism for surfacing that §VIS-04 still needs to be discharged. Test asserts {0, 2}, not strict 0."
  - "Documenting Pioneer-CDJ-headbob aesthetic in TWO places: MIXAMO-CLIP-SOURCES.md (selection guidance — what to download) AND KAAN-ACTION-LEGAL.md §VIS-04 step 7 (visual sanity — what to reject post-retarget). Two surfaces for the load-bearing 'no AI slop' constraint."

metrics:
  duration_seconds: 842
  completed: 2026-05-16
  task_count: 3
  files_created: 7
  files_modified: 1
  tests_added: 14
  tests_passing: 14
---

# Phase 43 Plan 05: Mixamo Retarget Pipeline + 5 prep_*.glb Swap Scaffold Summary

Ships the engineering scaffold for VIS-04: a Mixamo → Neon Rebel retarget driver, a two-tier bundle size gate (25 MB total + 400 KB-1200 KB per-clip), a Kaan-facing source-clip selection manifest, and the canonical §VIS-04 Kaan-discharge runbook. The pipeline plumbs end-to-end against the existing `character.glb` rig with dry-run inventory + file-existence guards + size-band predicates; the load-bearing skeleton-remap step is intentionally NotImplementedError-gated and discharged by the new §VIS-04 runbook (Mixamo login is Adobe-account-gated; aesthetic judgment for Pioneer-CDJ-headbob feel is Kaan-ear-gated).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Failing tests for Mixamo retarget pipeline scaffold | `823a8ad` | tests/mascot/__init__.py, tests/mascot/test_retarget_pipeline.py, scripts/mascot/__init__.py |
| 1 (GREEN) | Implement scripts/mascot/retarget_to_neon_rebel.py | `d5f0c20` | scripts/mascot/retarget_to_neon_rebel.py |
| 2 | Bundle-size two-tier gate + Mixamo source manifest + 6 sanity tests | `79084aa` | scripts/mascot/check_bundle_size.sh, tests/mascot/test_bundle_size_cap.py, scripts/mascot/MIXAMO-CLIP-SOURCES.md |
| 3 | Append §VIS-04 Kaan-discharge runbook to KAAN-ACTION-LEGAL.md | `ccc5e13` | KAAN-ACTION-LEGAL.md |

## Verification Results

### Plan-named verification

```
=== retarget pipeline tests (Task 1) ===
8 passed in 0.03s

=== bundle size cap tests (Task 2) ===
6 passed in 0.08s

=== full mascot suite ===
14 passed in 0.11s

=== Task 3 grep gate ===
TASK-3-VERIFICATION-OK   (§VIS-04 + Pioneer-CDJ-headbob + Neon Rebel + retarget_to_neon_rebel.py + check_bundle_size.sh all present)
```

### Regression checks

- Phase 31 bundle gate (`scripts/check_mascot_glb_size.sh`): green at 21.67 MB / 25 MB.
- Phase 43 Wave 1 (43-07 storyboard palette tests): 6/6 passing — no drift.

### Cross-cutting checks

- `git diff --diff-filter=D` empty on all 4 commits — no accidental deletions.
- `git status` clean for plan files; pre-existing dirty LFS-state files (worktree-vs-main smudge differences in mascot GLBs + library fixtures) untouched.

## Success Criteria

| Criterion | Status | Evidence |
|-----------|--------|----------|
| VIS-04 engineering scaffolding (retarget pipeline + bundle gate + Kaan-discharge runbook) shipped | ✅ | 4 commits + 14 green tests |
| 5-clip source-to-slot mapping documented with Mixamo asset selection guidance | ✅ | scripts/mascot/MIXAMO-CLIP-SOURCES.md (5-row table + Pioneer-CDJ-headbob guardrails + download checklist) |
| Per-clip band enforced via shell gate + Python test | ✅ | check_bundle_size.sh Tier 2 (400 * 1024 .. 1200 * 1024 bytes) + 6 sanity tests + Python verify_size_band() predicate |
| KAAN-ACTION-LEGAL.md §VIS-04 follows canonical §GATE-* format | ✅ | why-defer / files / Kaan steps / verification / what unblocks / sign-off block — matches §GATE-05 precedent |
| Retarget tests + bundle tests pass | ✅ | 8 + 6 = 14 / 14 |
| No regression in existing mascot specs or Phase 31 bundle gate | ✅ | Phase 31 gate green; 43-07 palette tests green |

## Deviations from Plan

### Stray commit on `main` (procedural defect — Bash cwd-reset)

**1. [Procedural — Worktree isolation breach] Test artifact commit `06ce7ce` landed on main repo's `main` branch instead of the worktree branch**

- **Found during:** Task 1 first commit attempt.
- **Issue:** The orchestrator-spawned shell's cwd is the worktree at `/.../agent-aa37880cfcd0c0021`, but Bash sessions reset cwd between tool calls. Early commands used `cd /Users/ozai/projects/dj-set-ai && git commit ...` which targeted the **main repo**, not the worktree. The result: a duplicate of the RED-phase test files (`tests/mascot/__init__.py` + `tests/mascot/test_retarget_pipeline.py`) landed at commit `06ce7ce` on the main repo's `main` branch BEFORE Wave 1 tip `71e5ef5`.
- **Why no destructive recovery was attempted:** `<destructive_git_prohibition>` forbids `git reset --hard` / `git update-ref refs/heads/main` to rewind protected refs. The HALT-and-surface protocol applies (cf. "If you discover that your worktree HEAD is attached to a protected branch and your commits landed there, DO NOT 'recover' by force-rewinding the protected ref"). Even though my worktree HEAD was correctly on `worktree-agent-...`, the stray commit went to main via a separate cwd; treating it the same way is the conservative call.
- **Mitigation:** All subsequent operations used `git -C "$WT" ...` with the worktree absolute path, and `Edit`/`Write` calls used worktree-rooted absolute paths. The plan was redone fully inside the worktree (commits `823a8ad`, `d5f0c20`, `79084aa`, `ccc5e13`). When the orchestrator merges the worktree branch back to main, the duplicate test-files content will be detected as no-op (identical bytes already present from `06ce7ce`) — git's merge resolves cleanly.
- **Recommendation for the user:** Decide whether to revert `06ce7ce` from main with a non-destructive `git revert 06ce7ce` (creates a new commit removing the stray files), which would then be re-introduced by the merge of this worktree's `feat(43-05)` commit `d5f0c20` that ships `retarget_to_neon_rebel.py` alongside the same test files. Or just leave it — the file content is identical to the worktree-side version.
- **Process improvement:** Future executors running under this worktree-spawn pattern should ALWAYS prefix git/file operations with the worktree root via `git -C` and worktree-rooted absolute paths. The cwd-drift assertion in the protocol caught my error retroactively but did not prevent it on the first commit.

### Auto-applied corrections during GREEN

**2. [Rule 1 — Bug] Dry-run output missing literal `1200` substring**

- **Found during:** Task 1 GREEN phase (1 / 8 tests failed initially).
- **Issue:** Test 5 asserted both `"400"` and `"1200"` are substrings of the dry-run output, but the original print used only the byte-formatted band (`409600..1228800`) which contains `400` but not `1200`.
- **Fix:** Extended the dry-run output line to include `400KB-1200KB / 0.4MB-1.2MB after draco compression` — surfaces the human-readable KB band Kaan reads from the runbook + satisfies the substring contract.
- **Commit:** `d5f0c20` (same commit as the GREEN implementation; fix was inline before commit).

## Known Stubs (intentional, runbook-tracked)

The scaffold ships `retarget()` as `raise NotImplementedError(...)` with exit code 3 — this is **transparent scaffolding**, not undisclosed slop:

| Surface | Reason | Discharge path |
|---------|--------|----------------|
| `scripts/mascot/retarget_to_neon_rebel.py::retarget()` | Skeleton-remap implementation is Adobe-Mixamo-account-gated for asset acquisition + Kaan-aesthetic-gated for Pioneer-CDJ-headbob feel | KAAN-ACTION-LEGAL.md §VIS-04 step 4 — Kaan picks pygltflib OR blender headless at discharge time and fills in the implementation. The CLI, slot taxonomy, draco shell-out, size-band predicate, and file-existence guard are ALL fully functional today. |
| 5 placeholder `prep_*.glb` files (44-56 KB each) | Engineering scaffold does not commit real Mixamo bytes (license + autonomous-discharge prohibition) | KAAN-ACTION-LEGAL.md §VIS-04 step 8 — Kaan commits real retargets after the discharge run |

Both stubs are **gated by the bundle-size wrapper**: `bash scripts/mascot/check_bundle_size.sh` exits 2 today (Tier 2 placeholder size mismatch), which is the visible signal that §VIS-04 discharge is still pending. The wrapper exit 0 happens automatically once Kaan replaces the placeholders.

## Threat Flags

None — VIS-04 introduces no new network surface, no new auth path, no schema changes. The Mixamo / Adobe trust boundary is documented as `accept` in the plan's threat model and lives entirely on Kaan's local machine during the discharge run.

## Files Created / Modified

### Created

- `scripts/mascot/__init__.py` (empty — package marker)
- `scripts/mascot/retarget_to_neon_rebel.py` (247 lines — CLI scaffold + size-band predicate + draco shell-out + slot taxonomy)
- `scripts/mascot/check_bundle_size.sh` (executable; 61 lines — two-tier bundle gate)
- `scripts/mascot/MIXAMO-CLIP-SOURCES.md` (104 lines — Kaan's source-clip selection manifest)
- `tests/mascot/__init__.py` (empty — package marker)
- `tests/mascot/test_retarget_pipeline.py` (134 lines — 8 sanity tests)
- `tests/mascot/test_bundle_size_cap.py` (95 lines — 6 sanity tests)

### Modified

- `KAAN-ACTION-LEGAL.md` (+114 lines — new `## §VIS-04` section appended after §GATE-05)

## Cross-References

- **Plan:** `.planning/phases/43-visual-ship-lock/43-05-PLAN.md`
- **Phase context:** `.planning/phases/43-visual-ship-lock/43-CONTEXT.md` §`<decisions>` VIS-04
- **Requirement:** REQUIREMENTS.md VIS-04
- **Dependency (Wave 1):** 43-07-SUMMARY.md (mascot personality memory + storyboard cleanup — "Neon Rebel" rename)
- **Affects (Wave 2 continuation):** 43-06-PLAN.md (mood pool runtime validation; smokes today against placeholders, flips post-discharge)
- **Locked memory:** `project_mascot_as_vtuber_personality_surface` — single VTuber rig, Neon Rebel name
- **Locked memory:** `project_visual_direction_cdj_whisper` — Pioneer-grade restraint, no vtuber slop
- **Existing Phase 31 gate:** `scripts/check_mascot_glb_size.sh` (delegated as Tier 1)
- **Existing placeholder origin:** `tauri/ui/assets/mascot/animations/PLACEHOLDER_NOTE.md` (Phase 22 lineage + idle-zero contract)

## Self-Check: PASSED

All 9 claimed files exist on disk in the worktree; all 4 claimed commit hashes (`823a8ad` RED, `d5f0c20` GREEN scaffold, `79084aa` bundle gate + manifest, `ccc5e13` §VIS-04 runbook) present in `git log --all`. Plan executed cleanly except for the procedural defect documented under Deviations §1 (stray commit on main repo). No missing items.
