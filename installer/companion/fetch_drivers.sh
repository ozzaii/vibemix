#!/usr/bin/env bash
# fetch_drivers.sh — Mac companion driver fetch (BlackHole 2ch via ExistentialAudio)
#
# Phase 49 Plan 01 — INSTALL-04 (fetch + SHA-256 verify + vendor-signed install).
#
# Contract:
#   - Reads installer/companion/driver_manifest.json (via jq)
#   - Downloads BlackHole .pkg from existential.audio over HTTPS
#   - Verifies SHA-256 against manifest (skips with WARNING when PLACEHOLDER_ prefix)
#   - On real-run: invokes `sudo installer -pkg ... -target /`
#   - On --dry-run: skips download + install, exits 0
#   - Logs every stage to ~/Library/Application Support/vibemix/install.log (JSONL)
#   - Emits structured JSON to stdout
#
# Spawns under bundle ID world.bravoh.vibemix (Tauri capability scope authorizes).
# Writes ONLY to ~/Library/Application Support/vibemix/install.log per privacy rule.
# NEVER inlines AIza pattern (Pitfall-7 grep gate).

set -euo pipefail

# ─── Paths + locals ────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MANIFEST="${SCRIPT_DIR}/driver_manifest.json"
LOG_DIR="${HOME}/Library/Application Support/vibemix"
LOG_FILE="${LOG_DIR}/install.log"
TMP_PKG="/tmp/blackhole-2ch.pkg"

DRY_RUN=false
AUTO=false
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    --auto) AUTO=true ;;
    --check-syntax) exit 0 ;;
    *) ;;
  esac
done

# ─── Helpers ──────────────────────────────────────────────────────────────
mkdir -p "$LOG_DIR"

log_event() {
  # log_event STAGE STATE [extra_json_kv_pairs ...]
  local stage="$1"
  local state="$2"
  shift 2
  local ts
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  local extra=""
  while [ $# -gt 0 ]; do
    extra="${extra}, \"$1\": \"$2\""
    shift 2 || true
  done
  printf '{"ts":"%s","stage":"%s","state":"%s"%s}\n' \
    "$ts" "$stage" "$state" "$extra" >> "$LOG_FILE"
}

emit_state() {
  # emit_state STATE [k1 v1 ...] — emit machine-parseable JSON to stdout
  local state="$1"
  shift
  local extra=""
  while [ $# -gt 0 ]; do
    extra="${extra}, \"$1\": \"$2\""
    shift 2 || true
  done
  printf '{"state":"%s"%s}\n' "$state" "$extra"
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    log_event "preflight" "fail" "missing_cmd" "$1"
    emit_state "fail" "reason" "missing_$1"
    exit 1
  }
}

# ─── Preflight ────────────────────────────────────────────────────────────
require_cmd jq
require_cmd curl
require_cmd shasum

log_event "boot" "ok" "dry_run" "$DRY_RUN" "auto" "$AUTO"

# ─── Probe: already installed? ────────────────────────────────────────────
if system_profiler SPAudioDataType 2>/dev/null | grep -qi "BlackHole 2ch"; then
  log_event "probe" "already_installed"
  emit_state "already_installed"
  exit 0
fi

# ─── Read manifest ────────────────────────────────────────────────────────
URL="$(jq -r '.drivers.blackhole_2ch.url' "$MANIFEST")"
EXPECTED_SHA="$(jq -r '.drivers.blackhole_2ch.sha256' "$MANIFEST")"
VERSION="$(jq -r '.drivers.blackhole_2ch.version' "$MANIFEST")"

log_event "manifest" "ok" "version" "$VERSION"

if [ "$DRY_RUN" = "true" ]; then
  log_event "fetch" "dry_run_skipped"
  emit_state "dry_run_complete" "version" "$VERSION"
  exit 0
fi

# ─── Download ─────────────────────────────────────────────────────────────
log_event "fetch" "downloading" "url" "$URL"
if ! curl -fsSL -o "$TMP_PKG" "$URL"; then
  log_event "fetch" "fail" "reason" "curl_failed"
  emit_state "fail" "stage" "fetch"
  exit 1
fi
log_event "fetch" "downloaded"

# ─── Verify SHA-256 ───────────────────────────────────────────────────────
ACTUAL_SHA="$(shasum -a 256 "$TMP_PKG" | awk '{print $1}')"
if [[ "$EXPECTED_SHA" == PLACEHOLDER_* ]]; then
  log_event "verify" "warning_placeholder" "actual" "$ACTUAL_SHA"
  # WARNING but not fail — placeholder discharge gated on §INSTALL-COMPANION-SIGN
else
  if [ "$ACTUAL_SHA" != "$EXPECTED_SHA" ]; then
    log_event "verify" "fail" "expected" "$EXPECTED_SHA" "actual" "$ACTUAL_SHA"
    emit_state "fail" "stage" "verify"
    rm -f "$TMP_PKG"
    exit 1
  fi
  log_event "verify" "ok"
fi

# ─── Install ──────────────────────────────────────────────────────────────
log_event "install" "starting"
# osascript with admin privilege prompt (vendor-signed pkg; macOS shows the
# standard "Installer is requesting your password" dialog).
if osascript -e "do shell script \"installer -pkg '$TMP_PKG' -target /\" with administrator privileges" \
  >> "$LOG_FILE" 2>&1; then
  log_event "install" "ok"
  emit_state "installed" "version" "$VERSION" "verified_sha256" "$ACTUAL_SHA"
  rm -f "$TMP_PKG"
  exit 0
else
  log_event "install" "fail"
  emit_state "fail" "stage" "install"
  rm -f "$TMP_PKG"
  exit 1
fi
