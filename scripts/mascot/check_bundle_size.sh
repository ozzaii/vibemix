#!/usr/bin/env bash
# Phase 47 / MASCOT-03 — Mascot bundle + per-clip size gate.
#
# Tier 1: total mascot GLB bytes <= 25 MB
#         Delegates to scripts/check_mascot_glb_size.sh (Phase 31 / Pitfall P52).
#         30 MB bump fallback documented in docs/mascot/BUNDLE-DECISION.md
#         and ONLY applied via the env override BUNDLE_CAP_BUMP=30 (set in
#         CI only after the Decision Log entry is committed).
#
# Tier 2: per-clip per-family bands (sourced from SLOT_FAMILIES in
#         scripts/mascot/retarget_to_neon_rebel.py):
#
#           base_*       200-600 KB  (looping, simple)
#           emotion_*    300-900 KB  (expressive face/torso)
#           prep_*       400-1200 KB (anticipation + legacy share this band)
#           react_*      400-1200 KB (peak-energy moves)
#
# Exit codes:
#   0 — both tiers green
#   1 — Tier 1 fail (total bundle exceeds cap)
#   2 — Tier 2 fail (one or more *.glb files outside their family band)
#
# Expected-fail UX: until Kaan discharges §VIS-04 with real Mixamo
# retargets, the placeholder GLBs sit below the floor of every band.
# The non-zero exit is the gate's reminder mechanism, NOT a bug.
#
# Run from repo root: bash scripts/mascot/check_bundle_size.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# ── Tier 1 ───────────────────────────────────────────────────────────
echo "==> Tier 1: total mascot bundle <= 25 MB (delegate -> check_mascot_glb_size.sh)"
bash "${REPO_ROOT}/scripts/check_mascot_glb_size.sh"

# ── Tier 2 (per-family bands) ────────────────────────────────────────
echo "==> Tier 2: per-clip per-family size bands"

band_for_prefix() {
    # Echoes "MIN_KB MAX_KB" for the given slot prefix.
    case "$1" in
        base) echo "200 600" ;;
        emotion) echo "300 900" ;;
        prep) echo "400 1200" ;;
        react) echo "400 1200" ;;
        *) return 1 ;;
    esac
}

stat_size() {
    if [[ "$(uname -s)" == "Darwin" ]]; then
        stat -f '%z' "$1"
    else
        stat -c '%s' "$1"
    fi
}

ANIM_DIR="${REPO_ROOT}/tauri/ui/assets/mascot/animations"
fail=0
found_any=0
shopt -s nullglob

for glb in "${ANIM_DIR}"/base_*.glb "${ANIM_DIR}"/emotion_*.glb "${ANIM_DIR}"/prep_*.glb "${ANIM_DIR}"/react_*.glb; do
    found_any=1
    name="$(basename "${glb}")"
    prefix="${name%%_*}"
    if ! band="$(band_for_prefix "${prefix}")"; then
        echo "  SKIP: ${name} (prefix '${prefix}' has no Phase 47 family band — out of scope)"
        continue
    fi
    read -r min_kb max_kb <<< "${band}"
    min_bytes=$(( min_kb * 1024 ))
    max_bytes=$(( max_kb * 1024 ))
    size=$(stat_size "${glb}")
    if (( size < min_bytes )) || (( size > max_bytes )); then
        echo "  FAIL: ${name} size ${size} bytes outside [${min_bytes},${max_bytes}] (${prefix} band ${min_kb}-${max_kb} KB)"
        fail=1
    else
        echo "  OK:   ${name} size ${size} bytes (${prefix} band ${min_kb}-${max_kb} KB)"
    fi
done

if (( found_any == 0 )); then
    echo "  WARN: no Phase 47 GLBs found in ${ANIM_DIR} — has §VIS-04 been discharged?"
    fail=2
fi

if (( fail != 0 )); then
    echo "==> Tier 2: FAIL"
    echo "Note: placeholder *.glb files legitimately fall outside the family bands"
    echo "      until KAAN-ACTION-LEGAL.md §VIS-04 discharge replaces them with"
    echo "      real Mixamo retargets."
    exit 2
fi
echo "==> Tier 2: OK"
exit 0
