#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# scripts/launch/sync_packaging.sh — replace SHA placeholders in
# Homebrew + Scoop scaffolds with real v0.1.0-rc1 release artifact SHAs.
#
# Phase 69 Plan 69-04 (OSS-05). The packaging scaffolds ship with 64-zero
# placeholder SHAs (audit-safe; brew audit + scoop checkver don't fetch).
# When OSS-04 fires (`cut_release.sh v0.1.0-rc1`), this helper replaces the
# placeholders with the actual signed-artifact SHAs so the manifests can
# be pushed to bravoh-ai/homebrew-tap + bravoh-ai/scoop-bucket as a
# follow-on milestone.
#
# Usage:
#   bash scripts/launch/sync_packaging.sh <path-to-macos-dmg> <path-to-windows-exe>
#
# Example:
#   bash scripts/launch/sync_packaging.sh \
#       dist/vibemix-v0.1.0-rc1-macos.dmg dist/vibemix-v0.1.0-rc1-windows-x64.exe
set -euo pipefail

usage() {
    echo "Usage: $0 <macos-dmg> <windows-exe>" >&2
    exit 2
}

[[ $# -eq 2 ]] || usage
MACOS_DMG="$1"
WINDOWS_EXE="$2"
[[ -f "$MACOS_DMG" ]] || { echo "Missing: $MACOS_DMG" >&2; exit 1; }
[[ -f "$WINDOWS_EXE" ]] || { echo "Missing: $WINDOWS_EXE" >&2; exit 1; }
MAC_SHA=$(shasum -a 256 "$MACOS_DMG" | awk '{print $1}')
WIN_SHA=$(shasum -a 256 "$WINDOWS_EXE" | awk '{print $1}')
PLACEHOLDER="0000000000000000000000000000000000000000000000000000000000000000"
sed -i.bak "s/${PLACEHOLDER}/${MAC_SHA}/" packaging/homebrew/Formula/vibemix.rb
sed -i.bak "s/sha256:${PLACEHOLDER}/sha256:${WIN_SHA}/" packaging/scoop/vibemix.json
rm -f packaging/homebrew/Formula/vibemix.rb.bak packaging/scoop/vibemix.json.bak
echo "synced packaging/ SHAs:"
echo "  homebrew (macOS DMG): ${MAC_SHA}"
echo "  scoop (Windows EXE):  ${WIN_SHA}"
