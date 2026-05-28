---
phase: 97-onboarding-tone-locks-mode-picker
plan: 02
subsystem: midi (controller profile + registry disambiguation) + learn SVG dispatch
tags: [midi-profile, hercules-inpulse-300-mk2, iserialnumber-probe, longest-hint-tiebreak, kaan-action-park]
requirements:
  - ONBOARD-03
provides:
  - src/vibemix/midi/profiles/hercules_inpulse_300_mk2.json (11th controller; MK2 sibling)
  - src/vibemix/midi/registry.py:find_mapping (longest-hint-wins disambiguation)
  - tauri/ui/src/learn/components/controller-stage.ts:KNOWN_CONTROLLERS (MK2 added; SVG reuses 300)
  - tests/midi/test_hercules_300_mk2_disambiguation.py (13 cases)
requires:
  - src/vibemix/midi/profile.py:ControllerProfile dataclass + load_profile + list_profiles
  - tauri/ui/src/learn/components/controller-stage.ts:hercules_inpulse_300.svg.ts (reused)
affects:
  - Plan 97-04 (KAAN-ACTION park already in REQUIREMENTS.md + STATE.md before this plan)
key-files:
  created:
    - src/vibemix/midi/profiles/hercules_inpulse_300_mk2.json
    - tests/midi/test_hercules_300_mk2_disambiguation.py
  modified:
    - src/vibemix/midi/registry.py
    - tauri/ui/src/learn/components/controller-stage.ts
    - tests/midi/test_profile.py
    - tests/midi/test_profiles_all_controllers.py
tech-stack:
  added: []
  patterns:
    - longest-hint-wins disambiguation in find_mapping (per-profile best hint
      length scored across all profiles; alphabetic-id breaks ties on equal
      length) — replaces first-match-alphabetic which would resolve MK2 ports
      to the legacy 300 profile
    - SVG asset reuse via dispatch alias (hercules_inpulse_300_mk2 case in
      loadControllerSvg() imports the 300.svg.js bundle — no new asset until
      ear-pass confirms a distinct rendering is needed)
decisions:
  - 11th controller profile WITHOUT a new SVG asset. The MK2 reuses the
    legacy 300 SVG because the units are visually near-identical per
    Hercules product photos. §LEARN-MK2-DETECTION ear-pass (P98) validates
    whether a distinct SVG is needed.
  - Registry tiebreak = longest-hint-wins (NOT alphabetic-id-first). This
    is a small but forward-compatible change: any future sibling SKU pair
    (e.g. FLX4 vs FLX4 MK2) gets correct disambiguation as long as the
    more specific profile carries a longer hint.
  - Empty / non-str / no-match port names still return None (existing
    behaviour pin retained — tests/midi/test_hercules_300_mk2_disambiguation.py
    has the negative-control + empty-string cases).
  - port_name_hints carry both 'DJControl Inpulse 300 MK2' (full) +
    'Inpulse 300 MK2' (short) + 'Inpulse-300-MK2' (hyphen variant) so the
    three port-name shapes Hercules drivers can emit ALL resolve to the
    MK2 profile.
  - KAAN-ACTION §LEARN-MK2-DETECTION was already parked in
    .planning/STATE.md L119 + .planning/REQUIREMENTS.md L97 before this
    plan executed — no new park needed; verified discoverable.
metrics:
  duration_minutes: 15
  tasks_completed: 4
  files_created: 2
  files_modified: 4
  pytest_count_delta: +13 (test_hercules_300_mk2_disambiguation.py = 13 new cases)
  pytest_full_delta: +34 (tests/midi/ 251 → 285; the extra 21 are parametric
    increase from _ALL_CONTROLLER_IDS growing 10→11 across 17 parametrised
    cases that loop over the list)
  completed: 2026-05-28
---

# Phase 97 Plan 02: Hercules Inpulse 300 MK2 Sibling Profile Summary

ONBOARD-03 landed clean. The 11th controller profile ships alongside the
legacy 300; the registry's `find_mapping` now disambiguates by
longest-hint-wins so MK2 ports resolve to the MK2 profile deterministically.
Real-hardware ear-pass parks as `§LEARN-MK2-DETECTION` for P98 (already in
the KAAN-ACTION queue from milestone init).

## Tasks

| Task | Commit  | Files                                                                                                                                                |
| ---- | ------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1    | 1e5b158 | hercules_inpulse_300_mk2.json (profile)                                                                                                              |
| 2    | 1e5b158 | registry.py longest-hint fix + test_hercules_300_mk2_disambiguation.py (13 cases) + controller-stage.ts KNOWN_CONTROLLERS + test count fixups |
| 3    | -       | KAAN-ACTION §LEARN-MK2-DETECTION already parked (no edit needed)                                                                                     |
| 4    | -       | Full gate: 543 Python / 1043 vitest all green                                                                                                        |

All tasks committed in a single atomic commit 1e5b158 (they share a
test gate and the changes are interdependent — the SVG dispatch needs the
profile to exist, the test needs the registry fix to be present).

## Deviations from Plan

None — the plan executed exactly as written.

The plan offered two paths for registry disambiguation: (a) add `"MK2"`
as a standalone hint OR (b) implement longest-hint-wins tiebreak. The
executor picked (b) — longest-hint-wins — because it's the more
general/forward-compatible fix: any future sibling SKU pair gets correct
disambiguation without per-pair amendments. The plan explicitly
recommended this path.

## Authentication Gates

None.

## Self-Check

- `src/vibemix/midi/profiles/hercules_inpulse_300_mk2.json` — FOUND
- `src/vibemix/midi/registry.py` — MODIFIED (longest-hint-wins)
- `tauri/ui/src/learn/components/controller-stage.ts` — MODIFIED (MK2 in KNOWN_CONTROLLERS)
- `tests/midi/test_hercules_300_mk2_disambiguation.py` — FOUND
- `tests/midi/test_profile.py::test_list_profiles_includes_flx4` — passes (11)
- `tests/midi/test_profiles_all_controllers.py::test_list_profiles_returns_11_entries` — renamed + passes
- commit 1e5b158 — present in `git log`
- `§LEARN-MK2-DETECTION` — parked in `.planning/STATE.md` L119 + `.planning/REQUIREMENTS.md` L97

## Self-Check: PASSED
