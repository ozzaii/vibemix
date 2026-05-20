#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# run_sidecar_from_source.sh — launch the vibemix sidecar FROM REPO SOURCE.
#
# Runs the real flag-less cohost entrypoint (`python -m vibemix`) against
# src/vibemix/ HEAD via `uv run`, with no PyInstaller rebuild — so live
# testing reflects what you just edited. Use it two ways:
#
#   1. Standalone live-drive / debugging without the Tauri shell:
#        ./scripts/dev/run_sidecar_from_source.sh
#        ./scripts/dev/run_sidecar_from_source.sh --wizard   # wizard pass
#
#   2. As the documented env contract the Tauri dev path reads. This script
#      exports the SAME env vars that `tauri/src-tauri/src/sidecar.rs`
#      (resolve_sidecar_invocation) honors, so the contract lives in one place:
#        VIBEMIX_DEV_SIDECAR=1   -> sidecar.rs spawns from source, not bundled
#        VIBEMIX_DEV_REPO=<root> -> the cwd `python -m vibemix` runs in
#      To make `cargo tauri dev` reflect HEAD instead, set the same flag:
#        VIBEMIX_DEV_SIDECAR=1 cargo tauri dev
#      See docs/dev-loop.md.
#
# Any extra args (e.g. --wizard) are passed straight through to the entrypoint.
set -euo pipefail

usage() {
  # Print the comment header (everything up to the first blank line after it).
  sed -n '3,30p' "$0" | sed 's/^# \{0,1\}//'
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

# Resolve the repo root from this script's location: scripts/dev/ -> repo root.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# The env contract sidecar.rs reads (keep in sync with resolve_sidecar_invocation).
export VIBEMIX_DEV_SIDECAR=1
export VIBEMIX_DEV_REPO="${REPO_ROOT}"

echo "-> running vibemix sidecar from source (repo: ${REPO_ROOT})" >&2
cd "${REPO_ROOT}"
exec uv run python -m vibemix "$@"
