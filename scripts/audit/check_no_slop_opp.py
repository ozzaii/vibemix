# SPDX-License-Identifier: Apache-2.0
"""Phase 48 / OPP — Anti-slop gate for docs/dep-opportunities/.

Sibling checker per CONTEXT Decision 4. Does NOT widen the
``scripts/launch/check_no_ai_slop.py`` script's target paths; instead
imports the ``AI_SLOP_BLOCKLIST`` tuple as the single source of truth
(via importlib so this script can run without installing the project
package) and applies the same 15-token + ``\\bdeeply\\s+\\w+`` regex
gate to every markdown file under ``docs/dep-opportunities/``.

Why a sibling: the original ``check_no_ai_slop.py`` is contract-pinned
to ``scripts/dayzero/launch_copy/`` and runs four gates beyond slop
(presence / signature footer / slop / anchor phrases). The OPP
artifact directory needs only the slop gate; widening the original's
paths would mix unrelated contract surfaces.

Run from repo root::

    uv run python scripts/audit/check_no_slop_opp.py
    uv run python scripts/audit/check_no_slop_opp.py --dir docs/dep-opportunities

Exit 0 = no slop. Exit 1 = at least one offending token or phrase.
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LAUNCH_SCRIPT = REPO_ROOT / "scripts" / "launch" / "check_no_ai_slop.py"
DEFAULT_DIR = REPO_ROOT / "docs" / "dep-opportunities"

DEEPLY_RE = re.compile(r"\bdeeply\s+\w+", re.IGNORECASE)


def _import_blocklist() -> tuple[str, ...]:
    """Pull AI_SLOP_BLOCKLIST from the canonical launch-side script via
    importlib so this script runs without the project package installed.
    """
    if not LAUNCH_SCRIPT.is_file():
        # Defensive fallback to literal blocklist copy if launch script
        # ever moves; CI will still gate correctly.
        return (
            "leverage", "synergize", "revolutionize", "game-changer",
            "next-generation", "cutting-edge", "seamless", "robust",
            "powerful", "intuitive", "delightful experience", "AI-powered",
            "harness the power", "unlock", "transformative", "paradigm",
        )
    spec = importlib.util.spec_from_file_location(
        "_launch_no_ai_slop", LAUNCH_SCRIPT,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load spec for {LAUNCH_SCRIPT}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.AI_SLOP_BLOCKLIST


AI_SLOP_BLOCKLIST: tuple[str, ...] = _import_blocklist()


def _display_path(path: Path) -> str:
    """Return a repo-relative path if possible, else the absolute path.
    tmp_path test fixtures are outside REPO_ROOT, so fall back gracefully.
    """
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def scan_file(path: Path) -> list[str]:
    """Return a list of error strings for the given markdown file.
    Empty list = clean."""
    text = path.read_text()
    text_lower = text.lower()
    errors: list[str] = []
    display = _display_path(path)
    for token in AI_SLOP_BLOCKLIST:
        if token.lower() in text_lower:
            errors.append(f"{display}: blocklist token '{token}' present")
    for m in DEEPLY_RE.finditer(text):
        errors.append(
            f"{display}: \\bdeeply\\s+\\w+ matched: '{m.group(0)}'"
        )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Phase 48 / OPP anti-slop checker (sibling)"
    )
    parser.add_argument(
        "--dir",
        type=Path,
        default=DEFAULT_DIR,
        help=f"directory to scan (default: {DEFAULT_DIR})",
    )
    args = parser.parse_args()

    if not args.dir.is_dir():
        print(f"error: directory not found: {args.dir}", file=sys.stderr)
        return 1

    md_files = sorted(args.dir.glob("*.md"))
    if not md_files:
        print(f"warning: no .md files in {args.dir}", file=sys.stderr)
        return 0

    all_errors: list[str] = []
    for md in md_files:
        all_errors.extend(scan_file(md))

    if all_errors:
        for e in all_errors:
            print(e, file=sys.stderr)
        print(
            f"\n{len(all_errors)} slop hit(s) across {len(md_files)} file(s) — "
            f"rewrite the offending lines and re-run",
            file=sys.stderr,
        )
        return 1

    print(f"anti-slop clean: {len(md_files)} file(s) in {_display_path(args.dir)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
