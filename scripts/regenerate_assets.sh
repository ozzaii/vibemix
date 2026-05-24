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

# Locate a headless-Chrome binary across macOS / Linux / CI. Honours an
# explicit $CHROME override first (CI runners set this).
_find_chrome() {
    if [[ -n "${CHROME:-}" && -x "${CHROME}" ]]; then echo "$CHROME"; return 0; fi
    local c
    for c in \
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
        "/Applications/Chromium.app/Contents/MacOS/Chromium" \
        google-chrome google-chrome-stable chromium chromium-browser; do
        if [[ -x "$c" ]]; then echo "$c"; return 0; fi
        if command -v "$c" >/dev/null 2>&1; then command -v "$c"; return 0; fi
    done
    return 1
}

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
        # Wave 1 (70P02) — GH-03 og-card. Rendered via headless Chrome
        # (--headless=new --screenshot), mirroring the existing
        # docs/assets/screenshots/regen.sh precedent. Chrome is preferred over
        # `npx puppeteer` here: it is already installed on the dev/CI box, needs
        # no npm fetch (smaller supply-chain surface — T-70P02-SC), and the same
        # --force-device-scale-factor=1 + fixed --window-size give a stable
        # render. Node/npx remains CI-side either way — NOT a Python dep.
        #
        # Determinism note: --window-size=1200,630 + --force-device-scale-factor=1
        # pins the output dimensions to exactly 1200×630. Pixel bytes can drift
        # by a Chrome MINOR-VERSION font-rasterisation change (sub-pixel hinting);
        # the asset-bitrot gate's "differs ONLY by intentional source edits"
        # clause covers that. Re-running on the SAME Chrome build is byte-stable.
        og-card)
            local chrome
            chrome="$(_find_chrome)" || {
                echo "Chrome not found for og-card render (set CHROME env or install Google Chrome)" >&2
                return 1
            }
            local outdir; outdir="$(dirname "$REPO/$path")"
            mkdir -p "$outdir"
            # --virtual-time-budget=4000 is LOAD-BEARING for determinism: without
            # it Chrome races the Google-Fonts webfont fetch and sometimes
            # screenshots with the system-ui fallback instead of Saira, producing
            # PIXEL-level drift run-to-run (not just encoding drift). The virtual
            # clock advances 4 s so the webfont always finishes loading first; the
            # render is then pixel-stable across separate invocations (verified 3×).
            "$chrome" --headless=new --disable-gpu --hide-scrollbars \
                --force-device-scale-factor=1 --window-size=1200,630 \
                --virtual-time-budget=4000 --default-background-color=00000000 \
                --screenshot="$REPO/$path" \
                "file://$REPO/$source" >/dev/null 2>&1
            [[ -f "$REPO/$path" ]] || { echo "og-card render produced no file at $path" >&2; return 1; }
            # Chrome's PNG encoder is NOT byte-stable across runs even when the
            # PIXELS are identical (chunk ordering / metadata differs), which
            # would break the asset-bitrot git-diff gate. Re-encode through
            # Pillow with fixed, metadata-stripped options so the committed PNG
            # is byte-reproducible from identical pixels. Pillow is already a
            # tracked dep (no new dep). quantize-to-palette also shrinks the
            # file to fit the docs/assets image budget.
            PYTHONPATH="$REPO/src" python3 - "$REPO/$path" <<'PY'
import sys
from PIL import Image

p = sys.argv[1]
im = Image.open(p).convert("RGB")
# Palette-quantize (256 colors) keeps the flat void + silk text + amber crisp
# while cutting the file well under the budget; the card has few distinct hues.
q = im.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
# Deterministic save: no metadata, fixed compression, no time chunk.
q.save(p, format="PNG", optimize=True, compress_level=9)
PY
            ;;
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
