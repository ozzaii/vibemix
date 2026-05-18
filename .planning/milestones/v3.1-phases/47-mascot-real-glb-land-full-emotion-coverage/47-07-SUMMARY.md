---
phase: 47-mascot-real-glb-land-full-emotion-coverage
plan: 07
subsystem: mascot
tags: [mascot, readme-hero, render, ci]

requires:
  - phase: 47-mascot-real-glb-land-full-emotion-coverage
    plan: 05
    provides: react_hype_peak.glb placeholder + manifest entry
provides:
  - docs/assets/readme-hero.{png,webm} placeholder hero assets so README embed does not 404
  - scripts/mascot/render_readme_hero.sh render-time CLI (regenerates from react_hype_peak.glb after VIS-04 discharge)
  - .github/workflows/readme-hero-sync.yml extended with Phase 47 / MASCOT-07 asset-exists + size-guard step
affects: [47-08, MASCOT-07]

tech-stack:
  added: []
  patterns:
    - Placeholder hero pattern (1.4 KB PNG / 2.9 KB WebM) — locked-verbatim Phase 44 README text references these
    - 50 KB PNG / 100 KB WebM size guards in CI

key-files:
  created:
    - docs/assets/readme-hero.png
    - docs/assets/readme-hero.webm
    - scripts/mascot/render_readme_hero.sh
    - tests/mascot/test_readme_hero_assets.py
  modified:
    - .github/workflows/readme-hero-sync.yml

key-decisions:
  - "Placeholder hero PNG + WebM ship in-repo at minimal byte cost (~4 KB combined) so README references do not 404"
  - "render_readme_hero.sh is the post-VIS-04 regeneration tool — Kaan invokes when react_hype_peak.glb has real Mixamo content"
  - "CI gate asserts both assets exist + within 50 KB / 100 KB ceilings"

patterns-established:
  - "Render scaffold pattern: placeholder asset + render-on-demand script + CI guard — works for any animated hero asset"

requirements-completed:
  - MASCOT-07

duration: 5min
completed: 2026-05-18
---

# Phase 47, Plan 07: README Hero Render Scaffold Summary

**Shipped placeholder docs/assets/readme-hero.{png,webm} so the locked Phase 44 README hero text does not 404 to dead assets, plus the render-time CLI to regenerate them from react_hype_peak.glb after Kaan §VIS-04 discharge, plus a CI gate that asserts both assets exist alongside size ceilings.**

## Performance

- **Duration:** 5 min (resume-from-stalled-state)
- **Tasks:** 4
- **Files modified:** 5
- **Tests added:** 7 (test_readme_hero_assets.py)

## Accomplishments

- `docs/assets/readme-hero.png` placeholder ships at 1.4 KB.
- `docs/assets/readme-hero.webm` placeholder ships at 2.9 KB.
- `scripts/mascot/render_readme_hero.sh` — render-on-demand CLI: builds Tauri UI → loads `react_hype_peak.glb` in headless browser → captures PNG + WebM → writes back to `docs/assets/`.
- `.github/workflows/readme-hero-sync.yml` extended with Phase 47 / MASCOT-07 step: asserts both assets exist + within 50 KB PNG / 100 KB WebM ceilings.
- 7 pytest tests pin: both assets present, byte sizes within ceilings, render script executable, hash file present.

## Files Created/Modified

- `docs/assets/readme-hero.png` — 1.4 KB placeholder
- `docs/assets/readme-hero.webm` — 2.9 KB placeholder
- `scripts/mascot/render_readme_hero.sh` — render-on-demand CLI (executable)
- `.github/workflows/readme-hero-sync.yml` — extended with Phase 47 asset-exists + size guards
- `tests/mascot/test_readme_hero_assets.py` — 7 asset-shape tests

## Decisions Made

- Placeholder assets are intentionally tiny (~4 KB combined) — minimal repo bloat while solving the 404 problem.
- Render script targets `react_hype_peak.glb` specifically (the Phase 47 reaction family's peak-energy clip — README hero anchor per `MIXAMO-CLIP-SOURCES.md`).
- CI ceilings (50 KB PNG, 100 KB WebM) set deliberately tight — post-discharge real renders should still fit comfortably (Mixamo retargets compress well via draco).

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

- Plan 47-08 (CI audit aggregation) consumes the new readme-hero-sync.yml step as part of the unified mascot-audit signal.
- Kaan-action §VIS-04 discharge: run `bash scripts/mascot/render_readme_hero.sh` after `react_hype_peak.glb` ships real Mixamo content.

---
*Phase: 47-mascot-real-glb-land-full-emotion-coverage*
*Completed: 2026-05-18*
