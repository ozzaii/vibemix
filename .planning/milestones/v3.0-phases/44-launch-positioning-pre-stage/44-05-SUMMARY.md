---
phase: 44-launch-positioning-pre-stage
plan: 05
subsystem: launch
tags: [launch, social-copy, anti-slop, ci-gate, kaan-discharge, francesco, ship-tweet, tdd]
requirements: [LAUNCH-07]
dependency_graph:
  requires:
    - "scripts/dayzero/launch_copy/{twitter,instagram,linkedin,reddit}.txt (Phase 36-era drafts)"
    - "KAAN-ACTION-LEGAL.md §GATE-01 canonical 8-block discharge format (reference template)"
    - "scripts/launch/check_readme_hero_lock.py (Plan 44-01 — sibling check pattern + AI-slop blocklist reference)"
  provides:
    - "scripts/launch/check_no_ai_slop.py — single-source-of-truth AI_SLOP_BLOCKLIST + ANCHOR_PHRASES + LAUNCH_COPY_FILES module-level tuples for cross-channel sweeps"
    - "scripts/dayzero/launch_copy/discord.txt — 5th channel SHIP-TWEET copy (Bravoh #announcements T-0 post)"
    - "5-file signature footer infrastructure (Kaan + Francesco markers + Locked-for tag)"
    - "tests/launch/test_no_ai_slop.py — 13-test CI gate (4-axis pin: presence, signature, blocklist, anchor)"
    - "KAAN-ACTION-LEGAL.md §LAUNCH-07 — mutual sign-off discharge runbook"
  affects:
    - "Phase 45 SHIP-08 SHIP-TWEET live publish — `scripts/launch/publish_social_posts.py` consumes the 5 locked files at T-0"
    - "Phase 44 success criterion 5 — engineering side closed; Kaan + Francesco mutual signatures are the only remaining discharge"
tech_stack:
  added:
    - "pytest module-level shape tests (mirrors test_readme_hero_lock.py pattern)"
  patterns:
    - "Single-source-of-truth constants exported as module-level tuples (planner DRY across launch checks)"
    - "TDD RED → GREEN per task with negative synthetic-corpus mutation tests (one axis per case)"
    - "Append-only edits to KAAN-ACTION-LEGAL.md (preserves all existing §GATE-* / §VIS-* / §SHIP sections at original line offsets)"
key_files:
  created:
    - "scripts/launch/check_no_ai_slop.py (216 LOC)"
    - "tests/launch/test_no_ai_slop.py (337 LOC)"
    - "scripts/dayzero/launch_copy/discord.txt (17 lines — 5-12 body + 4-line footer)"
  modified:
    - "scripts/dayzero/launch_copy/twitter.txt (+5 lines — signature footer)"
    - "scripts/dayzero/launch_copy/instagram.txt (+5 lines — signature footer)"
    - "scripts/dayzero/launch_copy/linkedin.txt (+5 lines — signature footer)"
    - "scripts/dayzero/launch_copy/reddit.txt (+5 lines — signature footer)"
    - "KAAN-ACTION-LEGAL.md (+108 lines — §LAUNCH-07 runbook, append-only)"
decisions:
  - "AI_SLOP_BLOCKLIST exposed as the cross-launch single source of truth — Plan 44-01's local copy in check_readme_hero_lock.py stays untouched (avoid wave-1 file conflict with 44-02 if it ever consolidates); future check scripts can re-import from check_no_ai_slop."
  - "Signature VALUES stay blank `____` placeholders — engineering's gate only pins that the MARKER LINES (`Kaan signature:` / `Francesco signature:`) persist. Filling the values is the Kaan + Francesco mutual discharge tracked in §LAUNCH-07."
  - "Anchor-phrase check operates on COMBINED corpus, not per-file — gives Kaan + Francesco room to distribute the 5 anchors naturally across channels without forcing every anchor into every file (twitter would feel stuffed)."
  - "Negative-corpus mutation tests strip ALL case-variants of the target anchor across all 5 files (not just one), because the case-insensitive combined-corpus check finds ANY occurrence — the test discovered this gap during the first RED pass."
  - "discord.txt voice locked as DJ-to-DJ Discord-server tone (per planner-task brief + memory `feedback_no_scope_creep_clean_utility`): 5-12 lines, anchor phrases woven naturally, link line at the bottom, no marketing-speak. Matches twitter.txt punch."
metrics:
  duration_minutes: 18
  duration_seconds: 1080
  task_count: 3
  files_created: 3
  files_modified: 5
  commits: 3
  tests_added: 13
  tests_passing: 13
  loc_added: ~605
  completed_date: "2026-05-17"
---

# Phase 44 Plan 05: SHIP-TWEET 5-channel copy lock + AI-slop grep gate + §LAUNCH-07 runbook (LAUNCH-07) Summary

**One-liner:** Locked the SHIP-TWEET 5-channel launch copy behind a CI grep gate enforcing the 16-token AI-slop blocklist + 5 positive anchor phrases across the combined corpus, shipped the missing `discord.txt` (5th channel), appended Kaan + Francesco signature footers to all 5 files, and discharged the mutual sign-off into `KAAN-ACTION-LEGAL.md §LAUNCH-07`.

## What landed

### Task 1 — TDD RED: AI-slop check + tests (commit `65aec0b`)

- `scripts/launch/check_no_ai_slop.py` (216 LOC) — 4 gates:
  1. **Presence** — all 5 channel files exist
  2. **Signature footer** — `Kaan signature:` AND `Francesco signature:` markers in every file
  3. **AI-slop blocklist** — none of the 16 CONTEXT §specifics verbatim tokens (`leverage`, `synergize`, `revolutionize`, `game-changer`, `next-generation`, `cutting-edge`, `seamless`, `robust`, `powerful`, `intuitive`, `delightful experience`, `AI-powered`, `harness the power`, `unlock`, `transformative`, `paradigm`) appear in ANY file; `\bdeeply\s+\w+` regex matches zero times
  4. **Anchor phrases** — each of `real DJ friend in your ear`, `built by DJs`, `your audio doesn't leave`, `open source`/`open-source`, `Mac + Windows` appears at least once across the COMBINED 5-file corpus
- `tests/launch/test_no_ai_slop.py` (337 LOC, 13 tests) — module-shape pins (blocklist has exactly 16 canonical tokens), happy path (currently RED), 5 negative synthetic-corpus mutation cases, 2 CLI subprocess smoke tests
- After commit: happy path RED (discord.txt missing + footers absent in 4 existing files), 4 negative-case tests GREEN — confirms gate fires on all axes

### Task 2 — TDD GREEN: discord.txt + signature footers (commit `c15ae3a`)

- `scripts/dayzero/launch_copy/discord.txt` (NEW, 17 lines):
  - Bravoh `#announcements` T-0 post framing
  - DJ-to-DJ voice (matches `twitter.txt` punch)
  - Weaves all 3 combined-corpus-missing anchors naturally: `real DJ friend in your ear`, `built by DJs`, `your audio doesn't leave`
  - Reinforces `Mac + Windows` + `open-source` (already present in 4 files but kept for redundancy)
  - 4-line signature footer at bottom
- Sign-off footer appended (append-only, existing content verbatim) to all 4 existing files:
  ```
  ---
  Kaan signature:     ____  (date: ____)
  Francesco signature: ____  (date: ____)
  Locked for: v3.0.0-rc1 launch
  ```
- After commit: all 13 tests GREEN; `check_no_ai_slop.py` exits 0; verification: 5/5 files present, all signatures present, all 5 anchors present in combined corpus, 0 slop hits

### Task 3 — §LAUNCH-07 runbook (commit `8487679`)

- Append-only edit to `KAAN-ACTION-LEGAL.md` (+108 lines at line 1371):
  - `## §LAUNCH-07 — SHIP-TWEET 5-channel copy sign-off`
  - Canonical 8-block §GATE-01-style structure (REQ-ID, Owner, Status checklist, Effort, Blocking-for, Why-this-is-KAAN-action, Files-involved, Kaan-oneliner, Verification, What-unblocks, Sign-off-block)
  - Kaan-oneliner shows: diff format for signing both blanks, dry-run cat of all 5 files end-to-end, `lock(launch): SHIP-TWEET 5-channel copy locked v3.0.0-rc1` commit template
  - All 7 prior §-sections (§SHIP, §POST-RC-CLEANUP, §GATE-01..05, §VIS-04, §VIS-09) preserved at their original line offsets (no shifts)
- Verification: `grep -c "^## §LAUNCH-07" KAAN-ACTION-LEGAL.md` → 1

## Plan vs. SUMMARY counts

| Axis | Plan target | Delivered |
|------|-------------|-----------|
| Tasks | 3 | 3 ✅ |
| Commits | 3 | 3 ✅ |
| Files created | 3 (discord.txt, check_no_ai_slop.py, test_no_ai_slop.py) | 3 ✅ |
| Files modified | 5 (4 launch_copy txts + KAAN-ACTION-LEGAL.md) | 5 ✅ |
| Tests added | 4 minimum (per Task 1 brief) | 13 (exceeded — shape tests + 5 negatives + 2 CLI) |
| LAUNCH-07 closed engineering-green | yes | yes ✅ |

## Verification (all 5 plan checks GREEN)

```
$ uv run pytest tests/launch/test_no_ai_slop.py -v
13 passed in 0.06s

$ uv run python scripts/launch/check_no_ai_slop.py
PASS: scripts/dayzero/launch_copy — 5/5 files, all signatures present, all anchors present, 0 slop hits
EXIT=0

$ ls scripts/dayzero/launch_copy/*.txt | wc -l
5

$ grep -l "Kaan signature:" scripts/dayzero/launch_copy/*.txt | wc -l
5

$ grep -c "^## §LAUNCH-07" KAAN-ACTION-LEGAL.md
1
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] Negative-anchor test stripped only one occurrence**

- **Found during:** Task 1 RED-pass verification
- **Issue:** `test_negative_missing_anchor` initially stripped `Mac + Windows` from `twitter.txt` only — the synthetic baseline `discord.txt` body also contained `Mac + Windows` (built into `_build_valid_corpus`), so the combined-corpus check still found the anchor and the test passed when it should have failed
- **Fix:** Switched the mutation target to `real DJ friend in your ear`, used `re.sub` with `IGNORECASE` flag across ALL 5 files to ensure no case-variant survives
- **Files modified:** `tests/launch/test_no_ai_slop.py` (one test method, in-test fix)
- **Commit:** Folded into `65aec0b` (Task 1) — discovered + fixed during the same RED-verification cycle, not a separate commit
- **Why Rule 1:** Test that "passes" without actually exercising the failure path is a silent gap; classifies as a bug in test logic, not a checker bug

No other deviations — plan executed exactly as written.

## Authentication gates

None — fully autonomous execution; no auth required.

## Known stubs

None. Signature VALUES (`____` placeholders) are intentional discharge surface for §LAUNCH-07, not stubs — documented in the Kaan-oneliner with exact diff format.

## Threat flags

None — this plan ships CI gates + sign-off runbook + 5 plain-text social-media copy files. No new network endpoints, auth paths, file-access patterns, or schema changes at trust boundaries.

## Files

### Created

- `scripts/launch/check_no_ai_slop.py` — 216 LOC, 4-gate CI check, exports `AI_SLOP_BLOCKLIST` / `ANCHOR_PHRASES` / `LAUNCH_COPY_FILES` as single source of truth
- `tests/launch/test_no_ai_slop.py` — 337 LOC, 13 tests
- `scripts/dayzero/launch_copy/discord.txt` — 17 lines, 5th channel SHIP-TWEET copy

### Modified

- `scripts/dayzero/launch_copy/twitter.txt` — +5 lines (signature footer appended)
- `scripts/dayzero/launch_copy/instagram.txt` — +5 lines (signature footer appended)
- `scripts/dayzero/launch_copy/linkedin.txt` — +5 lines (signature footer appended)
- `scripts/dayzero/launch_copy/reddit.txt` — +5 lines (signature footer appended)
- `KAAN-ACTION-LEGAL.md` — +108 lines (§LAUNCH-07 runbook, append-only at line 1371)

## Commits

| Hash | Type | Description |
|------|------|-------------|
| `65aec0b` | test | TDD RED — check_no_ai_slop.py + tests (4 negatives GREEN, happy path RED) |
| `c15ae3a` | feat | TDD GREEN — discord.txt drafted + 5 signature footers appended (all 13 tests GREEN) |
| `8487679` | docs | §LAUNCH-07 runbook appended to KAAN-ACTION-LEGAL.md |

## What unblocks

- **Phase 45 SHIP-08 SHIP-TWEET live publish** — `scripts/launch/publish_social_posts.py --really` reads the 5 locked files at T-0 (per the LAUNCH-SEQUENCE doc shipped in 44-07). Without the mutual lock, the publish step gates closed.
- **Phase 44 success criterion 5** — "SHIP-TWEET copy files signed off (Kaan + Francesco mutual approval) for all 5 channels." Engineering green; mutual-sign discharge closes the row.
- **AI-slop blocklist as a CI gate (not aspiration)** — any future copy-edit PR that introduces a slop token or removes an anchor or breaks a signature footer will fail the gate before merge.

## Self-Check: PASSED

- All 8 declared files present on disk
- All 3 commit hashes (`65aec0b`, `c15ae3a`, `8487679`) present in `git log --oneline --all`
- All 5 plan verification checks GREEN (13 tests pass, check script exits 0, 5 files, 5 Kaan-sig markers, 1 §LAUNCH-07)
