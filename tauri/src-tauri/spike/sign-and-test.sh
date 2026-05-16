#!/usr/bin/env bash
# vibemix Phase 24 Wave-0 — AX-from-Rust-parent sign-and-test harness.
#
# Pitfall 3 (Tauri #8329) reproduction harness. Builds the standalone
# spike binary, wraps it in a minimal .app bundle, ad-hoc codesigns it
# with the SAME entitlements.plist the shipping vibemix bundle uses,
# installs it under /Applications/ (mirrors the real TCC keying path),
# launches it against a running djay Pro, and prints one of four verdicts.
#
# CRITICAL: this script REFUSES to use the production bundle identifier
# `world.bravoh.vibemix` — corrupting that ID's TCC entries would force
# Kaan to revoke + re-grant Accessibility on every dev cycle. The spike
# bundle is locked to `world.bravoh.vibemix.spike`.
#
# Usage:
#   bash tauri/src-tauri/spike/sign-and-test.sh
#
# Verdicts (printed last line):
#   VERDICT_PASS                — AX_PASS observed in probe.log
#   VERDICT_PARTIAL             — AX_PARTIAL observed (fallback path)
#   VERDICT_FAIL                — AX_FAIL observed (Tauri #8329 confirmed)
#   VERDICT_INCONCLUSIVE        — djay Pro was not running at probe time

set -euo pipefail

# ---------------------------------------------------------------------------
# Constants — bundle ID + entitlements paths are LOCKED.
# ---------------------------------------------------------------------------
SPIKE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SPIKE_BUNDLE_ID="world.bravoh.vibemix.spike"
PRODUCTION_BUNDLE_ID="world.bravoh.vibemix"
SPIKE_APP_NAME="vibemix-ax-spike.app"
BUILD_DIR="${SPIKE_DIR}/build"
APP_PATH="${BUILD_DIR}/${SPIKE_APP_NAME}"
INSTALLED_PATH="/Applications/${SPIKE_APP_NAME}"
ENTITLEMENTS_SRC="${SPIKE_DIR}/../entitlements.plist"
ENTITLEMENTS_DEST="${SPIKE_DIR}/spike-entitlements.plist"
PROBE_LOG="${SPIKE_DIR}/probe.log"

# ---------------------------------------------------------------------------
# T-24-01-01 mitigation: refuse to sign with the production bundle ID.
# ---------------------------------------------------------------------------
if [[ "${SPIKE_BUNDLE_ID}" == "${PRODUCTION_BUNDLE_ID}" ]]; then
  echo "FATAL: spike refuses to use production bundle ID ${PRODUCTION_BUNDLE_ID}" >&2
  echo "       (TCC entry corruption avoidance — see threat T-24-01-01)" >&2
  exit 2
fi

# ---------------------------------------------------------------------------
# Step 1 — cargo build --release (clean every run).
# ---------------------------------------------------------------------------
echo "[1/7] cargo build --release"
(cd "${SPIKE_DIR}" && cargo build --release)

BINARY="${SPIKE_DIR}/target/release/vibemix-ax-spike"
if [[ ! -x "${BINARY}" ]]; then
  echo "FATAL: spike binary not found at ${BINARY}" >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# Step 2 — Build a minimal .app bundle wrapper.
# ---------------------------------------------------------------------------
echo "[2/7] assembling ${SPIKE_APP_NAME}"
rm -rf "${BUILD_DIR}"
mkdir -p "${APP_PATH}/Contents/MacOS"
cp "${BINARY}" "${APP_PATH}/Contents/MacOS/vibemix-ax-spike"

cat > "${APP_PATH}/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleIdentifier</key>
    <string>${SPIKE_BUNDLE_ID}</string>
    <key>CFBundleName</key>
    <string>vibemix-ax-spike</string>
    <key>CFBundleDisplayName</key>
    <string>vibemix-ax-spike</string>
    <key>CFBundleExecutable</key>
    <string>vibemix-ax-spike</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleVersion</key>
    <string>0.0.1</string>
    <key>CFBundleShortVersionString</key>
    <string>0.0.1</string>
    <key>LSMinimumSystemVersion</key>
    <string>12.3</string>
    <key>NSAccessibilityUsageDescription</key>
    <string>vibemix-ax-spike probes djay Pro window geometry to verify AX inheritance.</string>
</dict>
</plist>
PLIST

# ---------------------------------------------------------------------------
# Step 3 — Copy the shipped entitlements.plist verbatim (same surface the
# real bundle is signed with — Pitfall 3 requires identical entitlement
# context for an honest inheritance test).
# ---------------------------------------------------------------------------
echo "[3/7] copying entitlements"
if [[ ! -f "${ENTITLEMENTS_SRC}" ]]; then
  echo "FATAL: entitlements not found at ${ENTITLEMENTS_SRC}" >&2
  exit 1
fi
cp "${ENTITLEMENTS_SRC}" "${ENTITLEMENTS_DEST}"

# ---------------------------------------------------------------------------
# Step 4 — Ad-hoc codesign with hardened runtime.
# ---------------------------------------------------------------------------
echo "[4/7] codesign --force --deep --options runtime --sign -"
codesign --force --deep --options runtime \
  --entitlements "${ENTITLEMENTS_DEST}" \
  --sign - \
  "${APP_PATH}"

codesign --display --entitlements - "${APP_PATH}" 2>&1 | head -40 || true

# ---------------------------------------------------------------------------
# Step 5 — Install to /Applications/ (mirrors real TCC keying).
# ---------------------------------------------------------------------------
echo "[5/7] installing to ${INSTALLED_PATH}"
rm -rf "${INSTALLED_PATH}"
cp -R "${APP_PATH}" "${INSTALLED_PATH}"

# ---------------------------------------------------------------------------
# Step 6 — Launch + capture stdout to probe.log.
# ---------------------------------------------------------------------------
echo "[6/7] launching probe → ${PROBE_LOG}"
"${INSTALLED_PATH}/Contents/MacOS/vibemix-ax-spike" > "${PROBE_LOG}" 2>&1 || true

cat "${PROBE_LOG}"

# ---------------------------------------------------------------------------
# Step 7 — Parse verdict from probe.log.
# ---------------------------------------------------------------------------
echo "[7/7] parsing verdict"
if   grep -q "^AX_PASS"          "${PROBE_LOG}"; then echo "VERDICT_PASS"
elif grep -q "^AX_PARTIAL"       "${PROBE_LOG}"; then echo "VERDICT_PARTIAL"
elif grep -q "^AX_FAIL"          "${PROBE_LOG}"; then echo "VERDICT_FAIL"
elif grep -q "^AX_INCONCLUSIVE"  "${PROBE_LOG}"; then echo "VERDICT_INCONCLUSIVE"
else echo "VERDICT_UNKNOWN — inspect probe.log manually"; exit 3
fi
