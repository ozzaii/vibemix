---
phase: 44-launch-positioning-pre-stage
plan: 01
subsystem: launch
tags: [readme, launch, hero, anti-slop, ci-gate, tdd, pytest]

# Dependency graph
requires:
  - phase: 39-public-rc-cut-and-ship
    provides: README hero block (vibemix:hero-start/end sentinels, hero.png, demo.mp4 placeholder, sha256=PLACEHOLDER hash gate)
  - phase: 43-visual-ship-lock
    provides: scripts/launch/ + tests/launch/ scaffold pattern (check_storyboard_palette.py + test_storyboard_palette.py shape)
provides:
  - Locked README hero one-liner: "the only AI co-host that actually listens to your set" (verbatim, exactly once)
  - "## No AI slop" hook section directly below hero, above badges — hits all 5 CONTEXT §specifics anchor phrases
  - CI gate scripts/launch/check_readme_hero_lock.py — 3-gate enforcement (locked one-liner + anchors + slop blocklist + deeply-regex)
  - 11-test pytest suite at tests/launch/test_readme_hero_lock.py (module shape + happy path + 5 negative synthetic-README cases + 2 CLI subprocess smokes)
  - LAUNCH-01 requirement closed
affects: [44-02, 44-05, 45-01]  # 44-05 reuses the AI-slop blocklist for SHIP-TWEET copy; 44-02 may add anchor phrases for grid sections; 45-01 SHIP-TRANSFER includes README as canonical artifact

# Tech tracking
tech-stack:
  added: []  # no new deps — uses stdlib argparse/re/pathlib + existing pytest
  patterns:
    - "Subprocess + module-import dual-surface launch-check pattern (mirrors check_storyboard_palette.py / test_storyboard_palette.py shape established in Phase 43 Plan 43-07)"
    - "3-gate single-CLI lock: locked one-liner (case-sensitive, exact-count) + anchor phrases (case-insensitive, multi-variant OR'd) + blocklist (case-insensitive substring + regex)"

key-files:
  created:
    - scripts/launch/check_readme_hero_lock.py
    - tests/launch/test_readme_hero_lock.py
  modified:
    - README.md  # hero <em> tagline locked + new '## No AI slop' section inserted

key-decisions:
  - "Inserted '## No AI slop' between <!-- vibemix:hero-end --> and the badge row — first content readers hit after the video, ahead of Install — rather than below the existing 'A real DJ friend in your ear — no AI slop.' paragraph; keeps the anti-slop framing as the explicit value-prop H2 instead of buried prose."
  - "Locked one-liner gate is case-SENSITIVE + exact-count=1; anchor + blocklist gates are case-INSENSITIVE. Rationale: a Francesco reword like 'The Only AI Co-host...' or a copy-paste duplicate would silently drift if case-insensitive, but anchor phrases naturally vary in sentence casing across paragraphs."
  - "Pinned the AI-slop blocklist verbatim from CONTEXT §specifics — 15 literal tokens + '\\bdeeply\\s+\\w+' regex. No additions ('utilize', 'innovative', etc.) deferred to a planner decision rather than 'while I'm here' creep."
  - "Did NOT remove the existing post-badge 'A real DJ friend in your ear — no AI slop.' paragraph; the new H2 explains the framing, the paragraph keeps the inline editorial voice. Anchor phrase coverage is by design redundant — the gate only requires presence, not uniqueness."

patterns-established:
  - "Launch-check pattern: `scripts/launch/check_<topic>_<axis>.py` (CLI with `--<artifact>` PATH + `--quiet`) + `tests/launch/test_<topic>_<axis>.py` (module-import shape + live-artifact happy path + tmp_path negative cases + subprocess smoke). Both files SPDX-tagged Apache-2.0."
  - "Lock-style gate: 'lock' suffix in script name signals 'verbatim text, no drift tolerated' — distinct from drift-detector gates (e.g. check_readme_hero_hash.py) which check for asset-content sync."

requirements-completed: [LAUNCH-01]

# Metrics
duration: 10min
completed: 2026-05-16
---

# Phase 44 Plan 01: README hero one-liner lock + "No AI slop" hook (LAUNCH-01) Summary

**README hero `<em>` locked to "the only AI co-host that actually listens to your set" verbatim, new "## No AI slop" H2 inserted with all 5 CONTEXT-pinned anchor phrases, and a 3-gate CI lock (scripts/launch/check_readme_hero_lock.py + 11-test pytest) shipped so the marketing surface can't drift back into slop.**

## Performance

- **Duration:** 10 min
- **Started:** 2026-05-16T17:30:18Z
- **Completed:** 2026-05-16T17:40:31Z
- **Tasks:** 2/2 (both TDD: red → green)
- **Files modified:** 3 (1 README + 1 script + 1 test)

## Accomplishments

- Hero `<em>` tagline rewritten in-place: old `An AI co-host for your DJ set. Open source. Mac + Windows.` → locked `the only AI co-host that actually listens to your set` (CONTEXT §specifics; ROADMAP Phase 44 success criterion 1).
- New `## No AI slop` H2 section (3 paragraphs, ~210 words) sits between the hero block and the badge row — covers all 5 anchor phrases (`real DJ friend in your ear`, `built by DJs`, `your audio doesn't leave`, `open source`, `Mac + Windows`) organically, no marketing flourish, mirrors the existing post-badge editorial voice.
- 3-gate CI lock — `scripts/launch/check_readme_hero_lock.py` — exits non-zero on locked-one-liner drift, missing anchor phrases, AI-slop blocklist hits, or `deeply <word>` constructions.
- 11-test pytest suite at `tests/launch/test_readme_hero_lock.py` pins the contract (module-import shape, locked-one-liner value, blocklist canonical subset, live README happy path, 5 negative synthetic-README cases, 2 subprocess smokes).
- Phase 39 `scripts/check_readme_hero_hash.py` gate still GREEN — `sha256=PLACEHOLDER` sentinel + asset path preserved through the rewrite.

## Task Commits

Each task was committed atomically per TDD red/green cycle:

1. **Task 1: Failing README hero lock gate (TDD red)** — `3d6f132` (`test(44-01): add failing README hero lock gate (LAUNCH-01 TDD red)`)
   - Created `scripts/launch/check_readme_hero_lock.py` (3-gate enforcement).
   - Created `tests/launch/test_readme_hero_lock.py` (11 tests).
   - Initial test run: 9/11 PASS (module shape + all negatives + CLI-missing-readme), 2/11 FAIL (happy-path + CLI smoke against live README — expected RED since the live README still ships the old `<em>`).
2. **Task 2: Lock hero one-liner + ship "No AI slop" hook (TDD green)** — `12f7060` (`feat(44-01): lock hero one-liner + ship 'No AI slop' hook (LAUNCH-01 TDD green)`)
   - Updated `README.md` hero `<em>` to the locked one-liner verbatim.
   - Inserted `## No AI slop` H2 section between `<!-- vibemix:hero-end -->` and the badge row.
   - Final test run: 11/11 PASS.

## Files Created/Modified

- `scripts/launch/check_readme_hero_lock.py` (new, 175 lines) — CLI gate (`--readme PATH`, `--quiet`). Pins `LOCKED_ONE_LINER`, `_ANCHOR_PHRASES` (5-tuple with OR'd variants), `_AI_SLOP_BLOCKLIST` (15-token tuple), `_DEEPLY_RE`. Public function `check_readme()` returns int exit code. SPDX Apache-2.0.
- `tests/launch/test_readme_hero_lock.py` (new, 232 lines) — 11 tests, mirrors the `test_storyboard_palette.py` shape. Module-shape tests pin public surface; happy-path test runs `check_readme()` against the live README; 5 negative cases generate synthetic `tmp_path/README.md` violations (locked-one-liner-missing, slop-token-present, anchor-phrase-missing, `deeply <word>` construction, locked-one-liner-duplicated); 2 subprocess smokes wrap the CLI.
- `README.md` (modified, +9/-1) — hero `<em>` line replaced + new `## No AI slop` section inserted. All other surfaces (hero.png/demo.mp4/placeholder.gif, vibemix:hero-start/end sentinels with `sha256=PLACEHOLDER`, all 5 shield badges, Install onward) untouched.

## Decisions Made

- **Locked-one-liner gate is case-SENSITIVE + exact-count=1.** Anchor + blocklist gates are case-insensitive. The CONTEXT-pinned phrase is the public face of the launch — any Francesco reword to "The Only AI Co-host That Actually Listens To Your Set" should fail the gate and require explicit planner sign-off, not silent drift. Exact-count=1 also catches copy-paste leaks where a prior tagline is left in place alongside the new one.
- **"## No AI slop" section placement: between `<!-- vibemix:hero-end -->` and the badge row** (not below the existing `**A real DJ friend...**` paragraph at the bottom of the post-badge intro). Rationale: the section IS the H2 anti-slop framing, so it earns the H2 slot ahead of badges. The existing inline `**A real DJ friend in your ear — no AI slop.**` paragraph remains as editorial voice — anchor phrase coverage is intentionally redundant (the lock script only requires presence, not uniqueness).
- **Did not enumerate `_AI_SLOP_BLOCKLIST` beyond CONTEXT §specifics** — "utilize", "innovative", "ecosystem", "seamlessly", etc. would all be reasonable additions, but the blocklist is a planner decision surface. Deferred to a future PR with explicit Kaan/Francesco sign-off rather than scope-creeping.
- **Negative-case test for duplicate locked-one-liner** added beyond the plan's 2-case minimum — a copy-paste error during a future hero rewrite is the realistic regression vector. Cheap test to add, blocks a real failure mode.

## Deviations from Plan

None — plan executed exactly as written. The CONTEXT-recommended 2 negative-case tests grew to 5 (locked-one-liner missing, slop token, missing anchor, deeply construction, locked-one-liner duplicated) but that's coverage-within-scope, not a deviation from the plan's intent. Plan section "Pattern reuse: mirror `check_storyboard_palette.py` + `test_storyboard_palette.py` shape" was followed faithfully — same `subprocess.run` + `capfd`-style assertions, same SPDX tag, same `REPO_ROOT = Path(__file__).resolve().parents[2]` idiom.

**Total deviations:** 0
**Impact on plan:** None.

## Issues Encountered

None.

## Verification

Plan's `<verification>` block all PASS:

- `uv run pytest tests/launch/test_readme_hero_lock.py -v` — **11 passed in 0.05s**.
- `uv run python scripts/launch/check_readme_hero_lock.py` — exit 0 (`PASS: README.md — locked one-liner + 5 anchors + 0 slop hits`).
- `uv run python scripts/launch/check_readme_hero_lock.py --readme /dev/null` — exit 1 (correctly fails, all gates trip on empty input).
- `grep -F "the only AI co-host that actually listens to your set" README.md` — exactly **1 match**.
- `grep -v '^<!--' README.md | grep -iEc "leverage|synergize|...|paradigm"` — **0 matches**.
- `uv run python scripts/check_readme_hero_hash.py` — exit 0 (Phase 39 placeholder sentinel preserved).

## User Setup Required

None — no external service configuration or asset uploads required by this plan. (The `docs/assets/demo.mp4` Kaan-discharge tracked under `KAAN-ACTION-LEGAL.md §ASSETS-DEMO-CUT` is upstream of Phase 39 and remains a separate item.)

## Next Phase Readiness

- **LAUNCH-01 closed engineering-green** — README hero locked, anti-slop hook section live, 3-gate CI lock pinned. Future drift on the locked one-liner / anchor phrases / blocklist now fails CI.
- **Phase 44 Wave A** can continue to Plan 44-02 (LAUNCH-03 + LAUNCH-04 — DJ-software grid + controller grid + a11y check).
- **Cross-plan reuse:** Plan 44-05 (SHIP-TWEET 5-channel copy lock) can import `_AI_SLOP_BLOCKLIST` and `_DEEPLY_RE` from this module rather than redeclaring — the blocklist is now a single source of truth.
- **No new dependencies introduced** — pure stdlib + existing pytest. Bundle size unchanged.

## Self-Check: PASSED

- `scripts/launch/check_readme_hero_lock.py` — FOUND.
- `tests/launch/test_readme_hero_lock.py` — FOUND.
- `README.md` — locked one-liner present, anchor phrases present, slop hits zero, hero sentinels preserved.
- Commit `3d6f132` (Task 1 RED) — FOUND in git log.
- Commit `12f7060` (Task 2 GREEN) — FOUND in git log.

---

*Phase: 44-launch-positioning-pre-stage*
*Plan: 01*
*Completed: 2026-05-16*
