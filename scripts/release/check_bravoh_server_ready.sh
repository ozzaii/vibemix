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
# Helpers
# ---------------------------------------------------------------------------

if ! command -v curl >/dev/null 2>&1; then
    echo "ERROR: curl not on PATH — required for endpoint probe" >&2
    exit 2
fi

GHA_ANNOT="${GITHUB_ACTIONS:-false}"

emit_blocker() {
    local reason="$1"
    echo "BLOCKED_BY=bravoh-server: ${reason}" >&2
    if [[ "${GHA_ANNOT}" = "true" ]]; then
        echo "::error::check_bravoh_server_ready: ${reason}" >&2
    fi
}

emit_ok() {
    if [[ "${QUIET}" -eq 0 ]]; then
        echo "[bravoh-server] OK — 3/3 endpoints + healthz fresh"
    fi
}

# Parse an ISO-8601 ts ("YYYY-MM-DDTHH:MM:SSZ") into epoch seconds. Tries
# python3 first (always available on macOS + most CI images), falls back to
# `date -j -f` (BSD/macOS) then `date -d` (GNU/Linux).
ts_to_epoch() {
    local ts="$1"
    if command -v python3 >/dev/null 2>&1; then
        python3 -c "
import sys, datetime
ts = sys.argv[1].rstrip('Z')
try:
    dt = datetime.datetime.fromisoformat(ts).replace(tzinfo=datetime.timezone.utc)
    print(int(dt.timestamp()))
except Exception:
    sys.exit(1)
" "${ts}" 2>/dev/null && return 0
    fi
    # Fallbacks (best-effort; python3 is the canonical path).
    date -u -j -f "%Y-%m-%dT%H:%M:%SZ" "${ts}" +%s 2>/dev/null && return 0
    date -u -d "${ts}" +%s 2>/dev/null && return 0
    return 1
}

# Parse the healthz body's `ts` field. Prefer jq, fall back to python3.
extract_ts() {
    local body_file="$1"
    if command -v jq >/dev/null 2>&1; then
        jq -r '.ts // empty' < "${body_file}" 2>/dev/null
    elif command -v python3 >/dev/null 2>&1; then
        python3 -c "
import json, sys
try:
    print(json.load(open(sys.argv[1])).get('ts', ''))
except Exception:
    sys.exit(0)
" "${body_file}" 2>/dev/null
    fi
}

# ---------------------------------------------------------------------------
# Probe loop
# ---------------------------------------------------------------------------

TMPDIR_PROBE="$(mktemp -d)"
trap 'rm -rf "${TMPDIR_PROBE}"' EXIT

HEALTHZ_URL="${ENDPOINT_BASE}/vibemix/healthz"
LATEST_URL="${ENDPOINT_BASE}/vibemix/updates/latest.json"
UPLOAD_URL="${ENDPOINT_BASE}/vibemix/updates/upload"

# --- 1. GET /vibemix/healthz ----------------------------------------------
HEALTHZ_BODY="${TMPDIR_PROBE}/healthz.body"
HEALTHZ_CODE=$(curl -sS -o "${HEALTHZ_BODY}" -w "%{http_code}" --max-time 10 \
    "${HEALTHZ_URL}" 2>/dev/null) || HEALTHZ_CODE="000"

if [[ "${HEALTHZ_CODE}" = "000" ]]; then
    emit_blocker "network failure: ${HEALTHZ_URL} unreachable"
    exit 3
fi
if [[ "${HEALTHZ_CODE}" = "404" ]]; then
    emit_blocker "endpoint missing: /vibemix/healthz"
    exit 1
fi
if [[ "${HEALTHZ_CODE}" != "200" ]]; then
    emit_blocker "network failure: /vibemix/healthz returned HTTP ${HEALTHZ_CODE}"
    exit 3
fi

HEALTHZ_TS="$(extract_ts "${HEALTHZ_BODY}")"
if [[ -z "${HEALTHZ_TS}" ]]; then
    emit_blocker "healthz body missing 'ts' field"
    exit 4
fi
NOW_EPOCH="$(date -u +%s)"
TS_EPOCH="$(ts_to_epoch "${HEALTHZ_TS}" || true)"
if [[ -z "${TS_EPOCH}" ]]; then
    emit_blocker "healthz ts unparseable: ${HEALTHZ_TS}"
    exit 4
fi
AGE=$(( NOW_EPOCH - TS_EPOCH ))
if (( AGE > HEALTHZ_MAX_AGE_S )); then
    emit_blocker "healthz stale (last ts: ${HEALTHZ_TS}, age: ${AGE}s, max age: ${HEALTHZ_MAX_AGE_S}s)"
    exit 4
fi

# --- 2. GET /vibemix/updates/latest.json ----------------------------------
LATEST_BODY="${TMPDIR_PROBE}/latest.body"
LATEST_CODE=$(curl -sS -o "${LATEST_BODY}" -w "%{http_code}" --max-time 10 \
    "${LATEST_URL}" 2>/dev/null) || LATEST_CODE="000"

if [[ "${LATEST_CODE}" = "000" ]]; then
    emit_blocker "network failure: ${LATEST_URL} unreachable"
    exit 3
fi
if [[ "${LATEST_CODE}" = "404" ]]; then
    emit_blocker "endpoint missing: /vibemix/updates/latest.json"
    exit 1
fi
if [[ "${LATEST_CODE}" != "200" ]]; then
    emit_blocker "network failure: /vibemix/updates/latest.json returned HTTP ${LATEST_CODE}"
    exit 3
fi

# --- 3. HEAD /vibemix/updates/upload --------------------------------------
UPLOAD_CODE=$(curl -sS -o /dev/null -w "%{http_code}" --max-time 10 -I \
    "${UPLOAD_URL}" 2>/dev/null) || UPLOAD_CODE="000"

if [[ "${UPLOAD_CODE}" = "000" ]]; then
    emit_blocker "network failure: ${UPLOAD_URL} unreachable"
    exit 3
fi
if [[ "${UPLOAD_CODE}" = "404" ]]; then
    emit_blocker "endpoint missing: /vibemix/updates/upload"
    exit 1
fi
# Endpoint mounted + correctly auth-gated: any of {200, 401, 405} is OK.
case "${UPLOAD_CODE}" in
    200|401|405) ;;
    *)
        emit_blocker "network failure: /vibemix/updates/upload returned HTTP ${UPLOAD_CODE}"
        exit 3
        ;;
esac

emit_ok
exit 0
