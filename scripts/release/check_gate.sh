#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# Plan 42-04 / Task 1 — hybrid hallucination release gate.
#
# Per CONTEXT D-GATE-06 — this is the SHIP-CUT gate-2 implementation.
# It combines THREE inputs and passes iff ALL are green:
#
#   1. Last 7 nightly autonomous-proxy scorecards (.planning/eval-runs/)
#      all report:
#        - f1            >= f1_min            (THRESHOLD-LOCK.md)
#        - useful_resp.. >= substance_min     (THRESHOLD-LOCK.md)
#        - cited_cosine  >= cited_cosine_min  (THRESHOLD-LOCK.md)
#        - bypass_rate   <= bypass_max        (THRESHOLD-LOCK.md)
#
#   2. Last 7 INTEL fixture gate artifacts (.planning/eval-runs/*/intel_gate.json)
#      all report `.valid == true` and include rich scorecard evidence:
#        - schema == intel_gate_v1
#        - fixture audit, scorecard, and provenance stages green
#        - non-empty metrics, gates, and artifact_status
#        - every gate reports PASS
#        - every artifact_status entry is true
#        - fixture/threshold provenance hashes and replay tier are present
#        - artifact fixture-manifest hash matches the current fixture corpus
#        - fixture-audit manifest hash agrees with scorecard provenance
#        - artifact thresholds hash matches current INTEL lock values
#        - artifact threshold-lock hash matches the current INTEL lock
#
#   3. scripts/release/check_ear_test.sh exits 0 (≥2 ear-test sessions
#      ≥2 genres within 14d, zero slop flags).
#
# Exits 0 only when ALL gates pass; otherwise exits 1 with a structured
# stderr message naming each tripped input as `BLOCKED_BY=nightly`,
# `BLOCKED_BY=intel`, and/or `BLOCKED_BY=ear-test`. Under GitHub Actions
# (GITHUB_ACTIONS=true) the failures also surface as ::error:: annotations
# (mirrors the check_no_hardcoded_model.sh / check_ear_test.sh pattern).
#
# Inputs (env, with defaults):
#   EVAL_RUNS_DIR          default: .planning/eval-runs
#   THRESHOLD_LOCK         default: eval/THRESHOLD-LOCK.md
#   INTEL_THRESHOLD_LOCK   default: eval/INTEL-THRESHOLD-LOCK.md
#   INTEL_FIXTURE_MANIFEST default: tests/intel/fixtures/MANIFEST.json
#   EAR_TEST_GATE          default: scripts/release/check_ear_test.sh
#   MIN_CONSECUTIVE_GREEN  default: 7
#
# Non-zero from the ear-test gate propagates verbatim; we do not re-parse
# its internal failure reason.
#
# Threat-model note (T-42-04-01): scorecard/gate JSON is untrusted (committed
# by nightly canary CI). All field extraction goes through jq — never via
# shell `eval` or `$(...)` substitution of report values.

set -euo pipefail

EVAL_RUNS_DIR="${EVAL_RUNS_DIR:-.planning/eval-runs}"
THRESHOLD_LOCK="${THRESHOLD_LOCK:-eval/THRESHOLD-LOCK.md}"
INTEL_THRESHOLD_LOCK="${INTEL_THRESHOLD_LOCK:-eval/INTEL-THRESHOLD-LOCK.md}"
INTEL_FIXTURE_MANIFEST="${INTEL_FIXTURE_MANIFEST:-tests/intel/fixtures/MANIFEST.json}"
EAR_TEST_GATE="${EAR_TEST_GATE:-scripts/release/check_ear_test.sh}"
MIN_CONSECUTIVE_GREEN="${MIN_CONSECUTIVE_GREEN:-7}"

GHA_ANNOT="${GITHUB_ACTIONS:-false}"

BLOCKERS=()

# --- emit helpers ----------------------------------------------------------
emit_err() {
  local msg="$1"
  if [ "${GHA_ANNOT}" = "true" ]; then
    echo "::error::check_gate: ${msg}" >&2
  else
    echo "FAIL check_gate: ${msg}" >&2
  fi
}

# --- jq presence -----------------------------------------------------------
if ! command -v jq >/dev/null 2>&1; then
  emit_err "jq is required but not found on PATH — install jq and re-run"
  exit 1
fi

# --- python presence (for threshold parsing) ------------------------------
# We use a tiny python one-liner via the project's threshold_lock parser
# to extract locked values. PYTHON env override supported for hermetic
# CI; falls back to python3.
PYTHON_BIN="${PYTHON:-python3}"
if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  emit_err "${PYTHON_BIN} is required but not found on PATH — set PYTHON or install python3"
  exit 1
fi

# --- threshold lock presence ----------------------------------------------
if [ ! -f "${THRESHOLD_LOCK}" ]; then
  emit_err "THRESHOLD-LOCK missing: ${THRESHOLD_LOCK}"
  exit 1
fi
if [ ! -f "${INTEL_THRESHOLD_LOCK}" ]; then
  emit_err "INTEL-THRESHOLD-LOCK missing: ${INTEL_THRESHOLD_LOCK}"
  exit 1
fi
if [ ! -f "${INTEL_FIXTURE_MANIFEST}" ]; then
  emit_err "INTEL fixture manifest missing: ${INTEL_FIXTURE_MANIFEST}"
  exit 1
fi

# --- parse locked thresholds ----------------------------------------------
# Single python invocation extracts the 4 metric thresholds, emits as
# TAB-separated string for shell consumption. Falls through `set -e` if
# the parser errors. The parser uses yaml.safe_load (V5 ASVS).
TL_LINE=$(
  "${PYTHON_BIN}" - "${THRESHOLD_LOCK}" <<'PY'
import sys
from pathlib import Path

from scripts.eval.threshold_lock import parse_threshold_lock_frontmatter

parsed = parse_threshold_lock_frontmatter(Path(sys.argv[1]))
th = parsed.get("thresholds", {})
print(
    "{f1}\t{sub}\t{cit}\t{byp}".format(
        f1=th.get("f1_min", 0.0),
        sub=th.get("substance_min", 0.0),
        cit=th.get("cited_cosine_min", 0.0),
        byp=th.get("bypass_max", 1.0),
    )
)
PY
)

F1_MIN=$(echo "${TL_LINE}" | awk -F'\t' '{print $1}')
SUB_MIN=$(echo "${TL_LINE}" | awk -F'\t' '{print $2}')
CIT_MIN=$(echo "${TL_LINE}" | awk -F'\t' '{print $3}')
BYP_MAX=$(echo "${TL_LINE}" | awk -F'\t' '{print $4}')

if [ -z "${F1_MIN}" ] || [ -z "${SUB_MIN}" ] || [ -z "${CIT_MIN}" ] || [ -z "${BYP_MAX}" ]; then
  emit_err "threshold-lock parse returned empty values (line=${TL_LINE!r})"
  exit 1
fi

INTEL_THRESHOLD_LOCK_HASH=$(
  "${PYTHON_BIN}" - "${INTEL_THRESHOLD_LOCK}" <<'PY'
import hashlib
import sys
from pathlib import Path

print("sha256:" + hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest())
PY
)
INTEL_THRESHOLDS_HASH=$(
  "${PYTHON_BIN}" - "${INTEL_THRESHOLD_LOCK}" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

from scripts.eval.intel_scorecard import load_intel_thresholds_from_lock

thresholds = load_intel_thresholds_from_lock(Path(sys.argv[1]))
blob = json.dumps(thresholds, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
print("sha256:" + hashlib.sha256(blob).hexdigest())
PY
)
INTEL_FIXTURE_MANIFEST_HASH=$(
  "${PYTHON_BIN}" - "${INTEL_FIXTURE_MANIFEST}" <<'PY'
import hashlib
import sys
from pathlib import Path

print("sha256:" + hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest())
PY
)

# --- enumerate nightly runs -----------------------------------------------
NIGHTLY_FAIL_REASONS=()
INTEL_FAIL_REASONS=()

if [ ! -d "${EVAL_RUNS_DIR}" ]; then
  BLOCKERS+=("BLOCKED_BY=nightly: eval-runs dir missing: ${EVAL_RUNS_DIR}")
else
  # Direct-children only (T-42-04-02: no recursive descent, no symlink
  # traversal of nested paths). `ls -1dt */` rejects path traversal by
  # construction since it operates on glob-expanded direct entries.
  shopt -s nullglob
  RUN_DIRS=()
  while IFS= read -r d; do
    RUN_DIRS+=( "$d" )
  done < <(
    cd "${EVAL_RUNS_DIR}" 2>/dev/null \
      && find . -maxdepth 1 -mindepth 1 -type d -print0 2>/dev/null \
      | xargs -0 -I{} stat -f '%m %N' {} 2>/dev/null \
      | sort -rn \
      | awk '{ $1=""; sub(/^[ \t]+/, ""); sub(/^\.\//, ""); print }'
  )
  shopt -u nullglob

  TOTAL_DIRS=${#RUN_DIRS[@]}

  if [ "${TOTAL_DIRS}" -lt "${MIN_CONSECUTIVE_GREEN}" ]; then
    BLOCKERS+=("BLOCKED_BY=nightly: only ${TOTAL_DIRS} consecutive nightly runs (need ${MIN_CONSECUTIVE_GREEN})")
  else
    # Slice to the most-recent MIN_CONSECUTIVE_GREEN.
    CHECKED=0
    for name in "${RUN_DIRS[@]}"; do
      if [ "${CHECKED}" -ge "${MIN_CONSECUTIVE_GREEN}" ]; then
        break
      fi
      CHECKED=$((CHECKED + 1))

      run_path="${EVAL_RUNS_DIR}/${name}"
      report="${run_path}/eval_report.json"
      if [ ! -f "${report}" ]; then
        NIGHTLY_FAIL_REASONS+=("${name}: eval_report.json missing")
        continue
      fi

      intel_report="${run_path}/intel_gate.json"
      if [ ! -f "${intel_report}" ]; then
        INTEL_FAIL_REASONS+=("${name}: intel_gate.json missing")
      else
        intel_status=$(jq -r \
          --arg expected_intel_lock_hash "${INTEL_THRESHOLD_LOCK_HASH}" \
          --arg expected_intel_thresholds_hash "${INTEL_THRESHOLDS_HASH}" \
          --arg expected_fixture_manifest_hash "${INTEL_FIXTURE_MANIFEST_HASH}" '
          def nonempty_object(x): (x | type == "object" and length > 0);
          def nonempty_array(x): (x | type == "array" and length > 0);
          def sha256_hash(x): (x | type == "string" and startswith("sha256:"));

          if .schema != "intel_gate_v1" then
            "schema=\(.schema // "missing")"
          elif .valid != true then
            "valid=\(.valid // false)"
          elif .stages.fixture_audit.valid != true then
            "fixture_audit.valid=\(.stages.fixture_audit.valid // false)"
          elif .stages.scorecard.valid != true then
            "scorecard.valid=\(.stages.scorecard.valid // false)"
          elif .stages.scorecard.passed != true then
            "scorecard.passed=\(.stages.scorecard.passed // false)"
          elif .stages.provenance.valid != true then
            "provenance.valid=\(.stages.provenance.valid // false)"
          elif (nonempty_object(.stages.scorecard.metrics // {}) | not) then
            "scorecard.metrics missing"
          elif (nonempty_array(.stages.scorecard.gates // []) | not) then
            "scorecard.gates missing"
          elif ([.stages.scorecard.gates[]? | select(.status != "PASS")] | length) > 0 then
            "scorecard.gates contain non-PASS"
          elif (nonempty_object(.stages.scorecard.artifact_status // {}) | not) then
            "scorecard.artifact_status missing"
          elif ([.stages.scorecard.artifact_status | to_entries[]? | select(.value != true)] | length) > 0 then
            "scorecard.artifact_status contains false"
          elif .stages.scorecard.provenance.replay_tier != "tier0_fixture_replay" then
            "scorecard.provenance.replay_tier=\(.stages.scorecard.provenance.replay_tier // "missing")"
          elif (sha256_hash(.stages.scorecard.provenance.fixture_manifest_hash // "") | not) then
            "scorecard.provenance.fixture_manifest_hash missing"
          elif .stages.scorecard.provenance.fixture_manifest_hash != $expected_fixture_manifest_hash then
            "scorecard.provenance.fixture_manifest_hash mismatch"
          elif (sha256_hash(.stages.fixture_audit.manifest_hash // "") | not) then
            "fixture_audit.manifest_hash missing"
          elif .stages.fixture_audit.manifest_hash != $expected_fixture_manifest_hash then
            "fixture_audit.manifest_hash mismatch"
          elif .stages.fixture_audit.manifest_hash != .stages.scorecard.provenance.fixture_manifest_hash then
            "fixture_audit.manifest_hash disagrees with scorecard provenance"
          elif (sha256_hash(.stages.scorecard.provenance.thresholds_hash // "") | not) then
            "scorecard.provenance.thresholds_hash missing"
          elif .stages.scorecard.provenance.thresholds_hash != $expected_intel_thresholds_hash then
            "scorecard.provenance.thresholds_hash mismatch"
          elif (sha256_hash(.stages.scorecard.provenance.threshold_lock_hash // "") | not) then
            "scorecard.provenance.threshold_lock_hash missing"
          elif .stages.scorecard.provenance.threshold_lock_hash != $expected_intel_lock_hash then
            "scorecard.provenance.threshold_lock_hash mismatch"
          else
            "ok"
          end
        ' "${intel_report}" 2>/dev/null || echo "parse_error")
        if [ "${intel_status}" != "ok" ]; then
          INTEL_FAIL_REASONS+=("${name}: intel_gate.json ${intel_status}")
        fi
      fi

      # Single jq invocation extracts the 4 aggregate metrics. The
      # scorecard.py renderer (Phase 27-01) writes them under .overall.
      # jq is parse-only; values flow into shell via plain strings,
      # never via eval/source.
      vals=$(jq -r '
        [ (.overall.f1 // 0),
          (.overall.useful_response_ratio // 0),
          (.overall.cited_cosine // 0),
          (.overall.bypass_rate // 1)
        ] | @tsv
      ' "${report}" 2>/dev/null || echo "")

      if [ -z "${vals}" ]; then
        NIGHTLY_FAIL_REASONS+=("${name}: eval_report.json failed to parse")
        continue
      fi

      f1=$(echo "${vals}"     | awk -F'\t' '{print $1}')
      sub=$(echo "${vals}"    | awk -F'\t' '{print $2}')
      cit=$(echo "${vals}"    | awk -F'\t' '{print $3}')
      byp=$(echo "${vals}"    | awk -F'\t' '{print $4}')

      # Float compare via awk (bash arithmetic is integer-only).
      f1_ok=$(awk -v a="${f1}"   -v b="${F1_MIN}"  'BEGIN { print (a+0 >= b+0) ? "1" : "0" }')
      sub_ok=$(awk -v a="${sub}" -v b="${SUB_MIN}" 'BEGIN { print (a+0 >= b+0) ? "1" : "0" }')
      cit_ok=$(awk -v a="${cit}" -v b="${CIT_MIN}" 'BEGIN { print (a+0 >= b+0) ? "1" : "0" }')
      byp_ok=$(awk -v a="${byp}" -v b="${BYP_MAX}" 'BEGIN { print (a+0 <= b+0) ? "1" : "0" }')

      if [ "${f1_ok}" != "1" ]; then
        NIGHTLY_FAIL_REASONS+=("${name}: f1=${f1} < lock=${F1_MIN}")
      fi
      if [ "${sub_ok}" != "1" ]; then
        NIGHTLY_FAIL_REASONS+=("${name}: substance=${sub} < lock=${SUB_MIN}")
      fi
      if [ "${cit_ok}" != "1" ]; then
        NIGHTLY_FAIL_REASONS+=("${name}: cited_cosine=${cit} < lock=${CIT_MIN}")
      fi
      if [ "${byp_ok}" != "1" ]; then
        NIGHTLY_FAIL_REASONS+=("${name}: bypass=${byp} > lock=${BYP_MAX}")
      fi
    done

    if [ "${#NIGHTLY_FAIL_REASONS[@]}" -gt 0 ]; then
      for r in "${NIGHTLY_FAIL_REASONS[@]}"; do
        BLOCKERS+=("BLOCKED_BY=nightly: ${r}")
      done
    fi
    if [ "${#INTEL_FAIL_REASONS[@]}" -gt 0 ]; then
      for r in "${INTEL_FAIL_REASONS[@]}"; do
        BLOCKERS+=("BLOCKED_BY=intel: ${r}")
      done
    fi
  fi
fi

# --- ear-test gate --------------------------------------------------------
EAR_TEST_FAILED=0
if [ ! -f "${EAR_TEST_GATE}" ]; then
  BLOCKERS+=("BLOCKED_BY=ear-test: gate script missing: ${EAR_TEST_GATE}")
  EAR_TEST_FAILED=1
else
  # Bash invocation; suppress the gate's own stdout/stderr (we surface a
  # consolidated stderr line). The user can re-run check_ear_test.sh
  # directly for verbose output.
  if bash "${EAR_TEST_GATE}" >/dev/null 2>&1; then
    : # green
  else
    BLOCKERS+=("BLOCKED_BY=ear-test: ${EAR_TEST_GATE} exited non-zero (re-run for detail)")
    EAR_TEST_FAILED=1
  fi
fi

# --- verdict --------------------------------------------------------------
if [ "${#BLOCKERS[@]}" -eq 0 ]; then
  echo "PASS check_gate: ${MIN_CONSECUTIVE_GREEN}/${MIN_CONSECUTIVE_GREEN} nightly green + INTEL green + ear-test green"
  exit 0
fi

# Emit each blocker on its own stderr line (and as GHA annotation when
# applicable). Caller can `grep BLOCKED_BY=` to extract a structured
# machine-readable list.
echo "FAIL check_gate:" >&2
for b in "${BLOCKERS[@]}"; do
  emit_err "${b}"
done
exit 1
