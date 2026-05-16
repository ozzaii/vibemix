---
phase: 19-github-launch-presence
plan: 04
subsystem: launch-assets
tags: [svg, png, gif, pillow, cdj-whisper, v5-palette, deterministic-build, readme-assets, oss-launch]

# Dependency graph
requires:
  - phase: 14-cdj-whisper-v5
    provides: tauri/ui/src/tokens.css — canonical v5 palette literals (void-1..4, amber, silk)
  - phase: 19-github-launch-presence (plan 19-01)
    provides: docs/ directory + scripts/dist/ scaffolding + tests/repo/ harness
provides:
  - scripts/dist/render_architecture.py — deterministic stdlib-only SVG generator (CDJ Whisper v5 palette)
  - scripts/dist/render_hero_placeholder.py — Pillow-based PNG + GIF placeholder generator (deterministic)
  - docs/assets/architecture.svg — branded 4-swim-lane diagram (8.7 KB)
  - docs/assets/hero.png — 1280×640 amber-gradient hero banner (137 KB)
  - docs/assets/demo-placeholder.gif — 320×180 3-frame placeholder loop (1.2 KB)
  - docs/assets/controllers/ + docs/assets/screenshots/ — reserved drop zones for Kaan-provided assets
  - tests/repo/test_docs_assets.py — 21 CI gates locking presence + shape + determinism
affects: [19-03 README writeup, 19-launch-marketing-assets, post-launch artwork swap-in]

# Tech tracking
tech-stack:
  added: []  # No new deps. Pillow 12.2.0 already in .venv (Phase 8 dep chain).
  patterns:
    - "Deterministic asset generation — `--check` mode pins committed output to generator (gen_notice.py pattern)."
    - "v5 palette hard-coded as Python constants in generator scripts (single source of truth: tauri/ui/src/tokens.css)."
    - "PIL PNG/GIF save with optimize=True + no metadata = byte-identical regen across runs."

key-files:
  created:
    - scripts/dist/render_architecture.py
    - scripts/dist/render_hero_placeholder.py
    - docs/assets/architecture.svg
    - docs/assets/hero.png
    - docs/assets/demo-placeholder.gif
    - docs/assets/controllers/.gitkeep
    - docs/assets/screenshots/.gitkeep
    - tests/repo/test_docs_assets.py
  modified: []

key-decisions:
  - "Use the LIVE tauri/ui/src/tokens.css palette literals (#020205, #05070b, #0a0c12, #11141c, #ff8a3d, #d6cfc7), not the plan-interfaces hard-coded values (#0a0b0d, #14171c) which were stale from a pre-v5 token file. Plan interfaces block referenced `tauri/ui/src/styles/tokens.css` — that path doesn't exist; canonical is `tauri/ui/src/tokens.css`."
  - "Render hero subtitle as `AI co-host for your DJ set` (matches CONTEXT Area 1 tagline) and stamp `placeholder - final artwork by Bravoh design lead` in the bottom-right so README viewers know the artwork is temporary."
  - "Hero scaled bitmap-font wordmark via PIL Lanczos resize rather than vendoring a font file — keeps the placeholder dependency-clean. Final hero will use Saira/Geist from the design lead's deliverable."
  - "Architecture arrows are sorted by id at render time + ARROWS list is fixed; no random IDs, no timestamps, no PIL PNG metadata chunks. Re-running both generators produces byte-identical output — confirmed via SHA-256 across 2-run diff."
  - "GIF placeholder uses palette mode (3-color: void + amber + silk) with NEAREST resize — keeps file size at 1.2 KB while still pulsing the amber underline across 3 frames."

patterns-established:
  - "Generator + `--check` mode: every committed asset has a deterministic generator with `--check` that exits 1 on drift. CI catches both hand-edits to the artifact and silent generator regressions."
  - "v5 palette hard-coded duplicate: generator scripts can't read tokens.css at runtime (no CSS parser dep, no CI cycle dependency). The duplication is small and the test suite locks both `#ff8a3d` (amber) and `#0a0c12` (void-3) literals to gate any palette drift on review."

requirements-completed: [GH-02, GH-08]

# Metrics
duration: ~22 min
completed: 2026-05-13
---

# Phase 19 Plan 04: README Assets Summary

**Deterministic CDJ Whisper v5 architecture SVG (4 swim-lanes, 9 boxes, Gemini-lane glow) + 1280×640 amber-gradient hero PNG placeholder + tiny "demo coming soon" GIF + reserved subdirs for Kaan-provided controller logos and screenshots. README §10 in Plan 19-03 can now reference these paths without any 404s, and every artifact has a `--check`-gated regenerator that CI uses to catch drift.**

## Performance

- **Duration:** ~22 min
- **Started:** 2026-05-13 (immediate after rebase onto local main)
- **Completed:** 2026-05-13
- **Tasks:** 2 (Task 1 architecture SVG + Task 2 hero PNG / GIF / dirs)
- **Files created:** 8 (2 scripts + 3 assets + 2 .gitkeep + 1 test file)
- **Tests added:** 21 (all passing)

## Accomplishments

- **`scripts/dist/render_architecture.py` (379 lines, stdlib-only)** — emits a 8.7 KB branded SVG with the actual v5 palette from tokens.css (not the stale plan-listed values). 4 horizontal swim-lanes (User Hardware / vibemix Client / Network / Gemini), 9 named boxes (DJ Controller, Master output, Headphones, Python sidecar, Tauri UI, Local recording, Bravoh proxy, Gemini 3 Flash, Gemini TTS), 6 amber Bezier arrows with arrowhead markers, Gemini-lane drop-shadow glow. `--check` mode catches drift.
- **`scripts/dist/render_hero_placeholder.py` (240 lines, Pillow-based)** — 3-stop horizontal lerp (void-1 → amber → void-1) with cinematic top/bottom vignette + centered scaled `vibemix` wordmark + scaled `AI co-host for your DJ set` tagline + bottom-right placeholder watermark. Same script's `--demo-gif` subcommand emits a 3-frame 320×180 GIF (1.2 KB) with pulsing amber underline.
- **Reserved drop zones** — `docs/assets/controllers/.gitkeep` (Kaan will fill with 10 controller logo PNGs from Phase 9's MIDI profile list) and `docs/assets/screenshots/.gitkeep` (Kaan will fill with 5 screenshots: calibration wizard, mode picker, voice picker, in-session UI, recording browser).
- **21 CI tests** — gate architecture SVG XML validity + 4 swim-lane labels + 9 box names + amber + void hex literals + 1200×720 viewBox + determinism (SHA-256 diff across runs) + hero PNG dimensions (1280×640) + center column amber + left edge dark + GIF format + reserved-dir .gitkeep presence + total docs/assets size < 500 KB.

## Task Commits

Each task was committed atomically (TDD cycle):

1. **Test (RED): docs-assets failing tests** — `2331216` (test)
2. **Task 1 (GREEN): render_architecture.py + architecture.svg** — `b269836` (feat)
3. **Task 2 (GREEN): hero PNG + demo GIF + reserved dirs + test refinement** — `4d20511` (feat)

## Files Created/Modified

- `scripts/dist/render_architecture.py` (NEW, 379 lines) — Deterministic SVG generator with palette constants, swim-lane data structure, render() + main(), `--output` + `--check` CLI.
- `scripts/dist/render_hero_placeholder.py` (NEW, 240 lines) — Pillow-based hero PNG + demo GIF generator with `--all` / `--demo-gif` modes.
- `docs/assets/architecture.svg` (NEW, 8,690 bytes) — Committed branded diagram.
- `docs/assets/hero.png` (NEW, 136,528 bytes) — Committed 1280×640 amber gradient placeholder.
- `docs/assets/demo-placeholder.gif` (NEW, 1,221 bytes) — Committed 3-frame loop placeholder.
- `docs/assets/controllers/.gitkeep` (NEW, empty) — Reserved drop zone for 10 controller logos.
- `docs/assets/screenshots/.gitkeep` (NEW, empty) — Reserved drop zone for 5 UI screenshots.
- `tests/repo/test_docs_assets.py` (NEW, 273 lines) — 21 CI gates.

## Decisions Made

- **Use real tokens.css palette literals, not the plan's `<interfaces>` block values.** The plan listed `--void-0: #0a0b0d / --void-1: #14171c`, but the live `tauri/ui/src/tokens.css` (Phase 14 v5 CDJ Whisper) uses the cooler stack `#020205 / #05070b / #0a0c12 / #11141c`. The plan's interfaces block was anchored to a pre-v5 token snapshot. The user prompt explicitly instructs "use the EXACT hex values from tokens.css" — that takes precedence. Tests assert against the real `--void-*` literals so the artifact stays pinned to the live design tokens. The plan-interfaces hex values would have shipped a visually inconsistent diagram.
- **Pillow is acceptable for hero PNG.** Pillow 12.2.0 is already in `.venv` (transitive dep from Phase 8's screen-capture chain). No new dependency. Falling back to SVG-only hero would have lost the cinematic vignette feel.
- **Hero text rendered via `ImageFont.load_default()` upscaled with Lanczos resize.** Avoids vendoring a font file for a placeholder. Final artwork from the Bravoh design lead will use Saira/Geist.
- **GIF in palette mode with 3-color palette.** Keeps file size under 2 KB while still proving the "animated" property to PIL. NEAREST resize preserves the bitmap pixel look (intentional — this is a placeholder, not the final demo).
- **Architecture lane glow only on Gemini lane.** Pulls the eye toward the "this is where the AI lives" anchor point — matches CDJ Whisper restraint principle (`--glow-strong` reserved for the focal element).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Plan's hard-coded void hex literals stale relative to live v5 tokens.css**

- **Found during:** Task 1 (pre-implementation context read)
- **Issue:** Plan's `<interfaces>` block lists `--void-0: #0a0b0d` and `--void-1: #14171c`, but the canonical `tauri/ui/src/tokens.css` (Phase 14 v5 CDJ Whisper, 2026-05-12) uses `#000000 / #020205 / #05070b / #0a0c12 / #11141c`. The user prompt explicitly instructs "use the EXACT hex values from tokens.css" — implementing the plan literals would have shipped a diagram visually inconsistent with the rest of the v5 surface.
- **Fix:** Hard-coded the live v5 palette literals as Python constants in `render_architecture.py` (and matching for the hero generator). Updated test_arch_svg_uses_void_backgrounds to assert against the real `--void-*` literals (`#020205 / #05070b / #0a0c12 / #11141c`).
- **Files modified:** scripts/dist/render_architecture.py, scripts/dist/render_hero_placeholder.py, tests/repo/test_docs_assets.py
- **Verification:** `grep -c 'ff8a3d' docs/assets/architecture.svg` = 7; void-stack grep finds `#020205`, `#05070b`, `#0a0c12`. XML parses, viewBox `0 0 1200 720`. SVG renders sanely on visual inspection.
- **Committed in:** b269836 (Task 1)

**2. [Rule 1 - Bug] test_hero_png_center_is_amber sample point landed inside wordmark overlay**

- **Found during:** Task 2 (first GREEN test run)
- **Issue:** Test sampled at (640, 320) — mid-canvas center — which falls inside the rendered `vibemix` wordmark. The silk-white text bleaches the G channel above the test's [80, 200] amber range (saw G=205). Test was asserting "the gradient hits amber at the midpoint", but was reading a text pixel instead.
- **Fix:** Moved sample point to (640, 200) — well below the top vignette darkening, well above the wordmark. Now samples the pure gradient: (255, 138, 61). Documented inline with a comment so future readers understand the intent.
- **Files modified:** tests/repo/test_docs_assets.py
- **Verification:** Test passes; the gradient assertion still gates the actual amber midpoint at the correct y coordinate.
- **Committed in:** 4d20511 (Task 2, alongside the hero generator GREEN)

---

**Total deviations:** 2 auto-fixed (2 × Rule 1 bug fixes)
**Impact on plan:** Both fixes corrected stale assumptions in the plan against the live codebase (v5 palette + sample-point math). No scope change, no new files outside the plan's `files_modified` list, no new dependencies. Plan's intent (deterministic branded artifacts in v5 palette) is fully preserved.

## Issues Encountered

- **Worktree cwd reset between Bash calls.** First `Write` to test file landed in the main repo at `/Users/ozai/projects/dj-set-ai/tests/repo/test_docs_assets.py` instead of the worktree because absolute paths captured in conversation context resolve to the main repo. Mitigated by computing `WT_ROOT=$(git rev-parse --show-toplevel)` per-call and using worktree-absolute paths for all subsequent Write operations. The misplaced test file was moved to the worktree before commit — no orphan in the main repo.
- **`.venv` lives in the main repo, not the worktree.** All test runs used `/Users/ozai/projects/dj-set-ai/.venv/bin/python` (main-repo path) directly. Worked because the venv is Python-only and doesn't care about cwd — it just imports the test file by absolute path.
- **POC `.glb` LFS warnings during rebase.** The initial `git reset --hard main` reported 21 `.glb` files in `tauri/ui/assets/mascot/` that "should have been pointers" — left untouched (out of scope, pre-existing LFS state, not related to this plan). Per Scope Boundary rule, not investigated; logged here for visibility.

## Known Stubs

None. Both placeholder assets are intentional, fully-rendered placeholders (not hardcoded `=null` returns). The README in Plan 19-03 will reference them directly; the post-phase swap path is documented below.

## Threat Flags

No new threat surface introduced beyond what's covered in the plan's threat model (T-19-09 / T-19-10 / T-19-11 all mitigated via `--check` mode + CI test pinning).

## Self-Check

- [x] `scripts/dist/render_architecture.py` exists
- [x] `scripts/dist/render_hero_placeholder.py` exists
- [x] `docs/assets/architecture.svg` exists
- [x] `docs/assets/hero.png` exists
- [x] `docs/assets/demo-placeholder.gif` exists
- [x] `docs/assets/controllers/.gitkeep` exists
- [x] `docs/assets/screenshots/.gitkeep` exists
- [x] `tests/repo/test_docs_assets.py` exists
- [x] Commit `2331216` (test RED) exists in git log
- [x] Commit `b269836` (Task 1 GREEN) exists in git log
- [x] Commit `4d20511` (Task 2 GREEN) exists in git log
- [x] `pytest tests/repo/test_docs_assets.py` → 21 passed
- [x] `python scripts/dist/render_architecture.py --check` exits 0
- [x] SHA-256 byte-identical regen confirmed for both hero.png and architecture.svg
- [x] docs/assets/ total size = 146 KB (< 500 KB cap)

## Self-Check: PASSED

## User Setup Required

None. No environment variables, no secrets, no external services. Kaan-action follow-ups are art deliverables (not setup):

- **Final hero.png** (1280×640 PNG, replaces placeholder) — designed by Momo / Kaan
- **Final demo video** — 30-45s shot during a real DJ set with Francesco; export `docs/assets/demo.gif` or `docs/assets/demo.mp4`
- **10 controller logos** — drop as `docs/assets/controllers/<slug>.png` per Phase 9 MIDI profile slugs
- **5 UI screenshots** — drop as `docs/assets/screenshots/<surface>.png` (calibration wizard, mode picker, voice picker, in-session UI, recording browser)

## Next Phase Readiness

- **Plan 19-03 (README writeup)** unblocked — all referenced asset paths exist on disk and CI gates them.
- **Plan 19-05 / future repo-metadata** — `.github/repo-config.yml` script can reference `docs/assets/hero.png` for OG-image bootstrap if Kaan opts to use the placeholder before final artwork lands.
- No outstanding blockers. No deferred items.

---
*Phase: 19-github-launch-presence*
*Completed: 2026-05-13*
