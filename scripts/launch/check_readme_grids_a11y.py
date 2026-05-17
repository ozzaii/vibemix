# SPDX-License-Identifier: Apache-2.0
"""README grid accessibility + cell-count + balance gate (LAUNCH-03 + LAUNCH-04).

Phase 44 Plan 44-02: enforces that the two README grids — the
"Works alongside whatever DJ app you already use" section (LAUNCH-03)
and the "Supported controllers" section (LAUNCH-04) — stay structurally
sound forever:

1. **Alt-text gate** — every ``<img>`` in either grid carries a
   non-empty ``alt="..."`` attribute. No ``alt=""``, no missing ``alt``.
   A DJ visiting the README on a screen reader, a slow connection, or
   a markdown viewer that can't load remote images still gets a
   meaningful label.

2. **Cell-count gate** — the DJ-software grid has exactly 6 ``<img>``
   cells (rekordbox / Serato / Traktor / djay Pro / VirtualDJ / Mixxx —
   CONTEXT §LAUNCH-03 locked set); the controller grid has exactly 10
   cells (the canonical 10 controllers from
   ``src/vibemix/midi/controllers/*.json`` — CONTEXT §LAUNCH-04 locked
   set).

3. **AI-slop blocklist gate** — alt-text must contain none of the
   tokens pinned in :data:`_AI_SLOP_BLOCKLIST` (copied verbatim from
   the 44-01 hero-lock blocklist so the README stays slop-free on
   every surface, including alt-text). Catches drift like
   ``alt="powerful AI-powered controller for seamless mixing"``.

4. **Grid-balance gate** — DJ-software cell count must be divisible
   by 2 OR 3 (so it renders as 3x2 or 2x3). Controller cell count must
   be divisible by 2 OR 5 (so it renders as 5x2 or 2x5). A 7-cell
   "grid" with one orphan cell visually breaks on GitHub markdown.

Run from repo root::

    uv run python scripts/launch/check_readme_grids_a11y.py
    uv run python scripts/launch/check_readme_grids_a11y.py --readme path/to/README.md
    uv run python scripts/launch/check_readme_grids_a11y.py --quiet

Exit 0 = all four gates pass. Exit 1 = at least one failed; stderr
names which gate failed and what was found.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Grid section headings — matched against H2 lines in README.md to bound
# the per-grid <img> scan. Substring match against the line text after the
# leading ``## ``; case-insensitive so a future "## Works Alongside Whatever"
# title-case rewrite still binds.
# ---------------------------------------------------------------------------
DJ_SOFTWARE_HEADING_FRAGMENT: str = "works alongside"
CONTROLLERS_HEADING_FRAGMENT: str = "supported controllers"

# ---------------------------------------------------------------------------
# Locked cell counts — CONTEXT §LAUNCH-03 + §LAUNCH-04. The DJ-software list
# is the 6 mainstream apps Bravoh's first OSS launch targets; the controller
# list is the canonical 10 in src/vibemix/midi/controllers/*.json. Changing
# either set requires a planner decision (new requirement or scope change),
# not a "while I'm here" tweak.
# ---------------------------------------------------------------------------
DJ_SOFTWARE_CELL_COUNT: int = 6
CONTROLLERS_CELL_COUNT: int = 10

# ---------------------------------------------------------------------------
# Grid-balance divisors. 6 cells in 3x2 or 2x3 = divisible by 2 OR 3.
# 10 cells in 5x2 or 2x5 = divisible by 2 OR 5. Anything else suggests a
# missing or extra cell.
# ---------------------------------------------------------------------------
_DJ_SOFTWARE_BALANCE_DIVISORS: tuple[int, ...] = (2, 3)
_CONTROLLERS_BALANCE_DIVISORS: tuple[int, ...] = (2, 5)

# ---------------------------------------------------------------------------
# AI-slop blocklist for alt-text — copied verbatim from CONTEXT §specifics
# (same source as scripts/launch/check_readme_hero_lock._AI_SLOP_BLOCKLIST).
# We copy rather than import to keep this script standalone (the 44-01 hero
# lock has its own scope; this script enforces alt-text hygiene only).
# Case-insensitive substring match.
# ---------------------------------------------------------------------------
_AI_SLOP_BLOCKLIST: tuple[str, ...] = (
    "leverage",
    "synergize",
    "revolutionize",
    "game-changer",
    "next-generation",
    "cutting-edge",
    "seamless",
    "robust",
    "powerful",
    "intuitive",
    "delightful experience",
    "AI-powered",
    "harness the power",
    "unlock",
    "transformative",
    "paradigm",
)

# ---------------------------------------------------------------------------
# Regex for <img ...> tag extraction. Non-greedy match on attribute body so
# adjacent tags on the same line don't collapse into one match. Captures the
# full attribute body so the alt-extraction step can re-parse it.
# ---------------------------------------------------------------------------
_IMG_TAG_RE = re.compile(r"<img\b([^>]*)/?>", re.IGNORECASE)

# Alt attribute extractor. Matches alt="..." or alt='...' — single OR double
# quotes both legal in HTML. Capture group 1 is the alt value (may be empty).
_ALT_ATTR_RE = re.compile(
    r"""\balt\s*=\s*(?:"([^"]*)"|'([^']*)')""",
    re.IGNORECASE,
)


def _extract_section(text: str, heading_fragment: str) -> str | None:
    """Return the body of the H2 section whose heading contains
    ``heading_fragment`` (case-insensitive substring match), bounded by the
    next H2 line or end-of-file.

    Returns None if no matching heading is found.
    """
    lines = text.splitlines(keepends=True)
    needle = heading_fragment.lower()
    section_start: int | None = None
    section_end: int = len(lines)
    for idx, line in enumerate(lines):
        # An H2 line starts with "## " followed by text. "### " (H3) is NOT
        # an H2 boundary — we only break on sibling-level H2 headings.
        if not line.startswith("## "):
            continue
        if line.startswith("### "):  # defensive — shouldn't happen given prefix
            continue
        heading_text = line[3:].strip().lower()
        if section_start is None and needle in heading_text:
            section_start = idx + 1  # body starts AFTER the heading line
        elif section_start is not None:
            # next H2 = section boundary
            section_end = idx
            break
    if section_start is None:
        return None
    return "".join(lines[section_start:section_end])


def _extract_imgs(section_body: str) -> list[tuple[str, str | None]]:
    """Return a list of (raw_tag, alt_value_or_None) for every ``<img>`` in
    ``section_body``.

    ``alt_value_or_None`` is:
      - the alt string if the attribute is present (may be empty string)
      - ``None`` if the attribute is absent entirely (different failure mode
        than an empty-string alt — both fail but the diagnostic differs)
    """
    results: list[tuple[str, str | None]] = []
    for match in _IMG_TAG_RE.finditer(section_body):
        attr_body = match.group(1)
        alt_match = _ALT_ATTR_RE.search(attr_body)
        if alt_match is None:
            results.append((match.group(0), None))
        else:
            # Either group 1 (double-quoted) or group 2 (single-quoted) has the
            # value; the other is None. Empty string is a legal capture.
            value = alt_match.group(1) if alt_match.group(1) is not None else alt_match.group(2)
            results.append((match.group(0), value))
    return results


def _check_grid(
    section_body: str,
    *,
    expected_cells: int,
    balance_divisors: tuple[int, ...],
    section_label: str,
) -> list[str]:
    """Run alt-text + cell-count + balance + slop gates against one grid
    section. Return a list of failure strings (empty = all pass).
    """
    failures: list[str] = []
    imgs = _extract_imgs(section_body)

    # Cell-count gate.
    if len(imgs) != expected_cells:
        failures.append(
            f"{section_label} CELL_COUNT gate: expected exactly "
            f"{expected_cells} <img> cells, found {len(imgs)}"
        )

    # Grid-balance gate. Skip when the count is already wrong — the cell-count
    # failure already names the problem and a balance failure here would be
    # noise. If count is right, count must be divisible by at least one of
    # the listed divisors (sanity check — for 6 with (2, 3) this is always
    # true, but the check is correctness insurance for future scope changes).
    if len(imgs) == expected_cells:
        if not any(len(imgs) % d == 0 for d in balance_divisors):
            failures.append(
                f"{section_label} BALANCE gate: {len(imgs)} cells does not "
                f"divide evenly by any of {balance_divisors}; grid will "
                f"render unbalanced"
            )

    # Alt-text gate — per image. Report each violation separately so the
    # diagnostic is actionable.
    for raw_tag, alt in imgs:
        if alt is None:
            failures.append(
                f"{section_label} ALT gate: <img> missing alt attribute: "
                f"{raw_tag}"
            )
        elif alt.strip() == "":
            failures.append(
                f"{section_label} ALT gate: <img> has empty alt attribute: "
                f"{raw_tag}"
            )

    # AI-slop gate — per image alt. Only checks non-empty alts (an empty alt
    # is already flagged above; double-flagging is noise).
    for raw_tag, alt in imgs:
        if not alt:
            continue
        alt_lower = alt.lower()
        slop_hits = [t for t in _AI_SLOP_BLOCKLIST if t.lower() in alt_lower]
        if slop_hits:
            failures.append(
                f"{section_label} SLOP gate: alt-text contains forbidden "
                f"token(s) {slop_hits}: {raw_tag}"
            )

    return failures


def check_readme(readme_path: Path, *, quiet: bool = False) -> int:
    """Run all four gates against both grids in ``readme_path``. Return
    exit code (0 = pass; 1 = any failure).
    """
    if not readme_path.exists():
        if not quiet:
            print(f"ERROR: README not found: {readme_path}", file=sys.stderr)
        return 1

    text = readme_path.read_text(encoding="utf-8")
    failures: list[str] = []

    # DJ-software grid (LAUNCH-03).
    dj_section = _extract_section(text, DJ_SOFTWARE_HEADING_FRAGMENT)
    if dj_section is None:
        failures.append(
            f"DJ-SOFTWARE SECTION gate: no H2 heading containing "
            f"'{DJ_SOFTWARE_HEADING_FRAGMENT}' found in {readme_path}"
        )
    else:
        failures.extend(
            _check_grid(
                dj_section,
                expected_cells=DJ_SOFTWARE_CELL_COUNT,
                balance_divisors=_DJ_SOFTWARE_BALANCE_DIVISORS,
                section_label="DJ-SOFTWARE",
            )
        )

    # Controllers grid (LAUNCH-04).
    ctl_section = _extract_section(text, CONTROLLERS_HEADING_FRAGMENT)
    if ctl_section is None:
        failures.append(
            f"CONTROLLERS SECTION gate: no H2 heading containing "
            f"'{CONTROLLERS_HEADING_FRAGMENT}' found in {readme_path}"
        )
    else:
        failures.extend(
            _check_grid(
                ctl_section,
                expected_cells=CONTROLLERS_CELL_COUNT,
                balance_divisors=_CONTROLLERS_BALANCE_DIVISORS,
                section_label="CONTROLLERS",
            )
        )

    if failures:
        if not quiet:
            print(
                f"FAIL: README grid a11y check failed ({readme_path})",
                file=sys.stderr,
            )
            for f in failures:
                print(f"  - {f}", file=sys.stderr)
        return 1

    if not quiet:
        print(
            f"PASS: {readme_path} — DJ-software grid (6 cells) + "
            f"controllers grid (10 cells) — alt-text + balance + no slop"
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--readme",
        type=Path,
        default=Path("README.md"),
        help="README file to check (default: README.md)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress stdout/stderr (CI piping mode).",
    )
    args = parser.parse_args(argv)
    return check_readme(args.readme, quiet=args.quiet)


if __name__ == "__main__":
    sys.exit(main())
