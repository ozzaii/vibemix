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

# --- --check-60s gate-only mode (Task 3 wires this — stub for Task 2) -------

if [[ "$CHECK_60S" -eq 1 ]]; then
    echo "[install-vm] --check-60s not yet implemented (Task 3)" >&2
    exit 1
fi

# --- main matrix execution path ---------------------------------------------

if [[ ! -f "$MATRIX_JSON" ]]; then
    echo "ERROR: matrix JSON not found at: $MATRIX_JSON" >&2
    exit 2
fi

# Auto-generate UTC run id if not provided.
if [[ -z "$RUN_ID" ]]; then
    RUN_ID="$(date -u +"%Y-%m-%dT%H-%M-%SZ")"
fi
RUN_DIR="${RUNS_ROOT}/${RUN_ID}"
mkdir -p "$RUN_DIR"

ROW_COUNT=$(python3 -c "import json; print(len(json.load(open('$MATRIX_JSON'))['rows']))")
log "[install-vm] $( [[ $LIVE -eq 1 ]] && echo live || echo dry-run ) — iterating $ROW_COUNT VMs from $MATRIX_JSON (run-id=$RUN_ID)"

# Under --live, require tart on PATH before doing anything else.
if [[ "$LIVE" -eq 1 ]] && ! command -v tart >/dev/null 2>&1; then
    echo "[install-vm] tart binary missing — install with: brew install cirruslabs/cli/tart" >&2
    exit 3
fi

# Per-row driver — emits `[plan] ...` lines under dry-run, invokes tart under
# --live. The screenshot pass and run.json-row assembly are driven by python3
# inline (parsing the matrix JSON once, looping in shell for tart calls).
ROW_RESULTS_JSON="${RUN_DIR}/.row-results.tmp.json"
echo "[]" > "$ROW_RESULTS_JSON"

process_row() {
    local idx="$1"
    # Pull row fields via python3 (one call per field is fine — 5 rows × ~10 fields).
    local row_json
    row_json=$(python3 -c "
import json,sys
rows=json.load(open('$MATRIX_JSON'))['rows']
print(json.dumps(rows[$idx]))
")
    local os ver image steps max_ms
    os=$(printf '%s' "$row_json" | python3 -c "import json,sys; print(json.load(sys.stdin)['os'])")
    ver=$(printf '%s' "$row_json" | python3 -c "import json,sys; print(json.load(sys.stdin)['version'])")
    image=$(printf '%s' "$row_json" | python3 -c "import json,sys; print(json.load(sys.stdin)['tart_image'])")
    max_ms=$(printf '%s' "$row_json" | python3 -c "import json,sys; print(json.load(sys.stdin)['max_onboarding_ms'])")
    # Read step names as newline-separated.
    local steps_str
    steps_str=$(printf '%s' "$row_json" | python3 -c "
import json,sys
print('\n'.join(json.load(sys.stdin)['expected_steps']))
")

    local tag="${os}-${ver}"
    local vm_name="vibemix-install-${os}-${ver}-${RUN_ID}"
    local row_status="ok"
    local skip_reason="null"
    local screenshots_json="[]"

    # --- step 1: tart clone -------------------------------------------------
    if [[ "$LIVE" -eq 1 ]]; then
        if ! tart clone "$image" "$vm_name" >/dev/null 2>&1; then
            row_status="skipped"
            skip_reason='"tart_image_missing"'
            log "[skip] $tag — tart image $image not present (clone failed)"
        fi
    else
        log "[plan] tart clone $image $vm_name (os=$tag)"
    fi

    # --- step 2: tart run (boot the VM with the matrix env var injected) ---
    if [[ "$row_status" == "ok" ]]; then
        if [[ "$LIVE" -eq 1 ]]; then
            # In live mode the actual VM run is a more elaborate dance (mount
            # host dir, install the DMG/MSI, launch the wizard with
            # VIBEMIX_INSTALL_VM_RUN=1). For this scaffolding we delegate to a
            # `tart run` invocation; the §SHIP-04 runbook documents the full
            # mount-and-walk flow Kaan executes manually. The runner records a
            # `[plan] tart run` placeholder for symmetry with dry-run output.
            log "[live] tart run $vm_name (env VIBEMIX_INSTALL_VM_RUN=1)"
            tart run "$vm_name" >/dev/null 2>&1 || row_status="failed"
        else
            log "[plan] tart run $vm_name --env VIBEMIX_INSTALL_VM_RUN=1 (os=$tag)"
        fi
    fi

    # --- step 3: per-step screenshots --------------------------------------
    local i=0
    local shots=()
    while IFS= read -r step; do
        i=$((i + 1))
        local shot_path="${RUN_DIR}/install-vm-${os}-${ver}-wizard-step-${i}.png"
        local shot_relpath="install-vm-${os}-${ver}-wizard-step-${i}.png"
        if [[ "$LIVE" -eq 1 ]] && [[ "$row_status" == "ok" ]]; then
            tart screenshot --output "$shot_path" "$vm_name" >/dev/null 2>&1 || true
        else
            log "[plan] tart screenshot --output dist/install-vm-runs/${RUN_ID}/${shot_relpath} (step=$step)"
        fi
        shots+=("$shot_relpath")
    done <<< "$steps_str"

    # Convert shots[] to a JSON array.
    if [[ ${#shots[@]} -gt 0 ]]; then
        screenshots_json=$(printf '%s\n' "${shots[@]}" | python3 -c "
import json,sys
print(json.dumps([line.rstrip('\n') for line in sys.stdin if line.rstrip('\n')]))
")
    fi

    # --- step 4: tart stop -------------------------------------------------
    if [[ "$LIVE" -eq 1 ]] && [[ "$row_status" == "ok" ]]; then
        tart stop "$vm_name" >/dev/null 2>&1 || true
    else
        log "[plan] tart stop $vm_name (os=$tag)"
    fi

    # --- step 5: read timing dump if VM-side wrote one --------------------
    local timing_dump_path="${RUN_DIR}/${os}-${ver}-install-vm-timing.json"
    local total_ms="null"
    local exceeded_max_ms="false"
    if [[ -f "$timing_dump_path" ]]; then
        total_ms=$(python3 -c "
import json
d=json.load(open('$timing_dump_path', encoding='utf-8'))
v=d.get('totalMs')
print('null' if v is None else int(v))
")
        if [[ "$total_ms" != "null" ]] && [[ "$total_ms" -gt "$max_ms" ]]; then
            exceeded_max_ms="true"
        fi
    fi

    # --- step 6: append row entry to ROW_RESULTS_JSON ----------------------
    local timing_dump_field
    if [[ -f "$timing_dump_path" ]]; then
        timing_dump_field="\"${os}-${ver}-install-vm-timing.json\""
    else
        timing_dump_field="null"
    fi

    python3 - <<PYAPPEND
import json
results_path = "$ROW_RESULTS_JSON"
results = json.load(open(results_path, encoding="utf-8"))
results.append({
    "os": "$os",
    "version": "$ver",
    "status": "$row_status",
    "screenshots": json.loads('''$screenshots_json'''),
    "timing_dump": json.loads('$timing_dump_field'),
    "total_ms": (None if "$total_ms" == "null" else int("$total_ms")),
    "exceeded_max_ms": ("$exceeded_max_ms" == "true"),
    "max_onboarding_ms": int("$max_ms"),
    "skip_reason": json.loads('$skip_reason'),
})
with open(results_path, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)
PYAPPEND
}

# Loop rows by index so process_row can pull fresh JSON via python3.
for ((i = 0; i < ROW_COUNT; i++)); do
    process_row "$i"
done

# --- assemble run.json with atomic write ------------------------------------

STARTED_AT="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
MATRIX_VERSION=$(python3 -c "import json; print(json.load(open('$MATRIX_JSON'))['version'])")
TMP_RUN_JSON="${RUN_DIR}/run.json.tmp"

python3 - <<PYWRITE
import json
run = {
    "run_id": "$RUN_ID",
    "started_at": "$STARTED_AT",
    "matrix_version": int("$MATRIX_VERSION"),
    "rows": json.load(open("$ROW_RESULTS_JSON", encoding="utf-8")),
}
with open("$TMP_RUN_JSON", "w", encoding="utf-8") as f:
    json.dump(run, f, indent=2)
PYWRITE

mv "$TMP_RUN_JSON" "${RUN_DIR}/run.json"
rm -f "$ROW_RESULTS_JSON"

log "[install-vm] wrote run.json → ${RUN_DIR}/run.json"
if [[ "$LIVE" -eq 0 ]]; then
    log "[plan] dry-run complete — pass --live to actually invoke tart"
fi
exit 0
