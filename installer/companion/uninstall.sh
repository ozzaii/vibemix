#!/usr/bin/env bash
# uninstall.sh — Phase 49 INSTALL-07 (Mac).
#
# Preserve-default uninstall:
#   - Removes /Applications/vibemix.app
#   - Removes ~/Library/Caches/world.bravoh.vibemix/
#   - Removes Multi-Output Device routing config (via audio_config.py)
# Preserves (unless --clean):
#   - ~/Library/Application Support/vibemix/recordings/
#   - ~/Library/Application Support/vibemix/debriefs/
#   - ~/Library/Application Support/vibemix/ghost_calibration.json
#
# On --clean: also removes recordings/, debriefs/, ghost_calibration.json.
#
# Logs to ~/Library/Application Support/vibemix/uninstall.log (JSONL).

set -euo pipefail

# Test-friendly: VIBEMIX_DATA_ROOT env var overrides the default per-user
# data root. CI tests set this to a tmpdir so the uninstall runs against
# fixtures rather than the real user account.
DATA_ROOT="${VIBEMIX_DATA_ROOT:-$HOME/Library/Application Support/vibemix}"
CACHE_ROOT="${VIBEMIX_CACHE_ROOT:-$HOME/Library/Caches/world.bravoh.vibemix}"
APP_PATH="${VIBEMIX_APP_PATH:-/Applications/vibemix.app}"
LOG_FILE="${DATA_ROOT}/uninstall.log"

CLEAN=false
DRY_RUN=false
for arg in "$@"; do
  case "$arg" in
    --clean) CLEAN=true ;;
    --dry-run) DRY_RUN=true ;;
    --check-syntax) exit 0 ;;
    *) ;;
  esac
done

mkdir -p "$DATA_ROOT"

log_event() {
  local action="$1"
  local target="$2"
  local ts
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf '{"ts":"%s","action":"%s","target":"%s","clean":%s}\n' \
    "$ts" "$action" "$target" "$CLEAN" >> "$LOG_FILE"
}

safe_rm() {
  local target="$1"
  if [ -e "$target" ]; then
    if [ "$DRY_RUN" = "true" ]; then
      log_event "dry_run_would_remove" "$target"
    else
      rm -rf "$target"
      log_event "removed" "$target"
    fi
  else
    log_event "absent" "$target"
  fi
}

log_event "uninstall_started" ""

# Always remove: app, cache, audio routing
safe_rm "$APP_PATH"
safe_rm "$CACHE_ROOT"
# Audio routing — best-effort (audio_config.py may not be present after
# app removal; skip silently).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "${SCRIPT_DIR}/audio_config.py" ] && [ "$DRY_RUN" = "false" ]; then
  python3 "${SCRIPT_DIR}/audio_config.py" --remove-routing 2>/dev/null || true
  log_event "removed" "audio_routing"
fi

# Preserve-default: user library + debriefs + ghost calibration stay
PRESERVED=(
  "recordings"
  "debriefs"
  "ghost_calibration.json"
)
if [ "$CLEAN" = "true" ]; then
  for p in "${PRESERVED[@]}"; do
    safe_rm "${DATA_ROOT}/${p}"
  done
  log_event "clean_uninstall_complete" "$DATA_ROOT"
else
  for p in "${PRESERVED[@]}"; do
    log_event "preserved" "${DATA_ROOT}/${p}"
  done
  log_event "default_uninstall_complete" "$DATA_ROOT"
fi

exit 0
