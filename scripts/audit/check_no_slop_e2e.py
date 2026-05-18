# SPDX-License-Identifier: Apache-2.0
"""Phase 50 / E2E — Anti-slop gate for dist/e2e-macbook-runs/**/report.html.

Sibling checker per CONTEXT.md § Anti-Slop Coverage. Mirrors the Phase 48
``scripts/audit/check_no_slop_opp.py`` sibling-pattern precedent. Imports
the canonical ``AI_SLOP_BLOCKLIST`` from ``scripts/launch/check_no_ai_slop.py``
via importlib so this script runs without the project package installed.

Why a sibling: the original ``check_no_ai_slop.py`` is contract-pinned to
``scripts/dayzero/launch_copy/`` and runs four gates beyond slop. The e2e
report artifact directory needs only the slop gate; widening the original's
target paths would mix unrelated contract surfaces.

Run from repo root::

    uv run python scripts/audit/check_no_slop_e2e.py
    uv run python scripts/audit/check_no_slop_e2e.py --dir dist/e2e-macbook-runs

Exit 0 = no slop OR no report.html artifacts to scan. Exit 1 = at least one
offending token or phrase.
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LAUNCH_SCRIPT = REPO_ROOT / "scripts" / "launch" / "check_no_ai_slop.py"
DEFAULT_DIR = REPO_ROOT / "dist" / "e2e-macbook-runs"

DEEPLY_RE = re.compile(r"\bdeeply\s+\w+", re.IGNORECASE)


def _import_blocklist() -> tuple[str, ...]:
    """Pull AI_SLOP_BLOCKLIST from the canonical launch-side script via
    importlib so this script runs without the project package installed.
    """
    if not LAUNCH_SCRIPT.is_file():
        # Defensive fallback if launch script ever moves; CI still gates.
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
    """Return a repo-relative path if possible, else the absolute path."""
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def scan_file(path: Path) -> list[str]:
    """Return a list of error strings for the given report.html file.
    Word-boundary aware: 'deep' does NOT match 'deeply' token.
    Empty list = clean.
    """
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []
    display = _display_path(path)
    for token in AI_SLOP_BLOCKLIST:
        # Word-boundary match so substrings (e.g. 'deep' in 'deepwater') don't
        # false-positive against the 'deeply' token.
        pattern = re.compile(r"\b" + re.escape(token) + r"\b", re.IGNORECASE)
        for m in pattern.finditer(text):
            line_no = text.count("\n", 0, m.start()) + 1
            errors.append(
                f"{display}:{line_no}: blocklist token '{token}' present"
            )
    for m in DEEPLY_RE.finditer(text):
        line_no = text.count("\n", 0, m.start()) + 1
        errors.append(
            f"{display}:{line_no}: \\bdeeply\\s+\\w+ matched: '{m.group(0)}'"
        )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Phase 50 / E2E anti-slop sibling checker"
    )
    parser.add_argument(
        "--dir",
        type=Path,
        default=DEFAULT_DIR,
        help=f"directory to scan recursively (default: {DEFAULT_DIR})",
    )
    args = parser.parse_args()

    if not args.dir.is_dir():
        # No e2e runs yet — CI no-op. Plan 02 truths line 7.
        print(
            f"no e2e runs found at {_display_path(args.dir)} — exiting clean",
            file=sys.stderr,
        )
        return 0

    html_files = sorted(args.dir.rglob("report.html"))
    if not html_files:
        print(
            f"no report.html files in {_display_path(args.dir)} — exiting clean",
            file=sys.stderr,
        )
        return 0

    all_errors: list[str] = []
    for html in html_files:
        all_errors.extend(scan_file(html))

    if all_errors:
        for e in all_errors:
            print(e, file=sys.stderr)
        print(
            f"\n{len(all_errors)} slop hit(s) across {len(html_files)} report.html file(s) "
            f"— rewrite the offending lines and re-run",
            file=sys.stderr,
        )
        return 1

    print(
        f"anti-slop clean: {len(html_files)} report.html file(s) in {_display_path(args.dir)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
