#!/usr/bin/env bash
# Build a local unsigned macOS DMG that preserves the repaired PyInstaller sidecar.
#
# Direct `cargo tauri build --bundles dmg --no-sign` can create a DMG before the
# app-side PyInstaller dylib symlinks are repaired. This wrapper mirrors the
# release path: build the .app, repair/check it, create the DMG, then mount/copy
# and smoke the DMG artifact.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
TAURI_DIR="${REPO_ROOT}/tauri/src-tauri"
APP="${TAURI_DIR}/target/release/bundle/macos/vibemix.app"
OUT_DIR="${TAURI_DIR}/target/release/bundle/dmg"
OUT="${OUT_DIR}/vibemix_0.0.1_aarch64.dmg"
SMOKE="${VIBEMIX_LOCAL_DMG_SMOKE:-library-stats}"
PYTHON=(uv run python)

usage() {
  cat <<'EOF'
usage: build_macos_local_dmg.sh [--output PATH] [--smoke version|library-stats|none]

Builds an unsigned local DMG for drag-install rehearsal. This is not a release
artifact: the signed/notarized release path remains scripts/dist/sign_macos.sh.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output)
      OUT="${2:?--output requires a path}"
      shift 2
      ;;
    --smoke)
      SMOKE="${2:?--smoke requires version|library-stats|none}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[local-dmg] unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

case "$SMOKE" in
  version|library-stats|none) ;;
  *)
    echo "[local-dmg] invalid --smoke value: $SMOKE" >&2
    exit 2
    ;;
esac

mkdir -p "$(dirname "$OUT")"

echo "[local-dmg] building unsigned .app"
(cd "$TAURI_DIR" && VIBEMIX_FORCE_SIDECAR=1 cargo tauri build --bundles app --no-sign --ci)

echo "[local-dmg] repairing app-side sidecar symlinks"
"${PYTHON[@]}" "$REPO_ROOT/scripts/dist/repair_macos_app_sidecar_symlinks.py" "$APP"

echo "[local-dmg] checking repaired .app"
"${PYTHON[@]}" "$REPO_ROOT/scripts/dist/check_macos_app_bundle_ready.py" \
  "$APP" \
  --require-moss-source \
  --smoke "$SMOKE"

rm -f "$OUT"

if command -v create-dmg >/dev/null 2>&1; then
  echo "[local-dmg] creating DMG with create-dmg"
  VOLICON=()
  if [[ -f "$TAURI_DIR/icons/icon.png" ]]; then
    VOLICON=(--volicon "$TAURI_DIR/icons/icon.png")
  fi
  create-dmg \
    --volname "vibemix" \
    "${VOLICON[@]}" \
    --window-pos 200 120 \
    --window-size 600 400 \
    --icon-size 100 \
    --app-drop-link 425 200 \
    "$OUT" \
    "$APP"
else
  echo "[local-dmg] create-dmg not found; falling back to hdiutil"
  hdiutil create -volname "vibemix" -srcfolder "$APP" -ov -format UDZO "$OUT"
fi

echo "[local-dmg] checking DMG drag-install smoke"
"${PYTHON[@]}" "$REPO_ROOT/scripts/dist/check_macos_dmg_artifact_ready.py" \
  "$OUT" \
  --require-moss-source \
  --smoke "$SMOKE"

echo "$OUT"
