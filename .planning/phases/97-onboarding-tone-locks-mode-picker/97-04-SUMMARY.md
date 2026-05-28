---
phase: 97-onboarding-tone-locks-mode-picker
plan: 04
subsystem: KAAN-ACTION park + Phase 97 close
tags: [kaan-action-park, summary-only]
requirements: []
provides:
  - .planning/REQUIREMENTS.md:§LEARN-ONBOARD-EAR-PASS (P98 ride-forward)
  - .planning/STATE.md:§LEARN-ONBOARD-EAR-PASS (non-blocking carry-forward)
requires: []
affects:
  - P98 ear-pass discharge (this park IS the ear-pass requirement)
key-files:
  created: []
  modified:
    - .planning/REQUIREMENTS.md
    - .planning/STATE.md
tech-stack:
  added: []
  patterns:
    - Inline blockquote park (REQUIREMENTS.md uses `> **`§LEARN-NAME`...**` block
      between sibling REQ-IDs to surface ear-pass items without disrupting the
      flat checkbox list)
decisions:
  - Single inline park instead of a dedicated KAAN-ACTION section table.
    The existing REQUIREMENTS.md already has the convention of mentioning
    §LEARN-* discharges inline next to the related REQ-ID. Adding a separate
    table would fork the discovery surface; users CTRL-F for §LEARN- and
    find them all in one document.
  - §LEARN-ONBOARD-EAR-PASS is the SINGLE Phase 97 ride-forward (the
    plan's only sub-KAAN-ACTION). §LEARN-MK2-DETECTION (Plan 97-02) and
    §LEARN-AUDIO-ROUTING-WIZARD-DISCHARGE (Plan 97-03) were already in
    the milestone queue before Phase 97 started — they survived the
    plan; this SUMMARY just notes their continued presence.
metrics:
  duration_minutes: 5
  tasks_completed: 1
  files_created: 0
  files_modified: 2
  pytest_count_delta: 0
  vitest_count_delta: 0
  completed: 2026-05-28
---

# Phase 97 Plan 04: KAAN-ACTION Park Summary

Phase 97 wrap-up. `§LEARN-ONBOARD-EAR-PASS` parked in REQUIREMENTS.md +
STATE.md so P98 picks it up as part of the v9.0 ear-pass queue.

## KAAN-ACTION queue at Phase 97 close

| Park                                          | Source            | P98 owner |
| --------------------------------------------- | ----------------- | --------- |
| `§LEARN-MK2-DETECTION`                        | Plan 97-02        | Kaan      |
| `§LEARN-AUDIO-ROUTING-WIZARD-DISCHARGE`       | Plan 97-03        | Kaan      |
| `§LEARN-ONBOARD-EAR-PASS`                     | Plan 97-04 (this) | Kaan      |

## §LEARN-ONBOARD-EAR-PASS — full discharge contract

A stranger opens vibemix on a fresh-install Mac → sees the 4-mode picker
(cohost / learn / build / debrief) → picks Learn → plugs FLX4 (or 300
MK2) → tutor announces by name with "let's go." closer → L1.01 verbatim
dialog plays through → the lesson progress list shows the next 35
lessons (Course 1 / 2 / 3) with empty dots → no AI-slop language
anywhere → disclaimer footer visible.

ALL FIVE bullets must pass real-stranger ear; cannot be self-verified.

## Self-Check

- `.planning/REQUIREMENTS.md` — MODIFIED (§LEARN-ONBOARD-EAR-PASS added at L103)
- `.planning/STATE.md` — MODIFIED (§LEARN-ONBOARD-EAR-PASS added to non-blocking list L120)
- `§LEARN-MK2-DETECTION` — still in STATE.md L119 + REQUIREMENTS.md L97 (Plan 97-02 KAAN-ACTION)
- `§LEARN-AUDIO-ROUTING-WIZARD-DISCHARGE` — still in STATE.md L115 + REQUIREMENTS.md L98 (Plan 97-03 KAAN-ACTION)

## Self-Check: PASSED
