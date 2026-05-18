#!/usr/bin/env bash
# Phase 47 / MASCOT-07 — Render README hero assets from react_hype_peak.glb.
#
# Output:
#   docs/assets/readme-hero.png — 480x480 PNG, < 50 KB after pngcrush
#   docs/assets/readme-hero.webm — 480x480 3s WebM VP9, < 100 KB
#
# Both rendered against opaque var(--void-2) = #05070b background per
# Phase 47 / UI-SPEC § Layout — README Hero Render.
#
# NOT a CI-blocking step. Manual command run by Kaan after §VIS-04
# discharge replaces real react_hype_peak.glb. Until then, placeholders
# (committed under the same path) keep the README embed working.
#
# Run from repo root: bash scripts/mascot/render_readme_hero.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
OUT_DIR="${REPO_ROOT}/docs/assets"
PNG="${OUT_DIR}/readme-hero.png"
WEBM="${OUT_DIR}/readme-hero.webm"
SOURCE="${REPO_ROOT}/tauri/ui/assets/mascot/animations/react_hype_peak.glb"

mkdir -p "${OUT_DIR}"

if [[ ! -f "${SOURCE}" ]]; then
    echo "ERROR: missing ${SOURCE} — run scripts/mascot/seed_phase_47_placeholders.py first" >&2
    exit 1
fi

SOURCE_BYTES=$(stat -f '%z' "${SOURCE}" 2>/dev/null || stat -c '%s' "${SOURCE}")
if (( SOURCE_BYTES < 400 * 1024 )); then
    echo "WARN: ${SOURCE} is a placeholder (${SOURCE_BYTES} bytes); rendering anyway, expect degenerate output"
    echo "      Real hero render lands after Kaan §VIS-04 discharge produces a 400-1200 KB reaction GLB."
fi

echo "==> Phase 47 / MASCOT-07 render README hero (void-2 #05070b background)"
echo "    source:   ${SOURCE} (${SOURCE_BYTES} bytes)"
echo "    out PNG:  ${PNG}"
echo "    out WebM: ${WEBM}"

PLATFORM="$(uname -s)"
case "${PLATFORM}" in
    Darwin)
        command -v ffmpeg >/dev/null 2>&1 || { echo "ERROR: ffmpeg required" >&2; exit 1; }
        echo "==> Manual step: in a separate terminal, run:"
        echo "      cd ${REPO_ROOT}/tauri && cargo tauri dev -- --readme-hero"
        echo "==> Then ENTER to begin recording..."
        sleep 5
        ffmpeg -y -hide_banner -f avfoundation -framerate 24 -i "1" \
            -t 3 -s 480x480 -c:v libvpx-vp9 -b:v 800k -an "${WEBM}"
        ffmpeg -y -hide_banner -i "${WEBM}" -ss 1.5 -frames:v 1 "${PNG}"
        ;;
    Linux)
        command -v xvfb-run >/dev/null 2>&1 || { echo "ERROR: xvfb-run required" >&2; exit 1; }
        command -v ffmpeg >/dev/null 2>&1 || { echo "ERROR: ffmpeg required" >&2; exit 1; }
        xvfb-run -a -s "-screen 0 480x480x24" \
            bash -c "cd '${REPO_ROOT}/tauri' && cargo tauri dev -- --readme-hero &
                     sleep 5
                     ffmpeg -y -hide_banner -f x11grab -framerate 24 -video_size 480x480 -i :99.0 \
                         -t 3 -c:v libvpx-vp9 -b:v 800k -an '${WEBM}'
                     ffmpeg -y -hide_banner -i '${WEBM}' -ss 1.5 -frames:v 1 '${PNG}'"
        ;;
    *)
        echo "ERROR: unsupported platform ${PLATFORM}" >&2
        exit 1
        ;;
esac

PNG_BYTES=$(stat -f '%z' "${PNG}" 2>/dev/null || stat -c '%s' "${PNG}")
WEBM_BYTES=$(stat -f '%z' "${WEBM}" 2>/dev/null || stat -c '%s' "${WEBM}")
if (( PNG_BYTES > 50 * 1024 )); then
    echo "WARN: ${PNG} = ${PNG_BYTES} bytes (>50 KB target); consider pngcrush --brute"
fi
if (( WEBM_BYTES > 100 * 1024 )); then
    echo "WARN: ${WEBM} = ${WEBM_BYTES} bytes (>100 KB target); reduce bitrate"
fi

echo "==> OK: hero assets rendered"
echo "    PNG  ${PNG_BYTES} bytes"
echo "    WebM ${WEBM_BYTES} bytes"
