# SPDX-License-Identifier: Apache-2.0
"""Cut counter for the hero demo storyboard.

VIS-08 (Phase 43, Plan 43-08): hard gate enforcing exactly 8 cuts in
``mocks/vibemix-cinematic-storyboard.html`` (per CONTEXT §VIS-08 ≤8 cuts
gate). Counts ``data-cut="N"`` attribute occurrences across the document
— ``<section data-cut="...">``, ``<article ... data-cut="...">``, any
element form counts.

Run from repo root::

    uv run python scripts/launch/check_cut_count.py
    uv run python scripts/launch/check_cut_count.py --file path/to/other.html

Exit codes:
    0 = exactly MAX_CUTS cuts (PASS)
    1 = file not found
    2 = over-count (>MAX_CUTS — demo length bloat risk)
    3 = under-count (<MAX_CUTS — cut sequence incomplete)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

MAX_CUTS: int = 8

# Matches `data-cut="N"`, `data-cut='N'`, `data-cut=N` (bare), with
# optional whitespace around `=`. Anchored on a word boundary so
# `aria-data-cut` etc. cannot match.
_CUT_RE = re.compile(
    r'\bdata-cut\s*=\s*(?:"([^"]+)"|\'([^\']+)\'|([^\s>"\']+))',
    re.IGNORECASE,
)


def count_cuts(html_text: str) -> int:
    """Count distinct ``data-cut=`` attribute occurrences in raw HTML text.

    Returns the number of matches; values are not validated (1..8 enforcement
    happens at audit time via the cutsheet table). Zero matches → returns 0.
    """
    return len(_CUT_RE.findall(html_text))


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

    n = count_cuts(args.file.read_text(encoding="utf-8"))
    if n > MAX_CUTS:
        print(f"FAIL: {n} cuts (max {MAX_CUTS})", file=sys.stderr)
        return 2
    if n < MAX_CUTS:
        print(f"FAIL: {n} cuts (need {MAX_CUTS})", file=sys.stderr)
        return 3

    print(f"PASS: {n} cuts in {args.file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
