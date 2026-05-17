---
phase: 44-launch-positioning-pre-stage
plan: 07
subsystem: launch-orchestration
tags: [launch, outreach, calendar, sequence, docs, ci-gate]
requires:
  - "scripts/dayzero/seed_stars.md (existing pre-seed star protocol)"
  - "docs/launch-prep/README.md (Phase 43-09 index — extended append-only)"
  - "docs/launch-rotation.md (Phase 39 day-of rotation schedule)"
provides:
  - "docs/launch-prep/OUTREACH-CALENDAR.md (LAUNCH-09)"
  - "docs/launch-prep/LAUNCH-SEQUENCE.md (LAUNCH-10)"
  - "scripts/launch/check_launch_docs.py (CI gate)"
  - "tests/launch/test_launch_docs.py (structural pin, 7 tests)"
affects:
  - "docs/launch-prep/README.md (append-only 'Launch orchestration' section)"
tech-stack:
  added: []
  patterns:
    - "CI gate mirrors check_cut_count.py / check_storyboard_palette.py shape (Phase 43 family)"
    - "Try/except import fallback for cross-worktree Wave-1 parallel safety (AI_SLOP_BLOCKLIST sourced from Plan 44-05 when present, inline canonical CONTEXT §LAUNCH-07 copy otherwise)"
key-files:
  created:
    - "docs/launch-prep/OUTREACH-CALENDAR.md"
    - "docs/launch-prep/LAUNCH-SEQUENCE.md"
    - "scripts/launch/check_launch_docs.py"
    - "tests/launch/test_launch_docs.py"
    - ".planning/phases/44-launch-positioning-pre-stage/44-07-SUMMARY.md"
  modified:
    - "docs/launch-prep/README.md (append-only Launch-orchestration section)"
decisions:
  - "Relaxed the PLAN.md <verify> regex from literal '^## T-' to '^## T[-+]' so all 7 plan-prescribed rows (T-7, T-3, T-0, T+24h, T+72h, T+7d, T+30) count — the literal regex would only match the first 3 rows (Rule 1 fix; documented inline + below)"
  - "Sourced AI_SLOP_BLOCKLIST via try/except import from scripts.launch.check_no_ai_slop (Plan 44-05 SoT) with inline canonical fallback from CONTEXT §LAUNCH-07 — Wave-1 parallel-worktree safety so 44-07 ships independently of 44-05's merge order"
  - "Kept all editorial-pitch email bodies + subreddit post bodies as drafts (not lock-signed) — Kaan + Francesco edit on the day-of per CONTEXT §LAUNCH-09 discharge"
  - "Honored the CONTEXT §LAUNCH-09 anti-feature carveout (exactly 7 outreach entries — 3 editorial + 3 subreddit + 1 Discord T-3; no AI-generated channel sprawl)"
metrics:
  duration: ~25 min
  completed: 2026-05-16
  tasks_completed: 3
  files_created: 4
  files_modified: 1
  tests_added: 7
  tests_green: 7
---

# Phase 44 Plan 07: Outreach Calendar + Launch Sequence Doc Summary

T-7 → T+30 launch synchronization spine + per-channel outreach checklist
shipped, with a 5-assertion CI gate covering structural completeness and
AI-slop blocklist hygiene.

## What shipped

Two new Markdown docs under `docs/launch-prep/` plus a CI gate + pinning
test under `scripts/launch/` and `tests/launch/`:

1. **`docs/launch-prep/OUTREACH-CALENDAR.md`** (LAUNCH-09) — 268 lines.
   - 3 editorial pitches: DJ TechTools, DDJ Tips, Mixmag — each with a
     draft email body (~150-200 words) anchored on the locked hero
     one-liner ("the only AI co-host that actually listens to your set"),
     "built by DJs", "your audio doesn't leave your machine",
     open-source / Apache 2.0, and a Francesco-cut 30s demo offer
   - 3 subreddit cross-posts: r/DJs, r/Beatmatch, r/edmproduction — Show
     HN-style framing with title + body draft (~80-150 words) + explicit
     "feedback wanted on…" prompt per reddit norms
   - 1 DJ TechTools Discord T-3 soft-launch slot with channel
     (`#gear-talk` default, Ean-Golden-confirmed), CET evening window
     (19:00-22:00), and casual copy block
   - 4-state status checkbox on every entry
     (`☐ Drafted ☐ Sent ☐ Acknowledged ☐ Published`; Discord variant
     uses `Slot Reserved` / `Posted` per §LAUNCH-09)
   - Post-launch tracking table mirrors all 7 entries
2. **`docs/launch-prep/LAUNCH-SEQUENCE.md`** (LAUNCH-10) — 288 lines.
   - 7-row T-7 → T+30 timeline matching CONTEXT §LAUNCH-10 verbatim:
     T-7 pre-seed dev-network stars (cross-links `seed_stars.md` + P59);
     T-3 DJ TechTools Discord soft-launch (cross-links §LAUNCH-08);
     T-0 Show HN early-ET + 5-channel cross-post + outreach emails fire
     (cross-links Phase 45 SHIP-07/08/09 + §LAUNCH-07);
     T+24h maintainer-answers-every-comment rotation (cross-links
     `docs/launch-rotation.md` + §SHIP-ROTATE);
     T+72h Substack "how we built it" with 6-bullet outline + 2 optional
     bullets (why-DJs-not-VCs, anti-slop as UX problem, 3-Part Gemini
     grounding stack, what-we-cut, 30-day star delta, optional install
     dance, optional Francesco's DJ ear);
     T+7d "week-1 numbers" transparency template with `____` fill-in
     slots (stars, installs, Discord members, AI-slop incidents, PRs
     merged, controller-mapping contributions, learnings, next, thanks);
     T+30 SHIP-V1-DECISION review with 5-row decision rubric (cross-
     links Phase 45 SHIP-13)
   - 3 distinct `§LAUNCH-*` runbook anchors cross-referenced
     (`§LAUNCH-07`, `§LAUNCH-08`, `§LAUNCH-09`); additionally
     `§SHIP-ROTATE` + ROADMAP Phase 45 SHIP-07/08/09/13 anchors
   - AI-slop blocklist clean
3. **`docs/launch-prep/README.md`** — append-only "Launch orchestration"
   section listing both new docs; Phase 43-09 content preserved verbatim.
4. **`scripts/launch/check_launch_docs.py`** (296 lines) — 5-gate CI
   check:
     a. `OUTREACH-CALENDAR.md` exists and has ≥7 `☐ Drafted` checkbox
        blocks (`REQUIRED_CHECKBOX_BLOCKS = 7`)
     b. `LAUNCH-SEQUENCE.md` exists and has exactly 7 `^## T[-+]` rows
        (`REQUIRED_T_ROWS = 7`)
     c. `LAUNCH-SEQUENCE.md` cross-references ≥3 distinct `§LAUNCH-0[6-9]`
        anchors (`REQUIRED_LAUNCH_ANCHORS = 3`)
     d. Both docs are AI-slop-blocklist clean (substring + `\bdeeply\b`
        adverb regex)
     e. `README.md` references both new docs by filename
   - CLI: `--launch-prep-dir PATH` + `--quiet`; exit 0 on full pass, 1
     with failure-specific stderr on any miss
   - `AI_SLOP_BLOCKLIST` sourced via try/except import from
     `scripts.launch.check_no_ai_slop` (Plan 44-05 SoT) with inline
     canonical fallback from CONTEXT §LAUNCH-07
5. **`tests/launch/test_launch_docs.py`** (198 lines) — 7-test pin:
     - `test_module_imports_cleanly` — public symbols present
     - `test_constants_match_context` — 7 / 7 / 3 hard-pin
     - `test_ai_slop_blocklist_contains_canonical_tokens` — 5 canonical
       tokens spot-check (leverage / revolutionize / game-changer /
       seamless / paradigm)
     - `test_happy_path_against_real_launch_prep_docs` — exit 0 against
       real `docs/launch-prep/` after Tasks 1+2
     - `test_outreach_calendar_six_blocks_is_rejected` — 6 checkbox
       blocks → exit 1 + "checkbox" stderr
     - `test_launch_sequence_six_rows_is_rejected` — 6 T-rows → exit 1
     - `test_launch_sequence_with_slop_token_is_rejected` — slop token
       "leverage" → exit 1 + "slop"/"leverage" stderr

## Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Draft OUTREACH-CALENDAR.md | `014efbf` | `docs/launch-prep/OUTREACH-CALENDAR.md` |
| 2 | Draft LAUNCH-SEQUENCE.md + extend README | `beaf4e7` | `docs/launch-prep/LAUNCH-SEQUENCE.md`, `docs/launch-prep/README.md` |
| 3a (RED) | Failing test pin | `7562de6` | `tests/launch/test_launch_docs.py` |
| 3b (GREEN) | Implement check_launch_docs.py | `253163d` | `scripts/launch/check_launch_docs.py` |

## Verification

All plan-prescribed verifications green:

```text
=== uv run pytest tests/launch/test_launch_docs.py -v ===
7 passed in 0.07s

=== uv run python scripts/launch/check_launch_docs.py ===
[outreach-calendar] checkbox blocks: 7 (need >= 7)
[launch-sequence] T-rows: 7 (need exactly 7)
[launch-sequence] distinct §LAUNCH-0[6-9] anchors: 3 (need >= 3;
  saw ['§LAUNCH-07', '§LAUNCH-08', '§LAUNCH-09'])
[readme] cross-links present: True
[check_launch_docs] OK — all gates pass
exit=0
```

OUTREACH-CALENDAR.md (268 lines) ≥ 80-line min; LAUNCH-SEQUENCE.md
(288 lines) ≥ 60-line min. Both docs AI-slop-blocklist clean (no
`leverage` / `synergize` / `revolutionize` / `game-changer` /
`next-generation` / `cutting-edge` / `seamless` / `robust` / `powerful` /
`intuitive` / `delightful experience` / `AI-powered` /
`harness the power` / `unlock` / `transformative` / `paradigm` and no
`\bdeeply\s+\w+` adverb pattern).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Relaxed `^## T-` regex to `^## T[-+]`**

- **Found during:** Task 2 / Task 3 contract reconciliation
- **Issue:** PLAN.md Task 2 `<verify>` and Task 3 `<behavior>` both use
  the literal regex `^## T-` for the LAUNCH-SEQUENCE.md timeline-row
  count. The same PLAN.md prescribes 7 rows: T-7, T-3, T-0, T+24h,
  T+72h, T+7d, T+30. The literal regex only matches the first 3 (T-7,
  T-3, T-0) — the 4 post-launch rows start with `## T+`, not `## T-`.
  Using the literal regex would either (a) fail the verify with 3
  rows instead of 7, or (b) force ugly heading rewrites like
  `## T-+24h` that break the CONTEXT §LAUNCH-10 vocabulary.
- **Fix:** Authored the check script (which is the CI gate authority,
  per Task 3) to use `^## T[-+]` — matches all 7 plan-prescribed rows.
  The test `test_launch_sequence_six_rows_is_rejected` still pins the
  exact count (6 → reject; 7 → pass), so the structural contract is
  enforced; only the literal regex character class is widened.
- **Files modified:** `scripts/launch/check_launch_docs.py`,
  `tests/launch/test_launch_docs.py` (both via authoring choice)
- **Commit:** `253163d`

**2. [Rule 3 - Blocking] AI_SLOP_BLOCKLIST source fallback**

- **Found during:** Task 3 implementation
- **Issue:** The PLAN.md Task 3 behavior contract requires
  `Imports AI_SLOP_BLOCKLIST + ANCHOR_PHRASES from scripts.launch.check_no_ai_slop`
  (Plan 44-05 single-source-of-truth). Plan 44-05 runs in a parallel
  Wave-1 worktree and may not have merged to this worktree at write
  time (and indeed had not at this commit). A hard import would have
  blocked Task 3 from finishing until 44-05 merged.
- **Fix:** Authored a try/except import chain — prefers the 44-05 SoT
  module when on disk, falls back to an inline canonical copy of the
  blocklist + anchor phrases sourced verbatim from CONTEXT §LAUNCH-07.
  Once Plan 44-05 merges, the import succeeds silently and the inline
  fallback becomes a no-op. No coupling violation either way.
- **Files modified:** `scripts/launch/check_launch_docs.py`
- **Commit:** `253163d`

### Auth Gates

None.

## Known Stubs

None. The `____` slots in OUTREACH-CALENDAR.md (editor handles,
best-time-to-post windows) and LAUNCH-SEQUENCE.md (T+30 decision-rubric
bars, T+7d transparency-template numbers) are intentional fill-in
placeholders by design per CONTEXT §LAUNCH-09 + §LAUNCH-10 — they are
the Kaan-side discharge fields the docs are built around, not stubs.

## Threat Flags

None — both new docs are operator-facing planning artifacts. No network
endpoints, no auth paths, no schema changes, no new file-access
patterns introduced. The CI gate script is a pure read-only checker.

## Cross-link discipline

- `scripts/dayzero/seed_stars.md` — cross-linked (T-7 row), not
  duplicated; remains the source of truth for the pre-seed star list
- `docs/launch-rotation.md` — cross-linked (T+24h row), not duplicated;
  remains the day-of rotation source of truth
- `KAAN-ACTION-LEGAL.md §LAUNCH-07 / §LAUNCH-08 / §LAUNCH-09 /
  §SHIP-ROTATE` — cross-linked as runbook anchors (the actual
  discharge content lives in 44-05 + 44-06 + Phase 39)
- Phase 45 SHIP-07 / SHIP-08 / SHIP-09 / SHIP-13 — cross-linked as
  ROADMAP anchors (the actual ship-trigger code lives in Phase 45)

## Self-Check: PASSED

Files confirmed:
- `docs/launch-prep/OUTREACH-CALENDAR.md`: FOUND
- `docs/launch-prep/LAUNCH-SEQUENCE.md`: FOUND
- `docs/launch-prep/README.md` (modified): FOUND
- `scripts/launch/check_launch_docs.py`: FOUND
- `tests/launch/test_launch_docs.py`: FOUND

Commits confirmed:
- `014efbf` (Task 1): FOUND
- `beaf4e7` (Task 2): FOUND
- `7562de6` (Task 3 RED): FOUND
- `253163d` (Task 3 GREEN): FOUND
