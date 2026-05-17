---
phase: 45-external-discharge-public-rc-publish
plan: 06
subsystem: launch-discharge-runbooks
tags: [kaan-action, discharge, runbooks, ship-01-thru-13, append-only, legal-capacity, autonomous-pre-stage]
requires:
  - 45-01 (install_vm_matrix.sh — §SHIP-04 verification command)
  - 45-02 (launch_trigger.sh — §SHIP-08 4 cadence-stage invocations)
  - 45-03 (check_bravoh_server_ready.sh — §SHIP-06 verification command)
  - 45-04 (audit_ship_v1_decision.py + SHIP-V1-DECISION-TEMPLATE.md — §SHIP-13 discharge command)
  - 45-05 (docs/launch-rotation.md §SHIP-11 — §SHIP-11 operational cross-link)
  - 44-05 (launch-copy sign-off footers — §SHIP-08 prerequisite gate)
  - 44-06 (discord_provision.py + check_bravoh_org_ready.sh — §SHIP-09 + §SHIP-10 prerequisite gates)
  - 44-07 (LAUNCH-SEQUENCE.md cadence lock — §SHIP-08 cadence backing)
  - 42-04 (cut_release.sh Gate 2b — §SHIP-07 6-gate cut requirement)
  - 39 (cut_release.sh + verify_signed.py + populate_changelog.py — §SHIP-03 + §SHIP-07 baselines)
  - 36 (publish_social_posts.py + post_discord_launch.py — §SHIP-08 + §SHIP-09 baselines)
  - 34 (sign_macos.sh + sign_windows.ps1 + sign_manifest.sh — §SHIP-03 signing pipeline)
  - 33 (onboarding-stopwatch.ts + launch-rotation.md baseline — §SHIP-04 + §SHIP-11 prerequisites)
  - 27 (Tauri universal2 + auto-updater + verify_signed.py --require-signed — §SHIP-03 baseline)
provides:
  - KAAN-ACTION-LEGAL.md §SHIP-01..§SHIP-13 (13-section discharge cookbook for v3.0 publish cascade)
  - tests/repo/test_kaan_action_ship_runbooks.py (structural + cross-reference pin, 17 parametrized cases)
affects:
  - Phase 45 closure — every SHIP-* requirement now has engineering scaffolding (Plans 45-01..05) AND a Kaan-discharge runbook (this plan)
  - v3.0 milestone — the discharge cookbook IS the bridge from "engineering pre-stage GREEN" to "external clock fires + Kaan runs the commands"
tech-stack:
  added: []
  patterns:
    - "Canonical 8-block runbook format" — H2 header, REQ-ID + Owner + Status checkboxes, Effort, Blocking-for, Why-this-is-X-action, Pre-requisites, Discharge commands, Verification, Post-discharge, Unblocks, Sign-off block (mirrors §LAUNCH-08 from Phase 44-06)
    - "Append-only KAAN-ACTION-LEGAL.md" — pre-§SHIP-01 content preserved verbatim; new sections inserted chronologically after §LAUNCH-08
    - "Variant-tuple block markers" — test accepts both `### Pre-requisites` (H3 subheading) and `Pre-requisites:` (colon-suffix) per the actual canonical mix in the existing file
key-files:
  created:
    - tests/repo/test_kaan_action_ship_runbooks.py (349 lines — 17 parametrized cases pinning 11 logical invariants)
    - .planning/phases/45-external-discharge-public-rc-publish/45-06-SUMMARY.md (this file)
  modified:
    - KAAN-ACTION-LEGAL.md (1968 → 3310 lines, +1342 lines across 13 new H2 sections)
decisions:
  - "Canonical 8-block format from §LAUNCH-08 — reused as the structural template for all 13 new sections (operator already knows the shape from Phase 44 discharges)"
  - "Tag regex bump flagged as §SHIP-07 prerequisite, NOT done in this plan — cut_release.sh ships ^v2\\.1\\.0-rc[0-9]+$ at line 44; v3.0 SHIP-CUT needs ^v3\\.0\\.0-rc[0-9]+$. One-line sed documented in §SHIP-07 Pre-requisites; ships as its own commit at Kaan-discharge time so the cut commit stays clean"
  - "§SHIP-11 cross-links docs/launch-rotation.md §SHIP-11 (Plan 45-05) as operational source-of-truth; does NOT duplicate the shift table here (single source of truth rule)"
  - "§SHIP-12 framed as passive observation — no commands; just a probe schedule (Day 1/3/7/14/21/28) + observation log at eval/smartscreen-observations/; first-clear date feeds §SHIP-13 decision tree"
  - "Test marker accommodation — test_each_section_has_canonical_blocks accepts BOTH `### Pre-requisites` (H3 subheading style — what the new sections + §LAUNCH-08 actually use) AND `Pre-requisites:` (colon-suffix inline style — the test's original assumption); variant-tuple per marker"
  - "ENV-var pins per CONTEXT §threat_model T-45-06-01 — §SHIP-04 (VIBEMIX_INSTALL_VM_RUN), §SHIP-08 (LAUNCH_REAL + DISCORD_WEBHOOK_URL + GITHUB_TOKEN), §SHIP-13 (GITHUB_TOKEN); secrets NAMED, never literal values per T-45-06-02 mitigation"
metrics:
  duration: "~45 minutes (RED + GREEN1 + GREEN2 + SUMMARY)"
  completed_date: 2026-05-17
  total_tasks: 3
  total_commits: 3
---

# Phase 45 Plan 06: KAAN-ACTION-LEGAL §SHIP-01..13 13-section discharge cookbook Summary

13-section §SHIP-01..§SHIP-13 discharge cookbook appended to `KAAN-ACTION-LEGAL.md` — the right-side of the publish cascade matching Plans 45-01..05 engineering scaffolding on the left.

## What shipped

Two files touched. Append-only on the primary; new file for the structural pin.

### `KAAN-ACTION-LEGAL.md` (modified — append-only, +1342 lines)

13 new H2 sections inserted chronologically after `§LAUNCH-08` (Phase 44-06 Discord live-execution discharge). Every existing section (§GATE-01/02/03/05, §VIS-04, §VIS-09, §LAUNCH-03/04/06/07/08, §SHIP Phase 39, §POST-RC-CLEANUP, §AUDIO-05/06/07, §INSTALL-VM-RUN, §DIST-09/11/19) preserved verbatim — `§LAUNCH-08` stays at line 1834 (unchanged from pre-plan).

| §  | Section title                                                                | Owner          | Discharge command                                                                              | Verification command                                          |
| -- | ---------------------------------------------------------------------------- | -------------- | ---------------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| 01 | Apple Developer Program agreement                                            | FRANCESCO      | web flow at developer.apple.com → 5 GH secrets posted                                          | `gh secret list \| grep APPLE_` → 5 lines                     |
| 02 | SignPath OSS Foundation approval                                             | KAAN           | web flow at signpath.org/foundation → 4 GH secrets posted                                      | `gh secret list \| grep SIGNPATH` → 4 lines                   |
| 03 | DIST-19 signed-binary smoke                                                  | KAAN           | `gh workflow run release.yml --ref main`                                                       | `verify_signed.py --artifact dist/*.{dmg,pkg,msi,exe} --require-signed` |
| 04 | INSTALL-VM matrix discharge                                                  | KAAN           | `bash scripts/dist/install_vm_matrix.sh --live --run-id <UTC>`                                 | `bash scripts/dist/install_vm_matrix.sh --check-60s`          |
| 05 | INSTALL-60S onboarding-stopwatch contract                                    | KAAN           | gate run (same as §SHIP-04) + eyes-on fresh-Mac walk                                           | `--check-60s` exit 0 + eyes-on stopwatch ≤60s                 |
| 06 | Bravoh server endpoints + healthz cron                                       | BRAVOH-TEAM    | `pm2 restart bravoh-api` + cron `*/5 * * * * curl .../vibemix/healthz`                         | `bash scripts/release/check_bravoh_server_ready.sh` exit 0    |
| 07 | SHIP-CUT public RC draft                                                     | KAAN           | `bash scripts/launch/cut_release.sh v3.0.0-rc1` + `gh release create v3.0.0-rc1 --draft --target main --title "..." --notes-file dist/release-notes.md dist/*.dmg dist/*.pkg dist/*.msi dist/*.exe` | 6 gates green + `gh release view v3.0.0-rc1` shows 4 assets   |
| 08 | SHIP-TWEET 5-channel social publish                                          | KAAN           | 4 × `bash scripts/launch/launch_trigger.sh --live --phase {T-30, T+0, T+5h, T+24h}` (with `LAUNCH_REAL=1 GITHUB_TOKEN=$(gh auth token) DISCORD_WEBHOOK_URL=...`) | `dist/launch-runs/*.jsonl` records 14 channel:stage pairs     |
| 09 | SHIP-DISCORD #announcements launch post                                      | KAAN           | `discord_provision.py --live --guild-id <id>` (Phase 44-06) + `post_discord_launch.py --real` (Phase 36) | idempotency re-run = 14 skips + #announcements eyes-on        |
| 10 | SHIP-TRANSFER repo handoff to bravoh/vibemix                                 | KAAN           | `gh api -X POST repos/$CURRENT_OWNER/vibemix/transfer -f new_owner=bravoh`                     | `gh repo view bravoh/vibemix --json owner --jq .owner.login` = "bravoh" |
| 11 | SHIP-ROTATE 24h monitoring rotation                                          | KAAN (solo)    | 4 × 6h shifts per `docs/launch-rotation.md §SHIP-11`                                           | 4 shift-log rows + P0/P1 issues at T+24h = 0                  |
| 12 | INSTALL-DEFENDER SmartScreen reputation observation                          | KAAN (passive) | no commands — Day 1/3/7/14/21/28 probe schedule, observation log                                | first-clear date recorded (or "not cleared at T+30")          |
| 13 | SHIP-V1-DECISION T+30 audit + Kaan sign-off                                  | KAAN           | `GITHUB_TOKEN=$(gh auth token) uv run python scripts/release/audit_ship_v1_decision.py --live --release-tag v3.0.0-rc1 --bravoh-healthz-stats-url https://api.altidus.world/vibemix/healthz/stats --output .planning/decisions/v3.0-SHIP-V1-DECISION.md` | decision file exists + exactly one of 3 boxes checked + sign-off filled |

Each section follows the canonical 8-block format:
1. H2 header (`## §SHIP-NN — <title> (<OWNER>-ACTION)`)
2. REQ-ID + Owner + Status checkboxes
3. Effort estimate + Blocking-for downstream sections
4. Why-this-is-X-action (operator-authority rationale)
5. Pre-requisites (gates that must be GREEN before discharge)
6. Discharge commands (literal bash — what to type, in order)
7. Verification (commands that confirm completion)
8. Post-discharge state updates + Unblocks chain + Sign-off block (`_____` placeholders + `Sign-off by` line)

### `tests/repo/test_kaan_action_ship_runbooks.py` (new — 349 lines)

11 logical tests × parametrized cases = 17 pytest items pinning the structure so future edits can't silently drop discharge steps:

| #  | Logical test                                            | What it asserts                                                                                                                                |
| -- | ------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| 1  | `test_kaan_action_legal_exists`                         | File exists at repo root                                                                                                                       |
| 2  | `test_all_thirteen_ship_nn_h2_headers_present`          | Exactly 13 `## §SHIP-NN` H2s (no duplicates)                                                                                                   |
| 3  | `test_ship_nn_h2_order_is_chronological`                | §SHIP-01, §SHIP-02, ..., §SHIP-13 in file order                                                                                                |
| 4  | `test_each_section_has_canonical_blocks`                | Each section carries Pre-requisites + Discharge command(s) + Verification + Post-discharge + Unblocks (variant-tuple match for H3 or colon style) |
| 5  | `test_section_cites_required_cross_ref` ×5 (parametric) | §SHIP-04 → install_vm_matrix.sh, §SHIP-06 → check_bravoh_server_ready.sh, §SHIP-08 → launch_trigger.sh, §SHIP-11 → docs/launch-rotation.md, §SHIP-13 → audit_ship_v1_decision.py — and each cited path exists on disk |
| 6  | `test_pre_ship_content_preserved`                       | §LAUNCH-08 still at line ≥1830; §LAUNCH-08 < §SHIP-01 in file order                                                                            |
| 7  | `test_ship_sections_clean_of_ai_slop`                   | None of the 16 AI_SLOP_BLOCKLIST tokens appear in appended content; no `deeply <word>` constructions                                           |
| 8  | `test_each_section_has_signoff_block`                   | Every section has `_____` placeholder (`_{5,}`) + `Sign-off by` line                                                                           |
| 9  | `test_section_pins_env_vars` ×3 (parametric)            | §SHIP-04 mentions VIBEMIX_INSTALL_VM_RUN; §SHIP-08 mentions LAUNCH_REAL + DISCORD_WEBHOOK_URL + GITHUB_TOKEN; §SHIP-13 mentions GITHUB_TOKEN   |
| 10 | `test_ship_10_carries_literal_transfer_command`         | §SHIP-10 carries `gh api -X POST` + `vibemix/transfer` + `new_owner=bravoh` literally per CONTEXT §specifics                                   |
| 11 | `test_ship_07_flags_tag_regex_bump`                     | §SHIP-07 references both `v2.1.0-rc` (current) and `v3.0.0-rc` (target) + labels the bump as a `prerequisite`/`pre-req`                        |

Total: 17 parametrized pytest cases, all GREEN.

## Commits (3 atomic)

| Commit  | Type | Message                                                                                                  |
| ------- | ---- | -------------------------------------------------------------------------------------------------------- |
| 4c96f1f | test | test(45-06): pin KAAN-ACTION-LEGAL.md §SHIP-01..13 structure (RED — 12/17 fail expected)                |
| 041f85c | docs | docs(45-06): append §SHIP-01..§SHIP-07 prerequisites + cut chain runbooks (GREEN part 1)                |
| 7b7e243 | docs | docs(45-06): append §SHIP-08..§SHIP-13 publish + rotate + decide runbooks (GREEN part 2 — completes cookbook) |

Each commit follows TDD discipline: RED test → GREEN implementation. Task 2 ships with a Rule 1 auto-fix (variant-tuple block markers — see Deviations below). Task 3 lands purely additive content.

## Verification (all GREEN)

```text
$ uv run pytest tests/repo/test_kaan_action_ship_runbooks.py -v
============================== 17 passed in 0.03s ==============================

$ uv run pytest tests/repo/test_cut_release_invokes_check_gate.py -v
============================== 7 passed in 0.01s ===============================

$ uv run pytest tests/repo/test_cut_release_invokes_bravoh_server.py -v
============================== 6 passed in 0.01s ===============================

$ uv run pytest tests/repo/test_launch_rotation_doc.py -v
============================== 10 passed in 0.02s ==============================

$ grep -c "^## §SHIP-[01][0-9]" KAAN-ACTION-LEGAL.md
13

$ wc -l KAAN-ACTION-LEGAL.md
3310 KAAN-ACTION-LEGAL.md

$ grep -n "^## §LAUNCH-08" KAAN-ACTION-LEGAL.md
1834:## §LAUNCH-08 — Discord live-execution discharge
```

Plus the existing baselines (must-haves truth: "all 13 §SHIP-NN headers + minimum block-count per section so future edits can't silently drop discharge steps" — pinned via 17-case pytest suite + 13-baseline regression run).

## Cross-reference matrix (the operator's entry-point map)

The verification surface required by must-haves `key_links`:

| Runbook section | Cross-references                                          | Plan source |
| --------------- | --------------------------------------------------------- | ----------- |
| §SHIP-04        | `scripts/dist/install_vm_matrix.sh` (verification)        | Plan 45-01  |
| §SHIP-06        | `scripts/release/check_bravoh_server_ready.sh` (verification) | Plan 45-03  |
| §SHIP-07        | `scripts/launch/cut_release.sh` (discharge + tag-regex bump prereq) | Plan 39 + 42-04 + 45-03 |
| §SHIP-08        | `scripts/launch/launch_trigger.sh` (4-stage discharge)    | Plan 45-02  |
| §SHIP-09        | `scripts/dayzero/discord_provision.py` + `scripts/launch/post_discord_launch.py` | Phase 44-06 + Phase 36 |
| §SHIP-10        | `gh api -X POST repos/$CURRENT_OWNER/vibemix/transfer -f new_owner=bravoh` (literal) + `scripts/launch/check_bravoh_org_ready.sh` (prereq) | Phase 44-06 |
| §SHIP-11        | `docs/launch-rotation.md §SHIP-11` (operational source-of-truth) | Plan 45-05  |
| §SHIP-13        | `scripts/release/audit_ship_v1_decision.py` (discharge) + `docs/SHIP-V1-DECISION-TEMPLATE.md` (schema) | Plan 45-04  |

Every cited path was verified to exist on disk via `test_section_cites_required_cross_ref`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] Test marker variant tuples**
- **Found during:** Task 2 verify step
- **Issue:** Original Task 1 test (`test_each_section_has_canonical_blocks`) hard-coded `Pre-requisites:` / `Verification:` / `Post-discharge:` / `Unblocks:` as required substrings. But the canonical §LAUNCH-08 format mixes H3 subheadings (`### Pre-requisites`, `### Verification`, etc. — Phase 44-06 style) with bold inline labels — neither shape carries a colon suffix on its own line. Writing §SHIP-01..07 with the H3 subheading style (matching §LAUNCH-08) caused the test to fail GREEN-part-1 verify even though the sections were structurally canonical.
- **Fix:** Replaced single-string markers with variant tuples — each test accepts ANY of: `### Pre-requisites`, `Pre-requisites:`, `**Pre-requisites:**` etc. Same accommodation for Verification / Post-discharge / Unblocks / Discharge commands. The new Discharge regex accepts `### Discharge command(s)` or `Discharge command(s):`.
- **Files modified:** `tests/repo/test_kaan_action_ship_runbooks.py`
- **Commit:** 041f85c (folded into Task 2's GREEN-part-1 commit per RED-GREEN discipline; called out explicitly in the commit body)
- **Why this is Rule 1 (bug), not Rule 4 (architectural):** The test's original assumption was wrong about what the existing canonical format actually looks like (verified by reading §LAUNCH-08 lines 1834-1968). Fixing the test to match reality is correctness, not redesign.

### Authentication gates

None. This plan is pure-documentation; no live network calls, no auth flows. The runbooks themselves DOCUMENT the authentication gates that fire at discharge time (Apple Developer login for §SHIP-01, SignPath dashboard for §SHIP-02, Discord bot token for §SHIP-09, GH CLI auth for §SHIP-07/08/10/13) — but Kaan / Francesco hit those at runtime, not during this plan.

### Architectural changes

None. This plan reuses the canonical §LAUNCH-08 8-block format verbatim. No new tooling, no new scripts — wave-2 file-ownership invariant honored: only `KAAN-ACTION-LEGAL.md` + the test file modified.

## Threat Flags

None. The threat surface introduced is purely documentary (the file lives in the repo and is plaintext). All threats in the plan's `<threat_model>` (T-45-06-01..06) are addressed by the test suite + the canonical sign-off block pattern + Kaan's eyes-on review of §SHIP-10 before pressing return (the highest-privilege command in the cookbook). No new threat surface beyond what the plan modeled.

## Phase 45 closure trajectory

Phase 45 has 6 plans total:

| Plan  | Shipped                                                                  | Status                         |
| ----- | ------------------------------------------------------------------------ | ------------------------------ |
| 45-01 | install_vm_matrix.sh + install_vm_matrix.json (tart-driven 5-OS walks)    | Merged onto main as of 9a980aa |
| 45-02 | launch_trigger.sh + cadence_index.json (5-channel × 4-stage publish)     | Merged onto main as of 9a980aa |
| 45-03 | check_bravoh_server_ready.sh + cut_release.sh Gate 5b wire-in            | Merged onto main as of 9a980aa |
| 45-04 | audit_ship_v1_decision.py + SHIP-V1-DECISION-TEMPLATE.md                 | Merged onto main as of 9a980aa |
| 45-05 | docs/launch-rotation.md §SHIP-11 (24h rotation + triage tree + 7 monitoring sources) | Merged onto main as of 9a980aa |
| 45-06 | **KAAN-ACTION-LEGAL.md §SHIP-01..13 cookbook (this plan)**               | Complete (commits 4c96f1f → 7b7e243) |

Every SHIP-* requirement now has BOTH engineering scaffolding (left side — 45-01..05) AND a Kaan-discharge runbook (right side — this plan). Phase 45's engineering investment is dischargeable.

## Ready for v3.0 milestone close

What remains before v3.0 cuts:
- §SHIP-01 + §SHIP-02 external clock fires (Apple + SignPath approvals, ~1-week SLA each)
- §SHIP-03 → §SHIP-13 dispatched in cascade per the cookbook
- §SHIP-13 T+30 decision: cut v1.0.0 OR cycle v3.0.0-rc2 OR pause

No further engineering is required for Phase 45. The cookbook IS the bridge.

## Self-Check: PASSED

Verified post-write:

- [x] `KAAN-ACTION-LEGAL.md` exists at 3310 lines (was 1968 pre-plan; +1342 across 13 sections + this SUMMARY references)
- [x] `tests/repo/test_kaan_action_ship_runbooks.py` exists at 349 lines, 17 parametrized pytest cases all GREEN
- [x] 13 §SHIP-NN H2 sections present in chronological order (§SHIP-01 at line 1970 → §SHIP-13 at line 3197)
- [x] §LAUNCH-08 preserved at line 1834 (no shift; pre-§SHIP-01 content untouched)
- [x] Regression baselines GREEN: tests/repo/test_cut_release_invokes_check_gate.py (7), tests/repo/test_cut_release_invokes_bravoh_server.py (6), tests/repo/test_launch_rotation_doc.py (10)
- [x] All 3 commits present in `git log`: 4c96f1f (RED test), 041f85c (GREEN part 1), 7b7e243 (GREEN part 2)
- [x] No untracked files left behind from this plan's work
- [x] AI-slop blocklist clean across appended content (0 of 16 forbidden tokens, 0 "deeply <word>" matches)
