# SPDX-License-Identifier: Apache-2.0
"""Storyboard palette extractor + CDJ Whisper compliance gate.

VIS-07 (Phase 43, Plan 43-07): ensures ``mocks/vibemix-cinematic-storyboard.html``
resolves to the 5-warm-blacks + 1-amber CDJ Whisper palette (with the deliberate
REC pill red, paper-grain warm-cream cluster for cutsheet, and SVG neutrals).

Run from repo root::

    uv run python scripts/launch/check_storyboard_palette.py
    uv run python scripts/launch/check_storyboard_palette.py --file path/to/other.html

Exit 0 = palette compliant; non-zero = drift detected (stderr names colors).

The checker is intentionally strict on drift directions that have historically
caused regressions (cyan / teal / electric-blue chip overlays, lime green
"ok" tokens) — anything outside ALLOWED_PALETTE fails the gate.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# CDJ Whisper allowed palette (per CONTEXT §VIS-07 + tauri/ui/src/tokens.css).
#
# Hex literals are normalized to lowercase 6-digit form before lookup.
# Each cluster is documented below — when expanding, add a comment naming
# the design role and the file/line that introduced the color.
# ---------------------------------------------------------------------------
ALLOWED_PALETTE: frozenset[str] = frozenset({
    # 5 warm blacks (the spine of the palette)
    "#0a0b0e", "#15181e", "#1d2128", "#07080a", "#0c0d10",
    # additional warm-black gradient stops (frame backgrounds, header gradients)
    "#14171c", "#161a20", "#0e1014", "#05060a", "#050608",
    "#020203", "#0f0c08",
    # bezel + screw layers (chassis affordances)
    "#1a1e25", "#2a2f38", "#3a4150", "#5a606c",
    # ink (silk type), incl. silk-deep / engraved
    "#c8cdd6", "#6b7280", "#3d424c", "#1f242c",
    # amber (phosphor) — primary accent + warm/dim/halo variants
    "#ffa12e", "#ff8a1a", "#6e4815", "#ffb88a", "#ff5a1a",
    # amber sub-tones used in SVG fills (mascot body, glow stops, hand)
    "#ff7050", "#a86c10", "#a8540a", "#ffd28a", "#ff6b1e",
    # REC pill red — deliberate REC-indicator color
    "#ff3553",
    # universal extremes (used in SVG strokes / wordmark fills / overlay backdrops)
    "#ffffff", "#000000",
    # paper-grain cutsheet cluster (the timeline tape look)
    "#f3ead7", "#ece2c8", "#2a1f15", "#5a4a30",
    # warm-dark mascot ink / hair / chassis interior (SVG eye + iris fills)
    "#1a1408", "#0e0a05", "#1a0e05", "#241a08", "#2a1e08",
    "#2a2118", "#321e0a",
    # warm-leather / mascot accessory tones (headphone cushions, brim shadow)
    "#5a4a3e", "#7a6452",
})

_HEX_RE = re.compile(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b")
_RGB_RE = re.compile(
    r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*[\d.]+\s*)?\)"
)


def _hex_normalize(h: str) -> str:
    """Lowercase + expand #rgb to #rrggbb."""
    h = h.lower()
    if len(h) == 4:  # #rgb shorthand
        h = "#" + "".join(c * 2 for c in h[1:])
    return h


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02x}{g:02x}{b:02x}"


def extract_colors(html_path: Path) -> set[str]:
    """Extract all hex + rgb()/rgba() colors from an HTML file.

    Returns a set of lowercase 6-digit hex strings. Alpha channels are
    dropped — the gate checks chromaticity, not opacity (a low-alpha
    overlay of an allowed amber is still amber).
    """
    text = html_path.read_text(encoding="utf-8")
    colors: set[str] = set()
    for m in _HEX_RE.finditer(text):
        colors.add(_hex_normalize("#" + m.group(1)))
    for m in _RGB_RE.finditer(text):
        r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
        colors.add(_rgb_to_hex(r, g, b))
    return colors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--file",
        type=Path,
        default=Path("mocks/vibemix-cinematic-storyboard.html"),
        help="HTML file to scan (default: mocks/vibemix-cinematic-storyboard.html)",
    )
    args = parser.parse_args(argv)

    if not args.file.exists():
        print(f"ERROR: file not found: {args.file}", file=sys.stderr)
        return 1

    found = extract_colors(args.file)
    offenders = found - ALLOWED_PALETTE
    if offenders:
        print(f"FAIL: palette drift in {args.file}", file=sys.stderr)
        for c in sorted(offenders):
            print(
                f"  {c} not in CDJ Whisper allowed palette",
                file=sys.stderr,
            )
        return 2

    print(
        f"PASS: {args.file} palette compliant "
        f"({len(found)} unique colors, all in allowed set)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
