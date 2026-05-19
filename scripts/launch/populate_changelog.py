# SPDX-License-Identifier: Apache-2.0
"""Phase 39 / Plan 39-06 — Changelog auto-populator.

REQ-IDs: SHIP-01 (ext)

Walks .planning/phases/*/[NN]-SUMMARY.md files, extracts phase name +
"What shipped" table for each Phase 27+ entry, and renders it into
`scripts/launch/changelog_template.md` (the {{ phase_summaries }}
block). Writes the result to `CHANGELOG-{tag}.md` at repo root.

Also pulls v2.0 close summary from `.planning/milestones/v2.0-ROADMAP.md`
when present (informational — the template already references it inline).
"""

from __future__ import annotations

import argparse
import datetime as _dt
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PHASES_DIR = REPO_ROOT / ".planning" / "phases"
TEMPLATE = REPO_ROOT / "scripts" / "launch" / "changelog_template.md"

SUMMARY_FILE_RE = re.compile(r"^(\d+)-SUMMARY\.md$")


_PHASE_DIR_RE = re.compile(r"^\d{2,3}-")


def _all_phase_dirs() -> list[Path]:
    """Live + archived phase dirs.

    Live: ``.planning/phases/<NN>-<slug>/``.
    Archived (current): ``.planning/milestones/<version>-phases/<NN>-<slug>/``.
    Archived (legacy v0.1.0): ``.planning/milestones/<version>/phases/<NN>-<slug>/``.

    A "phase dir" is identified by an ``NN-`` basename prefix so we
    don't sweep up milestone metadata files.
    """
    dirs: list[Path] = []
    if PHASES_DIR.exists():
        dirs.extend(
            p for p in PHASES_DIR.iterdir() if p.is_dir() and _PHASE_DIR_RE.match(p.name)
        )
    archived_root = REPO_ROOT / ".planning" / "milestones"
    if archived_root.exists():
        for milestone in archived_root.iterdir():
            if not milestone.is_dir():
                continue
            for child in milestone.iterdir():
                if child.is_dir() and _PHASE_DIR_RE.match(child.name):
                    dirs.append(child)
            nested = milestone / "phases"
            if nested.is_dir():
                for child in nested.iterdir():
                    if child.is_dir() and _PHASE_DIR_RE.match(child.name):
                        dirs.append(child)
    return sorted(set(dirs), key=lambda p: p.name)


def find_phase_summaries(min_phase: int = 27) -> list[Path]:
    """Return phase summary files for Phase {min_phase}+ in ascending order."""
    out: list[tuple[int, Path]] = []
    for sub in _all_phase_dirs():
        for f in sub.iterdir():
            m = SUMMARY_FILE_RE.match(f.name)
            if not m:
                continue
            phase_no = int(m.group(1))
            if phase_no < min_phase:
                continue
            out.append((phase_no, f))
    out.sort(key=lambda x: x[0])
    return [p for _, p in out]


def extract_phase_section(path: Path) -> tuple[str, str]:
    """Return (heading, what-shipped-snippet) for a phase summary file.

    heading: the first `# Phase NN Summary — Name` line, normalized.
    snippet: the markdown chunk from the "## What shipped" heading
             through the next H2 heading (exclusive). If absent, returns
             a placeholder note.
    """
    text = path.read_text(encoding="utf-8")
    # Heading — first `# ...` line.
    heading_match = re.search(r"^#\s+(.+?)\s*$", text, re.MULTILINE)
    heading = heading_match.group(1).strip() if heading_match else path.parent.name

    # "What shipped" section.
    snippet_start = text.find("## What shipped")
    if snippet_start == -1:
        # Fall back to first paragraph after frontmatter.
        return heading, "_See phase summary at " + path.relative_to(REPO_ROOT).as_posix() + "._"
    # Find next "## " after the start.
    after = text[snippet_start:]
    # Skip the first "## What shipped" line itself.
    rest = after.split("\n", 1)[1] if "\n" in after else ""
    next_h2 = re.search(r"\n##\s+", rest)
    snippet = rest[: next_h2.start()] if next_h2 else rest
    return heading, snippet.strip()


def render_phase_summaries(min_phase: int = 27) -> str:
    """Render the {{ phase_summaries }} block for the changelog template."""
    summaries = find_phase_summaries(min_phase=min_phase)
    if not summaries:
        return "_No phase summaries found._"
    blocks: list[str] = []
    for path in summaries:
        heading, snippet = extract_phase_section(path)
        blocks.append(f"### {heading}\n\n{snippet}\n")
    return "\n".join(blocks)


def render_changelog(
    tag: str,
    release_date: str | None = None,
    template_path: Path = TEMPLATE,
    min_phase: int = 27,
) -> str:
    if release_date is None:
        release_date = _dt.date.today().isoformat()
    body = template_path.read_text(encoding="utf-8")
    summaries = render_phase_summaries(min_phase=min_phase)
    body = body.replace("{{ tag }}", tag)
    body = body.replace("{{ release_date }}", release_date)
    body = body.replace("{{ phase_summaries }}", summaries)
    return body


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--tag", required=True, help="release tag, e.g. v2.1.0-rc1")
    p.add_argument("--release-date", default=None,
                   help="ISO date (default: today)")
    p.add_argument("--output", type=Path, default=None,
                   help="output path; default CHANGELOG-{tag}.md at repo root")
    p.add_argument("--template", type=Path, default=TEMPLATE)
    p.add_argument("--min-phase", type=int, default=27,
                   help="lowest phase number to include in the v2.1 section")
    p.add_argument("--dry-run", action="store_true",
                   help="print to stdout, do not write file")
    args = p.parse_args(argv)

    body = render_changelog(
        tag=args.tag,
        release_date=args.release_date,
        template_path=args.template,
        min_phase=args.min_phase,
    )

    if args.dry_run:
        print(body)
        return 0

    output = args.output or (REPO_ROOT / f"CHANGELOG-{args.tag}.md")
    output.write_text(body, encoding="utf-8")
    print(f"wrote: {output}  ({len(body)} bytes)")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
