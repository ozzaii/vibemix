---
phase: 97-onboarding-tone-locks-mode-picker
plan: 03
subsystem: wizard headphone picker + audio-routing doc + progress list + disclaimer
tags: [wizard, headphone-picker, audio-routing-doc, progress-list-ui, disclaimer, trademarks]
requirements:
  - ONBOARD-04
  - ONBOARD-05
  - ONBOARD-06
  - ONBOARD-07
  - RENDER-08
provides:
  - tauri/ui/src/wizard/step2-output-device.ts (headphone picker section + Step2State.selectedHeadphoneDeviceIndex)
  - tauri/ui/src/learn/lesson/progress-list.ts (component + setStatus helper)
  - tauri/ui/src/learn/lesson/curriculum-meta.ts (frontend 36-lesson mirror)
  - tauri/ui/src/learn/learn-window.ts:TRADEMARK_DISCLAIMER (verbatim constant + footer mount)
  - docs/audio-routing.md (3-recipe guide + §LEARN-AUDIO-ROUTING-WIZARD-DISCHARGE park)
  - README.md:## Trademarks (verbatim disclaimer section)
  - tests/learn/test_disclaimer_present.py (4 cases gate disclaimer)
  - tauri/ui/tests/wizard/test_step2_headphone_picker.spec.ts (9 cases)
  - tauri/ui/tests/learn/test_progress_list.spec.ts (17 cases)
requires:
  - tauri/ui/src/wizard/components/dropdown-device.ts (DropdownDevice reused)
  - tauri/ui/src/ipc/messages.schema.json:learn.headphone_device_index (P93)
  - src/vibemix/learn/curriculum.py (authoritative — mirrored)
affects:
  - Plan 97-04 (KAAN-ACTION parks already discoverable; surfaces SUMMARY content)
key-files:
  created:
    - tauri/ui/src/learn/lesson/progress-list.ts
    - tauri/ui/src/learn/lesson/curriculum-meta.ts
    - tauri/ui/tests/learn/test_progress_list.spec.ts
    - tauri/ui/tests/wizard/test_step2_headphone_picker.spec.ts
    - docs/audio-routing.md
    - tests/learn/test_disclaimer_present.py
  modified:
    - tauri/ui/src/wizard/step2-output-device.ts (headphone picker section)
    - tauri/ui/src/wizard/router.ts (Step2State default + callback wiring)
    - tauri/ui/src/learn/learn-window.ts (progress list + footer + disclaimer mount)
    - tauri/ui/src/learn/styles/learn.css (vmx-progress-list + host + footer styles)
    - README.md (Trademarks section)
tech-stack:
  added: []
  patterns:
    - DropdownDevice reuse for the headphone picker (no new component;
      pseudo-option "[ system default ]" mapped to deviceIndex=null)
    - Frontend curriculum-meta mirror as a TS constant (authoritative
      source = curriculum.py; future P98 drift gate will assert parity)
    - Component-internal setStatus updater for in-place dot refresh
      (avoids full re-render on per-lesson status diffs)
    - Source-scan test gates (test_disclaimer_present.py walks
      tauri/ui/src/learn/**/*.ts; same shape as existing scripts/launch
      anti-slop gates)
    - Doc-only KAAN-ACTION discharge (§LEARN-AUDIO-ROUTING-WIZARD-
      DISCHARGE — docs/audio-routing.md ships the 3-recipe guide; future
      wizard plan automates Recipe 2 / 3)
decisions:
  - The headphone picker DOES NOT gate the wizard Continue button —
    windowSelected (existing contract) stays the sole armer. The picker
    is optional / side-affordance / skippable.
  - The "[ system default ]" pseudo-option lives at the TOP of the
    dropdown (before any real device) so a user who unsets a previous
    pick lands back at the safe default visually.
  - Frontend curriculum mirror = TS const (NOT a Python-to-TS codegen
    step). Defensible because the 36-lesson set is locked at milestone-
    scope. Future drift gate (P98 CI test) will assert ID/title/course
    parity against curriculum.py.
  - lesson_id format: short_id (L1.NN) + "-" + slug (e.g.
    "L1.01-opening-dialog"). Matches the schema regex
    ^L[0-9]+\\.[0-9]+-.+$ in messages.schema.json. Authoritative slug
    derivation lives in lessonIdWithSlug() — a single function call so
    every emit site uses the same shape.
  - Progress list HIDES on lesson_loaded (HUD takes over) and SHOWS on
    complete_lesson. The data-visible attribute drives CSS display
    (avoids layout shift across the toggle).
  - Disclaimer copy: VERBATIM (do not paraphrase). Same fragment in app
    footer + README + 4 test assertions. If a refactor strips it from
    either surface, test_disclaimer_present.py reds.
metrics:
  duration_minutes: 45
  tasks_completed: 6
  files_created: 6
  files_modified: 5
  pytest_count_delta: +4 (test_disclaimer_present.py = 4 new cases)
  vitest_count_delta: +26 (1043 → 1069: +9 wizard + +17 progress-list)
  completed: 2026-05-28
---

# Phase 97 Plan 03: Wizard + Audio Routing + Progress List + Disclaimer Summary

ONBOARD-04 + ONBOARD-05 + ONBOARD-06 + ONBOARD-07 + RENDER-08 all
landed clean. The wizard step 2 now carries a tutor-exemplar-playback
headphone picker; the Learn window mounts a 36-lesson progress list
between the stage and the footer; the trademark disclaimer rides in
both surfaces (Learn footer + README) and is gated by a fresh test
suite.

## Tasks

| Task | Commit  | Files                                                                              |
| ---- | ------- | ---------------------------------------------------------------------------------- |
| 1    | 81306cb | step2-output-device.ts + router.ts + test_step2_headphone_picker.spec.ts (9 tests) |
| 2    | 9d4c1ff | docs/audio-routing.md (3 recipes + KAAN-ACTION park comment)                       |
| 3    | 628d67e | progress-list.ts + curriculum-meta.ts + learn-window.ts mount + 17 tests           |
| 4    | 9d4c1ff | README.md Trademarks section (verbatim disclaimer)                                 |
| 5    | 9d4c1ff | tests/learn/test_disclaimer_present.py (4 cases)                                   |
| 6    | -       | Full gate: 837 pytest / 1069 vitest / cargo check all green                        |

## Deviations from Plan

None — the plan executed exactly as written.

Two surgical micro-decisions documented as decisions above (not
deviations):

- Progress-list CSS lives in `tauri/ui/src/learn/styles/learn.css` (the
  existing learn-side global stylesheet) instead of using the
  session-side `registerStyle` registry. The learn-window bundle has a
  single CSS surface; introducing the session-side registry there would
  fork the styling model.
- Frontend curriculum mirror is a TS constant (NOT a codegen step from
  curriculum.py). The 36-lesson set is locked at milestone scope; the
  drift cost is low. A future P98 CI test will assert parity.

## Authentication Gates

None.

## KAAN-ACTION parks

- `§LEARN-AUDIO-ROUTING-WIZARD-DISCHARGE` — already parked in
  `.planning/REQUIREMENTS.md` L98 (BlackHole + Multi-Output Device
  wizard automation; docs/audio-routing.md ships the manual recipe).
- `§LEARN-ONBOARD-EAR-PASS` — Plan 97-04 parks this for the full
  first-launch stranger-walk on real FLX4 hardware.

## Self-Check

- `tauri/ui/src/wizard/step2-output-device.ts` — MODIFIED (headphone picker section)
- `tauri/ui/src/wizard/router.ts` — MODIFIED (Step2State default + callback)
- `tauri/ui/src/learn/lesson/progress-list.ts` — FOUND
- `tauri/ui/src/learn/lesson/curriculum-meta.ts` — FOUND
- `tauri/ui/src/learn/learn-window.ts` — MODIFIED (mount + disclaimer)
- `tauri/ui/src/learn/styles/learn.css` — MODIFIED (vmx-progress-list + footer)
- `docs/audio-routing.md` — FOUND
- `README.md` — MODIFIED (Trademarks section)
- `tests/learn/test_disclaimer_present.py` — FOUND (4 cases green)
- `tauri/ui/tests/wizard/test_step2_headphone_picker.spec.ts` — FOUND (9 cases green)
- `tauri/ui/tests/learn/test_progress_list.spec.ts` — FOUND (17 cases green)
- commits 81306cba / 628d67e8 / 9d4c1ff5 — all in `git log`

## Self-Check: PASSED
