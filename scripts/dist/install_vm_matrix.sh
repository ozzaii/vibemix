#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# scripts/dist/install_vm_matrix.sh — Phase 45 SHIP-04 / SHIP-05.
#
# tart-based INSTALL-VM matrix runner. Enumerates the 5-row matrix in
# `scripts/dist/install_vm_matrix.json` (macOS 12.3 / 14 / 15 + Windows
# 10 / 11), walks the install wizard end-to-end in each VM, captures
# step screenshots + the onboarding-stopwatch timing dump, and ships a
# `--check-60s` sub-gate that fails when any VM exceeded 60s onboarding.
#
# Dry-run default: no `tart` is invoked unless `--live` is passed; the
# pytest suite pins this contract by stubbing `tart` on PATH and
# asserting the stub's marker file is absent after default invocation.
#
# Usage:
#   bash scripts/dist/install_vm_matrix.sh                 # dry-run, all 5 rows
#   bash scripts/dist/install_vm_matrix.sh --live          # actually invoke tart
#   bash scripts/dist/install_vm_matrix.sh --matrix PATH   # override JSON path
#   bash scripts/dist/install_vm_matrix.sh --run-id ID     # override UTC run id
#   bash scripts/dist/install_vm_matrix.sh --check-60s     # gate-only mode
#   bash scripts/dist/install_vm_matrix.sh --quiet         # suppress stdout chatter
#   bash scripts/dist/install_vm_matrix.sh --help          # this message
#
# Exit codes:
#   0  ok (or autonomous-degraded with WARN under --check-60s)
#   1  gate failed (a row exceeded max_onboarding_ms OR run.json missing under --check-60s)
#   2  CLI usage error (unknown flag, missing arg)
#   3  external dependency missing (tart binary absent under --live)

set -euo pipefail

# --- defaults ----------------------------------------------------------------

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MATRIX_JSON="${REPO_ROOT}/scripts/dist/install_vm_matrix.json"
RUN_ID=""
LIVE=0
CHECK_60S=0
QUIET=0
RUNS_ROOT="${REPO_ROOT}/dist/install-vm-runs"

usage() {
    sed -n '1,33p' "$0"
}

# --- arg parser --------------------------------------------------------------

while [[ $# -gt 0 ]]; do
    case "$1" in
        --matrix)
            if [[ $# -lt 2 ]]; then
                echo "ERROR: --matrix requires a path" >&2
                exit 2
            fi
            MATRIX_JSON="$2"
            shift 2
            ;;
        --run-id)
            if [[ $# -lt 2 ]]; then
                echo "ERROR: --run-id requires a value" >&2
                exit 2
            fi
            RUN_ID="$2"
            shift 2
            ;;
        --live)
            LIVE=1
            shift
            ;;
        --check-60s)
            CHECK_60S=1
            shift
            ;;
        --quiet)
            QUIET=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "ERROR: unknown argument: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

log() {
    if [[ "$QUIET" -eq 0 ]]; then
        echo "$@"
    fi
}

# --- placeholder dry-run loop (Task 1 RED stub; Task 2 replaces with real loop) -----

if [[ "$CHECK_60S" -eq 1 ]]; then
    # Task 3 will implement; for now exit 1 cleanly to satisfy RED contract.
    echo "[install-vm] --check-60s not yet implemented (Task 3)" >&2
    exit 1
fi

if [[ ! -f "$MATRIX_JSON" ]]; then
    echo "ERROR: matrix JSON not found at: $MATRIX_JSON" >&2
    exit 2
fi

# Read rows via python3 (jq optional — vibemix gates already standardize on python3).
ROW_COUNT=$(python3 -c "import json,sys; print(len(json.load(open('$MATRIX_JSON'))['rows']))")
log "[install-vm] dry-run — would iterate $ROW_COUNT VMs from $MATRIX_JSON"

# Emit a minimal `[plan] tart ...` line per row. The Task 2 GREEN step
# replaces this with the real per-screenshot loop + run.json index.
python3 - "$MATRIX_JSON" <<'PYSTUB'
import json, sys
rows = json.load(open(sys.argv[1]))['rows']
for r in rows:
    print(f"[plan] tart clone {r['tart_image']} (os={r['os']}-{r['version']})")
PYSTUB

log "[plan] dry-run complete — pass --live to actually invoke tart"
exit 0
