#!/usr/bin/env bash
# Phase 31 Plan 05 — v2.0 test name port-verbatim grep gate.
#
# Pitfall P47: the full 4-layer rewrite MUST preserve v2.0 test names
# verbatim so the rewrite-regression contract holds. This script greps
# for each load-bearing test name across the mascot test suite and
# fails CI if any are missing.
#
# Test names (from PITFALLS.md P47 evidence anchors):
#   - test_anticipation_priority_70_preserved
#   - test_2_5s_timeout_crossfades_to_settle
#   - test_speech_interrupt_force_true_crossfades_to_settle
#   - test_total_strip_crossfades_to_settle_then_ack_only
#
# Run from repo root: ./scripts/grep_v2_test_names.sh
set -euo pipefail

# Resolve the repo root regardless of where the script is invoked from.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

MASCOT_TESTS_DIR="${REPO_ROOT}/tauri/ui/src/mascot/__tests__"

if [[ ! -d "${MASCOT_TESTS_DIR}" ]]; then
  echo "FAIL: ${MASCOT_TESTS_DIR} missing" >&2
  exit 1
fi

REQUIRED_NAMES=(
  "test_anticipation_priority_70_preserved"
  "test_2_5s_timeout_crossfades_to_settle"
  "test_speech_interrupt_force_true_crossfades_to_settle"
  "test_total_strip_crossfades_to_settle_then_ack_only"
)

FAIL=0
for name in "${REQUIRED_NAMES[@]}"; do
  if ! grep -rq -- "${name}" "${MASCOT_TESTS_DIR}"; then
    echo "FAIL: missing v2.0 test name '${name}' under ${MASCOT_TESTS_DIR}" >&2
    FAIL=1
  fi
done

if [[ "${FAIL}" -ne 0 ]]; then
  echo "Pitfall P47 grep gate failed — see entries above." >&2
  exit 1
fi

echo "OK: all 4 v2.0 mascot test names present under ${MASCOT_TESTS_DIR}"
