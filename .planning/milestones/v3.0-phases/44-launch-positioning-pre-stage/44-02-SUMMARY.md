---
phase: 44-launch-positioning-pre-stage
plan: 02
subsystem: launch
tags: [readme, launch, controllers, dj-software, a11y, ci-gate, kaan-discharge]
dependency_graph:
  requires:
    - 44-01 (README hero one-liner lock + "No AI slop" hook — this plan inserts the "Works alongside" section IMMEDIATELY BELOW that hook + relies on the same AI-slop blocklist taxonomy)
    - src/vibemix/midi/controllers/*.json (10 canonical profiles — the controller grid is sourced verbatim from this set)
  provides:
    - scripts/launch/check_readme_grids_a11y.py (4-gate CI enforcement: alt-text + cell count + balance + slop-free)
    - 6 DJ-software wordmark SVG placeholders under docs/assets/dj-software/
    - 10 controller wordmark SVG placeholders under docs/assets/controllers/ (replacing legacy non-existent PNG references)
    - KAAN-ACTION-LEGAL.md §LAUNCH-03 + §LAUNCH-04 discharge runbooks (real-logo upload)
  affects:
    - Phase 45 SHIP-TWEET — outreach calendar editorial pitches reference the "10 mapped controllers" credibility hook; real-logo swap closes the visual-polish layer
    - Phase 44-06 — appends §LAUNCH-06 + §LAUNCH-08 to KAAN-ACTION-LEGAL.md immediately after this plan's §LAUNCH-04
tech_stack:
  added:
    - none (pure Python stdlib re + argparse + pathlib for the a11y script)
  patterns:
    - 4-gate CI enforcement (alt + count + balance + slop) — extends 44-01's hero-lock blocklist pattern to a second README surface
    - canonical-set-by-grep (controller grid sourced from src/vibemix/midi/controllers/*.json; drift fails CI)
    - SVG wordmark placeholders with embedded KAAN-DISCHARGE marker comments (real-logo swap is asset-only, no code touch)
    - canonical §GATE-* discharge runbook format (REQ-ID / Owner / Status / Effort / Blocking-for / Why / Files / Kaan-oneliner / Verification / What-unblocks / Sign-off-block)
key_files:
  created:
    - scripts/launch/check_readme_grids_a11y.py
    - tests/launch/test_readme_grids_a11y.py
    - docs/assets/dj-software/.gitkeep
    - docs/assets/dj-software/rekordbox.svg
    - docs/assets/dj-software/serato.svg
    - docs/assets/dj-software/traktor.svg
    - docs/assets/dj-software/djay-pro.svg
    - docs/assets/dj-software/virtualdj.svg
    - docs/assets/dj-software/mixxx.svg
    - docs/assets/controllers/ddj-200.svg
    - docs/assets/controllers/ddj-400.svg
    - docs/assets/controllers/ddj-flx4.svg
    - docs/assets/controllers/ddj-rev1.svg
    - docs/assets/controllers/kontrol-s2.svg
    - docs/assets/controllers/kontrol-s4.svg
    - docs/assets/controllers/mc-6000.svg
    - docs/assets/controllers/mc-7000.svg
    - docs/assets/controllers/mixtrack-platinum-fx.svg
    - docs/assets/controllers/mixtrack-pro-fx.svg
  modified:
    - README.md (insert "## Works alongside whatever DJ app you already use" 6-cell 3x2 table + replace "## Supported controllers" table with canonical 10 in 5x2 table)
    - KAAN-ACTION-LEGAL.md (append §LAUNCH-03 + §LAUNCH-04 discharge runbooks)
decisions:
  - Copied _AI_SLOP_BLOCKLIST verbatim from 44-01's check_readme_hero_lock.py rather than importing — per plan's "Claude's discretion" allowance. Single-source via import would entangle the two scripts' lifecycles (a future blocklist edit on 44-01's side would silently change a11y semantics here); a tested copy with the same canonical-tokens-pinned test guards drift in both directions independently.
  - Logo style = text wordmark (CONTEXT §Claude's discretion) over boxed-initials. Matches the project_visual_direction_cdj_whisper memory note (hardware-grade typographic logotypes, restraint, no cartoon styling). Single neutral grey (#888) on transparent; no amber accent on placeholders (amber reserved for real-asset polish layer or system chrome).
  - "Works alongside" section inserted BEFORE "## Install" (not BEFORE "## Feature matrix") — visual narrative: hero/pitch -> "works with your software" -> "here's how to install it" reads cleaner than interleaving with the feature-matrix table.
  - Controller grid arranged as 5x2 (not 2x5) — wide-screen-first since GitHub renders READMEs at 850-1200px content width on desktop, where 5-across reads naturally and 2-across feels cramped. The a11y balance gate accepts both orientations.
  - Reconciled the legacy "Supported controllers" table drift in this plan (not deferred) — the prior table referenced PNGs at paths that never existed in git (only .gitkeep was committed under docs/assets/controllers/), and listed 10 controllers (FLX6/FLX10/1000/SX3/XDJ-RX3/Numark Party Mix Live/Hercules Inpulse 300/500) that have ZERO mapping in src/vibemix/midi/controllers/. Leaving that drift would have shipped a launch-day credibility bomb. Plan 44-02 closes it engineering-side; §LAUNCH-04 covers only the asset-polish layer.
  - 10 controller SVGs ship in this plan (not just the 2 the plan suggested were "already shipped"). Reason: scan of git ls-files docs/assets/controllers/ returned ONLY .gitkeep — no real assets existed. Every controller grid cell gets a placeholder in this commit so the README renders cleanly out-of-the-box.
metrics:
  duration: ~1h
  completed: 2026-05-17
---

# Phase 44 Plan 02: DJ-software grid + controller grid + README a11y check Summary

**One-liner:** Shipped a 6-cell DJ-software grid + reconciled the controllers grid to the canonical 10 from `src/vibemix/midi/controllers/*.json`, with a 4-gate a11y CI enforcement (`check_readme_grids_a11y.py`) and §LAUNCH-03 + §LAUNCH-04 Kaan-discharge runbooks pre-staged for real-logo swap.

## What Shipped

### Engineering Green

1. **README "Works alongside whatever DJ app you already use" section** — inserted between the 44-01 "No AI slop" hook and `## Install`. 3x2 HTML table with 6 wordmark logos (rekordbox / Serato / Traktor / djay Pro / VirtualDJ / Mixxx) + brief framing paragraph ("vibemix doesn't care which DJ app you run — it listens to the master output") + a Don't-see-your-app fallback that surfaces the grounding-stack-is-app-agnostic story.

2. **README "Supported controllers" section reconciled** — replaced the legacy table (which referenced 10 controllers NONE of which were actually mapped: FLX6/FLX10/1000/SX3/XDJ-RX3/Numark Party Mix Live/Hercules Inpulse 300/500 + PNG paths that never existed in git) with the canonical 10 sourced from `src/vibemix/midi/controllers/*.json`: Pioneer DDJ-200/400/FLX4/REV1, NI Traktor Kontrol S2/S4, Denon DJ MC6000/7000, Numark Mixtrack Platinum FX / Pro FX. Arranged 5x2. Calibrate-callout preserved + sourced-from JSON link added.

3. **6 DJ-software SVG placeholders** under `docs/assets/dj-software/` — text-wordmark style, 200x80 viewBox, system sans-serif `#888` fill, KAAN-discharge marker comment per CONTEXT §Claude's discretion + project_visual_direction_cdj_whisper memory note (hardware-grade typographic restraint, no cartoon).

4. **10 controller SVG placeholders** under `docs/assets/controllers/` — same wordmark style, 2-line vendor + model layout, KAAN-discharge marker comment. Closes the asset-existence gap (prior to this plan, only `.gitkeep` lived under this directory; all README PNG references were dead links).

5. **`scripts/launch/check_readme_grids_a11y.py`** — 4-gate CI enforcement:
   - **ALT gate:** every `<img>` in either grid carries non-empty `alt="..."` (no missing alt, no empty alt)
   - **CELL_COUNT gate:** DJ-software = 6 cells, controllers = 10 cells (both locked)
   - **BALANCE gate:** DJ-software divisible by 2 OR 3 (3x2 or 2x3); controllers divisible by 2 OR 5 (5x2 or 2x5)
   - **SLOP gate:** alt-text contains none of the 16-token AI-slop blocklist (copied verbatim from 44-01's hero-lock taxonomy per CONTEXT §specifics)

6. **`tests/launch/test_readme_grids_a11y.py`** — 15 tests covering module shape (constants + heading fragments + blocklist subset), happy-path against live README, 7 negative synthetic-README cases (missing alt, empty alt, wrong DJ count, wrong controller count, slop-in-alt, missing DJ section, missing controllers section), CLI subprocess smoke + missing-file failure.

7. **`KAAN-ACTION-LEGAL.md §LAUNCH-03 + §LAUNCH-04`** — two discharge runbooks appended after 44-05's §LAUNCH-07. §LAUNCH-03 covers the 6 DJ-software real-logo swap (vendor press-kit sources per app, optimize commands, verification via the a11y gate). §LAUNCH-04 covers the 10 controller product-photography swap with the same pattern, plus pins `src/vibemix/midi/controllers/*.json` as the do-not-edit invariant during asset swap.

## Test Results

```
tests/launch/test_readme_grids_a11y.py ...............  (15/15)
tests/launch/test_readme_hero_lock.py ...........      (11/11, 44-01 regression — still green)
tests/launch/ full suite                                63/63 passed in 0.29s
```

### Verification gates (per plan `<verification>` block)

| Gate | Expected | Actual | Result |
|---|---|---|---|
| `uv run pytest tests/launch/test_readme_grids_a11y.py -v` | all green | 15/15 | PASS |
| `uv run pytest tests/launch/test_readme_hero_lock.py -v` | still green | 11/11 | PASS |
| `ls docs/assets/dj-software/*.svg` | 6 SVGs | 6 | PASS |
| `grep -c 'src="docs/assets/dj-software/' README.md` | 6 | 6 | PASS |
| controller grid count vs `ls src/vibemix/midi/controllers/*.json` | both = 10 | 10 == 10 | PASS |
| `grep -c "^## §LAUNCH-0[34]" KAAN-ACTION-LEGAL.md` | 2 | 2 | PASS |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Worktree base was 458 commits behind main (Phase 44-04 in-progress branch)**
- **Found during:** Step 0 sync check
- **Issue:** This worktree branched off `worktree-agent-ac406198878ff8285` from a stale commit (`d506373` — 44-04 in-progress) before 44-01, 44-05, 44-07 merged. The worktree README had no "## No AI slop" section + no `scripts/launch/check_readme_hero_lock.py` — both load-bearing for 44-02 (insertion point + blocklist reference).
- **Fix:** Per memory `feedback_worktree_must_sync_main_first`, ran `git merge main --no-edit` BEFORE any task work. Brought in 19 files / 3475 insertions including 44-01 + 44-05 + 44-07 surfaces. No conflicts.
- **Files modified:** worktree branch history (merge commit `2d997c3`).
- **Commit:** `2d997c3` (merge commit, pre-task).

**2. [Rule 2 - Missing critical functionality] 10 controller SVG placeholders shipped (plan suggested only 8)**
- **Found during:** Task 2 implementation
- **Issue:** Plan said "Existing logo references under `docs/assets/controllers/` are kept for the controllers that already have them (DDJ-FLX4 and DDJ-400 — verify via `ls docs/assets/controllers/`)". Verification showed NO real assets existed in git — only `.gitkeep` was committed. The legacy README table referenced PNG paths (`pioneer_ddj_flx4.png`, `pioneer_ddj_400.png`, etc.) that have never existed on disk. Leaving 2 cells "real" while the other 8 got placeholders would have shipped 2 broken `<img>` URLs.
- **Fix:** Generated SVG placeholders for ALL 10 canonical controllers under the canonical slug filenames (`ddj-200.svg`, `ddj-400.svg`, `ddj-flx4.svg`, `ddj-rev1.svg`, `kontrol-s2.svg`, `kontrol-s4.svg`, `mc-6000.svg`, `mc-7000.svg`, `mixtrack-platinum-fx.svg`, `mixtrack-pro-fx.svg`) — slug-to-JSON-stem map so the README references are stable across the future real-logo swap.
- **Files modified:** 10 new SVG files (see `key_files.created`).
- **Commit:** `0bc7b73`.

**3. [Rule 1 - Bug] Pre-existing dead `<img src>` references to non-existent PNGs (legacy controller table)**
- **Found during:** Task 2 README rewrite
- **Issue:** Legacy "Supported controllers" table referenced `docs/assets/controllers/pioneer_ddj_*.png` (8 files) + `numark_party_mix_live.png` + `hercules_inpulse_{300,500}.png` — NONE of which exist in the repo. Anyone landing on the README would see 10 broken-image icons. Pure launch-day credibility bomb.
- **Fix:** Replaced the legacy table entirely with the canonical-10 grid sourced from `src/vibemix/midi/controllers/*.json`, with the 10 fresh SVG placeholders. Now every `<img src>` resolves to a real file on disk.
- **Files modified:** README.md (Supported controllers section).
- **Commit:** `0bc7b73`.

### Asked / Architectural

None — no Rule 4 escalations needed.

## Authentication Gates

None encountered. Plan 44-02 is pure file work (Python + SVG + markdown).

## Threat Flags

None — Plan 44-02 only touches documentation surfaces (README, KAAN-ACTION-LEGAL) and static asset files (SVG placeholders). No new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries.

## Known Stubs

The 16 SVG placeholders (6 DJ-software + 10 controller) are intentional stubs by design — they ship a working grid surface so the README isn't broken at launch, but the trademark-compliant real logos require human judgement (per-vendor press-kit attribution) that an autonomous agent can't make. The stubs are:

| Stub | Files | Why | Discharge |
|---|---|---|---|
| 6 DJ-software wordmark SVG placeholders | `docs/assets/dj-software/{rekordbox,serato,traktor,djay-pro,virtualdj,mixxx}.svg` | Trademark-compliant logo sourcing requires per-vendor press-kit access + per-vendor attribution judgement | `KAAN-ACTION-LEGAL.md §LAUNCH-03` (this plan) |
| 10 controller wordmark SVG placeholders | `docs/assets/controllers/{ddj-200,ddj-400,ddj-flx4,ddj-rev1,kontrol-s2,kontrol-s4,mc-6000,mc-7000,mixtrack-platinum-fx,mixtrack-pro-fx}.svg` | Same pattern — vendor press-kit product photography sourcing requires human judgement | `KAAN-ACTION-LEGAL.md §LAUNCH-04` (this plan) |

Both stubs are explicitly tracked in the §LAUNCH-03 / §LAUNCH-04 runbooks, with the a11y CI gate enforcing structural correctness across the swap (alt-text + cell count + balance + slop-free survive real-asset replacement).

## TDD Gate Compliance

- **RED gate:** `b62b75c test(44-02): add README grid a11y check + tests (TDD RED)` — 14 passed + 1 expected failure (`test_real_readme_passes_a11y`).
- **GREEN gate:** `0bc7b73 feat(44-02): ship DJ-software + controller grids (TDD GREEN — LAUNCH-03 + LAUNCH-04)` — 15/15 a11y tests pass; 11/11 hero lock regression green.
- **REFACTOR gate:** N/A — no cleanup needed; GREEN implementation passed all 4 gates first try.

## What Unblocked

- **Phase 44 success criterion 3** ("DJ-software grid + controllers grid render in README; alt-text + accessibility checks pass") — engineering green.
- **LAUNCH-03 + LAUNCH-04 requirements** — closed engineering-side; real-asset polish pre-staged as §LAUNCH-03 + §LAUNCH-04 discharge runbooks (not blockers).
- **README controller-grid drift** — closed; the README is now sourced-of-truth-by-grep from `src/vibemix/midi/controllers/*.json`. Any future controller add / remove that updates the JSON profile set without updating the README grid fails CI.

## Commits

| # | Hash | Message | Files |
|---|---|---|---|
| 0 | `2d997c3` | merge main into worktree (pre-task sync) | 19 files / 3475 insertions |
| 1 | `b62b75c` | test(44-02): add README grid a11y check + tests (TDD RED) | scripts/launch/check_readme_grids_a11y.py + tests/launch/test_readme_grids_a11y.py |
| 2 | `0bc7b73` | feat(44-02): ship DJ-software + controller grids (TDD GREEN) | README.md + 16 SVG placeholders + 1 .gitkeep |
| 3 | `01974f6` | docs(44-02): append §LAUNCH-03 + §LAUNCH-04 Kaan-discharge runbooks | KAAN-ACTION-LEGAL.md |

## Self-Check: PASSED

- File `scripts/launch/check_readme_grids_a11y.py`: FOUND
- File `tests/launch/test_readme_grids_a11y.py`: FOUND
- File `docs/assets/dj-software/rekordbox.svg`: FOUND
- File `docs/assets/dj-software/mixxx.svg`: FOUND
- File `docs/assets/controllers/ddj-flx4.svg`: FOUND
- File `docs/assets/controllers/mixtrack-pro-fx.svg`: FOUND
- File `KAAN-ACTION-LEGAL.md` §LAUNCH-03 + §LAUNCH-04: FOUND (grep -c = 2)
- Commit `b62b75c`: FOUND (test(44-02): add README grid a11y check + tests (TDD RED))
- Commit `0bc7b73`: FOUND (feat(44-02): ship DJ-software + controller grids (TDD GREEN))
- Commit `01974f6`: FOUND (docs(44-02): append §LAUNCH-03 + §LAUNCH-04 Kaan-discharge runbooks)
- 63/63 tests/launch/ tests green (regression check on Phase 44 surface)
