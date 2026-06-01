All data is confirmed and the structured output has been provided successfully. Here is my summary of the dirty→package-lane mapping for branch `live-tuning-or-brain`.

## Command result
`uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary` → **RC=1 (strict-red FAIL)**.

## The 5 UNASSIGNED (strict-red) dirty paths
1. `codesign0`
2. `codesign1`
3. `codesign2`
4. `scripts/eval/judge.py`
5. `tests/eval/test_judge_pro_rubric.py`

These are the only paths in no Include/Hold lane across all 52 sections of `.planning/handoffs/2026-05-31-package-checklist.md`. Every other ~180 dirty paths map to a lane, so RED is caused solely by these 5.

## Key finding the name hides
`codesign0/1/2` are **NOT junk scratch** — `file` + `strings` show they are real Apple X.509 Developer ID signing certificates ("Developer ID Application: Francesco Fasanella (UK7DYFK6F8)"), and `git check-ignore` returns rc=1 (not ignored). They appear as `??` untracked, so a `git clean -fd` would permanently delete them. Triage before cleaning; never commit private-key material.

## At-risk capabilities = (high-value uncommitted) × (test coverage?) × (lane?)
| Capability | Files (status) | Tests | Lane | Loss mode |
|---|---|---|---|---|
| AI-message observability | `runtime/ai_observability.py`, `learn/observability.py`, `scripts/verify_ai_observability.py` (all `??`) | yes (`test_ai_observability.py`, `test_verify_ai_observability.py`) | Hold Lane L551-587 | **clean deletes; absent from clone** |
| Live-stack cost/pricing | `library/cost.py`, `library/pricing.py` (`??`) | yes | Package 10 L1424-1430 | clean deletes (+ tracked `__main__.py` hunks revert on stash) |
| Serato cue / cue-folder export | `library/export_serato.py`, `library/cue_folder.py` (`??`) | yes | Hold Lanes L649-673 / L1266-1273 | clean deletes |
| Judge-rubric eval | `scripts/eval/judge.py`, `tests/eval/test_judge_pro_rubric.py` (` M`) | yes | **NONE (strict-red)** | survives clean; **lost on stash/checkout** |
| Judge Voice evidence | `intel/judge_voice.py` + `test_judge_voice.py` (both `??`) | yes | Hold Lane L717-735 | **both halves vanish on clean** |
| Drop event detector | `state/event_detector.py` (` M`) + `test_event_detector_drop.py` (`??`) | yes | Mix Timing Oracle L2128-2178 | test deleted on clean |
| Coach progress emit | `runtime/coach.py` (` M`) + `test_coach_progress_emit.py` (`??`) | yes | Package 9 L1345 | test deleted on clean |

## Fresh-clone breakage
A clone of `origin/live-tuning-or-brain` would lack all ~40 untracked paths (8+ product modules with tests) and none of the ~145 uncommitted modifications. Packages 2/3 modify the generated IPC trio (`messages.schema.json` / `messages.ts` / `validator.generated.mjs`) — a clone carries the stale codegen baseline until `npm --prefix tauri/ui run check:ipc` regenerates.

## Recommended sequence
1. Triage `codesign0/1/2` (signing certs → secure store or gitignore).
2. Assign `judge.py` + `test_judge_pro_rubric.py` to a lane → flips RC to 0.
3. Commit / `stash --include-untracked` the untracked lane files before any clean.

The loss surface is bounded and enumerable, not chaotic.
