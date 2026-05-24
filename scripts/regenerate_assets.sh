#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# scripts/regenerate_assets.sh — deterministic regenerator for every
# source-derived asset listed in docs/assets/MANIFEST.yaml `assets:` (GH-04).
#
# Phase 70 Plan 70P01 (Wave 0). This is the runnable counterpart to the
# asset-reproducibility doctrine: re-running it must reproduce each committed
# `assets:` output byte-for-byte. The asset-bitrot CI gate
# (.github/workflows/asset-bitrot.yml) runs this then `git diff --exit-code
# docs/assets/` — any drift fails CI.
#
# SCOPE: this regenerates ONLY MANIFEST.yaml `assets:` entries. Assets with
# their own generator (architecture.svg, screenshots/*.png) or hand-cut
# bespoke originals live under MANIFEST `opt_out:` and are out of scope by
# design — the gate is scoped, not global.
#
# At Wave 0 the `assets:` list is empty, so this is a clean no-op exit 0.
# Wave 1 (70P02) registers the first real generator (og-card) at the marked
# extension point below.
#
# Usage:
#   bash scripts/regenerate_assets.sh
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
MANIFEST="$REPO/docs/assets/MANIFEST.yaml"

[[ -f "$MANIFEST" ]] || { echo "Missing manifest: $MANIFEST" >&2; exit 1; }

# Read the MANIFEST `assets:` list as TSV rows: path<TAB>source<TAB>generator.
# PyYAML is a tracked transitive dep (no new deps introduced). When `assets:`
# is empty (Wave 0) this prints nothing and the for-loop body never runs.
read_assets() {
    python3 - "$MANIFEST" <<'PY'
import sys
import yaml

with open(sys.argv[1], encoding="utf-8") as fh:
    data = yaml.safe_load(fh) or {}
for entry in data.get("assets", []) or []:
    print("\t".join((
        str(entry.get("path", "")),
        str(entry.get("source", "")),
        str(entry.get("generator", "")),
    )))
PY
}

# Dispatch one MANIFEST entry to its generator step. Each generator renders
# `path` from `source` and is responsible for deterministic output.
regenerate_one() {
    local path="$1" source="$2" generator="$3"
    case "$generator" in
        # ----------------------------------------------------------------
        # Wave 1 (70P02) registers the og-card generator here, e.g.:
        #   og-card)
        #       npx --yes puppeteer ... "$REPO/$source" -> "$REPO/$path"
        #       ;;
        # ----------------------------------------------------------------
        *)
            echo "Unknown generator '$generator' for asset '$path'" >&2
            return 1
            ;;
    esac
}

main() {
    local count=0
    while IFS=$'\t' read -r path source generator; do
        [[ -n "$path" ]] || continue
        echo "regenerating $path (generator=$generator, source=$source)"
        regenerate_one "$path" "$source" "$generator"
        sha="$(shasum -a 256 "$REPO/$path" | awk '{print $1}')"
        echo "  sha256=$sha"
        count=$((count + 1))
    done < <(read_assets)

    if [[ "$count" -eq 0 ]]; then
        echo "no source-derived assets registered in MANIFEST.yaml — nothing to regenerate"
    else
        echo "regenerated $count asset(s)"
    fi
}

main "$@"
