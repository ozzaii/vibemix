#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# Phase 50 / E2E — bash test for Gate 6b runner check_e2e_report.sh.
#
# 4 cases:
#   (a) all-PASS report     → exit 0
#   (b) one-FAIL report     → exit 1
#   (c) no report.html      → exit 2
#   (d) mixed PASS/PARTIAL  → exit 0

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPT="${REPO_ROOT}/scripts/e2e/check_e2e_report.sh"

TMP_BASE="$(mktemp -d -t check_e2e_report_test_XXXXXX)"
trap 'rm -rf "${TMP_BASE}"' EXIT

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

pass() {
  echo "OK: $*"
}

# Build a synthetic report.html with the given dimension statuses.
# Args: out_path, Functional, Visual, Aesthetic, Usability, Hallucination
synth_report() {
  local out="$1"; shift
  local funcS="$1" visS="$2" aesS="$3" usaS="$4" halS="$5"
  mkdir -p "$(dirname "${out}")"
  cat > "${out}" <<EOF
<!doctype html><html><body>
<div class="row ${funcS}">
  <span class="label">Functional</span>
  <span class="status">${funcS}</span>
</div>
<div class="row ${visS}">
  <span class="label">Visual</span>
  <span class="status">${visS}</span>
</div>
<div class="row ${aesS}">
  <span class="label">Aesthetic</span>
  <span class="status">${aesS}</span>
</div>
<div class="row ${usaS}">
  <span class="label">Usability</span>
  <span class="status">${usaS}</span>
</div>
<div class="row ${halS}">
  <span class="label">Hallucination</span>
  <span class="status">${halS}</span>
</div>
</body></html>
EOF
}

# Case (a): all PASS → exit 0.
case_a="${TMP_BASE}/case-a/dist/e2e-macbook-runs"
synth_report "${case_a}/2026-05-18T10-00-00Z/report.html" PASS PASS PASS PASS PASS
if VIBEMIX_E2E_RUN_ROOT="${case_a}" bash "${SCRIPT}" >/dev/null 2>&1; then
  pass "case-a all-PASS → exit 0"
else
  fail "case-a all-PASS did not return 0 (got $?)"
fi

# Case (b): one FAIL → exit 1.
case_b="${TMP_BASE}/case-b/dist/e2e-macbook-runs"
synth_report "${case_b}/2026-05-18T10-00-00Z/report.html" PASS FAIL PASS PASS PASS
set +e
VIBEMIX_E2E_RUN_ROOT="${case_b}" bash "${SCRIPT}" >/dev/null 2>&1
b_rc=$?
set -e
if [[ "${b_rc}" -eq 1 ]]; then
  pass "case-b one-FAIL → exit 1"
else
  fail "case-b one-FAIL expected exit 1, got ${b_rc}"
fi

# Case (c): no report.html → exit 2.
case_c="${TMP_BASE}/case-c/dist/e2e-macbook-runs"
mkdir -p "${case_c}"
set +e
VIBEMIX_E2E_RUN_ROOT="${case_c}" bash "${SCRIPT}" >/dev/null 2>&1
c_rc=$?
set -e
if [[ "${c_rc}" -eq 2 ]]; then
  pass "case-c no-report → exit 2"
else
  fail "case-c expected exit 2, got ${c_rc}"
fi

# Case (d): mixed PASS/PARTIAL/SKIPPED → exit 0.
case_d="${TMP_BASE}/case-d/dist/e2e-macbook-runs"
synth_report "${case_d}/2026-05-18T10-00-00Z/report.html" PASS PARTIAL SKIPPED PASS PASS
if VIBEMIX_E2E_RUN_ROOT="${case_d}" bash "${SCRIPT}" >/dev/null 2>&1; then
  pass "case-d mixed PASS/PARTIAL/SKIPPED → exit 0"
else
  fail "case-d mixed did not return 0 (got $?)"
fi

echo
echo "all 4 test cases passed"
exit 0
