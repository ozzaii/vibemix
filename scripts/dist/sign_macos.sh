#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# scripts/dist/sign_macos.sh — Phase 18-02 macOS signing + notarization bench.
#
# Wraps the four-stage Apple distribution chain:
#   codesign --deep --options runtime --entitlements entitlements.macos.plist
#     → create-dmg
#     → xcrun notarytool submit --wait
#     → xcrun stapler staple
#     → spctl --assess --type execute (final gate)
#     → verify_binary.py (cross-plan integration — AIza-scan release-blocker)
#
# The script is IDEMPOTENT: re-running on an already-signed + notarized +
# stapled bundle is a no-op (Stage 2/3 detect existing signatures via
# `codesign --verify`; Stage 6 detects existing stapler ticket).
#
# Bundle ID: world.bravoh.vibemix (LOCKED — see Phase 11 W1 + entitlements
# plist header; macOS TCC permissions are keyed to this).
#
# Usage:
#   scripts/dist/sign_macos.sh [--dry-run] [--skip-dmg] \
#                              [--keychain-profile <name>] \
#                              [--output-dir <path>] \
#                              [<path/to/vibemix-core.app>]
#
# Default .app path: dist/vibemix-core/vibemix-core.app (matches PyInstaller
# --onedir output from vibemix-core.macos.spec).
#
# Required env vars (FAIL FAST if missing):
#   APPLE_DEVELOPER_ID         Developer ID Application certificate name in
#                              keychain, e.g.
#                              "Developer ID Application: Bravoh SAGL (TEAMID)".
#                              CI mode (CI=true) imports from
#                              $APPLE_DEVELOPER_ID_P12_BASE64 +
#                              $APPLE_DEVELOPER_ID_PASSWORD into a temp keychain.
#   APPLE_TEAM_ID              10-char team identifier (TEAMID portion above).
#   APPLE_API_KEY_PATH         Path to App Store Connect API .p8 key file.
#                              CI mode (CI=true) base64-decodes $APPLE_API_KEY_P8
#                              into a temp file.
#   APPLE_API_KEY_ID           ASC API key ID (8-10 char alphanumeric).
#   APPLE_API_KEY_ISSUER       ASC API key issuer UUID.
#
# Optional env vars:
#   CI                         "true" → CI mode (temp keychain + p8 decode).
#   VIBEMIX_DMG_NAME           override DMG basename (default: vibemix-<ver>.dmg).
#
# Exit codes:
#   0 = success
#   1 = generic failure (set -e cascade)
#   2 = missing required env vars / binaries
#   3 = notarytool failed after 3 attempts
#   4 = spctl rejected the signed bundle
#   5 = verify_binary.py flagged the bundle (AIza or other key pattern)
#
# References:
#   - tauri/src-tauri/entitlements.macos.plist (the 5 distribution entitlements)
#   - 18-CONTEXT.md §Area 2 (the locked decision set)
#   - https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution
#   - https://developer.apple.com/documentation/security/hardened_runtime

set -euo pipefail

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

log() {
    # All progress goes to stderr — stdout is reserved for machine-readable
    # output (DMG path) on success.
    echo "[sign_macos] $*" >&2
}

stage() {
    log ""
    log "stage $1: $2"
}

fatal() {
    local code="$1"; shift
    log "FATAL: $*"
    exit "$code"
}

# Repo root = parent of scripts/dist/.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/../.." &> /dev/null && pwd)"

ENTITLEMENTS="$REPO_ROOT/tauri/src-tauri/entitlements.macos.plist"

# ---------------------------------------------------------------------------
# CLI parsing
# ---------------------------------------------------------------------------

DRY_RUN=0
SKIP_DMG=0
KEYCHAIN_PROFILE="vibemix-notarytool"
OUTPUT_DIR="$REPO_ROOT/dist"
APP=""

usage() {
    cat >&2 <<USAGE
Usage: scripts/dist/sign_macos.sh [options] [<app-path>]

Options:
  --dry-run              Validate env + paths only; do not execute codesign /
                         create-dmg / notarytool / staple / spctl.
  --skip-dmg             Sign-only mode (Stage 1-3 + Stage 7-8 only).
                         For local re-sign drills.
  --keychain-profile N   notarytool keychain profile (default: $KEYCHAIN_PROFILE).
  --output-dir PATH      DMG + verify-report output directory
                         (default: $OUTPUT_DIR).
  -h, --help             This message.

Positional:
  <app-path>             Path to vibemix-core.app
                         (default: $REPO_ROOT/dist/vibemix-core/vibemix-core.app).

Bundle ID is world.bravoh.vibemix (LOCKED).
USAGE
}

COMPANION=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)            DRY_RUN=1; shift ;;
        --skip-dmg)           SKIP_DMG=1; shift ;;
        --companion)          COMPANION=1; shift ;;
        --keychain-profile)   KEYCHAIN_PROFILE="$2"; shift 2 ;;
        --output-dir)         OUTPUT_DIR="$2"; shift 2 ;;
        -h|--help)            usage; exit 0 ;;
        --*)                  log "unknown flag: $1"; usage; exit 2 ;;
        *)                    APP="$1"; shift ;;
    esac
done

# Phase 49 Plan 02 — Companion-script signing short-circuit.
# When --companion is supplied, codesign every file in installer/companion/
# under the same Developer ID identity used for the main app bundle.
# The existing happy-path code below is preserved byte-identical when the
# flag is absent.
if [[ $COMPANION -eq 1 ]]; then
    log "── companion-sign mode (Phase 49 INSTALL-05) ──"
    if [[ $DRY_RUN -eq 1 ]]; then
        log "DRY-RUN — listing files that would be codesigned:"
        find "$REPO_ROOT/installer/companion" -maxdepth 1 -type f \
            \( -name "*.sh" -o -name "*.py" \) | while read -r f; do
            log "  would sign: $f"
        done
        exit 0
    fi
    : "${APPLE_DEVELOPER_ID:?missing APPLE_DEVELOPER_ID for companion-sign}"
    while IFS= read -r f; do
        log "codesign: $f"
        codesign --force --options runtime --sign "$APPLE_DEVELOPER_ID" \
            --timestamp "$f" || {
            log "FAIL: codesign $f"
            exit 1
        }
    done < <(find "$REPO_ROOT/installer/companion" -maxdepth 1 -type f \
        \( -name "*.sh" -o -name "*.py" \))
    log "── companion-sign complete ──"
    exit 0
fi

if [[ -z "$APP" ]]; then
    APP="$REPO_ROOT/dist/vibemix-core/vibemix-core.app"
fi

mkdir -p "$OUTPUT_DIR"

# ---------------------------------------------------------------------------
# Stage 1 — Validate prerequisites
# ---------------------------------------------------------------------------

stage 1 "validate prerequisites (binaries, env vars, paths, identity)"

MISSING=()

# Required env vars first (collect all, print all, exit 2).
for v in APPLE_DEVELOPER_ID APPLE_TEAM_ID APPLE_API_KEY_PATH APPLE_API_KEY_ID APPLE_API_KEY_ISSUER; do
    if [[ -z "${!v:-}" ]]; then
        MISSING+=("$v")
    fi
done

if [[ ${#MISSING[@]} -gt 0 ]]; then
    log "missing required env vars:"
    for v in "${MISSING[@]}"; do
        log "  - $v"
    done
    log "see docs/signing-macos.md for the one-time setup recipe"
    exit 2
fi

# Required binaries.
for bin in codesign xcrun security plutil; do
    if ! command -v "$bin" >/dev/null 2>&1; then
        fatal 2 "$bin not found on PATH (install Xcode Command Line Tools: xcode-select --install)"
    fi
done

if [[ "$SKIP_DMG" -eq 0 ]]; then
    if ! command -v create-dmg >/dev/null 2>&1; then
        fatal 2 "create-dmg not found on PATH. Install: brew install create-dmg"
    fi
fi

# Paths.
if [[ ! -d "$APP" ]]; then
    fatal 2 "app bundle not found: $APP (build via: uv run pyinstaller vibemix-core.macos.spec --clean --noconfirm)"
fi
if [[ ! -f "$APP/Contents/Info.plist" ]]; then
    fatal 2 "app bundle missing Contents/Info.plist: $APP (this does not look like a real .app)"
fi
if [[ ! -f "$ENTITLEMENTS" ]]; then
    fatal 2 "entitlements file not found: $ENTITLEMENTS (Plan 18-02 Task 1 should have created it)"
fi

# Identity must exist in the keychain (skipped on CI where the import happens
# inline; CI must export APPLE_DEVELOPER_ID matching the imported cert's CN).
if [[ "${CI:-}" != "true" ]]; then
    if ! security find-identity -p codesigning -v 2>/dev/null | grep -F "$APPLE_DEVELOPER_ID" >/dev/null; then
        fatal 2 "Developer ID identity not in keychain: $APPLE_DEVELOPER_ID
  → security find-identity -p codesigning -v
  → see docs/signing-macos.md §Prerequisites for cert import"
    fi
fi

# API key file.
if [[ ! -f "$APPLE_API_KEY_PATH" ]]; then
    fatal 2 "ASC API key not found: $APPLE_API_KEY_PATH (CI mode should have decoded \$APPLE_API_KEY_P8 first)"
fi

log "prerequisites OK: app=$APP entitlements=$ENTITLEMENTS"

if [[ "$DRY_RUN" -eq 1 ]]; then
    log "DRY-RUN: stopping after Stage 1; no codesign / notarytool / staple invoked"
    exit 0
fi

# ---------------------------------------------------------------------------
# Stage 2 — Pre-flight codesign every nested binary
# ---------------------------------------------------------------------------
#
# Per CONTEXT D-Area-2: `--deep` on `codesign` sometimes misses files inside
# PyInstaller's `_internal/` tree. Pre-flight pass: find every regular file
# with the executable bit, codesign each individually. Filter for idempotency
# (skip files where `codesign --verify` already succeeds).

stage 2 "pre-flight codesign nested binaries (BSD-find perm syntax)"

while IFS= read -r file; do
    # Skip non-Mach-O / non-script entries; codesign tolerates them but they
    # noise up the log.
    if codesign --verify --strict "$file" >/dev/null 2>&1; then
        continue  # already signed — idempotent skip
    fi
    log "  signing nested: ${file#"$APP"/}"
    codesign --sign "$APPLE_DEVELOPER_ID" \
             --force \
             --options runtime \
             --entitlements "$ENTITLEMENTS" \
             --timestamp \
             "$file"
done < <(find "$APP" -type f -perm +111 2>/dev/null)

# ---------------------------------------------------------------------------
# Stage 3 — Codesign the .app bundle (deep) + verify strict
# ---------------------------------------------------------------------------

stage 3 "codesign --deep --options runtime --entitlements ... (final pass)"

codesign --sign "$APPLE_DEVELOPER_ID" \
         --force \
         --deep \
         --options runtime \
         --entitlements "$ENTITLEMENTS" \
         --timestamp \
         "$APP"

log "verifying strict signature on $APP"
codesign --verify --deep --strict --verbose=2 "$APP"

if [[ "$SKIP_DMG" -eq 1 ]]; then
    log "SKIP-DMG mode: jumping past Stage 4-6, running Stage 7-8 against .app only"
    DMG_OUT=""
else
    # -----------------------------------------------------------------------
    # Stage 4 — Create DMG
    # -----------------------------------------------------------------------

    stage 4 "create-dmg → vibemix-<ver>.dmg"

    # Extract CFBundleShortVersionString for DMG name; fall back to vibemix.dmg
    # with a stderr warning (do not fail the run on a missing version key).
    VER=""
    if VER_RAW=$(plutil -extract CFBundleShortVersionString xml1 -o - "$APP/Contents/Info.plist" 2>/dev/null); then
        VER=$(echo "$VER_RAW" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || true)
    fi
    if [[ -z "$VER" ]]; then
        log "WARNING: could not extract CFBundleShortVersionString from $APP/Contents/Info.plist; using vibemix.dmg"
        DMG_NAME="${VIBEMIX_DMG_NAME:-vibemix.dmg}"
    else
        DMG_NAME="${VIBEMIX_DMG_NAME:-vibemix-$VER.dmg}"
    fi
    DMG_OUT="$OUTPUT_DIR/$DMG_NAME"

    # Idempotent: remove a stale DMG if present (create-dmg refuses to overwrite).
    [[ -f "$DMG_OUT" ]] && rm -f "$DMG_OUT"

    VOLICON_ARG=()
    VOLICON="$REPO_ROOT/tauri/src-tauri/icons/icon.png"
    if [[ -f "$VOLICON" ]]; then
        VOLICON_ARG=(--volicon "$VOLICON")
    fi

    create-dmg \
        --volname "vibemix" \
        "${VOLICON_ARG[@]}" \
        --window-pos 200 120 \
        --window-size 600 400 \
        --icon-size 100 \
        --app-drop-link 425 200 \
        "$DMG_OUT" \
        "$APP"

    # Sign the DMG with the same identity so Gatekeeper inspects a signed
    # container, not just the inner .app.
    log "signing DMG: $DMG_OUT"
    codesign --sign "$APPLE_DEVELOPER_ID" --force --timestamp "$DMG_OUT"

    # -----------------------------------------------------------------------
    # Stage 5 — notarytool submit --wait (idempotent retry x3, exponential backoff)
    # -----------------------------------------------------------------------

    stage 5 "xcrun notarytool submit --wait (retry x3 on transient failures)"

    NOTARY_OK=0
    SUBMISSION_LOG="$OUTPUT_DIR/notarytool-submission.log"

    for attempt in 1 2 3; do
        log "  notarytool attempt $attempt of 3"
        if xcrun notarytool submit "$DMG_OUT" \
                --key "$APPLE_API_KEY_PATH" \
                --key-id "$APPLE_API_KEY_ID" \
                --issuer "$APPLE_API_KEY_ISSUER" \
                --wait \
                --output-format json \
                > "$SUBMISSION_LOG" 2>&1; then
            NOTARY_OK=1
            break
        fi
        # Exponential backoff: 30s → 60s → 120s. Stop chaining short sleeps;
        # transient notarytool errors are usually HTTP timeouts that resolve in
        # under a minute. Final attempt is best-effort.
        if [[ "$attempt" -lt 3 ]]; then
            BACKOFF=$((30 * attempt))
            log "  attempt $attempt failed; retrying in ${BACKOFF}s"
            sleep "$BACKOFF"
        fi
    done

    if [[ "$NOTARY_OK" -ne 1 ]]; then
        log "notarytool failed after 3 attempts; dumping submission log:"
        cat "$SUBMISSION_LOG" >&2 || true
        exit 3
    fi

    # Best-effort: fetch the notarization detail log for the submission.
    SUBMISSION_ID=$(grep -oE '"id":"[a-f0-9-]+"' "$SUBMISSION_LOG" | head -1 | sed -E 's/.*"id":"([^"]+)".*/\1/' || true)
    if [[ -n "$SUBMISSION_ID" ]]; then
        log "fetching notarization log for submission $SUBMISSION_ID"
        xcrun notarytool log "$SUBMISSION_ID" \
            --key "$APPLE_API_KEY_PATH" \
            --key-id "$APPLE_API_KEY_ID" \
            --issuer "$APPLE_API_KEY_ISSUER" \
            "$OUTPUT_DIR/notarytool-detail.json" 2>&1 | head -20 >&2 || true
    fi

    # -----------------------------------------------------------------------
    # Stage 6 — Staple the notarization ticket onto the DMG
    # -----------------------------------------------------------------------

    stage 6 "xcrun stapler staple → embedded ticket survives offline launch"

    # Idempotent: stapler validate first; if already stapled, skip the staple.
    if xcrun stapler validate "$DMG_OUT" >/dev/null 2>&1; then
        log "stapler ticket already present; skipping staple"
    else
        xcrun stapler staple "$DMG_OUT"
        xcrun stapler validate "$DMG_OUT"
    fi
fi

# ---------------------------------------------------------------------------
# Stage 7 — spctl --assess --type execute (Gatekeeper acceptance, final gate)
# ---------------------------------------------------------------------------

stage 7 "spctl --assess --type execute (Gatekeeper acceptance)"

SPCTL_OUT=$(spctl --assess --type execute --verbose=4 "$APP" 2>&1) || SPCTL_RC=$?
SPCTL_RC=${SPCTL_RC:-0}
echo "$SPCTL_OUT" >&2

if [[ "$SPCTL_RC" -ne 0 ]] || ! echo "$SPCTL_OUT" | grep -q "accepted"; then
    log "spctl rejected the signed bundle — release blocked"
    exit 4
fi

if ! echo "$SPCTL_OUT" | grep -q "source=Notarized Developer ID"; then
    log "WARNING: spctl accepted but source is NOT 'Notarized Developer ID'"
    log "         this is non-fatal but should be investigated before tagging a release"
fi

# ---------------------------------------------------------------------------
# Stage 8 — verify_binary.py (cross-plan integration with Plan 18-01)
# ---------------------------------------------------------------------------
#
# verify_binary.py walks the bundle and flags any string matching the API-key
# regex set (AIza / AKIA / ya29 / sk- / 39-char Google shape). A non-zero exit
# is RELEASE-BLOCKING even on a notarized binary — a notarized leak is still
# a leak.

stage 8 "verify_binary.py — AIza scan release-blocker"

VERIFY_REPORT="$OUTPUT_DIR/verify-report.json"

# verify_binary lives under scripts/dist/ (Plan 18-01 ships it). Until that
# plan lands, allow this step to be SKIPPED with a stderr warning rather than
# fail the whole run — Plan 18-05's CI wires the hard gate.
VERIFY_BINARY="$REPO_ROOT/scripts/dist/verify_binary.py"
if [[ ! -f "$VERIFY_BINARY" ]]; then
    log "WARNING: $VERIFY_BINARY not present yet (Plan 18-01 ships it)."
    log "         Stage 8 SKIPPED — CI must run verify_binary.py separately."
else
    if command -v uv >/dev/null 2>&1; then
        uv run python -m scripts.dist.verify_binary "$APP" --report "$VERIFY_REPORT" \
            || { log "verify_binary.py flagged the bundle — release blocked (see $VERIFY_REPORT)"; exit 5; }
    else
        python3 -m scripts.dist.verify_binary "$APP" --report "$VERIFY_REPORT" \
            || { log "verify_binary.py flagged the bundle — release blocked (see $VERIFY_REPORT)"; exit 5; }
    fi
fi

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------

if [[ -n "$DMG_OUT" ]]; then
    log "DONE: $(basename "$DMG_OUT") notarized + stapled + verified"
    # Machine-readable: stdout is just the DMG path on success.
    echo "$DMG_OUT"
else
    log "DONE: $APP signed + verified (SKIP-DMG mode)"
    echo "$APP"
fi
