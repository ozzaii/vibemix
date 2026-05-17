---
phase: 44-launch-positioning-pre-stage
plan: 06
subsystem: launch-pre-stage
tags: [github-org, discord, kaan-discharge, dayzero, pre-stage, launch-06, launch-08]
requirements: [LAUNCH-06, LAUNCH-08]
req_ids: [LAUNCH-06, LAUNCH-08]
dependency_graph:
  requires:
    - 44-02 (KAAN-ACTION-LEGAL.md §LAUNCH-03 + §LAUNCH-04 — same file append pattern)
    - 44-05 (KAAN-ACTION-LEGAL.md §LAUNCH-07 — same file serialization gate)
  provides:
    - "scripts/launch/check_bravoh_org_ready.sh — polling gate for Plan 45 SHIP-TRANSFER"
    - "scripts/dayzero/discord_taxonomy.json — single source of truth for 5 roles + 9 channels"
    - "scripts/dayzero/discord_provision.py — refactored to consume taxonomy.json + Bravoh-token preference"
    - "KAAN-ACTION-LEGAL.md §LAUNCH-06 + §LAUNCH-08 — Kaan-discharge runbooks"
  affects:
    - 45-? (SHIP-TRANSFER will read check_bravoh_org_ready.sh as upstream gate)
    - 45-? (SHIP-DISCORD will read BRAVOH_DISCORD_BOT_TOKEN GH secret)
tech_stack:
  added:
    - "pytest marker: network (registered in pyproject.toml; opt-in live-network smoke tests)"
  patterns:
    - "Taxonomy lock via co-located JSON read at module import (Path(__file__).parent / *.json) — same pattern as future content packs / persona lists"
    - "Bot-token resolution order: Bravoh-naming preferred, legacy fallback for back-compat (BRAVOH_DISCORD_BOT_TOKEN → DISCORD_BOT_TOKEN)"
    - "Polling gate script convention: gh-first probe (uses Kaan's session if present), curl fallback (unauth-readable for public-org existence)"
key_files:
  created:
    - scripts/launch/check_bravoh_org_ready.sh
    - scripts/dayzero/discord_taxonomy.json
    - tests/dayzero/test_discord_provision_dryrun.py
    - tests/launch/test_check_bravoh_org_ready.py
    - tests/dayzero/.gitignore
  modified:
    - scripts/dayzero/discord_provision.py
    - tests/dayzero/test_discord_provision.py
    - pyproject.toml
    - KAAN-ACTION-LEGAL.md
decisions:
  - "Taxonomy MERGE rule: CONTEXT §LAUNCH-08 personal roles @kaan/@francesco collapse to existing founder; @member to lurker; @moderator is new. All Phase 36 channels preserved. Final canonical: 5 roles + 9 channels."
  - "Bot-token order: BRAVOH_DISCORD_BOT_TOKEN preferred over legacy DISCORD_BOT_TOKEN; both rejected → exit 2 with error naming both vars."
  - "Polling gate exit codes: 0=exists, 1=missing(404), 2=CLI usage error, 3=network failure. Discriminating 1 from 3 matters because Plan 45 SHIP-TRANSFER must distinguish 'not ready yet' (loop) from 'broken' (alert)."
  - "Pytest marker 'network' registered in pyproject.toml (--strict-markers requires it). Live-network smokes opt-in via pytest -m network; default CI uses 'not network'."
  - "Wave-2 file-ownership rule honored: KAAN-ACTION-LEGAL.md modified after 44-02 + 44-05 (each appended; no existing sections reordered/modified). All 4 prior §LAUNCH-* sections preserved verbatim."
metrics:
  duration_seconds: 587
  duration_human: "9m 47s"
  completed_date: "2026-05-17"
  tasks_completed: 3
  task_commits: 5
  files_created: 5
  files_modified: 4
  tests_added: 19
  tests_passing: 118
---

# Phase 44 Plan 06: Bravoh GH Org Standup + Discord Auto-Provision Dry-Run Lock + Check Scripts Summary

Bravoh GitHub org polling gate + Discord auto-provision taxonomy lock + dry-run zero-network pinning + Kaan-discharge runbooks (LAUNCH-06 + LAUNCH-08 pre-stage); engineering side ships everything; Kaan-discharge collapses to 4-line (LAUNCH-06) and 5-line (LAUNCH-08) Plan-45-launch-time tasks.

## What Shipped

### LAUNCH-06 — Bravoh GH org standup polling gate

- **`scripts/launch/check_bravoh_org_ready.sh`** (new, 156 lines, executable)
  - Polls `https://api.github.com/orgs/<org>` (default: bravoh).
  - **gh-first probe**: uses `gh api orgs/<org>` if `gh` is on PATH (zero-config, inherits Kaan's GH CLI session); discriminates HTTP 404 from other failure modes via stderr grep.
  - **curl fallback**: `curl -sS -o /dev/null -w "%{http_code}" https://api.github.com/orgs/<org>` (the public-org existence check is unauth-readable, so Plan 45 consumers don't need GH tokens just to verify the gate).
  - **CLI**: `--org NAME` (default bravoh), `--quiet` (suppress chatter; exit code is the contract), `-h`/`--help` (usage + exit-code reference).
  - **Exit codes**: 0=exists, 1=missing(404), 2=CLI usage error, 3=network failure. Discrimination matters for Plan 45 SHIP-TRANSFER's loop-vs-alert decision.
  - **Live verified**: `--org github` → exit 0; `--org vibemix-launch-06-canary-org-does-not-exist-xyz` → exit 1; `--org bravoh` → exit 1 (the entire point of the pre-stage — flips to 0 once Kaan creates the org).

- **`tests/launch/test_check_bravoh_org_ready.py`** (new, 9 offline tests + 2 network-marked)
  - Static invariants: file present + executable bit + `set -euo pipefail` header + `bash -n` clean + `--org` / `--quiet` / `--help` flags + default org=bravoh + targets GitHub orgs/ endpoint + `--help` exits 0.
  - Live network smokes (`@pytest.mark.network`, skipped by default): well-known org `github` → exit 0; long random-looking org → exit 1.

### LAUNCH-08 — Discord auto-provision dry-run lock

- **`scripts/dayzero/discord_taxonomy.json`** (new, single source of truth)
  - **5 roles**: founder, contributor, DJ, lurker, moderator.
  - **9 channels**: announcements, general, help, show-and-tell, controllers, ai-misbehavior, dev, bugs, showcase.
  - **Merge resolution embedded** in JSON `_merge_resolution` field: CONTEXT §LAUNCH-08 personal roles `@kaan`/`@francesco` collapse to existing `founder`; `@member` collapses to existing `lurker`; `@moderator` is new. All Phase 36 channels preserved (no regressions); CONTEXT additions `general`/`bugs`/`showcase` merged.

- **`scripts/dayzero/discord_provision.py`** (refactored, +124/-30 lines)
  - **Taxonomy load at module import**: `_load_taxonomy(TAXONOMY_PATH)` reads the JSON; `TARGET_ROLES`, `TARGET_CHANNELS`, `GUILD_NAME` derived from it. No second source of truth.
  - **`TAXONOMY_PATH` exposed** as module attribute so tests can pin path resolution + `Path(__file__).parent` semantics (script-relative, not CWD-relative).
  - **Bot-token resolution**: `_resolve_bot_token()` returns `(token, source_env_name)` — prefers `BRAVOH_DISCORD_BOT_TOKEN` (Bravoh-naming convention), falls back to `DISCORD_BOT_TOKEN` (Phase 36 back-compat). Both unset → `(None, None)` → `--live` exits 2 with error message naming BOTH vars.
  - **Audit logging**: `--live` always prints `[live] bot token source: <ENV_NAME>` (token value never logged); diagnostic env `DISCORD_PROVISION_DIAG_TOKEN_SOURCE=1` surfaces the same to stderr for test assertions.
  - **Upgraded dry-run output**: explicit `roles target (5): ...` + `channels target (9): #...` + `taxonomy source: <path>` for audit clarity; existing `[plan] create role <X>` / `[plan] create channel #<Y>` lines preserved.
  - **Lazy `discord.py` import preserved**: dry-run on a fresh checkout (no `pip install discord.py`) succeeds (pinned by the new test).

- **`tests/dayzero/test_discord_provision_dryrun.py`** (new, 10 tests)
  - **Taxonomy contract**: JSON exists + parseable; carries canonical merged 5 roles + 9 channels + guild_name=vibemix.
  - **Script consumption**: `TARGET_ROLES` + `TARGET_CHANNELS` derived from JSON (single source of truth); `TAXONOMY_PATH` exposed + script-relative.
  - **Dry-run defaults**: no CLI args → dry-run, exit 0, prints all 5 roles + 9 channels, no `[done]` markers.
  - **Dry-run zero-SDK**: sitecustomize import-blocker injected via PYTHONPATH proves dry-run never attempts `import discord`.
  - **Dry-run zero-network**: spawned under invalid `http_proxy=http://127.0.0.1:1`; still exits 0 (any HTTP attempt would fail through the proxy and surface non-zero).
  - **Token preference**: `--live` with both env vars set → BRAVOH wins (diagnostic env confirms); BRAVOH unset → falls back to legacy; neither → exit 2 with error naming BRAVOH var first.

- **`tests/dayzero/test_discord_provision.py`** (legacy test file, updated for new taxonomy)
  - `test_target_state_matches_requirements`: updated from 4 roles + 6 channels → 5 + 9 (Rule 1 fix: existing test would have broken on `TARGET_ROLES` change). Comment updated to reference LAUNCH-08 + the new dry-run test as the merge-resolution canonical.
  - `test_discord_provision_idempotent_partial`, `test_discord_provision_token_env_required_for_live`, `test_apply_plan_live_calls_only_missing_entries`: updated to expect the new taxonomy + the new error message format (which names both BRAVOH + legacy vars).

### Discharge runbooks

- **`KAAN-ACTION-LEGAL.md` §LAUNCH-06** (260-line append, canonical §GATE-01-style 8-block):
  - 5-step Kaan oneliner: resolve Bravoh Enterprise billing flag → create `bravoh` org (UI or Enterprise admin path documented) → invite Kaan + Francesco as admins → verify `bash scripts/launch/check_bravoh_org_ready.sh` exits 0.
  - Verification block: 4 commands (gate exit 0, offline pytest, live-network pytest, manual `gh api orgs/bravoh/members --jq` audit).
  - Unblocks: Plan 45 SHIP-TRANSFER + README install URLs going live + ROADMAP P44 success criterion 4.
  - 6-line sign-off block: engineering green / billing / org / owners / gate / Kaan signature.

- **`KAAN-ACTION-LEGAL.md` §LAUNCH-08** (same append, 8-block):
  - 5-step Kaan oneliner: create Bravoh-vibemix Discord guild → source bot token from Discord Developer Portal → `gh secret set BRAVOH_DISCORD_BOT_TOKEN` → dry-run verify → `--live` execute.
  - Verification block: pytest green + manual guild inspection (5 roles + 9 channels) + idempotency smoke (re-run shows 14 skips) + token-source audit (`[live] bot token source: BRAVOH_DISCORD_BOT_TOKEN`).
  - Unblocks: Plan 45 SHIP-DISCORD + onboarding doc community surface + ROADMAP P44 success criterion 6.
  - 8-line sign-off block: engineering / guild / token / guild-id / GH secret / dry-run / live execute / Kaan signature.

## Verification

Plan-level verification suite (all GREEN):

| # | Command | Result |
|---|---------|--------|
| 1 | `uv run pytest tests/dayzero/test_discord_provision_dryrun.py -v` | 10/10 pass |
| 2 | `uv run python scripts/dayzero/discord_provision.py` (default dry-run) | prints 5 roles + 9 channels + "DRY-RUN complete"; exit 0; zero network |
| 3 | `bash -n scripts/launch/check_bravoh_org_ready.sh` | syntax-ok |
| 4 | `bash scripts/launch/check_bravoh_org_ready.sh --org github --quiet && echo OK` | OK (live smoke) |
| 5 | `grep -c "^## §LAUNCH-0[68]" KAAN-ACTION-LEGAL.md` | exactly 2 |
| 6 | `python3 -c 'import json; d=json.load(open("scripts/dayzero/discord_taxonomy.json")); assert len(d["roles"])==5 and len(d["channels"])==9'` | exit 0 |

Full regression suite: `uv run pytest tests/dayzero/ tests/launch/ -v -m "not network"` → **118 passed**, zero regressions.

## Commits (this plan)

| # | Commit | Type | Summary |
|---|--------|------|---------|
| 1 | `5ba8aba` | test | RED — pin Discord taxonomy.json + dry-run zero-network + token preference (8 RED + 2 invariants) |
| 2 | `8d36609` | feat | GREEN — lock taxonomy + Bravoh-token preference (taxonomy.json + provision script refactor + legacy test update; 17/17 pass) |
| 3 | `d870d32` | test | RED — pin check_bravoh_org_ready.sh contract (9 RED + 2 network-marked) |
| 4 | `e656194` | feat | GREEN — implement check_bravoh_org_ready.sh polling gate (gh-first + curl fallback, 4 exit codes, 9/9 offline tests pass) |
| 5 | `32e6f33` | docs | §LAUNCH-06 + §LAUNCH-08 Kaan-discharge runbooks (260-line append, canonical §GATE-01-style 8-block) |

## Deviations from Plan

**1. [Rule 3 - Blocking] Registered `network` pytest marker in `pyproject.toml`**
- **Found during:** Task 2 RED test design.
- **Issue:** `pyproject.toml` configures pytest with `--strict-markers`, so any unregistered marker (including `@pytest.mark.network`) causes test collection to fail with `'network' not found in markers configuration option`.
- **Fix:** Added `"network: live-network smoke tests (e.g. LAUNCH-06 GitHub org poller); opt-in via 'pytest -m network'"` to the existing `markers = [...]` list in `[tool.pytest.ini_options]`, following the same pattern as `macos_audio`, `windows_only`, `integration`, `slow`, `parity`, `cli`, `e2e`.
- **Files modified:** `pyproject.toml` (one-line addition).
- **Commit:** `d870d32` (bundled with the Task 2 RED commit since the marker is needed for the test to even collect).

**2. [Rule 1 - Bug] Updated `tests/dayzero/test_discord_provision.py` to match new merged taxonomy**
- **Found during:** Task 1 GREEN — refactoring `discord_provision.py` to consume `discord_taxonomy.json` changed `TARGET_ROLES` from 4 → 5 and `TARGET_CHANNELS` from 6 → 9.
- **Issue:** The existing test `test_target_state_matches_requirements` pinned the OLD `OPS-09 4 roles + 6 channels` contract via `assert mod.TARGET_ROLES == ("founder", "contributor", "DJ", "lurker")`. Without updating, the legacy test file would break and the plan's success criteria couldn't be verified.
- **Fix:** Updated 4 assertions in the legacy file to expect the new merged taxonomy (5 roles + 9 channels) + the new error-message contract (names BRAVOH var first). Test comment updated to reference LAUNCH-08 + the new dry-run test as the merge-resolution canonical.
- **Files modified:** `tests/dayzero/test_discord_provision.py`.
- **Commit:** `8d36609` (bundled with Task 1 GREEN since both files must move together).

**3. [Rule 2 - Critical] Added audit logging of token source name in `--live` mode**
- **Found during:** Task 1 GREEN — `--live` mode picks a token from one of two env vars but never surfaced which one. Without this, post-incident audit cannot prove the live execution used the Bravoh-managed token vs the legacy var.
- **Fix:** `--live` always prints `[live] bot token source: <ENV_NAME>` to stdout (token VALUE never logged); diagnostic env `DISCORD_PROVISION_DIAG_TOKEN_SOURCE=1` surfaces the same line to stderr (used by the token-preference tests).
- **Why critical:** Bravoh's secrets-rotation runbook must distinguish Bravoh-managed tokens from Kaan-personal-fallback tokens; without the audit line, that distinction is invisible.
- **Files modified:** `scripts/dayzero/discord_provision.py`.
- **Commit:** `8d36609` (bundled with Task 1 GREEN).

**4. [Rule 3 - Blocking] Added `tests/dayzero/.gitignore` for `_discord_blocker/` test artifact**
- **Found during:** Task 1 RED — `test_dry_run_does_not_import_discord_sdk` writes a sitecustomize import-blocker module to `tests/dayzero/_discord_blocker/sitecustomize.py` then injects it via PYTHONPATH. Without a `.gitignore` entry, every test run would leave the artifact as an untracked file flagged by `git status`.
- **Fix:** Created `tests/dayzero/.gitignore` with `_discord_blocker/` entry.
- **Files modified:** `tests/dayzero/.gitignore` (new file, 2 lines).
- **Commit:** `5ba8aba` (bundled with Task 1 RED since the artifact is created the moment the test runs).

## Known Stubs

None. All shipped code is production-ready; the only "stub" surfaces are:

- `KAAN-ACTION-LEGAL.md §LAUNCH-06 + §LAUNCH-08` sign-off blocks have blank `_____` placeholders — by design (those are the Kaan-fill-in lines per the canonical §GATE-* format).
- `bravoh` GH org does not exist yet — by design (the entire point of the LAUNCH-06 pre-stage; the polling script correctly reports exit 1 until Kaan creates it).
- Bravoh-vibemix Discord guild does not exist yet — by design (LAUNCH-08 pre-stage; dry-run validates the plan without touching Discord).

## Threat Flags

None. This plan touches only:
- A pre-existing localhost-only provisioning script (defaults to dry-run; no new network surface).
- A new polling script that hits the GitHub public API for org existence (no auth, no PII, well-established surface).
- Documentation (KAAN-ACTION-LEGAL.md sections).

No new auth paths, no new file access patterns, no schema changes at trust boundaries.

## Self-Check: PASSED

- File `scripts/launch/check_bravoh_org_ready.sh` exists + executable bit set (verified via `git ls-files --stage` → `100755`).
- File `scripts/dayzero/discord_taxonomy.json` exists + valid JSON + 5 roles + 9 channels.
- File `tests/dayzero/test_discord_provision_dryrun.py` exists; 10 tests pass.
- File `tests/launch/test_check_bravoh_org_ready.py` exists; 9 offline tests pass; 2 network tests pinned.
- File `KAAN-ACTION-LEGAL.md` carries `## §LAUNCH-06` and `## §LAUNCH-08` headers (grep count = 2).
- All 5 task commits present in `git log` (5ba8aba, 8d36609, d870d32, e656194, 32e6f33).
- Plan verification suite all 6 checks green.
- Full regression: 118 dayzero + launch tests pass under `-m "not network"`.
