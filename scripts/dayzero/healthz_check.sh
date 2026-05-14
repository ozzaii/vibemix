#!/usr/bin/env bash
# Day-Zero healthz watchdog for vibemix.
#
# Polls a healthz endpoint at a configurable interval and emits a structured
# ALERT line to stderr on any non-200 response. Foreground process by design —
# Kaan tails it in a terminal during the launch window.
#
# --dry-run injects a deterministic alert schedule (status 503 on every 3rd
# iteration, 200 otherwise) so the script can be tested without hitting a real
# endpoint.
#
# Usage:
#   bash scripts/dayzero/healthz_check.sh \
#       --target https://api.altidus.world/healthz \
#       --interval 30
#
#   # Bounded test sweep:
#   bash scripts/dayzero/healthz_check.sh --dry-run --interval 0 --max-iterations 6
#
# Output:
#   stdout: [OK]    iso=... target=... status=200 iteration=N
#   stderr: [ALERT] iso=... target=... status=N   iteration=N
#   stderr: [SUMMARY] iterations=N ok=N alerts=N   (on clean shutdown)

set -euo pipefail

TARGET="https://api.altidus.world/healthz"
INTERVAL=30
MAX_ITERATIONS=0  # 0 = infinite
DRY_RUN=0
ALERT_CMD=""

usage() {
  cat <<'EOF'
Day-Zero healthz watchdog. Polls a URL on an interval; alerts on non-200.

Usage:
  healthz_check.sh [OPTIONS]

Options:
  --target URL          Target healthz URL (default: https://api.altidus.world/healthz)
  --interval SECONDS    Poll interval in seconds (default: 30)
  --max-iterations N    Stop after N iterations (0 = infinite, default: 0)
  --dry-run             Synthesize a deterministic alert schedule (no HTTP)
  --alert-cmd CMD       Shell command to invoke on non-200 (optional)
  -h | --help           Show this help

Output:
  stdout: [OK]    iso=... target=... status=200 iteration=N
  stderr: [ALERT] iso=... target=... status=N   iteration=N
  stderr: [SUMMARY] on clean shutdown
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target)
      TARGET="$2"; shift 2 ;;
    --interval)
      INTERVAL="$2"; shift 2 ;;
    --max-iterations)
      MAX_ITERATIONS="$2"; shift 2 ;;
    --dry-run)
      DRY_RUN=1; shift ;;
    --alert-cmd)
      ALERT_CMD="$2"; shift 2 ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "Unknown arg: $1" >&2
      usage >&2
      exit 2 ;;
  esac
done

ITERATIONS=0
OK_COUNT=0
ALERT_COUNT=0

emit_summary() {
  echo "[SUMMARY] iterations=${ITERATIONS} ok=${OK_COUNT} alerts=${ALERT_COUNT}" >&2
}
trap 'emit_summary; exit 0' INT TERM

while :; do
  ITERATIONS=$((ITERATIONS + 1))
  ISO_TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

  if [[ $DRY_RUN -eq 1 ]]; then
    # Deterministic schedule: every 3rd iteration returns 503.
    if (( ITERATIONS % 3 == 0 )); then
      STATUS=503
    else
      STATUS=200
    fi
  else
    # Live curl. --max-time 10 caps stalled requests.
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$TARGET" || echo "000")
  fi

  if [[ "$STATUS" != "200" ]]; then
    echo "[ALERT] iso=${ISO_TS} target=${TARGET} status=${STATUS} iteration=${ITERATIONS}" >&2
    ALERT_COUNT=$((ALERT_COUNT + 1))
    if [[ -n "$ALERT_CMD" ]]; then
      # Run via sh -c so multi-word commands work; failures don't terminate the loop.
      sh -c "$ALERT_CMD" || true
    fi
  else
    echo "[OK] iso=${ISO_TS} target=${TARGET} status=200 iteration=${ITERATIONS}"
    OK_COUNT=$((OK_COUNT + 1))
  fi

  if [[ $MAX_ITERATIONS -gt 0 ]] && [[ $ITERATIONS -ge $MAX_ITERATIONS ]]; then
    emit_summary
    exit 0
  fi

  # Sleep — skip if interval is 0 (used by deterministic tests).
  if [[ "$INTERVAL" != "0" ]]; then
    sleep "$INTERVAL"
  fi
done
