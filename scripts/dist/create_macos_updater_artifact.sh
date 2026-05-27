#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# Create the macOS updater artifact consumed by tauri-plugin-updater.
# The public first-install artifact is the DMG; the updater wants a tar.gz
# whose top-level entry is the signed .app bundle.

set -euo pipefail
set +x

log() {
    echo "[create_macos_updater_artifact] $*" >&2
}

usage() {
    cat >&2 <<'USAGE'
Usage:
  create_macos_updater_artifact.sh --arch <arm64|x86_64> \
      --output-dir <dir> <path/to/vibemix.app>

Optional signing:
  If TAURI_UPDATER_PRIVATE_KEY and TAURI_UPDATER_KEY_PASSWORD are present,
  the script also writes <artifact>.sig with the Tauri signer. The password
  variable may be intentionally empty, but it must be defined.
USAGE
    exit 2
}

ARCH=""
OUTPUT_DIR=""
APP=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --arch) ARCH="${2:-}"; shift 2 ;;
        --output-dir) OUTPUT_DIR="${2:-}"; shift 2 ;;
        -h|--help) usage ;;
        --*) log "unknown flag: $1"; usage ;;
        *) APP="$1"; shift ;;
    esac
done

[[ -n "$ARCH" ]] || usage
[[ -n "$OUTPUT_DIR" ]] || usage
[[ -n "$APP" ]] || usage

case "$ARCH" in
    arm64|x86_64) ;;
    *)
        log "FATAL: unsupported arch '$ARCH' (expected arm64 or x86_64)"
        exit 2
        ;;
esac

if [[ ! -d "$APP" ]]; then
    log "FATAL: app bundle not found: $APP"
    exit 2
fi
if [[ ! -f "$APP/Contents/Info.plist" ]]; then
    log "FATAL: app bundle missing Contents/Info.plist: $APP"
    exit 2
fi
if [[ "$APP" != *.app ]]; then
    log "FATAL: expected a .app bundle path: $APP"
    exit 2
fi

PLIST_BUDDY="/usr/libexec/PlistBuddy"
if [[ ! -x "$PLIST_BUDDY" ]]; then
    log "FATAL: PlistBuddy missing at $PLIST_BUDDY"
    exit 2
fi

VERSION=$("$PLIST_BUDDY" -c "Print :CFBundleShortVersionString" "$APP/Contents/Info.plist" 2>/dev/null || true)
if [[ -z "$VERSION" ]]; then
    log "FATAL: CFBundleShortVersionString missing from $APP/Contents/Info.plist"
    exit 2
fi

APP_PARENT=$(cd -- "$(dirname -- "$APP")" && pwd)
APP_BASENAME=$(basename -- "$APP")
PRODUCT=${APP_BASENAME%.app}
mkdir -p "$OUTPUT_DIR"
OUTPUT_DIR=$(cd -- "$OUTPUT_DIR" && pwd)
OUT="$OUTPUT_DIR/${PRODUCT}-${VERSION}-${ARCH}.app.tar.gz"
SIG_OUT="$OUT.sig"

rm -f "$OUT" "$SIG_OUT"
COPYFILE_DISABLE=1 tar -czf "$OUT" -C "$APP_PARENT" "$APP_BASENAME"

if ! tar -tzf "$OUT" | grep -q "^${APP_BASENAME}/Contents/"; then
    log "FATAL: updater archive does not contain ${APP_BASENAME}/Contents/"
    exit 2
fi

if [[ -n "${TAURI_UPDATER_PRIVATE_KEY:-}" && -n "${TAURI_UPDATER_KEY_PASSWORD+x}" ]]; then
    KEY_DIR=$(mktemp -d -t vibemix-updater-key.XXXXXX)
    trap "rm -rf '$KEY_DIR'" EXIT INT TERM
    KEY_PATH="$KEY_DIR/vibemix_updater.key"
    echo "$TAURI_UPDATER_PRIVATE_KEY" | base64 --decode > "$KEY_PATH"
    chmod 600 "$KEY_PATH"
    npx --yes @tauri-apps/cli signer sign \
        --private-key-path "$KEY_PATH" \
        --password "$TAURI_UPDATER_KEY_PASSWORD" \
        "$OUT" > "$SIG_OUT"
    log "wrote updater signature: $SIG_OUT"
else
    log "TAURI_UPDATER_PRIVATE_KEY/TAURI_UPDATER_KEY_PASSWORD absent; skipping .sig sidecar"
fi

log "wrote updater artifact: $OUT"
echo "$OUT"
