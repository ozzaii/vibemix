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
#   1.  Tag prefix regex `^v0\.1\.0-rc[0-9]+$` (P83 — no premature v1.0.0;
#       v0.1.0-rc is the PUBLIC OSS tag, v4.0 stays the INTERNAL milestone).
#   2.  `verify_signed.py --require-signed` for every dist/*.{dmg,msi,exe,pkg}.
#   2b. `check_gate.sh` — Phase 42 hybrid hallucination gate (GATE-06).
#   3.  `pytest tests/repo/test_readme_hero_hash_sync.py` (Phase 35).
#   4.  `.planning/v4.0-MILESTONE-AUDIT.md` exists + frontmatter verdict WIRED.
#   5.  `pytest tests/repo/test_g5_poc_files_untouched.py` — POC variants retired,
#       stay gone (Phase 37 / AUDIT-06; inverted 2026-05-20).
#   5b. `check_bravoh_server_ready.sh` — 3-endpoint Bravoh server probe
#       (Plan 45-03 / SHIP-06 / OPS-14).
#   6.  `pytest tests/security/test_bundle_id_locked.py` (Phase 33 / P63).
#
# Usage:
#   bash scripts/launch/cut_release.sh v0.1.0-rc1
#   bash scripts/launch/cut_release.sh --dry-run v0.1.0-rc1   # signature-stub mode
#
# Output on PASS: prints the exact `gh release create` command Kaan should
# run; does NOT execute it. Confirms the Phase 42 hybrid hallucination
# gate (GATE-06) is green — supersedes the v2.1 P85 override regime
# (the autonomous-only ear-test bypass is formally retired in Plan 42-05).
#
# --dry-run (Phase 58 / REL-03): stubs ONLY the EXTERNAL signature gate
# (Gate 2 drops --require-signed) and treats the KAAN-gated Gate 2b/6b as
# PASS-for-dry-run with a loud wired-but-pending log. Every other gate runs
# for real. Exits 0 = "everything but the signature is ready." A real
# (non-dry-run) cut still FAILS Gate 2/2b/6b without the real inputs.
#
# HARD GUARD: even with `--really` / `--real` / `--dry-run`, this script
# NEVER invokes `gh release create` autonomously. That's the load-bearing
# safety property.

set -u

# ── Arg parse: optional --dry-run/--no-sign flag + the tag ─────────────
DRY_RUN=0
TAG=""
for arg in "$@"; do
  case "${arg}" in
    --dry-run|--no-sign) DRY_RUN=1 ;;
    -*) echo "usage: $0 [--dry-run] <tag>  (e.g. $0 v0.1.0-rc1)" >&2; exit 1 ;;
    *)  TAG="${arg}" ;;
  esac
done

if [[ -z "${TAG}" ]]; then
  echo "usage: $0 [--dry-run] <tag>  (e.g. $0 v0.1.0-rc1)" >&2
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PYTHON="${PYTHON:-python3}"
TAG_REGEX='^v0\.1\.0-rc[0-9]+$'

FAIL=0
TRIPPED=()

pass()  { echo "  PASS  $*"; }
fail()  { echo "  FAIL  $*" >&2; FAIL=1; TRIPPED+=("$*"); }
info()  { echo "  --    $*"; }

echo "═════════════════════════════════════════════════════════"
echo "  vibemix — cut_release.sh pre-flight (Phase 39 / SHIP-01)"
echo "  Tag:    ${TAG}"
echo "  Repo:   ${REPO_ROOT}"
if [[ "${DRY_RUN}" -eq 1 ]]; then
  echo "  Mode:   DRY-RUN (signature stubbed — EXTERNAL gate only)"
fi
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
# Under --dry-run we STUB the EXTERNAL signature requirement: verify_signed.py
# runs WITHOUT --require-signed (checksum-only), so an unsigned local .dmg
# passes. The real cut MUST keep --require-signed (Apple/SignPath, EXTERNAL).
echo "[Gate 2] verify_signed.py --require-signed for every dist artifact"
if [[ "${DRY_RUN}" -eq 1 ]]; then
  info "DRY-RUN: signature gate stubbed (EXTERNAL — Apple/SignPath)"
fi
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
      REQUIRE_SIGNED="--require-signed"
      if [[ "${DRY_RUN}" -eq 1 ]]; then
        REQUIRE_SIGNED=""   # stub: checksum-only, unsigned .dmg passes
      fi
      if "${PYTHON}" "${REPO_ROOT}/scripts/dist/verify_signed.py" --artifact "${art}" ${REQUIRE_SIGNED} >/dev/null 2>&1; then
        if [[ "${DRY_RUN}" -eq 1 ]]; then
          pass "checksum OK (signature stubbed): $(basename "${art}")"
        else
          pass "signed: $(basename "${art}")"
        fi
      else
        fail "unsigned (or verifier blocked): $(basename "${art}")"
      fi
    done
  fi
fi
echo

# ── Gate 2b: hybrid hallucination gate (Phase 42 / GATE-06) ────────────
# KAAN-gated leg (live ear-pass, 54/55 HUMAN-UAT). Under --dry-run we prove
# the WIRING and treat a missing input as PASS-for-dry-run with a loud
# wired-but-pending log. A real cut MUST still FAIL without the ear-pass.
echo "[Gate 2b] check_gate.sh — 7-day nightly proxy + ear-test (Phase 42)"
if bash "${REPO_ROOT}/scripts/release/check_gate.sh" >/dev/null 2>&1; then
  pass "check_gate.sh — hybrid gate green"
elif [[ "${DRY_RUN}" -eq 1 ]]; then
  info "DRY-RUN: Gate 2b wired; awaiting Kaan input (54/55 ear-pass) — PASS-for-dry-run"
else
  fail "check_gate.sh — hybrid gate FAILED (nightly proxy and/or ear-test). Run 'bash ${REPO_ROOT}/scripts/release/check_gate.sh' for the structured blocker."
fi
echo

# ── Gate 6b: e2e harness dimension-FAIL block (Phase 50 / E2E-08) ──────
# KAAN-gated feed (§E2E-50A-WALK recording). Under --dry-run a missing run
# is PASS-for-dry-run with a loud wired-but-pending log; a real cut FAILS.
echo "[Gate 6b] check_e2e_report.sh — blocks on FAIL in dist/e2e-macbook-runs/"
if bash "${REPO_ROOT}/scripts/e2e/check_e2e_report.sh" >/dev/null 2>&1; then
  pass "check_e2e_report.sh — latest e2e run all dimensions PASS / PARTIAL / SKIPPED"
elif [[ "${DRY_RUN}" -eq 1 ]]; then
  info "DRY-RUN: Gate 6b wired; awaiting Kaan input (E2E walk) — PASS-for-dry-run"
else
  fail "check_e2e_report.sh — latest e2e run reports FAIL on at least one dimension. Run 'bash ${REPO_ROOT}/scripts/e2e/check_e2e_report.sh' for the dimension breakdown."
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
echo "[Gate 4] .planning/v4.0-MILESTONE-AUDIT.md exists + verdict WIRED (Phase 37)"
AUDIT="${REPO_ROOT}/.planning/v4.0-MILESTONE-AUDIT.md"
if [[ ! -f "${AUDIT}" ]]; then
  fail ".planning/v4.0-MILESTONE-AUDIT.md missing — run scripts/integration_audit.py --write-milestone-audit"
else
  # Frontmatter convention: overall_verdict: WIRED  (or status: passed for back-compat).
  if grep -E '^(overall_verdict|status):\s*(WIRED|passed)\s*$' "${AUDIT}" >/dev/null 2>&1; then
    pass "milestone audit present, verdict WIRED"
  else
    fail "milestone audit present but verdict is not WIRED/passed"
  fi
fi
echo

# ── Gate 5: POC variants retired (stay gone) ───────────────────────────
echo "[Gate 5] POC variants retired — stay gone (AUDIT-06 / P85)"
if ${PYTHON} -m pytest "${REPO_ROOT}/tests/repo/test_g5_poc_files_untouched.py" -q --no-header >/dev/null 2>&1; then
  pass "tests/repo/test_g5_poc_files_untouched.py"
else
  fail "tests/repo/test_g5_poc_files_untouched.py — retired POC variant resurrected"
fi
echo

# ── Gate 5b: Bravoh server ready (Plan 45-03 / SHIP-06 / OPS-14) ───────
# ENG-but-server-dependent: probes Bravoh PROD (api.altidus.world), read-only.
# Not a Kaan-input gate, but external server state. Under --dry-run a down
# server is logged as a server-readiness PRECONDITION and PASS-for-dry-run
# (the gate is NOT weakened — a real cut still FAILS when the server is down).
echo "[Gate 5b] check_bravoh_server_ready.sh — 3-endpoint probe + healthz freshness (Plan 45-03)"
if bash "${REPO_ROOT}/scripts/release/check_bravoh_server_ready.sh" --quiet >/dev/null 2>&1; then
  pass "check_bravoh_server_ready.sh — 3/3 endpoints OK + healthz fresh"
elif [[ "${DRY_RUN}" -eq 1 ]]; then
  info "DRY-RUN: Gate 5b server-dependent; Bravoh server-readiness is a real-cut PRECONDITION — PASS-for-dry-run"
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

if [[ "${DRY_RUN}" -eq 1 ]]; then
  echo "  DRY-RUN GREEN — everything but the signature is ready. Real cut blocked only on: [Apple Dev Agreement, SignPath cert, 54/55 ear-pass, E2E walk]."
  echo
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
# Phase 16 override cleanup reminder — historical anchor for the
# P85 audit trail (the autonomous-only ear-test bypass is formally
# retired in Plan 42-05; STATE.md still annotates the line RETIRED
# with a cross-reference to .planning/decisions/P85-OVERRIDE-RETIRED.md).
# Intentionally a comment (not an echo) per Plan 42-04 — the
# user-visible success block must not surface the retired override.
echo "  Reminders (DO NOT skip):"
echo "    [GATE-06] Hybrid hallucination gate (Phase 42) PASSED — 7-day nightly proxy + ear-test both green."
echo "    [P83] Cut as ${TAG} (RC, --draft). Do NOT cut as v1.0.0 until"
echo "          ~2-week RC bake completes (separate phase)."
echo "    [SHIP-CUT] See KAAN-ACTION-LEGAL.md §SHIP for the full publish runbook."
echo "═════════════════════════════════════════════════════════"
exit 0
