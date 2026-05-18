#!/usr/bin/env bash
# Phase 47 / MASCOT-06 — Persona smoke harness entry point.
#
# Runs the in-Tauri persona-smoke harness for 30s and captures the
# WebView output as docs/mascot/persona_smoke.webm.
#
# Platform behavior:
#   - Darwin (Mac): uses `cargo tauri dev -- --persona-smoke` to spawn the
#     harness; ffmpeg captures via avfoundation screen-record at 480p VP9.
#   - Linux (CI):   uses `xvfb-run` to provide a virtual display; ffmpeg
#     x11grab captures.
#
# Output:
#   docs/mascot/persona_smoke.webm — 30s @ 480p, VP9, ~800 kbps target,
#   < 5 MB (per Phase 47 / CONTEXT § Persona Smoke Script).
#
# NOT run on every PR — per CONTEXT, this runs as a weekly cron in CI plus
# manual workflow_dispatch on demand. vitest event-coverage-matrix is the
# per-PR gate; this is the visual-regression artifact.
#
# Exit codes:
#   0 — webm produced under 5 MB
#   1 — capture failed
#   2 — webm exceeds 5 MB size guard
#
# Run from repo root: bash scripts/mascot/persona_smoke.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
OUT_DIR="${REPO_ROOT}/docs/mascot"
OUT_FILE="${OUT_DIR}/persona_smoke.webm"
DURATION_SEC=30
SIZE_CAP_BYTES=$((5 * 1024 * 1024))

mkdir -p "${OUT_DIR}"

echo "==> Phase 47 / MASCOT-06 persona smoke"
echo "    output:   ${OUT_FILE}"
echo "    duration: ${DURATION_SEC}s"
echo "    size cap: ${SIZE_CAP_BYTES} bytes (5 MB)"

PLATFORM="$(uname -s)"

case "${PLATFORM}" in
    Darwin)
        echo "==> Platform: Darwin — using avfoundation screen-record"
        command -v ffmpeg >/dev/null 2>&1 || {
            echo "ERROR: ffmpeg required; install via brew install ffmpeg" >&2
            exit 1
        }
        echo "==> Manual step: in a separate terminal, run:"
        echo "      cd ${REPO_ROOT}/tauri && cargo tauri dev -- --persona-smoke"
        echo "==> Then ENTER to begin recording (waiting 5s for harness to render)..."
        sleep 5
        ffmpeg -y -hide_banner -f avfoundation -framerate 24 -i "1" \
            -t "${DURATION_SEC}" \
            -s 480x480 -c:v libvpx-vp9 -b:v 800k -an \
            "${OUT_FILE}"
        ;;
    Linux)
        echo "==> Platform: Linux — using xvfb-run + ffmpeg x11grab"
        command -v xvfb-run >/dev/null 2>&1 || {
            echo "ERROR: xvfb-run required; install via apt-get install xvfb" >&2
            exit 1
        }
        command -v ffmpeg >/dev/null 2>&1 || {
            echo "ERROR: ffmpeg required" >&2
            exit 1
        }
        xvfb-run -a -s "-screen 0 480x480x24" \
            bash -c "cd '${REPO_ROOT}/tauri' && cargo tauri dev -- --persona-smoke &
                     sleep 5
                     ffmpeg -y -hide_banner -f x11grab -framerate 24 -video_size 480x480 -i :99.0 \
                         -t '${DURATION_SEC}' -c:v libvpx-vp9 -b:v 800k -an '${OUT_FILE}'"
        ;;
    *)
        echo "ERROR: unsupported platform ${PLATFORM}" >&2
        exit 1
        ;;
esac

if [[ ! -f "${OUT_FILE}" ]]; then
    echo "ERROR: capture did not produce ${OUT_FILE}" >&2
    exit 1
fi

actual_bytes=$(stat -f '%z' "${OUT_FILE}" 2>/dev/null || stat -c '%s' "${OUT_FILE}")
if (( actual_bytes > SIZE_CAP_BYTES )); then
    echo "FAIL: ${OUT_FILE} is ${actual_bytes} bytes (> 5 MB cap)" >&2
    exit 2
fi

echo "==> OK: ${OUT_FILE} = ${actual_bytes} bytes"
