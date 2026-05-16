#!/usr/bin/env bash
# Phase 33 / Plan 33-08 — Fresh-Mac-VM rehearsal scaffold.
#
# Provisions a clean macOS 12.3 / 14 / 15 VM via Cirrus-Labs/tart so
# the install rehearsal harness can boot a known-state machine, install
# the signed DMG, and stopwatch the ≤60s onboarding flow.
#
# HARD GUARDS (refuse to run by default):
#
#   1. ``tart`` must be on PATH. If it isn't, bail with a documented
#      message pointing at KAAN-ACTION-LEGAL.md (real VM execution is
#      Kaan-action, not autonomous).
#   2. ``INSTALL_REHEARSAL_REAL=1`` must be set. Without it we print the
#      provisioning plan but do not spin a VM. CI calls the workflow
#      in --dry-run mode only.
#
# Both guards exist because actual VM execution requires disk space +
# a macOS license + a fresh-state image — none of which fit autonomous
# discharge. The scaffold is here so Kaan can flip the env var on a
# Mac that has tart + the images ready.
#
# Usage:
#   ./mac_vm_setup.sh                 # dry-run; print plan, exit 0
#   INSTALL_REHEARSAL_REAL=1 ./mac_vm_setup.sh   # actually run

set -euo pipefail

MATRIX=(
    "macos-12.3"
    "macos-14"
    "macos-15"
)

echo "[33-08] Fresh-Mac-VM rehearsal scaffold"
echo "[33-08] Matrix: ${MATRIX[*]}"

# Guard 1: tart on PATH?
if ! command -v tart >/dev/null 2>&1; then
    echo "[33-08] tart not on PATH — bailing out (Kaan-action)."
    echo "[33-08] Install: brew install cirruslabs/cli/tart"
    echo "[33-08] See: KAAN-ACTION-LEGAL.md INSTALL-VM-RUN section"
    exit 0
fi

# Guard 2: real-run opt-in?
if [ "${INSTALL_REHEARSAL_REAL:-}" != "1" ]; then
    echo "[33-08] INSTALL_REHEARSAL_REAL != 1 — dry-run mode."
    echo "[33-08] Would provision VMs:"
    for v in "${MATRIX[@]}"; do
        echo "  - tart clone ghcr.io/cirruslabs/${v}:latest ${v}-vibemix-rehearsal"
        echo "  - tart run ${v}-vibemix-rehearsal --no-graphics"
    done
    echo "[33-08] Set INSTALL_REHEARSAL_REAL=1 to actually spin VMs."
    exit 0
fi

# Real-run path — Kaan flipped the env var on a machine with tart.
for v in "${MATRIX[@]}"; do
    name="${v}-vibemix-rehearsal"
    echo "[33-08] Provisioning ${name}"
    tart clone "ghcr.io/cirruslabs/${v}:latest" "${name}"
    tart run --no-graphics "${name}" &
done
wait
echo "[33-08] Matrix provisioned."
