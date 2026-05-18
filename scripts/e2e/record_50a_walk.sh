#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# Phase 50 / E2E — Screencast capture rig for 50a Kaan-walk.
#
# Engineering scaffolds the capture command; Kaan executes the recording
# at §E2E-50A-WALK discharge time. macOS-only per project constraints
# (Win 50a walk deferred).
#
# Usage:
#   bash scripts/e2e/record_50a_walk.sh
#   # ... walk through the 50a checklist while screencapture runs ...
#   # Press Esc / Ctrl-C in the screencapture window to stop.
#
#   bash scripts/e2e/record_50a_walk.sh --transcode raw.mov
#   # transcodes raw.mov to docs/e2e/2026-05-walk.webm with a budget < 25 MB

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${REPO_ROOT}/../docs/e2e"
OUT_WEBM="docs/e2e/2026-05-walk.webm"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "error: 50a screencast capture is macOS-only (project constraint)" >&2
  exit 1
fi

mode="${1:---record}"

case "${mode}" in
  --record)
    raw_path="$(pwd)/50a-raw-$(date -u +%Y-%m-%dT%H-%M-%SZ).mov"
    echo "==> Starting screencapture. Press Esc when done."
    echo "    Output (raw): ${raw_path}"
    echo
    # -v interactive video capture (10.5+); -a includes audio; -k stops on Esc.
    screencapture -v -a "${raw_path}"
    echo
    echo "==> Recording stopped. Raw file: ${raw_path}"
    echo
    echo "Next: transcode to .webm under the 25 MB budget:"
    echo "    bash scripts/e2e/record_50a_walk.sh --transcode ${raw_path}"
    ;;
  --transcode)
    src="${2:-}"
    if [[ -z "${src}" || ! -f "${src}" ]]; then
      echo "error: --transcode requires a .mov input path" >&2
      exit 1
    fi
    if ! command -v ffmpeg >/dev/null 2>&1; then
      echo "error: ffmpeg not in PATH (brew install ffmpeg)" >&2
      exit 1
    fi
    mkdir -p "$(dirname "${OUT_WEBM}")"
    # VP9 + 32k mono audio + crf 32 = ~ 18-24 MB for a 4-5 min clip.
    ffmpeg -y -i "${src}" \
      -c:v libvpx-vp9 -crf 32 -b:v 0 -row-mt 1 \
      -c:a libopus -b:a 32k -ac 1 \
      "${OUT_WEBM}"
    size_mb=$(du -m "${OUT_WEBM}" | awk '{print $1}')
    echo "==> Transcoded: ${OUT_WEBM} (${size_mb} MB)"
    if [[ "${size_mb}" -gt 25 ]]; then
      echo
      echo "warning: size > 25 MB. Either lower bitrate (re-run with --transcode-tight) "
      echo "or track via git-lfs: git lfs track 'docs/e2e/*.webm'" >&2
    fi
    echo
    echo "Commit:"
    echo "    git add ${OUT_WEBM} && git commit -m 'chore(e2e): land 50a Kaan-walk screencast'"
    ;;
  *)
    echo "usage: $0 [--record|--transcode <path>]"
    exit 1
    ;;
esac
