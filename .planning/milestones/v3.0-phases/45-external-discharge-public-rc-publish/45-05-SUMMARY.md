---
phase: 45-external-discharge-public-rc-publish
plan: 05
subsystem: launch-rotation
type: execute
wave: 1
autonomous: true
tags: [launch, rotation, monitoring, ship-11, docs, runbook]
requirements: [SHIP-11]
req_ids: [SHIP-11]
dependencies:
  requires:
    - "docs/launch-rotation.md (Phase 39 / SHIP-07) — v2.1 24-row hourly archive preserved as the predecessor"
    - "scripts/launch/check_no_ai_slop.py — canonical AI_SLOP_BLOCKLIST + _DEEPLY_RE imported as single source of truth"
    - "scripts/dayzero/healthz_check.sh (Phase 36) — referenced in monitoring sources block"
    - "scripts/release/check_bravoh_server_ready.sh (Plan 45-03) — referenced in triage tree + monitoring sources"
  provides:
    - "docs/launch-rotation.md §SHIP-11 — operational source-of-truth for v3.0 24h rotation"
    - "4 × 6h shift table (Kaan-solo; Francesco + Momo deferred to v3.x per CONTEXT §SHIP-11)"
    - "Triage decision tree (comment-volume / crash-report / API-key-rate-limit / Bravoh-server-down)"
    - "Monitoring signal sources enumerated (≥7 numbered sources, fresh-VM install flagged HIGHEST PRIORITY)"
    - "Sign-off block stub (6 SHIP-11 placeholders + Sign-off-by(Kaan)) for live discharge tracking"
    - "tests/launch/test_launch_rotation_ship_11.py — 9-test grep gate pinning all structural invariants"
  affects:
    - "KAAN-ACTION-LEGAL.md §SHIP-11 (Plan 45-06) — will cross-reference §SHIP-11 doc anchor for operational protocol"
tech_stack:
  added: []
  patterns:
    - "Append-only doc edit (89 insertions, 0 deletions) preserves Phase 39 v2.1 archive verbatim"
    - "Grep-gate CI test pinning structural invariants (Phase 44 pattern: check_readme_hero_lock, check_no_ai_slop, check_launch_docs)"
    - "Single-source-of-truth blocklist re-import (AI_SLOP_BLOCKLIST + _DEEPLY_RE from check_no_ai_slop.py)"
key_files:
  created:
    - tests/launch/test_launch_rotation_ship_11.py
  modified:
    - docs/launch-rotation.md
decisions:
  - "Append-only edit: §SHIP-11 H2 added AFTER existing `## References` H2 — Phase 39 v2.1 hourly archive preserved verbatim (Test 8 line-order assertion + Test 2 archive-preservation pin)"
  - "4-shift CET window mapping verbatim from CONTEXT §specifics: 08:00–14:00, 14:00–20:00, 20:00–02:00, 02:00–08:00 (Shift 4 = sleep-shift on alerts only)"
  - "Kaan-solo rotation for v3.0; Francesco + Momo defer to v3.x per CONTEXT §SHIP-11 explicit scope"
  - "Triage tree categorizes 4 incident classes (CONTEXT §SHIP-11): comment-volume / crash-report / API-key-rate-limit / Bravoh-server-down"
  - "Fresh-VM install issues flagged HIGHEST PRIORITY in monitoring sources, per project memory `one-click-install-hard-req`"
  - "AI-slop gate reuses canonical AI_SLOP_BLOCKLIST + _DEEPLY_RE via import (not CLI shell-out) — check_no_ai_slop.py's CLI is launch_copy-dir scoped, not arbitrary-doc scoped; import keeps single-source-of-truth without inventing a new CLI surface"
  - "Test count grew from plan-spec 7 to delivered 9: split out the line-order assertion (Test 8) and AI-slop gate (Test 9) into their own tests so RED→GREEN states are visible per concern"
metrics:
  duration_minutes: ~10
  completed: 2026-05-17
  tasks_complete: 2
  tasks_total: 2
  tests_added: 9
  tests_passing: 9
  files_changed: 2
  doc_lines_added: 89
  test_lines_added: 324
---

# Phase 45 Plan 05: docs/launch-rotation.md §SHIP-11 24h-rotation table + triage tree (SHIP-11) Summary

§SHIP-11 v3.0 monitoring rotation contract (4 × 6h Kaan-solo shifts + triage decision tree + 7 monitoring signal sources) appended to `docs/launch-rotation.md` and pinned by a 9-test grep gate, without touching the Phase 39 v2.1 hourly archive — operational source-of-truth for Plan 45-06's §SHIP-11 Kaan-discharge runbook now lives in one place.

## What shipped

### `tests/launch/test_launch_rotation_ship_11.py` (NEW — 324 lines)

A 9-test pytest suite that pins every structural invariant of the §SHIP-11 section. Tests 1-2 are the archive baseline (file exists + Phase 39 v2.1 24-row hourly table preserved verbatim — proof the append never damaged history). Tests 3-7 are the §SHIP-11 contract proper (H2 title, 4 canonical shift windows, triage tree H3 + 4 branches, monitoring sources H3 + ≥5 numbered sources, sign-off block with 6 SHIP-11 placeholders + Sign-off-by). Tests 8-9 are the append-only + AI-slop gates (§SHIP-11 H2 must appear AFTER the existing `## References` H2; section text passes the canonical `AI_SLOP_BLOCKLIST` + `_DEEPLY_RE` imported from `check_no_ai_slop.py`).

The AI-slop gate (Test 9) imports the canonical constants rather than shelling out — `check_no_ai_slop.py`'s CLI is scoped to the 5-file launch_copy directory, not arbitrary doc files. Importing the constants preserves single-source-of-truth behavior: if `AI_SLOP_BLOCKLIST` changes, this test inherits the change automatically.

### `docs/launch-rotation.md` (EDIT — +89 lines, 0 deletions)

Pure append. Below the existing `## References` H2 (which closes the Phase 39 v2.1 archive), a new top-level `## §SHIP-11 — v3.0 24h Monitoring Rotation (4 × 6h shifts, Kaan solo)` section carries:

- **Shift table** — 4 × 6h CET windows mapping each shift to T-offset, focus, and primary signals.
- **Triage decision tree** — code-block ASCII tree branching on comment-volume / crash-report / API-key-rate-limit / Bravoh-server-down with concrete in-line commands (`healthz_check.sh`, `check_bravoh_server_ready.sh`).
- **Monitoring signal sources** — 7 numbered sources, fresh-VM install issues flagged HIGHEST PRIORITY per memory `project_one_click_install_hard_req`.
- **Handoff format** — shift-level self-note template (vs. the v2.1 hourly Discord-post template above).
- **Post-24h transition + Sign-off block + References** — bake-period handoff and per-shift COMPLETE placeholders for Kaan to fill in live.

## Atomic commits

| Hash | Task | Type | Description |
| --- | --- | --- | --- |
| `1021efd` | Task 1 | test | Pin §SHIP-11 launch-rotation section structure (RED — 7/9 fail expected, 2/9 baseline passes) |
| `fa0b1b4` | Task 2 | docs | Append §SHIP-11 v3.0 rotation (4×6h Kaan solo) + triage tree + monitoring sources (GREEN — 9/9 pass) |

TDD gate sequence preserved per plan-level `type: execute` (Tasks individually `tdd="true"`): `test(45-05)` RED commit precedes `docs(45-05)` GREEN commit.

> Note: Original commit hashes were `eef9c42` (RED) and `1caa389` (GREEN). A parallel agent's branch checkout reset `plan-45-04` to `f1700db` mid-execution; both commits were rescued from reflog and cherry-picked back, producing new hashes above with identical content (verified via `wc -l` + 9/9 GREEN pytest).

## Verification results

- **9/9 tests GREEN** in `tests/launch/test_launch_rotation_ship_11.py` (Tests 1-9 all passing on `1caa389`).
- **89 insertions, 0 deletions** on `docs/launch-rotation.md` — proven append-only via `git diff --stat`.
- **§SHIP-11 H2 count = 1** (`grep -c "^## §SHIP-11"`).
- **4 Phase 39 v2.1 row anchors preserved** (`grep -c "^| 0[8-9]:00 | T"` returns 4 — covers 08:00 T-1, 09:00 T+0, 08:00 T+23, 09:00 T+24 rows).
- **AI-slop gate clean** — Test 9 passes; §SHIP-11 section contains zero `AI_SLOP_BLOCKLIST` tokens and zero `deeply <word>` constructions.

## Deviations from plan

### Auto-fixed Issues

**1. [Rule 1 - Plan/CLI mismatch] AI-slop gate via import instead of CLI shell-out**

- **Found during:** Task 2 verify step.
- **Issue:** Plan Task 2 `<verify>` calls `uv run python scripts/launch/check_no_ai_slop.py docs/launch-rotation.md` — but `check_no_ai_slop.py`'s CLI exposes only `--dir` (launch_copy directory scoped, expects the 5 social-channel files), not a single-file mode. Shell-out would have errored.
- **Fix:** Test 9 in `tests/launch/test_launch_rotation_ship_11.py` imports the canonical `AI_SLOP_BLOCKLIST` tuple + `_DEEPLY_RE` regex directly from `scripts/launch/check_no_ai_slop.py` and applies them only to the §SHIP-11 section text. This preserves single-source-of-truth behavior (the script's module docstring explicitly calls these constants out as the "single source of truth across the launch-check family") without inventing a new CLI surface or duplicating the token tuple.
- **Files modified:** `tests/launch/test_launch_rotation_ship_11.py` (Test 9 implementation).
- **Commit:** `1021efd` (RED phase already encoded the import-based gate; no second pass needed).

**2. [Rule 2 - Test coverage clarity] Test count grew from 7 to 9**

- **Found during:** Task 1 authoring.
- **Issue:** Plan §tasks lists 7 invariants for Task 1's RED gate (Tests 1-7), and Task 2 mentions Tests 8 + 9 added in GREEN. Splitting them across two commits would have meant Test 8 + 9 don't run RED before going GREEN — losing TDD discipline on those two assertions.
- **Fix:** All 9 tests ship in the Task 1 RED commit (`eef9c42`). Tests 1-2 pass at RED (baseline: file exists + Phase 39 archive preserved). Tests 3-9 fail at RED (§SHIP-11 missing). After Task 2 GREEN commit, all 9 pass. Each invariant gets a proper RED→GREEN transition.
- **Files modified:** `tests/launch/test_launch_rotation_ship_11.py` (9 tests instead of 7).
- **Commit:** `1021efd` (RED), `fa0b1b4` (GREEN).

### No other deviations

Plan executed otherwise verbatim. Section skeleton inserted line-for-line from the plan's `<section_skeleton>` block; Phase 39 archive untouched (proven by `git diff` showing zero deletions).

## Plan 45-06 hand-off

Plan 45-06 ships `KAAN-ACTION-LEGAL.md §SHIP-01..13` discharge cookbook. The §SHIP-11 section in that doc can now cross-reference `docs/launch-rotation.md` §SHIP-11 as the operational source-of-truth — specifically:

- "When SHIP-11 fires (T-0), refer to `docs/launch-rotation.md §SHIP-11` for shift table, triage tree, and monitoring sources."
- "Sign each shift's COMPLETE line in the §SHIP-11 sign-off block as you finish it."

No further doc-rotation work is required from Plan 45-06; just the cross-reference + Kaan-action runbook.

## Known Stubs

None. Sign-off block lines (`_____________`) are intentional fill-in placeholders for live Kaan discharge — they're operational artifacts, not unwired UI stubs.

## Self-Check: PASSED

- **Files exist:**
  - `tests/launch/test_launch_rotation_ship_11.py` — FOUND.
  - `docs/launch-rotation.md` — FOUND (191 lines, was 102; +89).
- **Commits exist:**
  - `1021efd` — FOUND in git log (RED, cherry-picked from original `eef9c42`).
  - `fa0b1b4` — FOUND in git log (GREEN, cherry-picked from original `1caa389`).
- **TDD gates:**
  - `test(45-05)` commit present (RED gate `1021efd`).
  - `docs(45-05)` commit present (GREEN gate `fa0b1b4`, immediately follows the RED test).
- **Tests:** 9/9 pass on HEAD.
- **Archive preservation:** Phase 39 v2.1 anchors (`## Per-hour shift (24h, all times CET)`, `| 08:00 | T-1`, `## References`) all present in `git diff` post-image; zero deletions in changeset.
