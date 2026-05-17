#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# scripts/launch/cut_release.sh — vibemix Public RC pre-flight cutter
#
# Phase 39 / SHIP-01 / SHIP-06 / P83.
#
# This script is PRE-FLIGHT ONLY. It validates that a release is safe to cut
# but NEVER calls `gh release create`. The final `gh release create`
# invocation is a Kaan-action (see KAAN-ACTION-LEGAL.md §SHIP-CUT).
#
# Pre-flight gates (ALL must pass):
#   1.  Tag prefix regex `^v2\.1\.0-rc[0-9]+$` (P83 — no premature v1.0.0).
#   2.  `verify_signed.py --require-signed` for every dist/*.{dmg,msi,exe,pkg}.
#   2b. `check_gate.sh` — Phase 42 hybrid hallucination gate (GATE-06).
#   3.  `pytest tests/repo/test_readme_hero_hash_sync.py` (Phase 35).
#   4.  `.planning/v2.1-MILESTONE-AUDIT.md` exists + frontmatter verdict WIRED.
#   5.  `pytest tests/repo/test_g5_poc_files_untouched.py` (Phase 37 / AUDIT-06).
#   5b. `check_bravoh_server_ready.sh` — 3-endpoint Bravoh server probe
#       (Plan 45-03 / SHIP-06 / OPS-14).
#   6.  `pytest tests/security/test_bundle_id_locked.py` (Phase 33 / P63).
#
# Usage:
#   bash scripts/launch/cut_release.sh v2.1.0-rc1
#
# Output on PASS: prints the exact `gh release create` command Kaan should
# run; does NOT execute it. Confirms the Phase 42 hybrid hallucination
# gate (GATE-06) is green — supersedes the v2.1 P85 override regime
# (the autonomous-only ear-test bypass is formally retired in Plan 42-05).
#
# HARD GUARD: even with `--really` / `--real`, this script NEVER invokes
# `gh release create` autonomously. That's the load-bearing safety property.

set -u

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <tag>  (e.g. $0 v2.1.0-rc1)" >&2
  exit 1
fi

TAG="$1"
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PYTHON="${PYTHON:-python3}"
TAG_REGEX='^v2\.1\.0-rc[0-9]+$'

FAIL=0
TRIPPED=()

pass()  { echo "  PASS  $*"; }
fail()  { echo "  FAIL  $*" >&2; FAIL=1; TRIPPED+=("$*"); }
info()  { echo "  --    $*"; }

echo "═════════════════════════════════════════════════════════"
echo "  vibemix — cut_release.sh pre-flight (Phase 39 / SHIP-01)"
echo "  Tag:    ${TAG}"
echo "  Repo:   ${REPO_ROOT}"
echo "═════════════════════════════════════════════════════════"
echo

# ── Gate 1: tag prefix ─────────────────────────────────────────────────
echo "[Gate 1] Tag prefix matches ${TAG_REGEX} (P83)"
if [[ "${TAG}" =~ ${TAG_REGEX} ]]; then
  pass "${TAG} matches ${TAG_REGEX}"
else
  fail "${TAG} does NOT match ${TAG_REGEX} — refusing to cut (P83 — no premature v1.0.0)"
fi
echo

# ── Gate 2: signed binaries in dist/ ───────────────────────────────────
echo "[Gate 2] verify_signed.py --require-signed for every dist artifact"
DIST_DIR="${REPO_ROOT}/dist"
if [[ ! -d "${DIST_DIR}" ]]; then
  fail "dist/ directory missing — build artifacts before cutting"
else
  shopt -s nullglob
  ARTIFACTS=( "${DIST_DIR}"/*.dmg "${DIST_DIR}"/*.pkg "${DIST_DIR}"/*.msi "${DIST_DIR}"/*.exe )
  shopt -u nullglob
  if [[ ${#ARTIFACTS[@]} -eq 0 ]]; then
    fail "no .dmg/.pkg/.msi/.exe artifacts in dist/ — sign + drop them before cutting"
  else
    for art in "${ARTIFACTS[@]}"; do
      if "${PYTHON}" "${REPO_ROOT}/scripts/dist/verify_signed.py" --artifact "${art}" --require-signed >/dev/null 2>&1; then
        pass "signed: $(basename "${art}")"
      else
        fail "unsigned (or verifier blocked): $(basename "${art}")"
      fi
    done
  fi
fi
echo

# ── Gate 2b: hybrid hallucination gate (Phase 42 / GATE-06) ────────────
echo "[Gate 2b] check_gate.sh — 7-day nightly proxy + ear-test (Phase 42)"
if bash "${REPO_ROOT}/scripts/release/check_gate.sh" >/dev/null 2>&1; then
  pass "check_gate.sh — hybrid gate green"
else
  fail "check_gate.sh — hybrid gate FAILED (nightly proxy and/or ear-test). Run 'bash ${REPO_ROOT}/scripts/release/check_gate.sh' for the structured blocker."
fi
echo

# ── Gate 3: README hero hash sync ──────────────────────────────────────
echo "[Gate 3] README hero hash sync (Phase 35)"
if ${PYTHON} -m pytest "${REPO_ROOT}/tests/repo/test_readme_hero_hash_sync.py" -q --no-header >/dev/null 2>&1; then
  pass "tests/repo/test_readme_hero_hash_sync.py"
else
  fail "tests/repo/test_readme_hero_hash_sync.py — hero asset drift detected"
fi
echo

# ── Gate 4: milestone audit ────────────────────────────────────────────
echo "[Gate 4] .planning/v2.1-MILESTONE-AUDIT.md exists + verdict WIRED (Phase 37)"
AUDIT="${REPO_ROOT}/.planning/v2.1-MILESTONE-AUDIT.md"
if [[ ! -f "${AUDIT}" ]]; then
  fail ".planning/v2.1-MILESTONE-AUDIT.md missing — run scripts/integration_audit.py --write-milestone-audit"
else
  # Frontmatter convention: overall_verdict: WIRED  (or status: passed for back-compat).
  if grep -E '^(overall_verdict|status):\s*(WIRED|passed)\s*$' "${AUDIT}" >/dev/null 2>&1; then
    pass "milestone audit present, verdict WIRED"
  else
    fail "milestone audit present but verdict is not WIRED/passed"
  fi
fi
echo

# ── Gate 5: POC files untouched ────────────────────────────────────────
echo "[Gate 5] POC files untouched since v2.0 (AUDIT-06 / P85)"
if ${PYTHON} -m pytest "${REPO_ROOT}/tests/repo/test_g5_poc_files_untouched.py" -q --no-header >/dev/null 2>&1; then
  pass "tests/repo/test_g5_poc_files_untouched.py"
else
  fail "tests/repo/test_g5_poc_files_untouched.py — POC drift detected"
fi
echo

# ── Gate 5b: Bravoh server ready (Plan 45-03 / SHIP-06 / OPS-14) ───────
echo "[Gate 5b] check_bravoh_server_ready.sh — 3-endpoint probe + healthz freshness (Plan 45-03)"
if bash "${REPO_ROOT}/scripts/release/check_bravoh_server_ready.sh" --quiet >/dev/null 2>&1; then
  pass "check_bravoh_server_ready.sh — 3/3 endpoints OK + healthz fresh"
else
  fail "check_bravoh_server_ready.sh — Bravoh server gate FAILED. Run 'bash ${REPO_ROOT}/scripts/release/check_bravoh_server_ready.sh' for the BLOCKED_BY line."
fi
echo

# ── Gate 6: bundle ID locked ───────────────────────────────────────────
echo "[Gate 6] Bundle ID locked at world.bravoh.vibemix (P63)"
if ${PYTHON} -m pytest "${REPO_ROOT}/tests/security/test_bundle_id_locked.py" -q --no-header >/dev/null 2>&1; then
  pass "tests/security/test_bundle_id_locked.py"
else
  fail "tests/security/test_bundle_id_locked.py — bundle id drift"
fi
echo

# ── Verdict ────────────────────────────────────────────────────────────
echo "═════════════════════════════════════════════════════════"
if [[ "${FAIL}" -ne 0 ]]; then
  echo "  PRE-FLIGHT FAILED — ${#TRIPPED[@]} gate(s) tripped:"
  for t in "${TRIPPED[@]}"; do
    echo "    - ${t}"
  done
  echo
  echo "  REFUSING TO PRINT cut command. Fix the gates and re-run."
  echo "═════════════════════════════════════════════════════════"
  exit 1
fi

echo "  ALL GATES PASS — Kaan, run the following:"
echo
CHANGELOG="${REPO_ROOT}/CHANGELOG-${TAG}.md"
if [[ ! -f "${CHANGELOG}" ]]; then
  CHANGELOG="${REPO_ROOT}/scripts/launch/changelog_template.md"
fi
cat <<EOF
    gh release create ${TAG} \\
      --repo bravoh/vibemix \\
      --title "vibemix ${TAG}" \\
      --notes-file ${CHANGELOG} \\
      --draft \\
      --target main \\
      dist/*.dmg dist/*.msi dist/*.pkg dist/*.exe
EOF
echo
echo "  Reminders (DO NOT skip):"
echo "    [GATE-06] Hybrid hallucination gate (Phase 42) PASSED — 7-day nightly proxy + ear-test both green."
echo "    [P83] Cut as ${TAG} (RC, --draft). Do NOT cut as v1.0.0 until"
echo "          ~2-week RC bake completes (separate phase)."
echo "    [SHIP-CUT] See KAAN-ACTION-LEGAL.md §SHIP for the full publish runbook."
echo "═════════════════════════════════════════════════════════"
exit 0
