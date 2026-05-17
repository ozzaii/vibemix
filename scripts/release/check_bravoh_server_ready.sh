#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# scripts/release/check_bravoh_server_ready.sh — SHIP-06 / OPS-14 3-endpoint
# Bravoh server health probe. Cut-gate cousin of scripts/dayzero/healthz_check.sh
# (which is a monitoring watchdog; this is a release-blocking probe).
#
# Polls the 3 contractual endpoints used by the Tauri auto-updater + Bravoh
# backend, exits 0 iff ALL three are responsive AND healthz heartbeat is fresh.
# Plan 45-03 wires this as Gate 5b in scripts/launch/cut_release.sh.
#
# Endpoints (default base: https://api.altidus.world, override with
# --endpoint-base):
#   1. GET  /vibemix/healthz             — must be 200 + JSON {"status":"ok","ts":"<ISO-8601>"}; ts ≤ 10 min old.
#   2. GET  /vibemix/updates/latest.json — must be 200 + JSON {"version": "<semver>", ...}.
#   3. HEAD /vibemix/updates/upload      — must be in {200, 401, 405} (endpoint mounted + auth-gated correctly).
#
# Usage:
#   bash scripts/release/check_bravoh_server_ready.sh
#   bash scripts/release/check_bravoh_server_ready.sh --endpoint-base https://staging.api.altidus.world
#   bash scripts/release/check_bravoh_server_ready.sh --healthz-max-age-s 300
#   bash scripts/release/check_bravoh_server_ready.sh --quiet
#   bash scripts/release/check_bravoh_server_ready.sh --help
#
# Exit codes:
#   0  all 3 endpoints OK + healthz fresh
#   1  at least one endpoint missing (404)
#   2  CLI usage error (bad flag, missing curl)
#   3  network failure (DNS / TCP / TLS) on any endpoint
#   4  healthz reachable but stale (ts older than max-age, signals cron not running)
#
# Failure output is structured (machine-readable for GH Actions):
#   stderr `BLOCKED_BY=bravoh-server: <reason>`
#   when GITHUB_ACTIONS=true: also emit `::error::check_bravoh_server_ready: <reason>`

set -euo pipefail

ENDPOINT_BASE="https://api.altidus.world"
HEALTHZ_MAX_AGE_S=600
QUIET=0

usage() {
    cat <<'EOF'
Usage: check_bravoh_server_ready.sh [--endpoint-base URL] [--healthz-max-age-s SECONDS] [--quiet] [--help]

Polls the 3 contractual Bravoh server endpoints used by the vibemix Tauri
auto-updater + SHIP-06. Exits 0 iff all three are responsive AND the healthz
heartbeat is fresh. cut_release.sh Gate 5b invokes this before SHIP-CUT.

Options:
  --endpoint-base URL           Override the base URL (default: https://api.altidus.world)
  --healthz-max-age-s SECONDS   Max age for the healthz ts field in seconds (default: 600)
  --quiet                       Suppress OK output (exit code is the contract)
  -h, --help                    Print this message

Exit codes:
  0  all 3 endpoints OK + healthz fresh
  1  at least one endpoint missing (404)
  2  CLI usage error
  3  network failure
  4  healthz stale (ts older than --healthz-max-age-s)
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --endpoint-base)
            if [[ $# -lt 2 ]]; then
                echo "ERROR: --endpoint-base requires a value" >&2
                usage >&2
                exit 2
            fi
            ENDPOINT_BASE="$2"
            shift 2
            ;;
        --healthz-max-age-s)
            if [[ $# -lt 2 ]]; then
                echo "ERROR: --healthz-max-age-s requires a value" >&2
                usage >&2
                exit 2
            fi
            HEALTHZ_MAX_AGE_S="$2"
            shift 2
            ;;
        --quiet)
            QUIET=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "ERROR: unknown argument: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

# ---------------------------------------------------------------------------
# Placeholder probe — Task 2 (GREEN) implements the real loop.
# Returning exit 99 ensures every behaviour test fails RED.
# ---------------------------------------------------------------------------
echo "ERROR: probe not yet implemented (Task 2 GREEN pending)" >&2
exit 99
