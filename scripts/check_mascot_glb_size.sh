#!/usr/bin/env bash
# Phase 31 Plan 07 — Mascot GLB total size CI gate.
#
# Pitfall P52: real GLB animations can push the bundle past the 350 MB
# hard cap. Phase 31 sub-budget for mascot GLBs is 25 MB. This script
# sums every .glb under the mascot asset dirs and fails if the total
# exceeds the cap.
#
# Today (v2.1 pre-Phase-35) the v2.0 placeholder + anticipation rig is
# ~22 MB. Phase 35 (real GLBs) MUST respect this same budget.
#
# Run from repo root: ./scripts/check_mascot_glb_size.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# 25 MB cap in bytes (1024 * 1024 * 25).
readonly CAP_BYTES=26214400

# Asset roots — additive list; if Phase 35 adds new dirs, append here.
ASSET_DIRS=(
  "${REPO_ROOT}/tauri/ui/assets/mascot"
  "${REPO_ROOT}/tauri/ui/public/mascot"
)

total=0
found_any=0
for dir in "${ASSET_DIRS[@]}"; do
  [[ -d "${dir}" ]] || continue
  # Cross-platform file size: BSD `stat -f %z` (macOS) vs GNU `stat -c %s` (Linux).
  if [[ "$(uname -s)" == "Darwin" ]]; then
    while IFS= read -r -d '' f; do
      size=$(stat -f '%z' "${f}")
      total=$((total + size))
      found_any=1
    done < <(find "${dir}" -name '*.glb' -print0)
  else
    while IFS= read -r -d '' f; do
      size=$(stat -c '%s' "${f}")
      total=$((total + size))
      found_any=1
    done < <(find "${dir}" -name '*.glb' -print0)
  fi
done

# Report.
total_mb=$(awk "BEGIN {printf \"%.2f\", ${total} / 1024 / 1024}")
cap_mb=$(awk "BEGIN {printf \"%.2f\", ${CAP_BYTES} / 1024 / 1024}")

if [[ "${total}" -gt "${CAP_BYTES}" ]]; then
  echo "FAIL: mascot GLB total ${total_mb} MB exceeds cap ${cap_mb} MB (Pitfall P52)" >&2
  exit 1
fi

if [[ "${found_any}" -eq 0 ]]; then
  echo "OK: no mascot GLB files found (cap ${cap_mb} MB)"
else
  echo "OK: mascot GLB total ${total_mb} MB / ${cap_mb} MB cap"
fi
