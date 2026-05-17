#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# scripts/launch/check_bravoh_org_ready.sh — LAUNCH-06 polling gate.
#
# Polls https://api.github.com/orgs/<org> and exits 0 if the org exists,
# 1 if it does not (404), 2 on usage error, 3 on network failure.
#
# Plan 45 SHIP-TRANSFER consumes this as the pre-flight gate before
# `gh repo transfer ozai/dj-set-ai bravoh/vibemix` runs.
#
# Auth path:
#   1. Prefer `gh api orgs/<org>` if `gh` is on PATH and logged in
#      (zero-config: GH CLI inherits Kaan's session).
#   2. Fallback to `curl -fsS -o /dev/null -w '%{http_code}' \
#      https://api.github.com/orgs/<org>` (no token required for
#      public org existence checks — public-org 404 vs 200 distinction
#      is unauth-readable).
#
# Usage:
#   bash scripts/launch/check_bravoh_org_ready.sh                  # default org=bravoh
#   bash scripts/launch/check_bravoh_org_ready.sh --org github     # smoke-check vs well-known org
#   bash scripts/launch/check_bravoh_org_ready.sh --quiet          # suppress chatter
#   bash scripts/launch/check_bravoh_org_ready.sh --help           # print usage
#
# Exit codes:
#   0  org exists (HTTP 200 / gh exit 0)
#   1  org does not exist (HTTP 404 / gh exit non-zero for HTTP 404)
#   2  CLI usage error (unknown flag, missing arg)
#   3  network failure (curl / gh non-404 failure mode)

set -euo pipefail

ORG="bravoh"
QUIET=0

usage() {
    cat <<'EOF'
Usage: check_bravoh_org_ready.sh [--org NAME] [--quiet] [--help]

Polls https://api.github.com/orgs/<NAME> and exits 0 if the org exists,
1 if it does not. Plan 45 SHIP-TRANSFER consumes this as the org-ready
gate. Default org: bravoh (LAUNCH-06 target).

Options:
  --org NAME    GitHub org name to poll (default: bravoh)
  --quiet       Suppress OK / FAIL output (exit code is the contract)
  -h, --help    Print this message

Exit codes:
  0  org exists
  1  org does not exist (404)
  2  CLI usage error
  3  network failure
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --org)
            if [[ $# -lt 2 ]]; then
                echo "ERROR: --org requires a value" >&2
                usage >&2
                exit 2
            fi
            ORG="$2"
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

log_ok() {
    if [[ "$QUIET" -eq 0 ]]; then
        echo "OK: org '$ORG' exists on github.com"
    fi
}

log_fail() {
    if [[ "$QUIET" -eq 0 ]]; then
        echo "FAIL: org '$ORG' does not exist on github.com" >&2
    fi
}

log_neterr() {
    if [[ "$QUIET" -eq 0 ]]; then
        echo "ERROR: network failure polling github.com/orgs/$ORG: $1" >&2
    fi
}

# ---------------------------------------------------------------------
# Probe — gh first (authenticated, cleaner errors), curl fallback.
# ---------------------------------------------------------------------

if command -v gh >/dev/null 2>&1; then
    # `gh api orgs/<org>` returns non-zero on 404; we discriminate 404
    # from other failures by capturing stderr.
    gh_out=$(gh api "orgs/$ORG" 2>&1) && gh_rc=0 || gh_rc=$?
    if [[ $gh_rc -eq 0 ]]; then
        log_ok
        exit 0
    fi
    # gh reports HTTP 404 with "Not Found" in stderr — pin that match.
    if echo "$gh_out" | grep -qE 'HTTP 404|Not Found'; then
        log_fail
        exit 1
    fi
    # Anything else (auth missing, rate limit, transient) → fall
    # through to curl so we don't conflate network failure with
    # missing-org.
fi

# curl fallback — public-org existence check is unauth-readable.
if ! command -v curl >/dev/null 2>&1; then
    log_neterr "neither 'gh' nor 'curl' is on PATH"
    exit 3
fi

http_code=$(curl -fsS -o /dev/null -w "%{http_code}" \
    "https://api.github.com/orgs/$ORG" 2>&1) || curl_rc=$?

# When curl fails (`-f`) on a 404, it exits 22 and prints the code; we
# may or may not capture the code depending on shell semantics. Probe
# without `-f` for the discriminator.
http_code=$(curl -sS -o /dev/null -w "%{http_code}" \
    "https://api.github.com/orgs/$ORG" 2>/dev/null) || {
    log_neterr "curl invocation failed"
    exit 3
}

case "$http_code" in
    200)
        log_ok
        exit 0
        ;;
    404)
        log_fail
        exit 1
        ;;
    *)
        log_neterr "HTTP $http_code"
        exit 3
        ;;
esac
