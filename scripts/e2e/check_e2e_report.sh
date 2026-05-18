#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# Phase 50 / E2E — Gate 6b runner for scripts/launch/cut_release.sh.
#
# Parses the latest dist/e2e-macbook-runs/<UTC>/report.html, extracts the five
# dimension statuses (Functional / Visual / Aesthetic / Usability / Hallucination)
# from the locked row labels, exits non-zero if ANY dimension is FAIL.
#
# Exit codes:
#   0  - latest report all PASS / PARTIAL / SKIPPED                          (release OK)
#   1  - latest report has at least one dimension FAIL                       (release blocked)
#   2  - no dist/e2e-macbook-runs/<UTC>/report.html found                    (run e2e first)
#
# PARTIAL/SKIPPED are graceful states for CI-tolerant fallbacks (PITFALLS § 8 + § 19).
# Uses only bash + grep + awk — no Python dep.

set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
RUN_ROOT="${VIBEMIX_E2E_RUN_ROOT:-${REPO_ROOT}/dist/e2e-macbook-runs}"

if [[ ! -d "${RUN_ROOT}" ]]; then
  echo "[gate-6b] no e2e runs found at ${RUN_ROOT}" >&2
  echo "[gate-6b] hint: produce a run via 'pytest tests/e2e/macbook/test_report_render.py'" >&2
  exit 2
fi

# Latest report by mtime — POSIX-safe ordering.
# Try BSD stat first (macOS), then GNU stat (Linux). pipefail-safe via
# || true so an empty result doesn't kill the script.
LATEST_REPORT="$(
  {
    find "${RUN_ROOT}" -mindepth 2 -maxdepth 3 -type f -name 'report.html' \
      -exec stat -f '%m %N' {} \; 2>/dev/null \
    || find "${RUN_ROOT}" -mindepth 2 -maxdepth 3 -type f -name 'report.html' \
      -exec stat -c '%Y %n' {} \; 2>/dev/null
  } | sort -nr | head -n1 | awk '{$1=""; sub(/^ /, ""); print}' \
  || true
)"

if [[ -z "${LATEST_REPORT}" || ! -f "${LATEST_REPORT}" ]]; then
  echo "[gate-6b] no report.html under ${RUN_ROOT}" >&2
  exit 2
fi

echo "[gate-6b] inspecting ${LATEST_REPORT}"

# Extract dimension statuses from the locked label rows. Template renders:
#   <span class="label">Functional</span>
#   <span class="status">PASS</span>
# We pull the status that immediately follows each locked label.
fail_count=0
declare -a FAILED=()

# Flatten the report to a single line so dimension label + status pair scan
# cleanly even when the template renders them on separate lines.
FLAT_REPORT="$(tr -d '\n' < "${LATEST_REPORT}")"

for dim in Functional Visual Aesthetic Usability Hallucination; do
  # Find the label span for this dimension followed by the status span. The
  # template renders ``<span class="label">Dim</span>...<span class="status">PASS</span>``
  # We tolerate any whitespace and attribute order between the spans.
  status="$(
    printf '%s' "${FLAT_REPORT}" \
      | grep -oE "${dim}</span>[[:space:]]*<span[^>]*class=\"status\">[A-Z]+" \
      | head -n1 \
      | grep -oE 'class="status">[A-Z]+' \
      | sed -E 's|class="status">([A-Z]+)|\1|'
  )"

  # Fallback for templates that put status BEFORE label or in any order.
  if [[ -z "${status}" ]]; then
    status="$(
      printf '%s' "${FLAT_REPORT}" \
        | grep -oE "<span[^>]*class=\"status\">[A-Z]+</span>[[:space:]]*<span[^>]*class=\"label\">${dim}" \
        | head -n1 \
        | grep -oE 'class="status">[A-Z]+' \
        | sed -E 's|class="status">([A-Z]+)|\1|'
    )"
  fi

  if [[ -z "${status}" ]]; then
    status="UNKNOWN"
  fi

  printf "[gate-6b] %-14s %s\n" "${dim}" "${status}"

  case "${status}" in
    PASS|PARTIAL|SKIPPED) ;;  # graceful states — no block
    FAIL)
      fail_count=$((fail_count + 1))
      FAILED+=("${dim}")
      ;;
    *)
      # UNKNOWN treated as FAIL to be safe — release should not proceed on
      # a malformed report.
      fail_count=$((fail_count + 1))
      FAILED+=("${dim}(${status})")
      ;;
  esac
done

if [[ ${fail_count} -gt 0 ]]; then
  echo "[gate-6b] BLOCK — ${fail_count} dimension(s) FAIL: ${FAILED[*]}" >&2
  exit 1
fi

echo "[gate-6b] OK — all 5 dimensions PASS / PARTIAL / SKIPPED"
exit 0
