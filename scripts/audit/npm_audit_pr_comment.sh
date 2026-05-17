#!/usr/bin/env bash
# Phase 46 / DEPS-03 — npm-audit PR-comment producer.
#
# Runs `npm audit --json --omit dev` from tauri/ui/, writes a fenced
# markdown block to stdout for the PR comment body. The companion
# workflow step posts this via actions/github-script.
#
# Hard-fail mode: if any HIGH or CRITICAL vulnerability is present,
# exit 1 so the workflow goes red. LOW/MODERATE are surfaced in the
# comment but do NOT fail the build (security-only auto-merge stays
# OFF per DEPS-10).
#
# DEPS-03 contract: this script runs `npm ci` first to prove the
# lockfile is in sync (frozen-install). Drift between package.json
# and package-lock.json fails before audit even starts.

set -euo pipefail

cd tauri/ui

# 1. Frozen-lockfile install (DEPS-03 hard requirement).
npm ci --no-audit --no-fund >/dev/null

# 2. Audit runtime deps only (devDeps don't ship in the binary).
AUDIT_JSON="$(npm audit --json --omit dev || true)"
# `npm audit` exits non-zero on findings; we capture + parse instead.

HIGH=$(echo "$AUDIT_JSON" | python -c 'import json,sys; d=json.load(sys.stdin); print(d.get("metadata",{}).get("vulnerabilities",{}).get("high",0))' 2>/dev/null || echo "0")
CRITICAL=$(echo "$AUDIT_JSON" | python -c 'import json,sys; d=json.load(sys.stdin); print(d.get("metadata",{}).get("vulnerabilities",{}).get("critical",0))' 2>/dev/null || echo "0")
TOTAL=$(echo "$AUDIT_JSON" | python -c 'import json,sys; d=json.load(sys.stdin); v=d.get("metadata",{}).get("vulnerabilities",{}); print(sum(v.values()))' 2>/dev/null || echo "0")

{
  echo "## npm audit (tauri/ui — runtime deps)"
  echo ""
  echo "**Total findings:** ${TOTAL} · **HIGH:** ${HIGH} · **CRITICAL:** ${CRITICAL}"
  echo ""
  echo '```json'
  echo "$AUDIT_JSON"
  echo '```'
} > /tmp/npm_audit_comment.md

cat /tmp/npm_audit_comment.md

if [ "$HIGH" -gt 0 ] || [ "$CRITICAL" -gt 0 ]; then
  echo "::error::npm-audit found HIGH or CRITICAL vulnerabilities (HIGH=$HIGH, CRITICAL=$CRITICAL) — block per DEPS-03" >&2
  exit 1
fi

exit 0
