---
gsd_plan_summary_version: 1.0
phase: 19
plan: 19-03
plan_name: README rewrite + docs/midi-mapping.md
status: completed
requirements: [GH-02, GH-03, GH-04, GH-05, GH-06, GH-07, GH-09, GH-10, GH-11, GH-12]
---

# Plan 19-03 — README Rewrite + MIDI Mapping Guide

## What landed

- `README.md` full rewrite — 12 sections in order per CONTEXT Area 1:
  1. Hero banner (`docs/assets/hero.png`)
  2. Tagline + value prop one-paragraph
  3. Demo GIF placeholder + TODO for real shoot
  4. Badges row (5 shields.io: release / build / license / platforms / stars)
  5. Audio-privacy callout (FAQ Q2 surfaced above the fold)
  6. Install table with macOS DMG + Windows MSI links to Releases page
  7. Feature matrix (3 skill × 2 mode, 2-3 example reactions per cell, blockquote style)
  8. Supported-controllers grid (5×2 table, 10 controllers, logo placeholders)
  9. Screenshots gallery (5 surface placeholders)
  10. "How it works" with embedded architecture SVG
  11. FAQ (12 verbatim questions from CONTEXT Area 3, headed)
  12. Bravoh footer with utm-tagged altidus.world/vibemix link
- `docs/midi-mapping.md` — generic MIDI fallback guide: 2 paths (generic vs curated), CC/note extraction with `mido`, JSON schema mirror of existing profiles, contribution submission flow.
- `tests/repo/test_readme_shape.py` — 44 tests covering: 12 FAQ questions, 10 controllers, 5 asset refs, Bravoh utm footer, banned-slop gate, ≥5 badges, install section shape, feature matrix cells, midi-mapping.md sections.

## Execution path

The original `gsd-executor` worktree-based attempt hit a stream-idle timeout mid-flight (likely due to the size of the rewrite + the many parameterized acceptance gates). Per fully-autonomous mode, the orchestrator wrote the README + midi-mapping + test directly in main since:
- All 12 FAQ entries are CONTEXT-verbatim (zero invention required)
- Controller list is fully derived from `src/vibemix/midi/profiles/*.json`
- Feature matrix example reactions are short, locked to the Phase 10 tone, anti-slop-clean

## Acceptance gates — all green

- `pytest tests/repo/test_readme_shape.py -q` → 44 passed
- README length 7.3 KB (well over the 5 KB completeness gate)
- All 12 FAQ questions present
- All 10 controllers named
- All 5 asset refs present
- Bravoh utm-tagged footer present
- Anti-slop gate: 0 banned phrases in README (mirrors negative_dict philosophy)
- ≥5 shields.io badges
- docs/midi-mapping.md has all 4 required H2 sections

## Requirements completed

- GH-02 (hero banner ref)
- GH-03 (demo video/GIF block — placeholder)
- GH-04 (install section + one-click buttons)
- GH-05 (feature matrix)
- GH-06 (supported-controllers grid)
- GH-07 (screenshots gallery placeholders)
- GH-09 (12-question FAQ)
- GH-10 ("Built by Bravoh" footer with utm)
- GH-11 (badges row)
- GH-12 (OG/social preview — placeholder reference, real asset Kaan-side)

## Files not shipped this plan

- Real controller logos at `docs/assets/controllers/<slug>.png` — Kaan + Momo design lead deliver post-phase
- Real screenshot PNGs at `docs/assets/screenshots/<surface>.png` — captured post-binary-ship
- Real 30-45s demo MP4/GIF — Kaan + Francesco shoot during a real set
- Real hero artwork — Bravoh design lead
- Real OG image — Bravoh design lead
