#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# Plan 42-03 / Task 3 — ear-test release gate.
#
# Contract (from D-GATE-05): accept iff
#   1. ≥ 2 ear-test sessions signed within the last 14 days
#   2. ≥ 2 distinct genres across those in-window sessions
#   3. zero slop_flags reported (no felt_slop / felt_scripted /
#      felt_late / felt_generic == true across the in-window set)
#
# Reads JSON log files matching `${EAR_TEST_DIR}/*.json` produced by
# the Phase 29 debrief window's ear-test toggle (Plan 42-03 Task 2 →
# Plan 42-03 Task 1 writer). Schema:
# `eval/ear-test-logs/schema.json`.
#
# Inputs (env):
#   EAR_TEST_DIR   default: eval/ear-test-logs
#   WINDOW_DAYS    default: 14
#
# Exit codes:
#   0  accept (all 3 invariants pass)
#   1  reject (any invariant tripped, or jq missing)
#
# Output:
#   stdout:  single PASS / FAIL summary line on success/reject
#   stderr:  per-invariant reject reasons; ::error:: lines when running
#            under GitHub Actions (`$GITHUB_ACTIONS == "true"`)

set -euo pipefail

EAR_TEST_DIR="${EAR_TEST_DIR:-eval/ear-test-logs}"
WINDOW_DAYS="${WINDOW_DAYS:-14}"
MIN_SESSIONS=2
MIN_GENRES=2

GHA_ANNOT="${GITHUB_ACTIONS:-false}"

# --- emit helper -----------------------------------------------------------
fail() {
  local msg="$1"
  if [ "${GHA_ANNOT}" = "true" ]; then
    echo "::error::check_ear_test: ${msg}" >&2
  else
    echo "FAIL check_ear_test: ${msg}" >&2
  fi
}

pass() {
  echo "PASS check_ear_test: $*"
}

# --- jq presence -----------------------------------------------------------
if ! command -v jq >/dev/null 2>&1; then
  fail "jq is required but not found on PATH — install jq and re-run"
  exit 1
fi

# --- dir presence ----------------------------------------------------------
if [ ! -d "${EAR_TEST_DIR}" ]; then
  fail "ear-test log dir missing: ${EAR_TEST_DIR}"
  exit 1
fi

# --- cutoff date (macOS vs GNU date branch) --------------------------------
# macOS BSD date uses `-v-${N}d`; GNU date uses `-d "-${N} days"`. Probe
# once per invocation. Output ISO 8601 UTC.
if date -u -v-1d +%Y-%m-%dT%H:%M:%SZ >/dev/null 2>&1; then
  CUTOFF=$(date -u -v-"${WINDOW_DAYS}"d +%Y-%m-%dT%H:%M:%SZ)
elif date -u -d "-${WINDOW_DAYS} days" +%Y-%m-%dT%H:%M:%SZ >/dev/null 2>&1; then
  CUTOFF=$(date -u -d "-${WINDOW_DAYS} days" +%Y-%m-%dT%H:%M:%SZ)
else
  fail "date binary supports neither BSD (-v) nor GNU (-d) date math"
  exit 1
fi

# --- enumerate logs --------------------------------------------------------
# Glob *.json but exclude the co-located schema.json (lives in the same
# dir as the audit-trail logs to keep the validation source-of-truth
# adjacent to the data).
shopt -s nullglob
LOGS=()
for f in "${EAR_TEST_DIR}"/*.json; do
  base=$(basename "$f")
  [ "$base" = "schema.json" ] && continue
  LOGS+=( "$f" )
done
shopt -u nullglob

if [ "${#LOGS[@]}" -eq 0 ]; then
  fail "no ear-test logs found under ${EAR_TEST_DIR} (need ≥ ${MIN_SESSIONS})"
  exit 1
fi

# --- per-log parse → TSV ---------------------------------------------------
# Each line: signed_at<TAB>genre<TAB>any_slop_true (true/false)
TSV=$(
  for log in "${LOGS[@]}"; do
    # jq extracts signed_at, genre, OR-reduction over slop_flags values.
    jq -r '[
      .signed_at,
      .genre,
      (.slop_flags | to_entries | map(.value) | any)
    ] | @tsv' "$log" 2>/dev/null || true
  done
)

if [ -z "${TSV}" ]; then
  fail "all ear-test logs failed to parse via jq under ${EAR_TEST_DIR}"
  exit 1
fi

# --- window filter ---------------------------------------------------------
# Keep only rows with signed_at >= CUTOFF (lexicographic ISO 8601 compare).
IN_WINDOW=$(
  echo "${TSV}" | awk -F'\t' -v cutoff="${CUTOFF}" '
    $1 >= cutoff { print $0 }
  '
)

if [ -z "${IN_WINDOW}" ]; then
  fail "fewer than ${MIN_SESSIONS} sessions in the last ${WINDOW_DAYS} days (cutoff=${CUTOFF})"
  exit 1
fi

# --- counts ----------------------------------------------------------------
SESSION_COUNT=$(echo "${IN_WINDOW}" | wc -l | tr -d ' ')
GENRE_COUNT=$(echo "${IN_WINDOW}" | awk -F'\t' '{print $2}' | sort -u | wc -l | tr -d ' ')
SLOP_FLAGGED=$(echo "${IN_WINDOW}" | awk -F'\t' '$3 == "true"' | wc -l | tr -d ' ')

REJECT=0

if [ "${SESSION_COUNT}" -lt "${MIN_SESSIONS}" ]; then
  fail "fewer than ${MIN_SESSIONS} sessions in window (have ${SESSION_COUNT})"
  REJECT=1
fi

if [ "${GENRE_COUNT}" -lt "${MIN_GENRES}" ]; then
  fail "fewer than ${MIN_GENRES} genres in window (have ${GENRE_COUNT})"
  REJECT=1
fi

if [ "${SLOP_FLAGGED}" -gt 0 ]; then
  fail "slop-flagged sessions in window: ${SLOP_FLAGGED}"
  REJECT=1
fi

if [ "${REJECT}" -ne 0 ]; then
  exit 1
fi

pass "${SESSION_COUNT} sessions across ${GENRE_COUNT} genres in last ${WINDOW_DAYS} days, 0 slop-flags"
exit 0
