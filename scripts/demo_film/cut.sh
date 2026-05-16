#!/usr/bin/env bash
# Phase 35 Plan 35-02 — Demo film manual cut driver.
#
# Reads scripts/demo_film/cuts.json. Per cut: ffmpeg slice. Concat all
# cuts to docs/assets/demo.mp4.
#
# Pitfall P57: cuts.length MUST be <= 8. NO auto-pacing, NO AI-suggested
# cuts. Human-only editing.
#
# Pitfall P58: vo_track must be a Kaan/Francesco-recorded path OR null.
# AI-VO services are forbidden — enforced separately by
# tests/scripts/test_demo_film_no_ai_vo.py grep gate.
#
# Usage:
#   bash scripts/demo_film/cut.sh           # real run
#   bash scripts/demo_film/cut.sh --dry-run # print ffmpeg commands only
#
# Requires: jq, ffmpeg on PATH.
#
# Exit codes:
#   0 = OK
#   1 = budget / schema violation OR cut count > max
#   2 = missing tool (jq or ffmpeg)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
CUTS_JSON="${CUTS_JSON_OVERRIDE:-${SCRIPT_DIR}/cuts.json}"
DRY_RUN=0

for arg in "$@"; do
  case "${arg}" in
    --dry-run) DRY_RUN=1 ;;
    --help|-h)
      sed -n '1,30p' "${BASH_SOURCE[0]}" | grep -E '^#'
      exit 0
      ;;
  esac
done

# --- Tool checks ---
if ! command -v jq >/dev/null 2>&1; then
  echo "FAIL: jq not on PATH. Install: brew install jq" >&2
  exit 2
fi

if [[ "${DRY_RUN}" -eq 0 ]] && ! command -v ffmpeg >/dev/null 2>&1; then
  echo "FAIL: ffmpeg not on PATH. Install: brew install ffmpeg" >&2
  exit 2
fi

if [[ ! -f "${CUTS_JSON}" ]]; then
  echo "FAIL: cuts.json not found at ${CUTS_JSON}" >&2
  exit 1
fi

# --- Parse + validate ---
CUT_COUNT=$(jq '.cuts | length' "${CUTS_JSON}")
MAX_CUTS=$(jq '.max_cuts // 8' "${CUTS_JSON}")

# Pitfall P57 hard ceiling. The doctrine constant is 8 — we enforce
# min(max_cuts_from_json, 8) so the JSON can't relax the gate.
HARD_CEILING=8
if [[ "${MAX_CUTS}" -gt "${HARD_CEILING}" ]]; then
  MAX_CUTS="${HARD_CEILING}"
fi

if [[ "${CUT_COUNT}" -gt "${MAX_CUTS}" ]]; then
  echo "FAIL: cut count ${CUT_COUNT} exceeds max ${MAX_CUTS} (Pitfall P57 — no AI auto-pacing)" >&2
  exit 1
fi

if [[ "${CUT_COUNT}" -eq 0 ]]; then
  echo "OK: cuts.json has 0 cuts — nothing to do (template state). Add cuts then re-run."
  exit 0
fi

# vo_track sanity — if non-null, must be a real path (not a URL to an AI
# TTS endpoint). Grep gate (test_demo_film_no_ai_vo.py) is the real
# enforcement; this is a belt-and-braces local check.
VO_TRACK=$(jq -r '.vo_track // "null"' "${CUTS_JSON}")
if [[ "${VO_TRACK}" != "null" ]]; then
  case "${VO_TRACK}" in
    *elevenlabs*|*openai*|*gemini-tts*|*tts.googleapis*|*synth.voice*|*ai-voiceover*)
      echo "FAIL: vo_track points at an AI-VO service: ${VO_TRACK} (Pitfall P58)" >&2
      exit 1
      ;;
  esac
fi

SOURCE_REL=$(jq -r '.source' "${CUTS_JSON}")
SOURCE_ABS="${SCRIPT_DIR}/${SOURCE_REL}"
OUTPUT_REL=$(jq -r '.output' "${CUTS_JSON}")
OUTPUT_ABS="${REPO_ROOT}/${OUTPUT_REL}"

if [[ "${DRY_RUN}" -eq 0 ]] && [[ ! -f "${SOURCE_ABS}" ]]; then
  echo "FAIL: source file not found: ${SOURCE_ABS}" >&2
  echo "  (real-run requires source. Use --dry-run to validate schema only.)" >&2
  exit 1
fi

# --- Per-cut slicing ---
WORK_DIR="${SCRIPT_DIR}/.work"
if [[ "${DRY_RUN}" -eq 0 ]]; then
  rm -rf "${WORK_DIR}"
  mkdir -p "${WORK_DIR}"
  mkdir -p "$(dirname "${OUTPUT_ABS}")"
fi

CONCAT_LIST="${WORK_DIR}/concat.txt"
if [[ "${DRY_RUN}" -eq 0 ]]; then
  : > "${CONCAT_LIST}"
fi

for i in $(seq 0 $((CUT_COUNT - 1))); do
  START=$(jq -r ".cuts[${i}].start" "${CUTS_JSON}")
  END=$(jq -r ".cuts[${i}].end" "${CUTS_JSON}")
  ID=$(jq -r ".cuts[${i}].id // \"cut_${i}\"" "${CUTS_JSON}")
  OUT="${WORK_DIR}/$(printf 'cut_%02d.mp4' "${i}")"
  CMD=(
    ffmpeg -hide_banner -loglevel error -y
    -ss "${START}" -to "${END}" -i "${SOURCE_ABS}"
    -c:v libx264 -preset medium -crf 18
    -c:a aac -b:a 192k
    "${OUT}"
  )
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    echo "[dry-run cut ${i} (${ID})] ${CMD[*]}"
  else
    echo "-> cut ${i} (${ID}): ${START} -> ${END}"
    "${CMD[@]}"
    echo "file '${OUT}'" >> "${CONCAT_LIST}"
  fi
done

# --- Concat ---
CONCAT_CMD=(
  ffmpeg -hide_banner -loglevel error -y
  -f concat -safe 0 -i "${CONCAT_LIST}"
  -c copy
  "${OUTPUT_ABS}"
)
if [[ "${DRY_RUN}" -eq 1 ]]; then
  echo "[dry-run concat] ${CONCAT_CMD[*]}"
  echo "OK: dry-run complete. ${CUT_COUNT} cut(s), max ${MAX_CUTS}."
  exit 0
fi

echo "-> concat -> ${OUTPUT_ABS}"
"${CONCAT_CMD[@]}"

# --- VO mux (optional) ---
if [[ "${VO_TRACK}" != "null" ]]; then
  VO_ABS="${SCRIPT_DIR}/${VO_TRACK}"
  if [[ ! -f "${VO_ABS}" ]]; then
    echo "WARN: vo_track set but file missing: ${VO_ABS} — skipping VO mux" >&2
  else
    MUXED="${OUTPUT_ABS%.*}.muxed.mp4"
    ffmpeg -hide_banner -loglevel error -y \
      -i "${OUTPUT_ABS}" -i "${VO_ABS}" \
      -c:v copy -c:a aac -b:a 192k -shortest \
      "${MUXED}"
    mv "${MUXED}" "${OUTPUT_ABS}"
    echo "-> muxed VO from ${VO_TRACK}"
  fi
fi

echo "OK: ${OUTPUT_ABS} produced (${CUT_COUNT} cut(s) / max ${MAX_CUTS})."
