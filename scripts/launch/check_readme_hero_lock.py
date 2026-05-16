# SPDX-License-Identifier: Apache-2.0
"""README hero one-liner lock + AI-slop blocklist gate (LAUNCH-01).

Phase 44 Plan 44-01: enforces that ``README.md`` keeps the locked hero
one-liner verbatim, surfaces the 5 anchor phrases of the "No AI slop"
hook section, and stays free of marketing-slop tokens forever.

The three gates run together as a single CI gate so drift on any axis
fails loud:

1. **Locked one-liner gate** — the phrase
   ``the only AI co-host that actually listens to your set`` MUST appear
   exactly once. (Pinned in CONTEXT §specifics; ROADMAP Phase 44 success
   criterion 1.) No variations, no tweaks — if Francesco wants a
   reword, that's a deliberate code change with planner sign-off, not
   a silent drift.

2. **Anchor phrases gate** — all five anchor phrases from
   CONTEXT §specifics positive list MUST appear at least once
   (case-insensitive):

   - ``real DJ friend in your ear``
   - ``built by DJs``
   - ``your audio doesn't leave``
   - ``open source`` OR ``open-source``
   - ``Mac + Windows``

3. **AI-slop blocklist gate** — none of the tokens in
   :data:`_AI_SLOP_BLOCKLIST` may appear in README.md, and the regex
   ``\\bdeeply\\s+\\w+`` (catching "deeply integrated", "deeply
   thoughtful", etc.) must match zero times. The blocklist is pinned
   verbatim from CONTEXT §specifics — additions or removals require
   a planner decision, not a "while I'm here" tweak.

Run from repo root::

    uv run python scripts/launch/check_readme_hero_lock.py
    uv run python scripts/launch/check_readme_hero_lock.py --readme path/to/README.md
    uv run python scripts/launch/check_readme_hero_lock.py --quiet

Exit 0 = all three gates pass. Exit 1 = at least one gate failed
(stderr names which gate and what was found/missing).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Locked one-liner — CONTEXT §specifics, ROADMAP Phase 44 success criterion 1.
# Memory: project_anti_slop_grounded_gemini_thesis — this is the public
# anti-slop framing for the OSS launch. Verbatim, no variations.
# ---------------------------------------------------------------------------
LOCKED_ONE_LINER: str = "the only AI co-host that actually listens to your set"

# ---------------------------------------------------------------------------
# Anchor phrases — CONTEXT §specifics positive list. All 5 must appear at
# least once (case-insensitive). "open source" / "open-source" are accepted
# interchangeably because both spellings are idiomatic. The phrases are
# matched literally; substring match is sufficient (a paragraph that says
# "your audio doesn't leave your machine" satisfies "your audio doesn't
# leave").
# ---------------------------------------------------------------------------
_ANCHOR_PHRASES: tuple[tuple[str, ...], ...] = (
    ("real DJ friend in your ear",),
    ("built by DJs",),
    ("your audio doesn't leave",),
    # "open source" OR "open-source" — either spelling satisfies the anchor
    ("open source", "open-source"),
    ("Mac + Windows",),
)

# ---------------------------------------------------------------------------
# AI-slop blocklist — CONTEXT §specifics negative list. Pinned verbatim.
# Case-insensitive substring match. The "deeply <word>" regex below catches
# adverb-construction slop ("deeply integrated", "deeply thoughtful",
# "deeply respected") which the literal blocklist can't enumerate.
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

# Regex for "deeply <adverb-construction>" slop. \b matches word boundary so
# "deeply" inside a longer word (e.g. "indeeply" — not a real word, but
# defensive) won't trigger. \s+ requires at least one whitespace then \w+
# requires a word character following.
_DEEPLY_RE = re.compile(r"\bdeeply\s+\w+", re.IGNORECASE)


def _count_occurrences(text: str, needle: str) -> int:
    """Count occurrences of ``needle`` in ``text`` (case-sensitive for the
    locked one-liner — Francesco's reword would otherwise slip through).
    """
    return text.count(needle)


def _has_anchor(text_lower: str, variants: tuple[str, ...]) -> bool:
    """True if any variant of an anchor phrase appears in ``text_lower``."""
    return any(v.lower() in text_lower for v in variants)


def check_readme(readme_path: Path, *, quiet: bool = False) -> int:
    """Run all three gates against ``readme_path``. Return exit code.

    Returns 0 on full pass; 1 on any gate failure. Prints gate-specific
    diagnostics to stderr unless ``quiet`` is True.
    """
    if not readme_path.exists():
        if not quiet:
            print(f"ERROR: README not found: {readme_path}", file=sys.stderr)
        return 1

    text = readme_path.read_text(encoding="utf-8")
    text_lower = text.lower()
    failures: list[str] = []

    # Gate 1: locked one-liner (exactly once, case-sensitive)
    n_locked = _count_occurrences(text, LOCKED_ONE_LINER)
    if n_locked != 1:
        failures.append(
            f"LOCKED_ONE_LINER gate: expected exactly 1 occurrence of "
            f"'{LOCKED_ONE_LINER}', found {n_locked}"
        )

    # Gate 2: anchor phrases (case-insensitive, all 5 must appear)
    missing_anchors: list[str] = []
    for variants in _ANCHOR_PHRASES:
        if not _has_anchor(text_lower, variants):
            missing_anchors.append(" OR ".join(f"'{v}'" for v in variants))
    if missing_anchors:
        failures.append(
            "ANCHOR_PHRASES gate: missing required anchor phrase(s): "
            + ", ".join(missing_anchors)
        )

    # Gate 3a: AI-slop blocklist (case-insensitive substring)
    slop_hits: list[str] = []
    for token in _AI_SLOP_BLOCKLIST:
        if token.lower() in text_lower:
            slop_hits.append(token)
    if slop_hits:
        failures.append(
            "AI_SLOP_BLOCKLIST gate: found forbidden token(s): "
            + ", ".join(f"'{t}'" for t in slop_hits)
        )

    # Gate 3b: "deeply <word>" regex (case-insensitive)
    deeply_hits = _DEEPLY_RE.findall(text)
    if deeply_hits:
        failures.append(
            "AI_SLOP_DEEPLY gate: found 'deeply <word>' construction(s): "
            + ", ".join(f"'{h}'" for h in deeply_hits)
        )

    if failures:
        if not quiet:
            print(f"FAIL: README hero lock check failed ({readme_path})", file=sys.stderr)
            for f in failures:
                print(f"  - {f}", file=sys.stderr)
        return 1

    if not quiet:
        print(
            f"PASS: {readme_path} — locked one-liner + 5 anchors + 0 slop hits"
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
