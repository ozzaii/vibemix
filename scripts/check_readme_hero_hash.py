# SPDX-License-Identifier: Apache-2.0
"""Phase 35 Plan 35-03 — README hero asset hash sync gate.

Pitfall P68: the README hero asset (`docs/assets/demo.mp4` once Phase 35
Kaan-action ASSETS-DEMO-CUT lands) silently drifts behind code. This
gate detects drift on every PR + nightly.

How it works
------------
The README hero block is delimited by HTML comments that carry the
expected SHA256 of the asset:

    <!-- vibemix:hero-start sha256=abc123... path=docs/assets/demo.mp4 -->
    <video ...>...</video>
    <!-- vibemix:hero-end -->

This script:
    1. Parses the start comment from README.md.
    2. Extracts sha256= and path= attrs.
    3. If sha256 == PLACEHOLDER: asset is not-yet-shipped, exit 0.
    4. Else hash the asset; compare; exit 1 on drift.

Run from repo root:
    python scripts/check_readme_hero_hash.py
    python scripts/check_readme_hero_hash.py --readme path/to/README.md
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Anchored comment regex — start delimiter only (we don't need the end).
# Attrs are space-separated key=value; values are non-whitespace.
_HERO_RE = re.compile(
    r"<!--\s*vibemix:hero-start\s+(?P<attrs>[^>]+?)-->",
    re.IGNORECASE,
)
_ATTR_RE = re.compile(r"(?P<k>[a-zA-Z0-9_-]+)\s*=\s*(?P<v>\S+)")

PLACEHOLDER_SENTINEL = "PLACEHOLDER"


def _parse_hero_block(readme_text: str) -> dict[str, str] | None:
    """Return the hero attr dict, or None if no hero block found."""
    m = _HERO_RE.search(readme_text)
    if not m:
        return None
    attrs = dict(_ATTR_RE.findall(m.group("attrs")))
    return attrs


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def check(readme: Path, repo_root: Path) -> tuple[int, str]:
    """Return (exit_code, message)."""
    if not readme.is_file():
        return 1, f"FAIL: README not found at {readme}"

    text = readme.read_text(encoding="utf-8")
    attrs = _parse_hero_block(text)
    if attrs is None:
        # No hero block — phase 35 hasn't landed yet OR the block was
        # accidentally stripped. Be loud about it so CI catches drift in
        # both directions.
        return 1, (
            "FAIL: README has no <!-- vibemix:hero-start ... --> block. "
            "Phase 35 ships this block; if you removed it, restore it."
        )

    sha = attrs.get("sha256")
    path = attrs.get("path")
    if sha is None or path is None:
        return 1, (
            "FAIL: README hero comment missing sha256= or path= attr. "
            f"Found attrs: {attrs}"
        )

    if sha == PLACEHOLDER_SENTINEL:
        return 0, (
            f"OK: hero asset pending Kaan-action (sha256=PLACEHOLDER). "
            f"Will activate when ASSETS-DEMO-CUT lands {path}."
        )

    asset = repo_root / path
    if not asset.is_file():
        return 1, (
            f"FAIL: README claims sha256={sha[:12]}... for {path}, "
            f"but {asset} does not exist. Either restore the asset OR "
            f"reset sha256=PLACEHOLDER until it lands (Pitfall P68)."
        )

    actual = _sha256(asset)
    if actual != sha:
        return 1, (
            f"FAIL: hero asset hash drift (Pitfall P68).\n"
            f"  README expects: {sha}\n"
            f"  {path} actual:  {actual}\n"
            f"Update the README hero comment to:\n"
            f"  <!-- vibemix:hero-start sha256={actual} path={path} -->"
        )

    return 0, f"OK: hero asset hash matches ({path} -> {sha[:12]}...)"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--readme",
        type=Path,
        default=REPO_ROOT / "README.md",
        help="Path to README.md (default: repo-root README.md).",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT,
        help="Repo root for resolving asset path (default: derived).",
    )
    args = parser.parse_args(argv)
    code, msg = check(args.readme, args.repo_root)
    stream = sys.stderr if code != 0 else sys.stdout
    print(msg, file=stream)
    return code


if __name__ == "__main__":
    sys.exit(main())
