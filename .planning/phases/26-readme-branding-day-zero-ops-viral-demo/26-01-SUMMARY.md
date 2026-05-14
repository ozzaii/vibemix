---
phase: 26
plan: "01"
subsystem: docs / branding
tags: [readme, branding, anti-slop, cdj-whisper, launch-prep]
requires: [phase-19 hero PNG + architecture SVG]
provides: [README anti-slop hook, BRANDING.md visual direction doc, docs/branding/logo.svg placeholder]
affects: [public repo front door]
tech_stack_added: []
tech_stack_patterns: [SVG XML comment syntax (no double-hyphen)]
key_files_created:
  - BRANDING.md
  - docs/branding/logo.svg
key_files_modified:
  - README.md
decisions:
  - "README rewrite is surgical, not destructive — existing structure (hero, install, feature matrix, controllers, screenshots, how-it-works, FAQ) preserved; lede paragraph + community PR call added."
  - "BRANDING.md establishes CDJ Whisper as the canonical visual direction with mocks/vibemix-direction-final.html as the live reference. Hard no-list documents the slop patterns to reject in PR review."
  - "Logo SVG ships as text-based placeholder; designer-finalized logo is a Kaan-action item post-v2.0 (tracked in KAAN-ACTION.md)."
metrics:
  duration_minutes: ~15
  completed_date: "2026-05-14"
  tasks_completed: 3
  files_created: 2
  files_modified: 1
---

# Phase 26 Plan 01: README Anti-Slop Hook + BRANDING.md + Placeholder Logo

One-liner: **README now leads with "real DJ friend in your ear — no AI slop"; BRANDING.md documents the CDJ Whisper visual direction; placeholder logo SVG ships at docs/branding/logo.svg.**

## What Was Done

### Task 1 — README anti-slop hook + community PR call

Edited `README.md` (3 surgical changes):

1. Lede paragraph rewritten so the anti-slop thesis is the FIRST claim, not buried mid-sentence. New opening: "A real DJ friend in your ear — no AI slop." followed by what vibemix listens to, then concrete denials (no generic commentary, no hallucinated tracks, no late reactions).
2. New "Don't see your controller?" subsection added below the controller grid, pointing to `scripts/sniff_controller.py` + the new-controller issue template — opens the community PR path explicitly.
3. Install URL block now carries an explicit `<TBD launch>` comment noting Phase 21 dependency + `bravoh/vibemix` org-slug verification gate. No fabricated URLs.

### Task 2 — BRANDING.md + placeholder logo SVG

Created `BRANDING.md` (root): documents the CDJ Whisper visual direction — Pioneer-grade DJ hardware in library mode. Covers:

- Why CDJ Whisper (warm blacks not pitch black, single amber accent, glow-not-bevel tactility, readability)
- Palette (5 warm-black tokens `--ink-0..4`, 4 amber intensities `--amber-100..10`, 2 neutral text tokens)
- Typography (Geist for UI, Fraunces for display)
- Tactility principles (glow over bevel, static surfaces with animated affordances, 8px grid)
- Hard no-list (generic AI gradients, neon cyan/magenta, glass-morphism, faux 3D, multi-color palettes, pure black, stock icons)
- Logo status (placeholder; pro logo = Kaan-action post-v2.0)
- Cross-references to `mocks/vibemix-direction-final.html` and the placeholder SVG

Created `docs/branding/logo.svg`: text-based wordmark using the amber accent (#FF8A3D) on warm-black background. Placeholder status marked in the SVG `<desc>` element AND a visible "PLACEHOLDER — see BRANDING.md" line at 92% Y for close-inspection visibility.

### Task 3 — Install instructions audit

Cross-referenced the README install table against Phase 21 deliverables. The existing `github.com/bravoh/vibemix/releases/latest` URL pattern is preserved (it's a redirect that works once the first release ships). Added a TBD comment immediately after the install table noting the Phase 21 dependency + org-slug verification gate.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] SVG XML parser rejected double-hyphen in comments**
- **Found during:** Task 2 (`xmllint --noout` validation)
- **Issue:** Initial SVG had comments like `<!-- CDJ Whisper: --ink-0 -->`. XML spec forbids `--` inside comments; xmllint exited 1.
- **Fix:** Rephrased comments to avoid `--`: "CDJ Whisper token ink-0" instead of `--ink-0`.
- **Files modified:** `docs/branding/logo.svg`
- **Commit:** `6578f9d` (folded into single plan commit)

## Verification

- `grep -i "AI slop" README.md` returns hit on the lede paragraph ✅
- `grep "sniff_controller" README.md` returns the community PR section hit ✅
- `[ -f BRANDING.md ]` exits 0 ✅
- `[ -f docs/branding/logo.svg ]` exits 0 ✅
- `grep -i "CDJ Whisper" BRANDING.md` returns multiple hits ✅
- `grep -i "placeholder" docs/branding/logo.svg` returns 3 hits ✅
- `xmllint --noout docs/branding/logo.svg` exits 0 ✅
- No regression: `pytest -q` baseline unchanged (10 pre-existing failures, all unrelated)

## Commits

- `6578f9d` — feat(26-01): README anti-slop hook + BRANDING.md + placeholder logo

## Self-Check: PASSED
