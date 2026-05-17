#!/usr/bin/env bash
# Phase 46 / DEPS-06 — CycloneDX SBOM producer.
#
# Emits a CycloneDX 1.5 JSON SBOM per ecosystem (Python / Rust / JS)
# plus a merged file. Designed to run alongside the existing syft
# SPDX workflow — both formats land in dist/sbom/.
#
# Tools (all pinned):
#   - cyclonedx-bom (cyclonedx-py CLI) 7.3.0   — Python tree
#   - cargo-cyclonedx 0.5.7                    — Rust tree
#   - @cyclonedx/cdxgen 10.10.5                — JS tree (npx)
#
# Output:
#   dist/sbom/vibemix.python.cdx.json
#   dist/sbom/vibemix.rust.cdx.json
#   dist/sbom/vibemix.js.cdx.json
#   dist/sbom/vibemix.cdx.json    — merged release asset

set -euo pipefail

OUT_DIR="dist/sbom"
mkdir -p "$OUT_DIR"

# --- Python ----------------------------------------------------------
if command -v uv >/dev/null 2>&1; then
  uv tool install --quiet "cyclonedx-bom==7.3.0" 2>/dev/null || true
  uv tool run cyclonedx-py environment \
    --output-format JSON \
    --output-file "$OUT_DIR/vibemix.python.cdx.json"
else
  pip install --quiet "cyclonedx-bom==7.3.0"
  cyclonedx-py environment \
    --output-format JSON \
    --output-file "$OUT_DIR/vibemix.python.cdx.json"
fi

# --- Rust ------------------------------------------------------------
if ! command -v cargo-cyclonedx >/dev/null 2>&1; then
  cargo install cargo-cyclonedx --version 0.5.7 --locked --force
fi
(
  cd tauri/src-tauri
  cargo cyclonedx --format json --output-pattern package
)
# cargo-cyclonedx emits per-package files at tauri/src-tauri/*.cdx.json;
# the workspace-level result is bom.cdx.json — copy the top-level one.
if [ -f "tauri/src-tauri/bom.cdx.json" ]; then
  cp "tauri/src-tauri/bom.cdx.json" "$OUT_DIR/vibemix.rust.cdx.json"
else
  cp "$(find tauri/src-tauri -maxdepth 1 -name '*.cdx.json' | head -1)" "$OUT_DIR/vibemix.rust.cdx.json"
fi

# --- JS --------------------------------------------------------------
npx --yes "@cyclonedx/cdxgen@10.10.5" \
  -o "$OUT_DIR/vibemix.js.cdx.json" \
  tauri/ui/

# --- Merge -----------------------------------------------------------
# Fall back to jq merge if cdxgen --merge unavailable.
npx --yes "@cyclonedx/cdxgen@10.10.5" \
  --merge "$OUT_DIR/vibemix.python.cdx.json" \
  --merge "$OUT_DIR/vibemix.rust.cdx.json" \
  --merge "$OUT_DIR/vibemix.js.cdx.json" \
  -o "$OUT_DIR/vibemix.cdx.json" 2>/dev/null || {
    echo "cdxgen --merge unavailable, falling back to jq merge"
    jq -s '
      {
        bomFormat: "CycloneDX",
        specVersion: "1.5",
        serialNumber: "urn:uuid:vibemix-merged",
        version: 1,
        metadata: { component: { type: "application", name: "vibemix", version: "0.1.0-dev0" } },
        components: ([.[] | .components // []] | flatten | unique_by(.["bom-ref"] // .name))
      }
    ' "$OUT_DIR/vibemix.python.cdx.json" "$OUT_DIR/vibemix.rust.cdx.json" "$OUT_DIR/vibemix.js.cdx.json" \
      > "$OUT_DIR/vibemix.cdx.json"
  }

echo "CycloneDX SBOMs in $OUT_DIR:"
ls -la "$OUT_DIR"/*.cdx.json
