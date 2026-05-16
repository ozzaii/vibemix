#!/usr/bin/env bash
# VIS-04 (Phase 43, Plan 43-05) — Mascot bundle + per-clip size gate.
#
# Two-tier check enforced on every CI run that touches the mascot bundle:
#
#   Tier 1: total mascot GLB bytes ≤ 25 MB
#           Delegates to scripts/check_mascot_glb_size.sh (Phase 31 / Pitfall P52).
#
#   Tier 2: per-clip prep_*.glb size band 400 KB – 1200 KB
#           CONTEXT §VIS-04 — guarantees draco compression is tuned;
#           catches both over-compressed (degenerate) and under-compressed
#           (bundle-budget regression) clips.
#
# Exit codes:
#   0 — both tiers green
#   1 — Tier 1 fail (total bundle exceeds 25 MB)
#   2 — Tier 2 fail (one or more prep_*.glb files outside the 400 KB–1200 KB band)
#
# Until §VIS-04 Kaan-discharge replaces the prep_*.glb placeholders with
# real Mixamo retargets, Tier 2 is expected to fail (the placeholders are
# ~44–56 KB each, well below the 400 KB floor). The non-zero exit on
# placeholder GLBs is the gate's mechanism for reminding the operator
# that the §VIS-04 runbook still needs to be discharged.
#
# Run from repo root: bash scripts/mascot/check_bundle_size.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Tier 1: delegate to the existing Phase 31 gate (25 MB total bundle cap).
echo "==> Tier 1: total mascot bundle <= 25 MB (delegate -> check_mascot_glb_size.sh)"
bash "${REPO_ROOT}/scripts/check_mascot_glb_size.sh"

# Tier 2: per-clip prep_*.glb size band 400 KB – 1200 KB.
echo "==> Tier 2: prep_*.glb per-clip 400 KB - 1200 KB band"
readonly MIN_BYTES=$((400 * 1024))   # 409600
readonly MAX_BYTES=$((1200 * 1024))  # 1228800

ANIM_DIR="${REPO_ROOT}/tauri/ui/assets/mascot/animations"
fail=0
found_any=0
shopt -s nullglob
for glb in "${ANIM_DIR}"/prep_*.glb; do
    found_any=1
    if [[ "$(uname -s)" == "Darwin" ]]; then
        size=$(stat -f '%z' "${glb}")
    else
        size=$(stat -c '%s' "${glb}")
    fi
    name="$(basename "${glb}")"
    if (( size < MIN_BYTES )) || (( size > MAX_BYTES )); then
        echo "  FAIL: ${name} size ${size} bytes outside band (${MIN_BYTES}..${MAX_BYTES})"
        fail=1
    else
        echo "  OK:   ${name} size ${size} bytes"
    fi
done

if (( found_any == 0 )); then
    echo "  WARN: no prep_*.glb files under ${ANIM_DIR}"
fi

if (( fail != 0 )); then
    echo "FAIL: prep_*.glb per-clip band check" >&2
    echo "Note: placeholder prep_*.glb files legitimately fall outside the band " >&2
    echo "      until KAAN-ACTION-LEGAL.md §VIS-04 discharge replaces them with " >&2
    echo "      real Mixamo retargets." >&2
    exit 2
fi

echo "PASS: bundle <= 25 MB AND prep_*.glb per-clip 400 KB - 1200 KB"
exit 0
