# SPDX-License-Identifier: Apache-2.0
"""Phase 39 / Plan 39-02 — Feature matrix auto-syncer for README.md.

REQ-IDs: SHIP-02
Pitfall: P68 (README hero / feature drift detection).

Walks `.planning/ROADMAP.md` for completed phase entries matching:

    - [x] **Phase NN: Name** — short description ...

Emits a markdown table between the AUTO-GEN markers in README.md:

    <!-- AUTO-GEN: feature-matrix START -->
    | Phase | Name | What shipped |
    |---|---|---|
    | 27 | Eval Harness ... | ... |
    ...
    <!-- AUTO-GEN: feature-matrix END -->

Run as part of pre-release prep so the README always reflects the
shipped surface. CI verifies the in-tree README matches the generator
output via tests/repo/test_readme_feature_matrix_sync.py.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ROADMAP = REPO_ROOT / ".planning" / "ROADMAP.md"
README = REPO_ROOT / "README.md"

START_MARKER = "<!-- AUTO-GEN: feature-matrix START"
END_MARKER = "<!-- AUTO-GEN: feature-matrix END -->"

# Matches: `- [x] **Phase N: Name** — short desc`
# Or:      `- [x] Phase N: Name (... ) — short desc`
# Splits ONLY on em-dash (—), not hyphens, because phase names contain hyphens
# (e.g. "Eval Harness + v2.0 Carry-Forward Close-Out").
PHASE_LINE_RE = re.compile(
    r"^- \[x\] (?:\*\*)?Phase\s+(\d+):\s*(.+?)(?:\*\*)?\s+—\s+(.+?)\s*$"
)


def parse_completed_phases(roadmap_text: str) -> list[tuple[int, str, str]]:
    """Return [(phase_no, name, short_desc), ...] for v2.1 phases (27+).

    v0.1.0 + v2.0 phases (<27) are excluded — this is the v2.1 surface.
    """
    rows: list[tuple[int, str, str]] = []
    for line in roadmap_text.splitlines():
        m = PHASE_LINE_RE.match(line)
        if not m:
            continue
        phase_no = int(m.group(1))
        if phase_no < 27:
            continue  # v0.1.0 + v2.0 are not v2.1 surface.
        name = m.group(2).strip()
        desc = m.group(3).strip()
        # Trim the description at the first " REQ count" / " Pitfalls" /
        # " Shipped " marker so the cell stays compact.
        for marker in (". REQ count:", " REQ count:", ". Pitfalls:", " Pitfalls:", ". Shipped ", " Shipped "):
            idx = desc.find(marker)
            if idx != -1:
                desc = desc[:idx].rstrip(" .")
                break
        rows.append((phase_no, name, desc))
    return rows


def render_table(rows: list[tuple[int, str, str]]) -> str:
    """Render the markdown table to slot between the AUTO-GEN markers."""
    out = ["| Phase | Surface | What shipped |", "|---|---|---|"]
    for phase_no, name, desc in rows:
        # Escape pipes inside cells.
        safe_name = name.replace("|", "\\|")
        safe_desc = desc.replace("|", "\\|")
        out.append(f"| {phase_no} | {safe_name} | {safe_desc} |")
    return "\n".join(out)


def assemble_block(rows: list[tuple[int, str, str]]) -> str:
    """Return the full replacement block (start marker, body, end marker)."""
    table = render_table(rows)
    return (
        f"{START_MARKER} — auto-populated by scripts/launch/sync_feature_matrix.py -->\n"
        f"\n{table}\n\n"
        f"{END_MARKER}"
    )


def splice_into_readme(readme_text: str, replacement_block: str) -> str:
    """Replace everything between (and including) the AUTO-GEN markers."""
    start_idx = readme_text.find(START_MARKER)
    end_idx = readme_text.find(END_MARKER)
    if start_idx == -1 or end_idx == -1:
        raise ValueError(
            "README.md missing AUTO-GEN markers — expected both "
            f"'{START_MARKER}' and '{END_MARKER}'"
        )
    end_idx += len(END_MARKER)
    return readme_text[:start_idx] + replacement_block + readme_text[end_idx:]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--check", action="store_true",
                   help="Exit 1 if the README is out of sync (CI mode).")
    p.add_argument("--write", action="store_true",
                   help="Write the updated README in place.")
    p.add_argument("--readme", type=Path, default=README)
    p.add_argument("--roadmap", type=Path, default=ROADMAP)
    args = p.parse_args(argv)

    roadmap_text = args.roadmap.read_text(encoding="utf-8")
    rows = parse_completed_phases(roadmap_text)
    if not rows:
        print("::warning::no completed Phase 27+ entries found in ROADMAP.md")
        return 0

    readme_text = args.readme.read_text(encoding="utf-8")
    new_block = assemble_block(rows)
    new_readme = splice_into_readme(readme_text, new_block)

    if args.check:
        if new_readme != readme_text:
            print("::error::README.md feature matrix out of sync. "
                  "Run `python scripts/launch/sync_feature_matrix.py --write`.",
                  file=sys.stderr)
            return 1
        print("README.md feature matrix in sync.")
        return 0

    if args.write:
        args.readme.write_text(new_readme, encoding="utf-8")
        print(f"wrote: {args.readme}  ({len(rows)} phase rows)")
        return 0

    # Default: print to stdout.
    print(new_readme)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
