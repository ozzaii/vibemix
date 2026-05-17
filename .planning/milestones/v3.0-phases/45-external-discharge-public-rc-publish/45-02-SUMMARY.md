---
phase: 45-external-discharge-public-rc-publish
plan: 02
subsystem: launch
tags: [launch, orchestration, social, discord, dry-run-default, ship-08]
requires:
  - scripts/dayzero/launch_copy/twitter.txt   # Plan 44-05 locked
  - scripts/dayzero/launch_copy/instagram.txt # Plan 44-05 locked
  - scripts/dayzero/launch_copy/linkedin.txt  # Plan 44-05 locked
  - scripts/dayzero/launch_copy/reddit.txt    # Plan 44-05 locked
  - scripts/dayzero/launch_copy/discord.txt   # Plan 44-05 locked
  - scripts/launch/publish_social_posts.py    # Phase 36 / SHIP-03
  - scripts/launch/post_discord_launch.py     # Phase 36 / SHIP-04
  - scripts/launch/check_no_ai_slop.py        # Plan 44-05 / LAUNCH-07
provides:
  - scripts/launch/launch_trigger.sh           # single discharge entry point — SHIP-08
  - scripts/dayzero/launch_copy/cadence_index.json # versioned per-channel × per-stage matrix
  - dist/launch-runs/<UTC>.jsonl               # append-only audit log (Plan 45-04 consumes)
affects:
  - scripts/launch/                            # new bash orchestrator
  - scripts/dayzero/launch_copy/               # +1 JSON data file
  - dist/launch-runs/                          # whitelisted in .gitignore
tech-stack:
  added: []
  patterns:
    - dry-run-default with explicit --live flag (memory project_one_click_install_hard_req)
    - JSON-driven cadence matrix (matches Plan 44-06 taxonomy.json pattern)
    - PATH-shim test seam via VIBEMIX_LAUNCH_SHIM_DIR (zero-network in CI)
    - GH Actions ::error:: annotation parity with cut_release.sh + check_gate.sh
key-files:
  created:
    - scripts/launch/launch_trigger.sh
    - scripts/dayzero/launch_copy/cadence_index.json
    - tests/launch/test_launch_trigger_orchestration.py
    - dist/launch-runs/.gitkeep
  modified:
    - .gitignore  # whitelist dist/launch-runs/ + .gitkeep
decisions:
  - "Cadence matrix data-driven via cadence_index.json (not in-bash tuples) so adding/removing per-stage variants requires no script edit."
  - "Sign-off footer regex pinned to literal 'Kaan signature:' + 'Francesco signature:' strings (matches check_no_ai_slop.py Gate 2 single source of truth — no second regex form)."
  - "--live triple-env precondition (LAUNCH_REAL=1 + GITHUB_TOKEN + DISCORD_WEBHOOK_URL); each missing → exit 2 with named blocker. No partial publishes."
  - "Test seam via VIBEMIX_LAUNCH_SHIM_DIR env (NOT PATH manipulation) — simpler than rewriting PATH inside bash, deterministic across CI."
  - "JSONL audit dir whitelisted in .gitignore (negation pattern); runtime .jsonl files stay ignored, only .gitkeep tracked."
metrics:
  duration: "~45min"
  completed: 2026-05-17
---

# Phase 45 Plan 02: launch_trigger.sh Orchestration + cadence_index.json Summary

## One-liner

Single discharge entry point (`scripts/launch/launch_trigger.sh`) that consumes a per-channel × per-stage JSON cadence matrix and dispatches to existing Phase 36 publish scripts; dry-run default, triple-env-gated --live, pre-publish slop + sign-off footer gates, append-only JSONL audit log for Plan 45-04 SHIP-V1-DECISION evidence.

## What shipped

| Surface                                                          | Purpose                                                                                                          |
| ---------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `scripts/launch/launch_trigger.sh`                               | The orchestrator — 313 lines bash. Reads cadence matrix, runs pre-publish gates, dispatches subordinates, appends JSONL audit. |
| `scripts/dayzero/launch_copy/cadence_index.json`                 | 5-channel × 4-stage matrix (twitter, instagram, linkedin, reddit, discord × T-30, T+0, T+5h, T+24h). `null` = no publish that pair. Versioned (version: 1). |
| `tests/launch/test_launch_trigger_orchestration.py`              | 22 tests pinning the contract: schema + CLI + dry-run/live + slop gate + sign-off footer + audit log + GH Actions annotation. |
| `dist/launch-runs/.gitkeep`                                      | Audit-log directory placeholder. Runtime `*.jsonl` stays ignored via the same .gitignore negation pattern.       |
| `.gitignore` (modified)                                          | Whitelist `dist/launch-runs/` and its `.gitkeep` while keeping runtime `*.jsonl` ignored.                        |

## Three atomic commits

1. **`1686c60` — `test(45-02): pin launch_trigger.sh CLI + cadence_index.json schema (RED)`** —
   cadence_index.json + 22-test file + bash stub (only --help). 17/22 tests RED (CLI parsing, cadence loop, env preconditions, sign-off footer, audit log, ::error:: annotation all unimplemented); 5/22 PASS by virtue of pure-data tests (schema, file references, executable bit, --help, syntax-clean).

2. **`d2e8c00` — `feat(45-02): launch_trigger.sh dry-run orchestration + cadence routing + JSONL audit log (GREEN)`** —
   Full CLI arg parser, --phase validation, slop gate via check_no_ai_slop.py with `set +e` capture pattern, cadence-row resolution via python3 heredoc reading cadence_index.json, dispatch loop routing discord → post_discord_launch.py and rest → publish_social_posts.py, JSONL audit row append per channel. `VIBEMIX_LAUNCH_SHIM_DIR` + `VIBEMIX_LAUNCH_RUN_DIR` test seams. 18/22 GREEN; 4 tests RED (Task 3 surface: triple-env, sign-off footer, ::error:: annotation).

3. **`e4e751b` — `feat(45-02): --live discharge contract + Plan 44-05 sign-off footer gate (GREEN)`** —
   --live triple-env check (LAUNCH_REAL=1 + GITHUB_TOKEN + DISCORD_WEBHOOK_URL, each → named exit-2 stderr blocker), sign-off footer gate (literal `Kaan signature:` + `Francesco signature:` markers per Plan 44-05 lock), `err()` emits `::error::<msg>` when GITHUB_ACTIONS=true. 22/22 GREEN.

## Verification (plan §verification block, all PASS)

```text
✓ bash -n scripts/launch/launch_trigger.sh                                       → exit 0
✓ bash scripts/launch/launch_trigger.sh --help                                    → exit 0 (references all 5 flags)
✓ bash scripts/launch/launch_trigger.sh --phase T+0                               → exit 0, 5 [plan] lines, 5 JSONL rows
✓ bash scripts/launch/launch_trigger.sh --phase T+5h                              → exit 0, 2 [plan] lines (twitter + discord)
✓ python3 -c '... cadence_index.json schema assert ...'                           → exit 0
✓ git ls-files --stage scripts/launch/launch_trigger.sh                           → 100755
✓ LAUNCH_REAL=1 bash scripts/launch/launch_trigger.sh --live --phase T+0          → exit 2 (missing GITHUB_TOKEN)
✓ uv run pytest tests/launch/test_launch_trigger_orchestration.py                 → 22/22 GREEN
```

## Decisions Made

### Cadence matrix as data, not bash tuple

`cadence_index.json` is the versioned source of truth. Adding a new cadence stage (e.g. T+72h Substack — currently §SHIP-13's territory) means appending one stage to `stages[]` and one column to each channel row. No bash edit. This matches the Phase 44-06 `discord_taxonomy.json` precedent and Plan 45-01's `install_vm_matrix.json` pattern.

### Sign-off footer gate uses literal strings, not a regex

The plan suggested `Kaan.*Francesco|Francesco.*Kaan` regex. Chose instead to reuse the exact literal markers `Kaan signature:` + `Francesco signature:` that `check_no_ai_slop.py` Gate 2 already enforces (single source of truth — no two competing definitions of "footer present"). Test 17 pins both per file in any order — matches the launch_copy/*.txt content as actually locked Plan 44-05.

### --live triple-env enforcement order

Order: `LAUNCH_REAL=1` → `GITHUB_TOKEN` → `DISCORD_WEBHOOK_URL`. Reasoning: LAUNCH_REAL is the convention shared with publish_social_posts.py + post_discord_launch.py (least surprise); GITHUB_TOKEN is needed by gh release transfer (next stage of the cascade); DISCORD_WEBHOOK_URL is the actual publish path. Stderr names each blocker individually so a missing-env operator gets one fix per re-run, not a chained discovery.

### Test seam via env var, not PATH

`VIBEMIX_LAUNCH_SHIM_DIR` is read inside the bash script to override subordinate paths. Cleaner than rewriting `PATH` inside bash (which would need to also override `python3` lookup) and is explicit at the call site. Production code path is unchanged when the env is unset.

### JSONL audit dir whitelisted via .gitignore negation

`dist/` is globally ignored (build artifact dir). Whitelisted `dist/launch-runs/` + `.gitkeep` so a fresh clone has the directory present, but the per-run `*.jsonl` files stay ignored. Matches the Phase 18 `scripts/dist/` / `tests/dist/` whitelist precedent.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocker] check_no_ai_slop.py has no shebang + isn't executable**
- **Found during:** Task 2 smoke test
- **Issue:** The plan implied `"${SLOP_CHECK}" --dir ... --quiet` would just work, but the production script has no shebang and is `-rw-r--r--`. Direct exec fails with `cannot execute binary file`.
- **Fix:** Branch on `-x`: if executable (test shim with shebang), exec directly; else `python3 ${SLOP_CHECK} ...`. Same pattern for `publish_social_posts.py` + `post_discord_launch.py`.
- **Files modified:** `scripts/launch/launch_trigger.sh` (Task 2 commit)
- **Commit:** d2e8c00

**2. [Rule 1 - Bug] `set -euo pipefail` aborts before non-zero exit can be captured**
- **Found during:** Task 2 test_13a debugging
- **Issue:** `set -e` causes the script to abort the moment the slop-check subprocess returns non-zero, before the explicit `[[ ${SLOP_EXIT} -ne 0 ]]` branch can fire. The script exits with the subprocess's exit code (1) instead of the named blocker exit code (2).
- **Fix:** Wrap the slop-check invocation in `set +e` / `set -e` so the exit is captured into `SLOP_EXIT` for explicit handling.
- **Files modified:** `scripts/launch/launch_trigger.sh` (Task 2 commit, before final RED→GREEN cycle)
- **Commit:** d2e8c00

**3. [Rule 3 - Blocker] `dist/` globally gitignored — .gitkeep wouldn't ship**
- **Found during:** Task 1 staging
- **Issue:** Adding `dist/launch-runs/.gitkeep` to git fails silently because `dist/` is ignored on line 9 of .gitignore. The Phase 45 plan asks for the dir to be present on a fresh clone (Plan 45-04 reads from it).
- **Fix:** Added .gitignore negation block (matches the Phase 18 `scripts/dist/` whitelist precedent): explicitly un-ignore `dist/launch-runs/` + `.gitkeep`, leave per-run `*.jsonl` ignored.
- **Files modified:** `.gitignore` (Task 1 RED commit)
- **Commit:** 1686c60

### Architectural / scope changes

None. Plan executed as written. No new social channels, no new providers, no scope creep (memory `feedback_no_scope_creep_clean_utility`).

## Authentication gates

None hit. All --live env checks tested with synthetic placeholder values (e.g. `gh_fake_test_token`) — the script never attempts a network call in test mode (subordinate shims record argv + exit 0).

## Known Stubs

None. The only "stub" is the post-Task-1 intermediate state which was replaced inline by Task 2 / Task 3 commits.

## Threat Flags

None — the plan's <threat_model> covers all 6 STRIDE entries (T-45-02-01..06) with explicit `mitigate` dispositions, all enforced by tests:

| Threat ID | Mitigation | Test |
| --------- | ---------- | ---- |
| T-45-02-01 (spoofing --live) | Triple-env check | test_12, test_15, test_16 |
| T-45-02-02 (cadence row swap) | Schema lock + plan tests | test_01, test_02, test_03 |
| T-45-02-03 (slop introduced post-44-05) | check_no_ai_slop pre-gate | test_13a, test_13b |
| T-45-02-04 (publish repudiation) | JSONL audit log | test_14, test_18 |
| T-45-02-05 (DoS by accidental loop) | Dry-run default + triple-env | test_07-10, test_12 |
| T-45-02-06 (env webhook URL secret) | accepted — Plan 45-06 §SHIP-08 runbook | — |

## Plan 45-04 hand-off (SHIP-V1-DECISION audit consumer)

JSONL audit log shape per row:

```jsonl
{"ts": "2026-05-17T07:55:01Z", "stage": "T+0", "channel": "twitter",   "mode": "dry-run", "copy_file": "twitter.txt",   "status": "ok"}
{"ts": "2026-05-17T07:55:01Z", "stage": "T+0", "channel": "instagram", "mode": "dry-run", "copy_file": "instagram.txt", "status": "ok"}
{"ts": "2026-05-17T07:55:01Z", "stage": "T+0", "channel": "linkedin",  "mode": "dry-run", "copy_file": "linkedin.txt",  "status": "ok"}
{"ts": "2026-05-17T07:55:01Z", "stage": "T+0", "channel": "reddit",    "mode": "dry-run", "copy_file": "reddit.txt",    "status": "ok"}
{"ts": "2026-05-17T07:55:01Z", "stage": "T+0", "channel": "discord",   "mode": "dry-run", "copy_file": "discord.txt",   "status": "ok"}
```

Plan 45-04 SHIP-V1-DECISION audit (`scripts/release/audit_ship_v1_decision.py`) glob-reads `dist/launch-runs/*.jsonl`, filters `mode == "live"` rows, counts per-stage publish coverage. A T+0 live launch produces 5 rows; T-30 produces 3; T+5h produces 2; T+24h produces 4. Total 14 rows for a clean cadence.

## Plan 45-06 hand-off (literal §SHIP-08 discharge command)

For the §SHIP-08 KAAN-ACTION-LEGAL runbook, the literal invocation is:

```bash
# Pre-discharge: ensure all 3 envs set in current shell (not .env — runbook §SHIP-08 specifies export)
export LAUNCH_REAL=1
export GITHUB_TOKEN=<gh_pat_with_repo_transfer_scope>
export DISCORD_WEBHOOK_URL=<vibemix-announcements-webhook-url>

# T-30 teaser (4 channels — no linkedin, no reddit, no discord skipped; discord teases announcement channel)
bash scripts/launch/launch_trigger.sh --live --phase T-30

# T+0 main publish (5 channels — full discharge)
bash scripts/launch/launch_trigger.sh --live --phase T+0

# T+5h follow-up (2 channels — twitter + discord)
bash scripts/launch/launch_trigger.sh --live --phase T+5h

# T+24h retrospective (4 channels — no reddit, avoid karma-farming pattern)
bash scripts/launch/launch_trigger.sh --live --phase T+24h

# Verification per stage: dist/launch-runs/<UTC>.jsonl rows mode == "live", status == "ok"
```

The triple-env check enforces the runbook order: forgetting any one of the three causes an immediate exit-2 with the named missing var — no partial publishes possible.

## TDD Gate Compliance

Plan-level TDD gate: full RED → GREEN-loop → GREEN-live cycle observed:

1. **RED commit (1686c60):** `test(45-02): pin launch_trigger.sh CLI + cadence_index.json schema (RED)` — 22 tests committed; 17 fail.
2. **GREEN commit Task 2 (d2e8c00):** `feat(45-02): launch_trigger.sh dry-run orchestration + cadence routing + JSONL audit log (GREEN)` — 18/22 pass.
3. **GREEN commit Task 3 (e4e751b):** `feat(45-02): --live discharge contract + Plan 44-05 sign-off footer gate (GREEN)` — 22/22 pass.

No REFACTOR commit needed — the Task-2 → Task-3 split is itself the structural separation.

## Self-Check: PASSED

- ✅ `scripts/launch/launch_trigger.sh` exists, executable, bash -n clean
- ✅ `scripts/dayzero/launch_copy/cadence_index.json` exists, valid JSON, canonical 5-channel × 4-stage matrix
- ✅ `tests/launch/test_launch_trigger_orchestration.py` exists, 22 tests pass
- ✅ `dist/launch-runs/.gitkeep` exists (whitelisted in .gitignore)
- ✅ Commit `1686c60` (RED) reachable from HEAD
- ✅ Commit `d2e8c00` (Task 2 GREEN) reachable from HEAD
- ✅ Commit `e4e751b` (Task 3 GREEN) reachable from HEAD
- ✅ All <success_criteria> items satisfied (1-7 from PLAN §success_criteria)
