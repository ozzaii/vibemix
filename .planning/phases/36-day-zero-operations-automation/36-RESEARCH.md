# Phase 36: Day-Zero Operations Automation — RESEARCH

**Generated:** 2026-05-15
**Mode:** `gsd-autonomous fully` (autonomous deliverables only — real-world execution is Kaan-action)

---

## 1. Existing v2.0 scaffold (carry-forward map)

`scripts/dayzero/` currently contains:

| File | Source | Phase 36 disposition |
|------|--------|----------------------|
| `__init__.py` | v2.0 P26 | leave |
| `healthz_check.sh` | v2.0 P26 | EXTEND — add `--webhook-url` Discord alert path (OPS-11 wants Discord alert on failure, not just stderr). Keep --dry-run schedule. |
| `proxy_load_test.py` | v2.0 P26 | EXTEND — add `--target=local-mock` as default + `.planning/eval-runs/` artifact write (OPS-10). p99<500ms + error<1% gates already there. |

Phase 36 adds:

| File | REQ | Status |
|------|-----|--------|
| `scripts/dayzero/discord_provision.py` | OPS-09 | NEW |
| `scripts/dayzero/launch_trigger.sh` | OPS-13 | NEW |
| `scripts/dayzero/seed_stars.md` | OPS-12 | NEW (markdown protocol — no executable) |
| `scripts/dayzero/healthz_cron.example` | OPS-11 | NEW |
| `docs/bravoh-ops-endpoint.md` | OPS-14 | NEW |
| Tests under `tests/dayzero/` | all | NEW directory |
| `.planning/KAAN-ACTION-LEGAL.md` entries | OPS-09..14 | APPEND |

---

## 2. Library / tool selection

### Discord auto-provision (OPS-09)

- **discord.py** (`pip install discord.py`) is the maintained Python Discord library; current stable line is 2.x. Provides `discord.Client`, `Guild.create_role`, `Guild.create_text_channel`, `Guild.create_category`.
- For Phase 36 *autonomous deliverable* we DO NOT add `discord.py` to `requirements.txt`. The script imports lazily with a `try/except ImportError` and a clear "install discord.py to run live" message — same pattern as `proxy_load_test.py` uses for `httpx`.
- **Token source:** `os.environ["DISCORD_BOT_TOKEN"]` only. Never written to disk. Test asserts the script aborts cleanly when env var missing in `--live` mode.
- **Idempotency:** plan-then-act. Fetch existing roles + channels; only create missing entries. Re-running the script must be a no-op when the server is already provisioned. Test injects a mock guild that already has `founder` role + `#announcements` channel; assertion: `create_role` / `create_text_channel` is NEVER called for those.
- **Dry-run mode:** prints planned operations as `[plan] create role founder` etc., never calls the SDK. This is the default in tests.

### Load test (OPS-10)

- `scripts/dayzero/proxy_load_test.py` already exists. Phase 36 work:
  - Add explicit `--target=local-mock` flag (mapped internally to `http://127.0.0.1:0/mock` — never hits the network; equivalent to current `--dry-run`).
  - Default target switches from `https://api.altidus.world/vibemix/healthz` to `local-mock` (autonomous safety — never DDOS prod from a CI run).
  - On completion, write the verdict JSON to `.planning/eval-runs/loadtest_<unix_ts>.json`. Test asserts artifact appears + JSON is well-formed.
  - Document the live-target invocation in `docs/release-process.md`-adjacent KAAN-ACTION-LEGAL entry.

### Healthz watchdog (OPS-11)

- `scripts/dayzero/healthz_check.sh` already polls a URL on an interval. Phase 36 work:
  - Discord webhook payload: `{"content": "vibemix healthz alert: target=… status=… iso=…"}` → POST JSON to `$DISCORD_WEBHOOK_URL`.
  - Webhook URL pulled from env (`DISCORD_WEBHOOK_URL`) — never committed.
  - On `--dry-run`, no real curl POST; instead log `[would-post] webhook=… body=…` to stdout. Test greps for that line.
  - Add `scripts/dayzero/healthz_cron.example`: 5-min cron entry + cron-environment notes (PATH, DISCORD_WEBHOOK_URL). Real install is Kaan-action.
- **`requests` vs `curl`:** stay with `curl` (already a dep, no install drift; bash-only keeps the script ssh-paste-able).

### Pre-seeded stars (OPS-12, P59)

- **No executable.** This is a sourcing protocol document.
- Pools: (1) Bravoh closed-beta users — invested in team; (2) Kaan + Francesco's DJ network — actual DJs who'll use it; (3) ARRAY OSS community — open-source builders; (4) contributor circle — Kaan's GitHub graph. Target: ≥15 aligned-community stars on Day 1.
- **Anti-pattern explicit ban:** the doc contains the phrase "NOT 15 random friend-favors" and a P59 callout. A test greps the file for the anti-pattern keyword (`random friend-favors` MUST appear inside a "Forbidden" / "Anti-pattern" / "NOT" context — guard sentence is the gate).
- **Day-1 log:** `seed_stars.log` is gitignored (contains personal handles + contact). Doc says where to store it locally.

### Launch trigger (OPS-13, P78)

- `scripts/dayzero/launch_trigger.sh` orchestrates T-30, T+0, T+5, T+24h. Single bash file with `case "$STAGE"` dispatch.
- **Stages:**
  - T-30: healthz spot-check via `healthz_check.sh --max-iterations 1`; Discord webhook announcement preview.
  - T+0: `gh release edit <tag> --draft=false` (publishes the draft); 4 social cross-posts via `cat` of pre-written copy under `scripts/dayzero/launch_copy/`.
  - T+5: healthz validate + `gh api /repos/:owner/:repo --jq .stargazers_count`; Discord celebration.
  - T+24h: 24-hour metrics report; Discord recap.
- **Dry-run default:** without `--publish`, every stage prints `[dry-run] would run: <command>` and exits 0. Real publish requires explicit `--publish` flag, AND the script aborts if `--publish` is passed without `GH_TOKEN` / `DISCORD_WEBHOOK_URL` env vars (auth-or-bust).
- **Test:** assert that invoking the script with no flags lists all 4 stages but executes none — every line starts with `[dry-run]`. Assert default mode never calls `gh release edit`.
- **Timing aid (P78):** the dry-run output includes a `# Recommended slot: 09:00 EST (HN front-page sweet spot)` comment line. Auto-scheduling cron is out of scope — Francesco runs the script manually at the target slot.

### Bravoh ops endpoint (OPS-14)

- **Server-side is Bravoh team's deliverable.** vibemix only documents the request shape.
- `docs/bravoh-ops-endpoint.md` covers:
  - `POST api.altidus.world/vibemix/updates/upload` — multipart upload of `vibemix.dmg` / `vibemix.exe` + ed25519 signature blob.
  - `GET api.altidus.world/vibemix/updates/latest.json` — Tauri-updater feed (already documented in `docs/updater.md`; cross-link).
  - Auth: bearer token (Bravoh-issued; rotation cadence).
  - PagerDuty alert hookup notes — webhook DSN on the Bravoh side; vibemix sends Discord webhook only.

---

## 3. Test discipline (per CONTEXT.md "Test discipline" block)

| Test | REQ | Gate |
|------|-----|------|
| `test_discord_provision_idempotent` | OPS-09 | Mock SDK; assert no `create_*` calls when entities exist |
| `test_discord_provision_token_env_required` | OPS-09 | Missing `DISCORD_BOT_TOKEN` in `--live` → exit 2 |
| `test_discord_provision_dry_run_default` | OPS-09 | No flags → dry-run, no SDK calls |
| `test_loadtest_defaults_to_local_mock` | OPS-10 | `args.target` defaults to `local-mock` (NEVER prod URL) |
| `test_loadtest_writes_artifact` | OPS-10 | After dry-run, `.planning/eval-runs/loadtest_*.json` exists + parses |
| `test_loadtest_pass_fail_logic` | OPS-10 | Synthetic samples → PASS/FAIL verdict matches expectation |
| `test_healthz_discord_webhook_on_failure` | OPS-11 | Dry-run schedule (every 3rd = 503) triggers `[would-post]` line |
| `test_healthz_cron_example_present` | OPS-11 | Example file exists + contains `*/5` cron syntax |
| `test_seed_stars_md_no_random_friend_antipattern` | OPS-12 | File grep: `random friend-favors` appears only inside a Forbidden/Anti-pattern context |
| `test_seed_stars_md_aligned_pools_listed` | OPS-12 | File mentions Bravoh / DJ network / ARRAY / contributor |
| `test_launch_trigger_default_dry_run` | OPS-13 | No `--publish` → every line `[dry-run]`; no `gh release edit` runs |
| `test_launch_trigger_publish_requires_auth` | OPS-13 | `--publish` without `GH_TOKEN` → exit 2 |
| `test_launch_trigger_all_stages_present` | OPS-13 | T-30 / T+0 / T+5 / T+24h all dispatch-handled |
| `test_bravoh_ops_endpoint_doc_present` | OPS-14 | `docs/bravoh-ops-endpoint.md` exists + mentions updates/upload + auth |

Total: 14 new tests. All mock external services. All default to dry-run.

---

## 4. Hard safety gates (autonomous-mode invariants)

1. **No real Discord API call** — discord.py import is lazy; tests always go through mock SDK; live mode only runs when `--live` flag + env var token both present.
2. **No prod load test from CI** — default `--target=local-mock`. Test asserts default value; CI runs of the loadtest hit local-mock only.
3. **No real launch trigger** — `--publish` not present → every action is `[dry-run]`. CI never sets `--publish`.
4. **No webhook URL in repo** — `DISCORD_WEBHOOK_URL` env-only. Gitleaks (Phase 34) already greps for Discord webhook hostname pattern.
5. **POC files untouched** — final commit-set assertion: `git diff <start>..<end> -- cohost*.py cohost*.bak run*.sh fillers/` is empty.

---

## 5. Out-of-scope re-confirm

- Multi-region — N/A.
- Slack — N/A.
- PagerDuty escalation policies — webhook only on vibemix side; Bravoh side owns PD.
- Analytics dashboards — v2.2.
- Auto-scheduling cron for launch — Francesco runs manually.

---

## 6. KAAN-ACTION-LEGAL entries (appended in Plan 36-06)

1. **OPS-09-RUN — Real Discord server provisioning**
   - Kaan creates Discord bot, copies token.
   - `export DISCORD_BOT_TOKEN=…; python scripts/dayzero/discord_provision.py --live`
   - Idempotent — safe to re-run.

2. **OPS-10-RUN — Live 100 RPS load test against api.altidus.world**
   - Bravoh team windowed maintenance slot.
   - `python scripts/dayzero/proxy_load_test.py --target https://api.altidus.world/vibemix/healthz --rps 100 --duration 300`
   - Artifact archived to `.planning/eval-runs/`.

3. **OPS-11-CRON — Install healthz_check.sh cron on Bravoh server**
   - Bravoh sysadmin installs `scripts/dayzero/healthz_cron.example` content.
   - `DISCORD_WEBHOOK_URL` env var configured server-side.

4. **OPS-12-OUTREACH — Pre-seed star outreach to aligned community**
   - Kaan + Francesco contact pools per `scripts/dayzero/seed_stars.md`.
   - Target ≥15 stars on Day 1. Log to `seed_stars.log` (gitignored).

5. **OPS-13-EXECUTE — Run launch_trigger.sh at HN/Reddit prime window**
   - `bash scripts/dayzero/launch_trigger.sh --publish` at 09:00 EST.
   - Verify dry-run preview first.

6. **OPS-14-SERVER — Bravoh deploys `vibemix/updates/upload` endpoint**
   - Bravoh team implements per `docs/bravoh-ops-endpoint.md` request shape.
   - PagerDuty escalation hooked on Bravoh side.

---

End of research.
