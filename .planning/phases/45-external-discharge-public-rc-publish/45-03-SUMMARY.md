---
phase: 45-external-discharge-public-rc-publish
plan: 03
subsystem: release-gating
tags: [release, bravoh-server, healthz, ops-14, cut-release, ship-06, polling-gate]
requires: [SHIP-06]
provides:
  - "scripts/release/check_bravoh_server_ready.sh — 3-endpoint Bravoh server health probe with structured exit codes"
  - "cut_release.sh Gate 5b — release-blocking invocation of the probe before SHIP-CUT"
  - "tests/release/test_check_bravoh_server_ready.py — 12-test probe contract suite (mock http.server, zero network)"
  - "tests/repo/test_cut_release_invokes_bravoh_server.py — 6-test wire-in contract suite"
affects:
  - scripts/launch/cut_release.sh
  - .planning/REQUIREMENTS.md (SHIP-06 engineering side complete; Bravoh-team deploy side handed off to KAAN-ACTION-LEGAL §SHIP-06 / Plan 45-06)
tech-stack:
  added:
    - "http.server.ThreadingHTTPServer mock fixture for zero-network probe tests"
  patterns:
    - "Polling-gate (Phase 44-06 template): structured exit codes 0/1/2/3 + new 4 for stale-healthz"
    - "Structured BLOCKED_BY=<key>: ... stderr line (Phase 42-04 check_gate.sh convention)"
    - "GitHub Actions ::error:: annotation passthrough (Phase 36 monitoring pattern)"
    - "Gate Nb co-numbering (Phase 42-04 established): additive insertion preserves downstream gate numbers"
key-files:
  created:
    - scripts/release/check_bravoh_server_ready.sh
    - tests/release/test_check_bravoh_server_ready.py
    - tests/repo/test_cut_release_invokes_bravoh_server.py
  modified:
    - scripts/launch/cut_release.sh
decisions:
  - "Default endpoint base = https://api.altidus.world (per <probe_contract> in PLAN.md — the Bravoh proxy host, not bravoh.com directly). Override via --endpoint-base for staging."
  - "Healthz max-age default = 600s (per CONTEXT §SHIP-06 cron `*/5 * * * *` — leaves 2× margin)."
  - "Gate 5b co-numbering (not Gate 7 append): preserves Phase 39 + Phase 42 traceability and the established additive-gate-naming pattern."
  - "HEAD (-I) not POST for the upload endpoint probe: POST would need auth + a real artifact; HEAD verifies endpoint mount + auth-gating shape (200/401/405) without side effects."
  - "Tag regex left as `^v2\\.1\\.0-rc[0-9]+$` unchanged in this plan; Plan 45-06 (or a later v3 plan) owns the bump."
  - "jq is optional: python3 fallback handles healthz `ts` parsing when jq is absent (one-click-install friendly — no extra brew dep)."
metrics:
  tests_added: 18
  tests_regression_baseline_preserved: 7
  commits: 3
  files_created: 3
  files_modified: 1
---

# Phase 45 Plan 03: check_bravoh_server_ready.sh + Gate 5b — SHIP-06 Engineering

**One-liner:** Ship the engineering side of SHIP-06 — a 3-endpoint Bravoh-server health probe with structured exit codes (0/1/2/3/4) wired as `cut_release.sh` Gate 5b, so `gh release create` can never publish an RC against a missing or stale auto-updater backend.

## What landed

### `scripts/release/check_bravoh_server_ready.sh` (152 lines, +x)

Bash probe that polls 3 endpoints under `${ENDPOINT_BASE}` (default `https://api.altidus.world`):

| # | Method | Endpoint                         | Accepted codes      | Failure mode   |
|---|--------|----------------------------------|---------------------|----------------|
| 1 | GET    | `/vibemix/healthz`               | 200 + JSON `ts ≤ N` | exit 1/3/4     |
| 2 | GET    | `/vibemix/updates/latest.json`   | 200                 | exit 1/3       |
| 3 | HEAD   | `/vibemix/updates/upload`        | 200, 401, 405       | exit 1/3       |

Exit-code contract:
- `0` — all 3 endpoints OK + healthz fresh
- `1` — at least one endpoint missing (404)
- `2` — CLI usage error (bad flag, missing curl)
- `3` — network failure (DNS / TCP / TLS) on any endpoint
- `4` — healthz reachable but stale (`ts` older than `--healthz-max-age-s`, signals cron not heartbeating)

Flags: `--endpoint-base URL`, `--healthz-max-age-s SECONDS` (default 600), `--quiet`, `-h|--help`.

On any non-zero exit the probe emits a structured `BLOCKED_BY=bravoh-server: <reason>` line to stderr (machine-readable for `cut_release.sh` and GH Actions grep). Under `GITHUB_ACTIONS=true` it also emits `::error::check_bravoh_server_ready: <reason>` for CI annotations.

Threat-register mitigations encoded in source:
- **T-45-03-01 (Tampering — malicious JSON):** every `curl` writes to a tempfile; parsing is jq-or-python3 (never `eval`/`$(...)`), tempdir wiped on exit via `trap`.
- **T-45-03-02 (DoS — slow server):** every curl invocation pinned to `--max-time 10` (test 12 enforces this via source-grep).
- **T-45-03-05 (Repudiation — did Gate 5b run?):** banner echo precedes invocation; wire-in test 13 asserts presence.

### `scripts/launch/cut_release.sh` — Gate 5b insertion

Added between Gate 5 (POC files untouched) and Gate 6 (bundle ID locked):

```bash
# ── Gate 5b: Bravoh server ready (Plan 45-03 / SHIP-06 / OPS-14) ───────
echo "[Gate 5b] check_bravoh_server_ready.sh — 3-endpoint probe + healthz freshness (Plan 45-03)"
if bash "${REPO_ROOT}/scripts/release/check_bravoh_server_ready.sh" --quiet >/dev/null 2>&1; then
  pass "check_bravoh_server_ready.sh — 3/3 endpoints OK + healthz fresh"
else
  fail "check_bravoh_server_ready.sh — Bravoh server gate FAILED. Run 'bash ${REPO_ROOT}/scripts/release/check_bravoh_server_ready.sh' for the BLOCKED_BY line."
fi
```

Header comment block updated to list Gate 5b alongside the other 7 gates (doc/impl parity).

### Test suites — 18 new tests

- **`tests/release/test_check_bravoh_server_ready.py`** (12 tests, 4.0s)
  - Tests 1–3: CLI shape (executable, `set -euo pipefail`, `--help`, unknown flag exits 2).
  - Tests 4–9: probe behaviour against `http.server.ThreadingHTTPServer` mock on a random localhost port:
    - 200 across all 3 + fresh healthz → exit 0
    - 404 on `latest.json` → exit 1 + `BLOCKED_BY=...endpoint missing: /vibemix/updates/latest.json`
    - 200 healthz with 30-min-old `ts` → exit 4 + `BLOCKED_BY=...stale`
    - closed port → exit 3 + `BLOCKED_BY=...network failure`
    - `--healthz-max-age-s 60` strict mode flips a 5-min-old `ts` from fresh→stale (proves the flag works)
    - `GITHUB_ACTIONS=true` emits `::error::check_bravoh_server_ready: ...` alongside `BLOCKED_BY`
  - Tests 10–12: GREEN-specific contracts:
    - PATH-stubbed without jq → still works via python3 fallback
    - `--quiet` suppresses stdout (exit codes preserved)
    - `--max-time 10` source-pinned in every curl invocation (regex-based scan; ignores `command -v curl` + echo lines)

- **`tests/repo/test_cut_release_invokes_bravoh_server.py`** (6 tests, 0.02s)
  - `[Gate 5b]` banner + `check_bravoh_server_ready.sh` reference present
  - Gate ordering: Gate 5 < Gate 5b < Gate 6 (line-position assertion)
  - Bash invocation shape mirrors Gate 2b's `bash "${REPO_ROOT}/scripts/release/check_gate.sh"`
  - `fail()` message routes operator to the probe AND mentions `BLOCKED_BY`
  - Probe artifact exists + is executable
  - Tag regex `^v2\.1\.0-rc[0-9]+$` untouched (negative pin: no `v3\.0` regex sneaks in)

**Phase 42 baseline preserved:** `tests/repo/test_cut_release_invokes_check_gate.py` (7 tests) still 7/7 GREEN — Gate 5b is purely additive.

## 3 atomic commits

| Commit | Type | Summary | Tests |
|--------|------|---------|-------|
| `359dad3` | test | Pin probe CLI + 9 RED behaviour tests + mock http.server fixture | 3 pass / 9 fail (designed) |
| `78eddc2` | feat | 3-endpoint probe + healthz freshness + jq optional fallback (GREEN) | 12/12 |
| `09b4d2e` | feat | Wire Gate 5b into cut_release.sh + 6 wire-in tests | +6 wire-in, +7 Phase 42 baseline still green |

Total: **18 new tests + 7 baseline = 25/25 GREEN** in 4.10s.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test 12 curl-invocation regex over-matched**
- **Found during:** Task 2 GREEN run (test_12 failed despite source containing `--max-time 10` on every real curl call).
- **Issue:** Simple substring match `"curl "` also matched `if ! command -v curl >/dev/null` (existence check) and `echo "ERROR: curl not on PATH"` (diagnostic message).
- **Fix:** Tightened to regex `(^|[\s\(`=])curl\s+-[A-Za-z]` (curl followed by a flag) and added `command -v curl` + `echo` exclusion guards.
- **Files modified:** `tests/release/test_check_bravoh_server_ready.py`
- **Commit:** `78eddc2`

No architectural deviations. No auth gates. No CLAUDE.md conflicts.

## Hand-off to Plan 45-06 §SHIP-06 runbook

Plan 45-06 (KAAN-ACTION-LEGAL discharge runbooks) can cite this plan's engineering surface verbatim:

```bash
# Bravoh-team-discharge: deploy the 3 endpoints + cron heartbeat.
# Pre-flight verification before declaring SHIP-06 GREEN:
bash scripts/release/check_bravoh_server_ready.sh
# Override the base for staging-first sanity:
bash scripts/release/check_bravoh_server_ready.sh \
  --endpoint-base https://staging.api.altidus.world

# Inside cut_release.sh, Gate 5b automatically runs this probe before
# printing the gh release create command. There is no "skip" flag —
# SHIP-06 is gating SHIP-CUT by construction.

# Failure semantics:
#   exit 1 → tell Bravoh team: endpoint X not deployed
#   exit 3 → tell Bravoh team: network unreachable (DNS / cert / firewall)
#   exit 4 → tell Bravoh team: cron `*/5 * * * *` isn't running; healthz file stale
```

## Known Stubs

None. The probe is production-ready; the Bravoh-side endpoint deploy is the only remaining work (tracked as KAAN-ACTION-LEGAL §SHIP-06 / Plan 45-06).

## Threat Flags

None. The plan's `<threat_model>` covers the new surface (T-45-03-01..05), and the implementation honours every `mitigate` disposition. No new threat surfaces introduced.

## Self-Check: PASSED

- `scripts/release/check_bravoh_server_ready.sh` — FOUND, +x (100755)
- `tests/release/test_check_bravoh_server_ready.py` — FOUND
- `tests/repo/test_cut_release_invokes_bravoh_server.py` — FOUND
- `scripts/launch/cut_release.sh` — modified (Gate 5b block + header)
- Commit `359dad3` — FOUND in `git log`
- Commit `78eddc2` — FOUND in `git log`
- Commit `09b4d2e` — FOUND in `git log`
- 25/25 tests pass (12 probe + 6 wire-in + 7 Phase 42 baseline)
- Tag regex `^v2\.1\.0-rc[0-9]+$` preserved
- Gate 5b banner reachable in `cut_release.sh` execution
