# SPDX-License-Identifier: Apache-2.0
"""Phase 49 / INSTALL-03 — Anti-slop gate for the installer + wizard surface.

Sibling checker per Phase 49 CONTEXT Decision 4. Imports the
``AI_SLOP_BLOCKLIST`` tuple from ``scripts/launch/check_no_ai_slop.py``
via importlib (single source of truth) and applies the 15-token +
``\\bdeeply\\s+\\w+`` regex gate to the Phase 49 surface:

  - installer/companion/onboarding_copy.json
  - installer/companion/README.md
  - installer/companion/uninstall.sh
  - installer/companion/uninstall.ps1
  - tauri/ui/src/wizard/copy.json (mirror of onboarding_copy.json)
  - tauri/ui/src/wizard/copy.ts
  - tauri/ui/src/wizard/step-forewarning.ts
  - tauri/ui/src/wizard/step-driver-fetch.ts
  - tauri/ui/src/wizard/step-48k-probe.ts
  - tauri/ui/src/wizard/uninstall-dialog.ts

Excluded: docs/internal/copy-substitutions.md — that file is the
preferred-substitution dictionary, so it intentionally contains the
forbidden tokens as table entries.

Why a sibling: the original ``check_no_ai_slop.py`` is contract-pinned
to ``scripts/dayzero/launch_copy/`` and runs four gates beyond slop
(presence / signature footer / slop / anchor phrases). The installer
wizard surface needs only the slop gate; widening the original's paths
mixes unrelated contract surfaces (Phase 47/48 sibling-pattern
invariant per memory ``feedback_no_gsd_orchestra_for_trivial_tweaks``).

On a hit: the report includes the preferred substitution looked up from
``docs/internal/copy-substitutions.md``.

Run from repo root::

    python scripts/audit/check_no_slop_install.py

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
SUBSTITUTIONS = REPO_ROOT / "docs" / "internal" / "copy-substitutions.md"

DEFAULT_TARGETS = [
    "installer/companion/onboarding_copy.json",
    "installer/companion/README.md",
    "installer/companion/uninstall.sh",
    "installer/companion/uninstall.ps1",
    "tauri/ui/src/wizard/copy.json",
    "tauri/ui/src/wizard/copy.ts",
    "tauri/ui/src/wizard/step-forewarning.ts",
    "tauri/ui/src/wizard/step-driver-fetch.ts",
    "tauri/ui/src/wizard/step-48k-probe.ts",
    "tauri/ui/src/wizard/uninstall-dialog.ts",
]
DEEPLY_RE = re.compile(r"\bdeeply\s+\w+", re.IGNORECASE)


def _import_blocklist() -> tuple[str, ...]:
    """Pull AI_SLOP_BLOCKLIST from the canonical launch-side script."""
    if not LAUNCH_SCRIPT.is_file():
        return (
            "leverage", "synergize", "revolutionize", "game-changer",
            "next-generation", "cutting-edge", "seamless", "robust",
            "powerful", "intuitive", "delightful experience", "AI-powered",
            "harness the power", "unlock", "transformative", "paradigm",
        )
    spec = importlib.util.spec_from_file_location("check_no_ai_slop", LAUNCH_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load {LAUNCH_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return tuple(module.AI_SLOP_BLOCKLIST)


def _load_substitutions() -> dict[str, str]:
    """Parse the substitutions table from copy-substitutions.md.

    Returns dict mapping lowercase forbidden -> preferred substitution.
    """
    if not SUBSTITUTIONS.is_file():
        return {}
    out: dict[str, str] = {}
    text = SUBSTITUTIONS.read_text()
    # Pull rows like "| seamless | one-tap | rationale |"
    row_re = re.compile(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*$", re.MULTILINE)
    for m in row_re.finditer(text):
        forbidden = m.group(1).strip().lower()
        preferred = m.group(2).strip()
        # Skip the header row + the divider row.
        if forbidden in {"forbidden", "---", "------", "------------", "----"}:
            continue
        if "-" * 3 in forbidden:
            continue
        out[forbidden] = preferred
    return out


def _scan_file(path: Path, blocklist: tuple[str, ...], subs: dict[str, str]) -> list[tuple[str, str]]:
    """Return list of (forbidden_token, preferred_substitution) hits."""
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    text_lc = text.lower()
    hits: list[tuple[str, str]] = []
    for token in blocklist:
        if token.lower() in text_lc:
            preferred = subs.get(token.lower(), "(rewrite)")
            hits.append((token, preferred))
    if DEEPLY_RE.search(text):
        hits.append(("deeply <word>", subs.get("deeply (anything)", "(rewrite)")))
    return hits


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--target",
        action="append",
        default=None,
        help="Override target file path (repeatable; default = Phase 49 surface)",
    )
    args = p.parse_args(argv)

    targets = args.target or DEFAULT_TARGETS
    blocklist = _import_blocklist()
    subs = _load_substitutions()

    any_hit = False
    for rel in targets:
        path = REPO_ROOT / rel
        hits = _scan_file(path, blocklist, subs)
        if hits:
            any_hit = True
            print(f"FAIL {rel}:", file=sys.stderr)
            for forbidden, preferred in hits:
                print(f"    forbidden: {forbidden!r} → preferred: {preferred!r}", file=sys.stderr)

    if any_hit:
        print(
            f"\nAnti-slop gate failed. See docs/internal/copy-substitutions.md "
            f"for full vocabulary.",
            file=sys.stderr,
        )
        return 1
    print(f"OK — {len(targets)} target(s) clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
