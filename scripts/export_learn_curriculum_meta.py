#!/usr/bin/env python
# SPDX-License-Identifier: Apache-2.0
"""Generate or verify the Learn frontend curriculum projection."""
from __future__ import annotations

import argparse
import difflib
import sys
from pathlib import Path

from vibemix.learn.curriculum_projection import render_curriculum_meta_ts

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "tauri" / "ui" / "src" / "learn" / "lesson" / "curriculum-meta.ts"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help="TypeScript output path.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if the output file is not up to date.",
    )
    parser.add_argument(
        "--print",
        action="store_true",
        help="Print generated TypeScript to stdout instead of writing.",
    )
    args = parser.parse_args(argv)

    rendered = render_curriculum_meta_ts()
    if args.print:
        print(rendered, end="")
        return 0

    target = args.out
    if args.check:
        current = target.read_text(encoding="utf-8")
        if current == rendered:
            return 0
        diff = difflib.unified_diff(
            current.splitlines(keepends=True),
            rendered.splitlines(keepends=True),
            fromfile=str(target),
            tofile="generated curriculum-meta.ts",
        )
        sys.stderr.writelines(diff)
        return 1

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
