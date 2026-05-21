---
phase: 57-sexify-finish
plan: 02
subsystem: wizard-firstrun
tags: [polish, first-run, friction-audit, continuity-smoke, wizard]
requires:
  - "tauri/ui/src/wizard/router.ts (STEP_ORDER, advanceTo, currentStep, getDevSurface)"
  - "scripts/audit/check_no_slop_install.py (anti-slop gate)"
provides:
  - "docs/internal/first-run-friction-audit.md — mapped fresh-account flow + installer-step resolution"
  - "tauri/ui/src/wizard/__tests__/first-run-continuity.spec.ts — headless no-dead-end smoke"
affects:
  - "Phase 58 (sidecar binary rebuild surfaced as a dependency, not done here)"
tech-stack:
  added: []
  patterns:
    - "Headless wizard-chain drive: mock @tauri-apps/api/core + /event + ipc/client, drive advanceTo/currentStep, assert render + forward affordance per step"
    - "Gated-then-armable continuity contract (permissions gates until grants land, then arms)"
key-files:
  created:
    - "docs/internal/first-run-friction-audit.md"
    - "tauri/ui/src/wizard/__tests__/first-run-continuity.spec.ts"
  modified: []
decisions:
  - "forewarning/driver-fetch/48k-probe are Phase 49 installer-companion steps — intentionally absent from in-app STEP_ORDER, NOT wired in"
  - "No code-fixable friction found beyond the continuity smoke — clean-walk outcome, no router/copy edits invented"
  - "Sidecar binary rebuild deferred to Phase 58 (REL-01 ship-artifact territory)"
metrics:
  duration: "~25m"
  tasks: 2
  files: 2
  completed: "2026-05-21"
---

# Phase 57 Plan 02: First-Run Friction Audit + Continuity Smoke Summary

POLISH-03 — audited the fresh-account first-run → first-session flow, found a clean walk with no code-fixable friction, resolved the absent-installer-step question (Phase 49 installer-companion, intentionally out of the in-app `STEP_ORDER`), and pinned the no-dead-end property with a headless continuity smoke (711 → 716 vitest green).

## What was built

**Task 1 — Friction audit (`docs/internal/first-run-friction-audit.md`):**
- Mapped the in-app wizard chain `intro → permissions → audio → controller → profile-consent → telemetry-consent → smoke-test → [Open vibemix] → live session` with a per-step disposition table. Every step has a forward affordance; all disposition NOT-A-GAP.
- Resolved RESEARCH Open Question 3: `step-forewarning.ts` (Phase 49 INSTALL-03), `step-driver-fetch.ts` (INSTALL-01/02/04/06), `step-48k-probe.ts` (INSTALL-10) are installer-companion steps tied to the one-click-install lifecycle (driver fetch / system-extension+UAC approval / post-install format check). They are intentionally absent from the in-app `STEP_ORDER` — the in-app `audio` step already covers BlackHole/device/audio-probe, so wiring them in would duplicate the surface and add friction. The router type comment (router.ts:50-53) confirms they tie to install lifecycle (plan-49-04). No router/STEP_ORDER edit made.
- Documented the two historically-stranding cases that are already closed: the `audio` step Continue no longer requires `audioPassed` (arms on `windowSelected`), and the `smoke-test` Open-CTA arms even on greeting cascade failure.
- Confirmed the `permissions` step is gated-then-armable (not a dead-end): Continue stays disabled until both grants land, with discoverable recovery (Grant buttons + Open-Settings deep-links + 1Hz poll). vibemix genuinely cannot run without mic + screen-recording, so the gate is correct.
- Confirmed the persisted `visible:false` mascot recovery (tray Toggle Mascot) exists; not a fresh-account gap.
- Surfaced the sidecar-binary staleness as a Phase 58 dependency and the real fresh-account walk + Privacy-list check as KAAN-ACTION.

**Task 2 — Continuity smoke (`tauri/ui/src/wizard/__tests__/first-run-continuity.spec.ts`):**
- 5 tests driving the router across the full `STEP_ORDER` chain. For each step asserts (a) it renders into `#wizard-primary` and (b) an enabled forward affordance exists. Drives gated steps into their armed state (the sidecar-success analogue) and asserts the gate releases.
- Asserts the chain reaches `smoke-test` and the `Open vibemix` wizard-done CTA is reachable (not disabled).
- Pins the gated-then-armable contract explicitly: a separate test proves `permissions` Continue is disabled when ungranted, then arms when both grants land.
- Headless: `@tauri-apps/api/core`, `@tauri-apps/api/event`, and `../../ipc/client.js` are mocked so it runs under the default `npm test` (jsdom, no watch flag, no opt-in marker).

## How it was verified

- `python3 scripts/audit/check_no_slop_install.py` → OK, 10 targets clean (and the audit doc itself passes the slop gate after replacing a banned token).
- `cd tauri/ui && npm test` → 716 passed (76 files), up from the 711 baseline, no regressions.
- `cd tauri/ui && npm test -- first-run-continuity.spec.ts` → 5 passed.
- `git diff --name-only b0bfff4..HEAD` → exactly the two new files; no Kaan WIP file (`mascot_window.rs`, `tauri.conf.json5`, `__main__.py`, `dj_cohost.py`, `constants.py`, `matrix.py`, `tests/agent/*`) touched; sidecar IPC contract (`runtime/wizard.py`) unchanged.

## Deviations from Plan

**Scope reduction (valid clean-walk outcome, plan-sanctioned):** The plan's `files_modified` listed `router.ts`, `copy.json`, and `copy.ts` as potential edit targets. The audit found NO code-fixable friction beyond the continuity smoke — every step already has a forward affordance, the two stranding cases were already closed, and the installer-step question resolved to "intentional, out of flow." Per the plan's scope guardrail ("If the audit finds NO code-fixable friction beyond the continuity smoke, that is a valid outcome — document the clean walk; do not invent edits"), no router/copy edits were made. The committed diff is the two new artifacts only.

No auto-fixes (Rules 1-3) were triggered — the audited surface was already correct. No authentication gates encountered.

## Known Stubs

None. The two new artifacts are complete (a doc and a passing test suite); no placeholder data or unwired surfaces introduced.

## KAAN-ACTION (not auto-completed)

- Real fresh macOS account first-run → first-session-with-audio walk — the felt "no friction / no dead-ends" sign-off (engineering proved continuity headlessly; the lived walk is Kaan's).
- macOS Privacy-list population on a truly fresh account (OS-registration state; prime path is wired).
- Sidecar binary rebuild — Phase 58 ship-artifact dependency (documented in the audit; surface if the live walk hits log lag).

## Self-Check: PASSED

- FOUND: docs/internal/first-run-friction-audit.md
- FOUND: tauri/ui/src/wizard/__tests__/first-run-continuity.spec.ts
- FOUND commit d2c4e1f (Task 1 — friction audit doc)
- FOUND commit cc08cfb (Task 2 — continuity smoke)
