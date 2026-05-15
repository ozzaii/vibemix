# Phase 36: Day-Zero Operations Automation — PLAN

**Mode:** `gsd-autonomous fully`
**Plans:** 6 (1 per REQ-ID).
**Discipline:** Atomic commits, mock all external services, dry-run defaults, KAAN-ACTION-LEGAL captures real-world execution.

---

## Plan 36-01 — Discord auto-provision (OPS-09)

**Files:**
- `scripts/dayzero/discord_provision.py` (new) — idempotent server scaffolder.
- `tests/dayzero/__init__.py` (new — empty).
- `tests/dayzero/test_discord_provision.py` (new).

**Behavior:**
- Loads `DISCORD_BOT_TOKEN` from env. Aborts with exit 2 in `--live` if absent.
- Lazy-imports `discord.py`. Without it, `--live` mode exits 2 with install hint; dry-run mode still works (no SDK needed).
- Defines target state:
  - Server name: `vibemix`
  - Roles: `founder`, `contributor`, `DJ`, `lurker`
  - Channels: `#announcements`, `#help`, `#show-and-tell`, `#controllers`, `#ai-misbehavior`, `#dev`
- Inspect-then-create: only creates missing entries.
- Default mode = `--dry-run`. Prints `[plan] create role founder`, `[plan] create channel #help`, etc.

**Gates:**
- `test_discord_provision_dry_run_default` — no args → dry-run path, no SDK module imported in test process.
- `test_discord_provision_idempotent` — mock guild with existing `founder` + `#announcements`; assert `create_role(name='founder')` NEVER called, only missing entries created.
- `test_discord_provision_token_env_required` — `--live` without `DISCORD_BOT_TOKEN` → exit 2.

---

## Plan 36-02 — Load test target gates (OPS-10)

**Files:**
- `scripts/dayzero/proxy_load_test.py` (extend) — add `--target=local-mock` flag, default to it, write artifact.
- `tests/dayzero/test_proxy_load_test.py` (new).

**Behavior changes:**
- `--target` accepts `local-mock` literal → resolves to `http://127.0.0.1:0/mock`; the load runner short-circuits to synthesize_samples() (same as `--dry-run` path).
- Default `--target` value flips from prod URL to `local-mock` (autonomous safety).
- After verdict computed: write `dataclasses.asdict(verdict)` to `.planning/eval-runs/loadtest_<unix_ts>.json` (best-effort: skip if `.planning/eval-runs/` absent — log to stderr).
- `--target=https://api.altidus.world/...` still works for the Kaan-action live run.

**Gates:**
- `test_loadtest_defaults_to_local_mock` — `argparse` default for `--target` MUST equal `local-mock`. Hard regression gate.
- `test_loadtest_writes_artifact` — after dry-run, `loadtest_*.json` lands under tmp eval-runs dir + parses with all Verdict fields.
- `test_loadtest_pass_fail_logic` — synthetic samples (existing code) hit PASS verdict with default budgets.

---

## Plan 36-03 — Healthz Discord webhook + cron example (OPS-11)

**Files:**
- `scripts/dayzero/healthz_check.sh` (extend) — add `--webhook-url` flag (or `DISCORD_WEBHOOK_URL` env var) that posts on non-200.
- `scripts/dayzero/healthz_cron.example` (new) — `*/5 * * * *` line + env-var notes.
- `tests/dayzero/test_healthz_check.py` (new).

**Behavior:**
- On non-200, if webhook configured: in dry-run, log `[would-post] webhook=… body=…`; in live, `curl -X POST -H 'Content-Type: application/json' -d "$BODY" "$DISCORD_WEBHOOK_URL"`.
- Webhook body: JSON `{"content": "vibemix healthz alert: target=… status=… iso=…"}`.
- Cron example documents 5-min interval + required env vars + safe PATH for cron environment.

**Gates:**
- `test_healthz_discord_webhook_on_failure` — run `bash healthz_check.sh --dry-run --max-iterations 3 --interval 0 --webhook-url https://discord/test` and grep stdout/stderr for `[would-post]` on iteration 3 (the synthetic 503).
- `test_healthz_cron_example_present` — file exists, contains `*/5`, mentions `DISCORD_WEBHOOK_URL`.

---

## Plan 36-04 — Seed stars protocol (OPS-12 / P59)

**Files:**
- `scripts/dayzero/seed_stars.md` (new).
- `.gitignore` (extend) — add `scripts/dayzero/seed_stars.log` entry.
- `tests/dayzero/test_seed_stars_protocol.py` (new).

**Document content:**
- Mission: ≥15 aligned-community stars by Day-1.
- Pools (4): Bravoh team, Kaan+Francesco DJ network, ARRAY OSS community, contributor circle.
- Explicit "Forbidden" section listing the P59 anti-pattern: `NOT 15 random friend-favors. Asking strangers for marketing stars triggers unstars within a week …`.
- Day-1 log location: `scripts/dayzero/seed_stars.log` (gitignored).

**Gates:**
- `test_seed_stars_md_no_random_friend_antipattern` — `random friend-favors` substring exists ONLY inside a "Forbidden" / "Anti-pattern" / "NOT" line; positive-mention assertion fails the test.
- `test_seed_stars_md_aligned_pools_listed` — file mentions `Bravoh`, `DJ network`, `ARRAY`, `contributor`.
- `test_seed_stars_log_is_gitignored` — `.gitignore` includes `scripts/dayzero/seed_stars.log`.

---

## Plan 36-05 — Launch trigger sequence (OPS-13 / P78)

**Files:**
- `scripts/dayzero/launch_trigger.sh` (new) — T-30/T+0/T+5/T+24h dispatcher.
- `scripts/dayzero/launch_copy/` (new dir, 4 placeholder files) — `twitter.txt`, `instagram.txt`, `linkedin.txt`, `reddit.txt`.
- `tests/dayzero/test_launch_trigger.py` (new).

**Behavior:**
- Stages selected via `--stage t-30 | t+0 | t+5 | t+24h | all`. Default `--stage all`.
- `--publish` flag required to actually run any external command. Without it, every action prints `[dry-run] would run: <cmd>`.
- `--publish` mode aborts with exit 2 if `GH_TOKEN` or `DISCORD_WEBHOOK_URL` missing.
- T-30: spot-check healthz (1 iteration); preview Discord announcement.
- T+0: `gh release edit "$RELEASE_TAG" --draft=false`; Discord announce; cross-post copy file paths.
- T+5: healthz validate; `gh api /repos/$REPO --jq .stargazers_count`; Discord celebration.
- T+24h: stargazer + traffic snapshot; Discord recap.
- Header comment includes `# Recommended slot: 09:00 EST (HN front-page sweet spot) — P78` per timing pitfall.

**Gates:**
- `test_launch_trigger_default_dry_run` — invoke with no flags; every meaningful output line begins with `[dry-run]`; `gh release edit` never invoked (assert via PATH-shim shell test).
- `test_launch_trigger_publish_requires_auth` — `bash launch_trigger.sh --stage t+0 --publish` with `GH_TOKEN` unset → exit 2.
- `test_launch_trigger_all_stages_present` — script contains `t-30)`, `t+0)`, `t+5)`, `t+24h)` case branches.
- `test_launch_trigger_recommends_p78_window` — header mentions `09:00 EST` (P78 timing).

---

## Plan 36-06 — Bravoh ops endpoint doc + KAAN-ACTION-LEGAL entries (OPS-14)

**Files:**
- `docs/bravoh-ops-endpoint.md` (new).
- `.planning/KAAN-ACTION-LEGAL.md` (append section "Phase 36 Day-Zero Ops").
- `tests/dayzero/test_bravoh_ops_endpoint_doc.py` (new).

**Doc content:**
- `POST api.altidus.world/vibemix/updates/upload` — multipart form fields: `binary`, `signature`, `version`, `channel`. Auth: `Authorization: Bearer <bravoh-token>`. Response: `{"status":"ok","sha256":"…"}`.
- `GET api.altidus.world/vibemix/updates/latest.json` — Tauri updater feed; cross-link to `docs/updater.md`.
- PagerDuty: Bravoh-side webhook hookup; vibemix sends Discord webhook only.
- Rate limits + retry guidance.

**KAAN-ACTION-LEGAL entries:** OPS-09-RUN, OPS-10-RUN, OPS-11-CRON, OPS-12-OUTREACH, OPS-13-EXECUTE, OPS-14-SERVER (per 36-RESEARCH §6).

**Gates:**
- `test_bravoh_ops_endpoint_doc_present` — file exists, mentions `updates/upload`, `Bearer`, `updates/latest.json`.
- `test_kaan_action_legal_has_phase_36_entries` — file contains anchor for `OPS-09-RUN` through `OPS-14-SERVER`.

---

## Cross-plan invariants

- All Python tests use `pytest` (existing project convention).
- All shell tests use subprocess invocation of the bash script with `--dry-run` flags.
- No real network: every test mocks Discord SDK / curl / gh CLI.
- POC files (`cohost*.py`, `cohost*.bak`, `run*.sh`, `fillers/`) NOT touched.
- Each plan ships in its own commit per `gsd-autonomous fully` atomic-commit discipline.

## Phase exit criteria

1. All 14 tests under `tests/dayzero/` green.
2. `git diff phase36-start..HEAD -- cohost*.py cohost*.bak fillers/` empty.
3. `.planning/KAAN-ACTION-LEGAL.md` has Phase 36 section with 6 entries.
4. `36-SUMMARY.md` written.
