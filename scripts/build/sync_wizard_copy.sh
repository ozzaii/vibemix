#!/usr/bin/env bash
# sync_wizard_copy.sh — Phase 49: mirror onboarding_copy.json into the
# tauri/ui/src/wizard/ tree so Vite can import it without crossing roots.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cp "$ROOT/installer/companion/onboarding_copy.json" "$ROOT/tauri/ui/src/wizard/copy.json"
echo "synced: tauri/ui/src/wizard/copy.json"
