#!/usr/bin/env bash
# firstrun_companion.sh — Phase 49 INSTALL-04 Mac first-launch hook.
#
# macOS DMGs cannot legally bundle BlackHole .pkg (ExistentialAudio license).
# We defer the companion fetch to the app's first launch instead. The Tauri
# main.rs setup() hook invokes this script ONCE (gated by sentinel file).
#
# Contract:
#   - Sentinel: ~/Library/Application Support/vibemix/firstlaunch.done
#   - If sentinel exists → exit 0 (no-op, already configured)
#   - Else → invoke installer/companion/fetch_drivers.sh --auto
#   - On success → touch sentinel + log + exit 0
#   - On failure → log + emit Tauri event wizard.firstrun_companion.failed +
#                  exit 1 (wizard step-driver-fetch.ts surfaces the fallback)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPANION_DIR="${SCRIPT_DIR}/../companion"
LOG_DIR="${HOME}/Library/Application Support/vibemix"
SENTINEL="${LOG_DIR}/firstlaunch.done"
LOG_FILE="${LOG_DIR}/install.log"

DRY_RUN=false
CHECK_SYNTAX=false
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    --check-syntax) CHECK_SYNTAX=true ;;
    *) ;;
  esac
done

if [ "$CHECK_SYNTAX" = "true" ]; then
  exit 0
fi

mkdir -p "$LOG_DIR"

log_event() {
  local stage="$1"
  local state="$2"
  local ts
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf '{"ts":"%s","stage":"%s","state":"%s","source":"firstrun_companion"}\n' \
    "$ts" "$stage" "$state" >> "$LOG_FILE"
}

# Sentinel check — only run once per user account.
if [ -f "$SENTINEL" ]; then
  log_event "firstrun" "sentinel_present"
  exit 0
fi

log_event "firstrun" "starting"

if [ ! -f "${COMPANION_DIR}/fetch_drivers.sh" ]; then
  log_event "firstrun" "missing_companion_script"
  echo "MISSING: fetch_drivers.sh at ${COMPANION_DIR}" >&2
  exit 1
fi

if [ "$DRY_RUN" = "true" ]; then
  log_event "firstrun" "dry_run"
  touch "$SENTINEL"
  exit 0
fi

# Invoke the companion fetch. Capture stdout (machine-parseable JSON) +
# exit code.
FETCH_OUTPUT=$(bash "${COMPANION_DIR}/fetch_drivers.sh" --auto 2>&1) || {
  log_event "firstrun" "fetch_failed"
  echo "$FETCH_OUTPUT" >&2
  # Surface to wizard via Tauri event (if running under tauri-bridge).
  # Falls back to a stderr line that the parent picks up.
  echo "::wizard.firstrun_companion.failed:: $FETCH_OUTPUT" >&2
  exit 1
}

log_event "firstrun" "ok"
touch "$SENTINEL"
exit 0
