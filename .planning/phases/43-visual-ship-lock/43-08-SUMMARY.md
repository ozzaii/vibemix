---
phase: 43-visual-ship-lock
plan: 08
subsystem: docs
tags: [storyboard, cut-count, ui-chip, cdj-whisper, hero-demo, vis-08]

# Dependency graph
requires:
  - phase: 43-visual-ship-lock (Wave 2)
    provides: 43-07 — Saira + Geist Mono fonts + palette gate already wired
    on storyboard baseline

provides:
  - mocks/vibemix-cinematic-storyboard.html re-mocked to 8 cuts in
    CONTEXT-specified sequence
  - UI chip overlays in cuts 2-6 inline-rendered with CDJ Whisper v5
    (wizard welcome, calibration meter, session shell, AI caption pop,
    EvidenceRegistry chip strip)
  - scripts/launch/check_cut_count.py — ≤8 cut hard gate
  - tests/launch/test_cut_count.py — 6-test pytest spec covering the gate
  - End-card now carries star-goal funnel CTA:
    "open-source · MIT · github.com/bravoh/vibemix"

affects:
  - 43-09 (Francesco handoff package can lift the 8-cut sequence directly
    into docs/launch-prep/SHOT-LIST.md without rework)
  - capture day post-Phase 43 — storyboard is the cut script Francesco
    will shoot from; UI chips inline-rendered show the actual shipped UI
  - any future plan that touches mocks/vibemix-cinematic-storyboard.html —
    both the palette gate (from 43-07) and the cut-count gate (from
    43-08) will reject regressions on contact

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Cut-count gate pattern (regex parse of data-cut= attributes,
      symmetric over/under-count failure modes)
    - data-cut="N" attribute as the storyboard's structured shot-list
      contract — DOM-grep-able from any tool, no XML/HTML parser needed
    - Cluster-documented frame metadata (info-h title, info-tag chip-type,
      stamp "frame N / 08") so audit-time review can be done at a glance

key-files:
  created:
    - scripts/launch/check_cut_count.py
    - tests/launch/test_cut_count.py
  modified:
    - mocks/vibemix-cinematic-storyboard.html
      (page title, header meta, brief sound-timestamp, full frames
      section, cutsheet header + timeline-ruler)

key-decisions:
  - "Wholesale replaced the 10-frame 45s cinematic narrative with the
    8-cut 30s CONTEXT sequence rather than tagging 8 of 10 existing
    frames with data-cut + leaving 2 as B-roll. Plan §<interfaces>
    explicitly preferred consolidation ('(a) Remove the extra frame
    entirely — preferred — CONTEXT says ≤8 hard gate'). Leaving B-roll
    frames bloats the document for Francesco and risks shoot-day
    confusion about which frames are in the final cut."
  - "Used a one-off Python splice script (/tmp/splice_storyboard.py,
    deleted after run) to perform the ~750-line frames-section
    replacement atomically. Single Edit with a ~750-line old_string is
    fragile; per-frame Edits would have created an inconsistent
    intermediate state where check_cut_count.py and the visual layout
    disagreed. The splice approach landed both in one commit."
  - "Re-timed the brief 'sound brief' card from '0:31 / 0:48' to
    '0:14 / 0:18' to match the 30s scale. Plan said preserve the
    brief 'intent narrative' — preserved the prose (140 bpm, F minor,
    commissioned bed, Avery TTS framing) but updated the absolute
    timestamps because leaving 45s-scale timestamps inside a 30s
    document is a Rule-1 bug Francesco would hit on shoot day."
  - "Inline-rendered the wizard welcome chip (cut 2) using the actual
    DOM structure of tauri/ui/src/wizard/step0-intro.ts — amber V lead
    on VIBEMIX wordmark, DJ FRIEND phrase, rule-bracketed 'IN YOUR EAR'
    slogan, [ let's go ] CTA. Not a stylized approximation. This way
    the storyboard chip is byte-faithful to what the shoot will capture
    from a real running build."
  - "EvidenceRegistry chip strip (cut 6) uses three distinct event types
    (KICK SWAP / LAYER DROP / BPM SHIFT) with technical-evidence sub-rows
    (deck cross + cc number; onset frequency + dB rolling window;
    autocorr ring + bar window) — the anti-slop thesis made visual.
    The Saira-italic chip text on the right of each row matches the
    canonical AVERY line vocabulary the AI quoted in cut 5, making the
    causal chain (event → registry chip → AI line) legible in 4s."
  - "Mascot celebrate pose (cut 7) follows the locked memory direction
    project_visual_direction_cdj_whisper: 'Pioneer CDJ headbob, NOT a
    generic VTuber dance'. Closed-mouth grin, both hands up at modest
    amplitude, music notes drifting — never the wide-arms VTuber dance
    Mixamo would default to. Plan 43-04 clip retarget should match
    this storyboard pose, not the other way around."
  - "End-card open-source CTA copy added at this plan even though
    Plan 43-07 explicitly deferred it ('Plan 43-07 §<action> step 6
    explicitly stated to leave the end-card logo-focused if Phase 44
    hadn't locked the README hero one-liner'). Plan 43-08's
    must_haves.truths line 23 explicitly requires the copy
    ('open-source · MIT · github.com/bravoh/vibemix') so it lands now;
    star-goal funnel anchor in place ahead of Phase 44/45."

patterns-established:
  - "Cut-count gate scripts in scripts/launch/ + matching tests/launch/
    pytest spec, using the scripts.launch.* import path — extends the
    pattern 43-07 introduced for the palette gate"
  - "data-cut='N' as the structured cut-list contract; both grep-able
    from shell scripts and rendered as visual cut numbers in the DOM"
  - "Sequenced verification: cut-count gate AND palette gate AND copy
    grep AND no-regression grep, all in a single pipe-chained verify
    line — fast feedback for downstream plans touching the storyboard"

requirements-completed: [VIS-08]

# Metrics
duration: 14m 57s
completed: 2026-05-16
---

# Phase 43 Plan 08: Hero Demo Storyboard v5 Re-mock — 8-cut Shot List Summary

**Hero demo storyboard re-mocked from 10-frame 45s narrative to 8-cut 30s sequence per CONTEXT §VIS-08; UI chip overlays in cuts 2-6 inline-rendered with CDJ Whisper v5 (wizard welcome, calibration meter, session shell, AI caption pop, EvidenceRegistry chip strip); end-card carries open-source CTA; ≤8 cut hard gate wired via scripts/launch/check_cut_count.py + 6-test pytest spec.**

## Performance

- **Duration:** 14m 57s (897 sec)
- **Started:** 2026-05-16T16:34:03Z
- **Completed:** 2026-05-16T16:49:00Z
- **Tasks:** 2 / 2
- **Files created:** 2 (check_cut_count.py + test_cut_count.py)
- **Files modified:** 1 (mocks/vibemix-cinematic-storyboard.html — +393 / -461 lines)

## Accomplishments

- `scripts/launch/check_cut_count.py` ships as a ≤8 cut hard gate. Parses
  `data-cut="N"` attribute occurrences via regex; exits 0 iff count ==
  MAX_CUTS (8). Symmetric drift rejection: >8 returns rc 2 with "max 8"
  in stderr; <8 returns rc 3 with "need 8" — both surface the actual
  count for fast triage.
- `tests/launch/test_cut_count.py` ships as a 6-test pytest spec covering
  module imports, MAX_CUTS constant shape, count_cuts API behavior,
  storyboard compliance, over-count rejection (CLI smoke), and
  under-count rejection (CLI smoke).
- `mocks/vibemix-cinematic-storyboard.html` re-mocked end-to-end:
  - Page title, header runtime/cuts cards, subtitle copy, brief sound-
    timestamps all re-scaled from 45s to 30s.
  - Full `<section class="frames">` block (~750 lines) replaced with 8
    `<article class="frame" data-cut="N">` blocks in the CONTEXT-specified
    sequence: (1) cold open + DDJ-FLX4 hands in dim room; (2) wizard
    welcome chip with amber-V VIBEMIX wordmark + [ let's go ] CTA;
    (3) calibration screen with 16-segment amber LED meter + peak-hold
    lozenge + dB FS readout; (4) live session UI with titlebar + master
    meter + phase tape + transcript + mascot canvas (subtle reaction) +
    status bar; (5) AI caption pop "nice kick swap @ 2:33" in Saira
    italic 500 amber-on-warm-black; (6) EvidenceRegistry strip with
    three timecode-headed anti-slop receipt chips (kick swap @ 2:33,
    layer drop @ 4:50, bpm shift @ 6:00); (7) mascot Hype-man celebrate
    clip in DJ-headbob pose with both hands up; (8) end card with
    vibemix wordmark + altidus.world/vibemix URL + open-source CTA
    + Caveat handwriting signature.
  - Cutsheet header text updated ("cut sheet · 30 s · 8 cuts"); 8
    timeline-segs replace the prior 10; timeline-ruler ticks go 0-30s
    in 5s steps.
- TDD gate compliance on Task 1: separate `test(...)` RED commit landing
  the failing import → `feat(...)` GREEN commit landing the
  implementation that makes 5/6 tests pass (test 4 expected to fail
  pre-Task-2; closed by Task 2 commit).
- All 4 gates green at the end: cut-count gate exit 0, palette gate
  exit 0, cut-count pytest 6/6, palette pytest 6/6.

## Task Commits

1. **Task 1 — Cut counter script + pytest sanity (TDD)**
   - RED: `c1877ed` (`test(43-08): add failing cut-count gate spec for storyboard (VIS-08)`)
   - GREEN: `6e7dd06` (`feat(43-08): add ≤8 cut count gate for storyboard (VIS-08)`)
2. **Task 2 — Re-mock storyboard to 8 cuts with CDJ Whisper v5 UI chips**
   - `f53cb9f` (`feat(43-08): re-mock storyboard to 8 cuts with CDJ Whisper v5 UI chips (VIS-08)`)

## Files Created/Modified

**Created:**
- `scripts/launch/check_cut_count.py` — 76 lines; parses HTML for
  `data-cut=` attributes via regex; symmetric over/under-count gate
- `tests/launch/test_cut_count.py` — 92 lines; 6-test pytest spec

**Modified:**
- `mocks/vibemix-cinematic-storyboard.html` — 393 insertions, 461
  deletions. Net is shorter (-68 lines) because the new 8 frames are
  each more compact in surrounding markup than the old 10, even though
  the new content carries richer inline SVG UI-chip mocks per frame.

## Decisions Made

See `key-decisions` in frontmatter (7 documented).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Brief sound-timestamp drift on 30s scale**
- **Found during:** Task 2 (header/brief metadata edit)
- **Issue:** Brief sound-card carried "builds at 0:31, drops at 0:48"
  (45s scale) which would contradict the 30s cutsheet (cuts 7+8 land
  at 0:22 and 0:26 respectively). Francesco would either trust the
  brief and miss-cue the drop, or trust the cutsheet and ignore the
  brief — either way a shoot-day bug.
- **Fix:** Re-scaled timestamps to "builds at 0:14, drops at 0:18"
  (placing the build inside the live-session frame 04 transcript and
  the drop right before the mascot celebrate frame 07, matching the
  narrative arc).
- **Files modified:** `mocks/vibemix-cinematic-storyboard.html`
- **Commit:** included in `f53cb9f`

**2. [Rule 2 - Critical functionality] Added open-source CTA copy on
end-card that Plan 43-07 had deferred**
- **Found during:** Plan reading (must_haves.truths line 23)
- **Issue:** Plan 43-07 §key-decisions explicitly said "Did NOT add
  'open-source · MIT · github.com/bravoh/vibemix' to frame-10 end card.
  Plan §<action> step 6 explicitly stated to leave the end-card
  logo-focused..." — but Plan 43-08 must_haves.truths line 23 requires
  this exact copy on the end card as a Plan-43-08-scoped requirement.
- **Fix:** Added the copy beneath the URL in Geist Mono 11px silk on
  the cut-8 end card SVG. This is correctly Plan-43-08 scope (not
  43-07 scope) — 43-07 deferred specifically because 43-08 hadn't
  required it yet; now 43-08 requires it, so it lands here.
- **Files modified:** `mocks/vibemix-cinematic-storyboard.html`
  (cut 8 SVG `<text>` element)
- **Commit:** included in `f53cb9f`

### Out-of-scope (not auto-fixed)

**1. Pre-existing worktree dirty state on 23 LFS-tracked binary files**
- 21 mascot GLB files + 2 fixture files appeared as modified due to
  LFS-pointer drift inherited from worktree creation. Same artifact
  43-07 documented in `deferred-items.md`. NOT staged or touched.

**Total auto-fixes:** 2 (both Rule-2-grade: shoot-day consistency +
plan-requirement satisfaction). Neither changed plan scope.

## TDD Gate Compliance

Task 1 had `tdd="true"`. Gate sequence verified in git log:
- RED: `c1877ed` (`test(43-08): ...`) — committed with the test failing
  on collection due to `ModuleNotFoundError: scripts.launch.check_cut_count`
- GREEN: `6e7dd06` (`feat(43-08): ...`) — committed the implementation;
  5/6 tests pass at this point (test 4 intentionally fails until Task 2
  lands data-cut markers on the storyboard, per plan §<behavior> Test 4
  note).
- REFACTOR: skipped (no cleanup needed after GREEN landed clean).

Task 2 closed the still-failing test 4 (now 6/6 pytest pass + cut-count
gate exit 0) by landing the data-cut="N" attributes on the storyboard.

## Issues Encountered

**Worktree absolute-path drift (#3099) bit me once.** First Edit call
used the bare `/Users/ozai/projects/dj-set-ai/...` path which resolved
to the **main repo**, not the worktree. Caught immediately via grep
verification; reverted the main-repo edit with `git checkout -- <file>`
(per-file form, not a blanket reset — within the destructive-git-
prohibition rules) and re-applied the edit inside the worktree path.
No commits leaked to the main repo branch. Going forward, all file
operations in Task 2 used `/Users/ozai/projects/dj-set-ai/.claude/worktrees/agent-acdd40062dde72d87/...` absolute paths anchored to
`git rev-parse --show-toplevel`.

This issue points to a process improvement worth noting (NOT a code
fix this plan owns): the worktree-isolated agents must always resolve
absolute paths from `WT_ROOT=$(git rev-parse --show-toplevel)`, never
from `pwd` captured before a `cd` boundary. The orchestrator could
prefix every Edit/Write prompt with `WT_ROOT=...` but that's a tooling
change beyond this plan's scope.

## User Setup Required

None — no external service configuration introduced.

## Next Phase Readiness

- **Plan 43-09** (Francesco handoff package — `docs/launch-prep/SHOT-LIST.md`
  + `AUDIO-CAPTURE.md` + `DEMO-MODE-CONFIG.md`) — fully unblocked. The
  8-cut sequence in `mocks/vibemix-cinematic-storyboard.html` is now
  the canonical script Francesco hands his crew. The data-cut="N"
  attributes are grep-able so the SHOT-LIST.md can be auto-generated
  from the storyboard frames if Plan 43-09 chooses.
- **Capture day post-Phase 43** — the storyboard now contains
  inline-rendered UI chips matching the actual shipped CDJ Whisper v5
  UI surfaces. The shoot can capture real running builds for cuts 2-6
  with confidence that the on-screen UI matches the storyboard.

Recommended follow-up (not in 43-08 scope):
- Resolve the deferred LFS-pointer drift on the 21 mascot GLB assets
  before Plan 43-04's Mixamo retarget pipeline runs.

## Known Stubs

None. The 8 cuts are fully fleshed out with SVG chip content + info
metadata + timecodes + durations. No "[placeholder]" or "TODO" markers
remain in the frames section.

## Threat Flags

None. The end-card publicly displays `altidus.world/vibemix` and
`github.com/bravoh/vibemix` — both are intended public marketing
surfaces per CONTEXT §VIS-08 + memory `project_github_star_goal`
(disposition: `accept` in the plan's threat register T-43-08-04). No
new trust boundaries crossed.

## Self-Check: PASSED

Verified via execution log:
- `scripts/launch/check_cut_count.py` exists — FOUND
- `tests/launch/test_cut_count.py` exists — FOUND
- Commit `c1877ed` (RED) exists — FOUND
- Commit `6e7dd06` (GREEN) exists — FOUND
- Commit `f53cb9f` (Task 2) exists — FOUND
- Cut count gate exit 0 — VERIFIED
- Palette gate exit 0 — VERIFIED (38 colors, all in allow-list)
- Cut count pytest 6/6 — VERIFIED
- Palette pytest 6/6 — VERIFIED
- 8 data-cut="N" attributes in storyboard — VERIFIED
- End-card CTA "open-source · MIT · github.com/bravoh/vibemix" present — VERIFIED
- AI caption verbatim "nice kick swap @ 2:33" present — VERIFIED
- No Workbench/DSEG7 regression — VERIFIED

---
*Phase: 43-visual-ship-lock*
*Plan: 08*
*Completed: 2026-05-16*
