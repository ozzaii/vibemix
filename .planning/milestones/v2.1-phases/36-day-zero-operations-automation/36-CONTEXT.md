# Phase 36: Day-Zero Operations Automation - Context

**Gathered:** 2026-05-15
**Status:** Ready for planning
**Mode:** Auto-generated (gsd-autonomous fully)

<domain>
## Phase Boundary

Public launch day operates from version-controlled scripts — Discord up, healthz live, proxy load-tested at real RPS, star coordination ready, launch trigger sequence one command away.

**Mapped REQ-IDs (6):** OPS-09 (Discord auto-provision), OPS-10 (100 RPS × 5min proxy load test), OPS-11 (Healthz watchdog cron), OPS-12 (15+ aligned-community pre-seeded stars), OPS-13 (launch_trigger.sh T-30/T+0/T+5/T+24h with --dry-run), OPS-14 (Bravoh ops endpoint + healthz PagerDuty).

**In scope (autonomous):**
- `scripts/dayzero/discord_provision.py` — Discord server scaffolder with roles + channels (idempotent; takes bot token from env).
- `scripts/dayzero/healthz_check.sh` + cron + Discord webhook alert (the script + cron config, NOT the live cron run on a server — that's Kaan-action).
- `scripts/dayzero/loadtest.py` — 100 RPS × 5min asyncio-aiohttp load test against `api.altidus.world/vibemix`, p99 < 500ms gate, artifact in `.planning/eval-runs/`.
- `scripts/dayzero/launch_trigger.sh` — T-30 / T+0 / T+5 / T+24h sequence with `--dry-run` preview gate.
- `scripts/dayzero/seed_stars.md` — aligned-community sourcing protocol (Bravoh team / DJ network / ARRAY / contributors) — NO "15 random friends" anti-pattern.
- Bravoh ops endpoint: `api.altidus.world/vibemix/updates/upload` request shape doc (server-side Bravoh deployment is Bravoh team's job, not vibemix).

**Out of scope (autonomous; deferred to KAAN-ACTION-LEGAL):**
- ACTUAL Discord server creation execution (Kaan-action — needs Discord bot token + admin).
- ACTUAL load-test run against live api.altidus.world (Bravoh team coordination — could DDOS prod).
- ACTUAL cron deployment on Bravoh server (Kaan/Bravoh sysadmin action).
- ACTUAL pre-seeded star coordination outreach (Kaan-action — human outreach).
- ACTUAL launch trigger execution (Kaan-action — manual launch day).

**Pure out of scope:**
- Multi-region deployment.
- Slack integration (Discord only).
- PagerDuty escalation policies (only webhook alert).
- Analytics dashboards.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion (locked per gsd-autonomous fully)

Grounded in:
- ROADMAP Phase 36 verbatim
- REQUIREMENTS.md OPS-09..14
- Pitfalls P59 (15-friend star-unstar → aligned-community sourcing), P78 (launch timing drift → dry-run gate)
- v2.0 Phase 21 CI + Phase 26 day-zero scaffold (shipped)
- Bravoh proxy infrastructure (Bravoh team)
- Memory `project_one_click_install_hard_req` — frictionless install drives star conversion
- Memory `project_github_star_goal` — 500+ min, 1000+ realistic

### Discord auto-provision (OPS-09)
- `scripts/dayzero/discord_provision.py`: uses `discord.py` library + bot token env var.
- Creates server `vibemix` with roles: `founder`, `contributor`, `DJ`, `lurker`.
- Creates channels: `#announcements`, `#help`, `#show-and-tell`, `#controllers`, `#ai-misbehavior`, `#dev`.
- Idempotent: skips role/channel if already exists.
- Dry-run mode prints the would-do plan without touching Discord.
- Test: mock Discord SDK, assert idempotency + role/channel structure.

### Load test (OPS-10)
- `scripts/dayzero/loadtest.py`: aiohttp + asyncio.
- 100 concurrent workers × 5 minutes (~30k requests) against `api.altidus.world/vibemix`.
- Measures p50/p95/p99 latency + error rate.
- Pass: p99 < 500ms, error rate < 1%.
- Artifact written to `.planning/eval-runs/loadtest_<timestamp>.json`.
- `--target=staging` / `--target=prod` / `--target=local-mock` flags. Default = local-mock (autonomous safety).
- Test: synthetic mock target, assert artifact written, assert pass/fail logic.

### Healthz watchdog (OPS-11)
- `scripts/dayzero/healthz_check.sh`: shell script that curl-checks `api.altidus.world/healthz` → 200 OK.
- On failure, posts to Discord webhook URL from env.
- Cron config example provided in `scripts/dayzero/healthz_cron.example` (5min interval). Actual cron install is Kaan-action.
- Test: mock curl, assert webhook called on 5xx.

### Pre-seeded stars (OPS-12 / P59)
- `scripts/dayzero/seed_stars.md`: aligned-community sourcing protocol.
- Pools: Bravoh team (8) + Kaan's DJ network (5+) + ARRAY OSS community (∞) + contributor circle.
- ANTI-PATTERN: "15 random friend-favors" — explicitly forbidden in protocol.
- Day-1 star list logged in `seed_stars.log` (gitignored — personal contact info).

### Launch trigger (OPS-13 / P78)
- `scripts/dayzero/launch_trigger.sh`: orchestrates T-30, T+0, T+5, T+24h sequence.
- T-30 (30min before): healthz spot-check + Discord "T-30 announce" preview.
- T+0: GitHub Release publish trigger (gh CLI) + Discord announcement + 4-channel social cross-post (Twitter, IG, LinkedIn, Reddit).
- T+5 (5min after): healthz validate + GitHub stars current count + Discord celebration.
- T+24h: 24h metrics report + Discord recap.
- `--dry-run` shows exact commands without executing.
- Test: dry-run mode, assert no real API calls.

### Bravoh ops endpoint (OPS-14)
- Request shape: `POST api.altidus.world/vibemix/updates/upload` — auto-updater file upload.
- Documented in `docs/bravoh-ops-endpoint.md`. Bravoh team owns server-side implementation.

### Frontend convention
- N/A — Phase 36 is server-side / scripts only.

### Test discipline
- Mock all external services (Discord SDK, HTTP, gh CLI).
- Dry-run mode is the default in tests.
- Test: P59 anti-pattern detection — assert seed_stars.md mentions "aligned-community" + forbids "random friend-favors".
- Test: P78 dry-run gate — launch_trigger.sh without `--dry-run` fails in test env.

</decisions>

<code_context>
## Existing Code Insights

- **v2.0 Phase 21 (shipped)** — CI scaffold.
- **v2.0 Phase 26 (shipped)** — day-zero scaffold base. `scripts/dayzero/` directory may exist with scaffolding.
- **Phase 34 (just shipped)** — SECURITY.md outbound list includes `api.altidus.world` endpoints.
- **Bravoh proxy** — `api.altidus.world` (BRAVOH server per user CLAUDE.md).
- **`.planning/eval-runs/`** — artifact storage from Phase 27.

Codebase maps under `.planning/codebase/` feed plan-phase research.

</code_context>

<specifics>
## Specific Ideas

- **No random-friend stars (P59)** — aligned communities only. Star unstar within a week is the failure pattern.
- **Dry-run is default in tests** (P78) — prevents accidental real launch from CI.
- **Loadtest defaults to local-mock** — never accidentally DDOS prod from autonomous runs.
- **Discord webhook URL is env-only** — never committed.
- **Bravoh server-side endpoint** — vibemix only provides the client + request shape doc.

</specifics>

<deferred>
## Deferred Ideas

- **Multi-region Discord servers** — out of scope.
- **Slack integration** — out of scope.
- **PagerDuty escalation policies** — webhook only.
- **Analytics dashboard** — v2.2.
- **A/B testing launch timing** — v2.2.
- **Twitter Spaces / IG Live launch event** — Kaan-action if desired.

</deferred>

<kaan_action_required>
## Critical: Kaan-Action Required (KAAN-ACTION-LEGAL.md)

Phase 36 cannot fully ship without Kaan-action items:
1. **OPS-09 actual run:** Kaan generates Discord bot token, runs `discord_provision.py` against real Discord.
2. **OPS-10 actual run:** Bravoh team coordination for 100 RPS load test on prod (could DDOS).
3. **OPS-11 cron install:** Bravoh sysadmin installs healthz_check cron on server.
4. **OPS-12 outreach:** Kaan does aligned-community outreach manually (no automation).
5. **OPS-13 launch execution:** Kaan runs launch_trigger.sh on actual launch day (autonomous = scripts ready, NOT triggered).
6. **OPS-14 server-side:** Bravoh team deploys `vibemix/updates/upload` endpoint.

Autonomous deliverables: all scripts + tests + docs + protocols ready. Real-world execution is Kaan-action.
</kaan_action_required>
