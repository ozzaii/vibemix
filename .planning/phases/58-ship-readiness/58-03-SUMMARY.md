---
phase: 58-ship-readiness
plan: 03
subsystem: release/kaan-action
tags: [release, kaan-action, ship-cut, cookbook, REL-03]
requires:
  - "KAAN-ACTION-LEGAL.md §SHIP-CUT runbook (existing, this file)"
  - "DIST-09 / DIST-11 sign-off blocks (existing)"
  - "scripts/launch/check_no_ai_slop.py::AI_SLOP_BLOCKLIST (canonical)"
provides:
  - "§SHIP-V4 — Consolidated v4.0 Ship Surface (single discharge map)"
  - "tests/repo/test_kaan_action_v4_surface.py (completeness + anti-slop + P46 pin)"
affects:
  - "KAAN-ACTION-LEGAL.md (append-only)"
tech-stack:
  added: []
  patterns:
    - "Canonical 8-block KAAN-ACTION section format"
    - "importlib-loaded canonical AI_SLOP_BLOCKLIST (no hand-copied duplicate)"
    - "hard-coded open-item token list as a STATE-drift guard"
key-files:
  created:
    - "tests/repo/test_kaan_action_v4_surface.py"
  modified:
    - "KAAN-ACTION-LEGAL.md"
decisions:
  - "Extended the canonical cookbook (single source of truth) with a dated §SHIP-V4 section rather than a sibling 58-KAAN-ACTION.md — per RESEARCH recommendation."
  - "Public tag surfaced as v0.1.0-rc1 (recommended) with v4.0.0-rc1 a one-line override — confirm, NOT a blocker (CONTEXT decision)."
  - "SignPath cert documented as ONE shared cert across INSTALL-COMPANION-SIGN + DIST-11 + this ship — not double-counted."
metrics:
  duration: "~15 min"
  completed: 2026-05-21
  tasks: 2
  files: 2
---

# Phase 58 Plan 03: Consolidated v4.0 Ship Surface Summary

One dated `§SHIP-V4` section in the canonical `KAAN-ACTION-LEGAL.md` cookbook now maps every open external-clock + Kaan-action discharge item between engineering-green v4.0 and a live public release — cross-referencing (never re-writing) the existing §SHIP-CUT runbook, pinned against STATE drift by a completeness test.

## What shipped

- **`§SHIP-V4 — Consolidated v4.0 Ship Surface (2026-05)`** appended to `KAAN-ACTION-LEGAL.md` in the canonical 8-block format (header / who / pre-req / discharge commands / public-tag confirm / verification / post-discharge / unblocks / fenced sign-off). It:
  - Cross-references the existing §SHIP-CUT 9-step runbook (points at it; does NOT re-type the 9 steps or the `gh release create` command).
  - Enumerates every open discharge item with owner + status + pointer: DIST-09 (Apple, Francesco), DIST-11 / §INSTALL-COMPANION-SIGN (SignPath — flagged as ONE shared cert), 54-HUMAN-UAT + 55-HUMAN-UAT ear-passes (Gate 2b feed), §E2E-50A-WALK → `docs/e2e/2026-05-walk.webm` (Gate 6b feed), §INSTALL-VM-RUN, §VIS-04 / §VIS-05, §SHIP-CONTACT-VBAUDIO, DEPS-08.
  - Surfaces the public-tag Kaan-confirm: `v0.1.0-rc1` recommended; `v4.0.0-rc1` is a one-line TAG_REGEX override (confirm, not blocker).
  - States the Gate-5b precondition: Bravoh prod server up + `/vibemix/healthz` fresh (≤10 min) via `check_bravoh_server_ready.sh`.
  - Carries a canonical fenced sign-off block (`_____` placeholders + `Sign-off by`). No POST/PUT to apple/signpath (P46).
- **`tests/repo/test_kaan_action_v4_surface.py`** (7 tests) — pins: section exists once; every open-item token present (hard-coded drift guard); SHIP-CUT cross-reference with no 9-step duplication; `v0.1.0-rc1`/`v4.0.0-rc1` confirm + `healthz` Gate-5b precondition; anti-slop clean via importlib-loaded canonical `AI_SLOP_BLOCKLIST`; sign-off block present; P46 no-external-POST guard.

## Verification

- `grep "SHIP-V4" KAAN-ACTION-LEGAL.md` + `grep "SHIP-CUT"` — both match.
- Scoped anti-slop scan of the §SHIP-V4 section (mirrors the test): 0 blocklist hits, 0 `deeply <word>` hits.
- `pytest tests/repo/test_kaan_action_v4_surface.py -q` — 7 passed.
- `pytest tests/repo/test_kaan_action_ship_runbooks.py -q` — 17 passed (append-only / byte-preservation invariant for all pre-existing content holds).

## Deviations from Plan

### Tooling note (not a code deviation)

- The plan's Task-1 `<verify>` command `python3 scripts/launch/check_no_ai_slop.py KAAN-ACTION-LEGAL.md` does not run as written: the checker CLI takes `--dir`/`--audit-md`, not a positional path (it exits 2 on the positional arg, and `--audit-md` scans a fixed directory set that has pre-existing known false positives in the slop-checker scripts themselves — unrelated to this plan). The anti-slop guarantee was instead enforced exactly as the plan's Task-2 acceptance criteria specify: import the canonical `AI_SLOP_BLOCKLIST` and scan only the appended §SHIP-V4 section. Result: clean (0 hits). No change to the checker.

No code-behavior deviations. The plan executed as written.

## Kaan-action surface

This plan DOCUMENTS the discharge items; it never attempts a signature (P46). Every listed item — Apple Dev Agreement (Francesco), SignPath OSS cert (Kaan, shared with v3.x), the §E2E-50A-WALK recording, the 54+55 ear-passes, the public-tag confirm, the Gate-5b Bravoh precondition — is a Kaan/Francesco/external-clock action surfaced in §SHIP-V4.

## Self-Check: PASSED

- FOUND: KAAN-ACTION-LEGAL.md (§SHIP-V4 present)
- FOUND: tests/repo/test_kaan_action_v4_surface.py
- FOUND commit bb10c93 (Task 1)
- FOUND commit 11ee834 (Task 2)
