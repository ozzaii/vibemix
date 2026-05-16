#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""scripts/launch/check_launch_docs.py — Phase 44 / LAUNCH-09 + LAUNCH-10
structural gate for ``docs/launch-prep/OUTREACH-CALENDAR.md`` and
``docs/launch-prep/LAUNCH-SEQUENCE.md``.

Asserts:

a. ``OUTREACH-CALENDAR.md`` exists and contains >=7 status-checkbox
   blocks (3 editorial + 3 subreddit + 1 Discord T-3 — CONTEXT §LAUNCH-09).
   A "checkbox block" is any line containing the canonical 4-state
   pattern ``☐ Drafted`` (with or without leading list marker / bold
   ``**Status:**`` wrapper).
b. ``LAUNCH-SEQUENCE.md`` exists and contains exactly 7 timeline-row
   headings of the form ``^## T[-+]`` (T-7, T-3, T-0, T+24h, T+72h,
   T+7d, T+30 — CONTEXT §LAUNCH-10). The PLAN.md verify line uses
   ``^## T-`` but that regex literally only matches T-N rows and would
   miss the T+24h/T+72h/T+7d/T+30 rows the same plan prescribes; the
   relaxed ``^## T[-+]`` matches all 7 plan-prescribed rows (deviation
   recorded in 44-07-SUMMARY.md).
c. ``LAUNCH-SEQUENCE.md`` cross-references >=3 distinct
   ``§LAUNCH-0[6-9]`` runbook anchors (KAAN-ACTION-LEGAL.md sections).
d. Both docs are AI-slop-blocklist clean (case-insensitive substring
   check + ``\\bdeeply\\s+\\w+`` regex). The blocklist is sourced from
   ``scripts.launch.check_no_ai_slop`` (Plan 44-05 single-source-of-
   truth) when that module is on disk; otherwise an inline canonical
   copy from CONTEXT §LAUNCH-07 is used (Plan 44-05 lives in a parallel
   Wave-1 worktree and may not have merged yet).
e. ``README.md`` references both new docs by filename so the Phase
   43-09 index doc stays the source-of-truth entry point for the
   launch-prep package.

CLI:
    --launch-prep-dir PATH   default: docs/launch-prep
    --quiet                  suppress per-check stdout (errors still go to stderr)

Exit codes:
    0  all 5 gates pass
    1  one or more gates fail (specific failure printed to stderr)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LAUNCH_PREP = REPO_ROOT / "docs" / "launch-prep"

# Hard-pinned contract counts from CONTEXT §LAUNCH-09 + §LAUNCH-10.
REQUIRED_CHECKBOX_BLOCKS: int = 7  # 3 editorial + 3 subreddit + 1 Discord T-3
REQUIRED_T_ROWS: int = 7  # T-7, T-3, T-0, T+24h, T+72h, T+7d, T+30
REQUIRED_LAUNCH_ANCHORS: int = 3  # >=3 distinct §LAUNCH-0[6-9] cross-refs

# Canonical AI-slop blocklist (CONTEXT §LAUNCH-07). Mirrors the list Plan
# 44-05 ships as scripts.launch.check_no_ai_slop.AI_SLOP_BLOCKLIST; we
# import 44-05's module when it is on disk, fall back to this inline copy
# otherwise (Wave-1 parallel-worktree safety).
_INLINE_AI_SLOP_BLOCKLIST: tuple[str, ...] = (
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

# Inline canonical anchor phrases (positive — at least one must appear in
# the launch-copy lock per CONTEXT §LAUNCH-07). Not enforced here (the
# launch-prep docs are operator-facing, not customer-facing copy), but
# exposed for callers that want to spot-check them.
_INLINE_ANCHOR_PHRASES: tuple[str, ...] = (
    "real DJ friend in your ear",
    "built by DJs",
    "your audio doesn't leave",
    "open-source",
    "open source",
    "Mac + Windows",
)


def _load_blocklist() -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return (AI_SLOP_BLOCKLIST, ANCHOR_PHRASES).

    Prefers Plan 44-05's check_no_ai_slop module (single source of truth)
    when it lives on disk; falls back to the inline canonical copy from
    CONTEXT §LAUNCH-07 when Plan 44-05 has not yet merged to this
    worktree (Wave-1 parallel execution safety).
    """
    try:
        from scripts.launch.check_no_ai_slop import (  # type: ignore[import-not-found]
            AI_SLOP_BLOCKLIST as _UPSTREAM_BLOCKLIST,
        )

        try:
            from scripts.launch.check_no_ai_slop import (  # type: ignore[import-not-found]
                ANCHOR_PHRASES as _UPSTREAM_ANCHORS,
            )
        except ImportError:
            _UPSTREAM_ANCHORS = _INLINE_ANCHOR_PHRASES

        return tuple(_UPSTREAM_BLOCKLIST), tuple(_UPSTREAM_ANCHORS)
    except ImportError:
        return _INLINE_AI_SLOP_BLOCKLIST, _INLINE_ANCHOR_PHRASES


AI_SLOP_BLOCKLIST, ANCHOR_PHRASES = _load_blocklist()

_DEEPLY_ADVERB_RE = re.compile(r"\bdeeply\s+\w+", re.IGNORECASE)
_CHECKBOX_BLOCK_RE = re.compile(r"☐\s*Drafted")
_T_ROW_HEADING_RE = re.compile(r"^##\s+T[-+]", re.MULTILINE)
_LAUNCH_ANCHOR_RE = re.compile(r"§LAUNCH-0[6-9]")


def count_checkbox_blocks(text: str) -> int:
    """Return the number of ``☐ Drafted`` status-checkbox blocks in TEXT."""
    return len(_CHECKBOX_BLOCK_RE.findall(text))


def count_t_rows(text: str) -> int:
    """Return the number of ``## T[-+]...`` timeline-row headings in TEXT.

    The PLAN.md ``<verify>`` block uses the literal regex ``^## T-`` but
    the plan also prescribes T+24h, T+72h, T+7d, T+30 rows — those start
    with ``## T+``, not ``## T-``. The relaxed ``^## T[-+]`` regex used
    here matches all 7 plan-prescribed rows; the literal verify regex
    would only see 3 (deviation recorded in 44-07-SUMMARY.md).
    """
    return len(_T_ROW_HEADING_RE.findall(text))


def distinct_launch_anchors(text: str) -> set[str]:
    """Return the set of distinct ``§LAUNCH-0[6-9]`` anchors in TEXT."""
    return set(_LAUNCH_ANCHOR_RE.findall(text))


def scan_ai_slop(text: str, blocklist: Iterable[str] = ()) -> list[str]:
    """Return the list of slop tokens / phrases found in TEXT.

    Case-insensitive substring match for every entry in BLOCKLIST plus
    the ``\\bdeeply\\s+\\w+`` regex (the "deeply X" adverb-as-adjective
    pattern called out in CONTEXT §LAUNCH-07). Empty list means clean.
    """
    if not blocklist:
        blocklist = AI_SLOP_BLOCKLIST
    text_lower = text.lower()
    hits: list[str] = []
    for token in blocklist:
        if token.lower() in text_lower:
            hits.append(token)
    deeply_hits = _DEEPLY_ADVERB_RE.findall(text)
    hits.extend(deeply_hits)
    return hits


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _check_outreach_calendar(
    path: Path,
    *,
    quiet: bool,
) -> list[str]:
    """Return list of failure messages (empty if all checks pass)."""
    failures: list[str] = []
    if not path.is_file():
        failures.append(f"missing file: {path}")
        return failures
    text = _read(path)

    n = count_checkbox_blocks(text)
    if not quiet:
        print(f"[outreach-calendar] checkbox blocks: {n} (need >= {REQUIRED_CHECKBOX_BLOCKS})")
    if n < REQUIRED_CHECKBOX_BLOCKS:
        failures.append(
            f"OUTREACH-CALENDAR.md: only {n} '☐ Drafted' checkbox block(s); "
            f"need >= {REQUIRED_CHECKBOX_BLOCKS} (3 editorial + 3 subreddit + 1 Discord T-3)"
        )

    slop_hits = scan_ai_slop(text)
    if slop_hits:
        failures.append(
            "OUTREACH-CALENDAR.md: AI-slop tokens detected: "
            + ", ".join(sorted({h.lower() for h in slop_hits}))
        )
    return failures


def _check_launch_sequence(
    path: Path,
    *,
    quiet: bool,
) -> list[str]:
    failures: list[str] = []
    if not path.is_file():
        failures.append(f"missing file: {path}")
        return failures
    text = _read(path)

    n_rows = count_t_rows(text)
    if not quiet:
        print(f"[launch-sequence] T-rows: {n_rows} (need exactly {REQUIRED_T_ROWS})")
    if n_rows != REQUIRED_T_ROWS:
        failures.append(
            f"LAUNCH-SEQUENCE.md: {n_rows} '## T...' row(s); "
            f"need exactly {REQUIRED_T_ROWS} (T-7, T-3, T-0, T+24h, T+72h, T+7d, T+30)"
        )

    anchors = distinct_launch_anchors(text)
    if not quiet:
        print(
            f"[launch-sequence] distinct §LAUNCH-0[6-9] anchors: {len(anchors)} "
            f"(need >= {REQUIRED_LAUNCH_ANCHORS}; saw {sorted(anchors)})"
        )
    if len(anchors) < REQUIRED_LAUNCH_ANCHORS:
        failures.append(
            f"LAUNCH-SEQUENCE.md: only {len(anchors)} distinct §LAUNCH-0[6-9] "
            f"anchor(s) ({sorted(anchors) or '(none)'}); need >= "
            f"{REQUIRED_LAUNCH_ANCHORS}"
        )

    slop_hits = scan_ai_slop(text)
    if slop_hits:
        failures.append(
            "LAUNCH-SEQUENCE.md: AI-slop tokens detected: "
            + ", ".join(sorted({h.lower() for h in slop_hits}))
        )
    return failures


def _check_readme(path: Path, *, quiet: bool) -> list[str]:
    failures: list[str] = []
    if not path.is_file():
        failures.append(f"missing file: {path}")
        return failures
    text = _read(path)
    for filename in ("OUTREACH-CALENDAR.md", "LAUNCH-SEQUENCE.md"):
        if filename not in text:
            failures.append(
                f"README.md: missing reference to {filename}; the launch-prep "
                f"index must cross-link both Phase 44 docs"
            )
    if not quiet:
        print(f"[readme] cross-links present: {len(failures) == 0}")
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--launch-prep-dir",
        default=str(DEFAULT_LAUNCH_PREP),
        help="path to docs/launch-prep (default: %(default)s)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="suppress per-check stdout; failures still printed to stderr",
    )
    args = parser.parse_args(argv)

    launch_prep = Path(args.launch_prep_dir)
    failures: list[str] = []
    failures.extend(
        _check_outreach_calendar(launch_prep / "OUTREACH-CALENDAR.md", quiet=args.quiet)
    )
    failures.extend(
        _check_launch_sequence(launch_prep / "LAUNCH-SEQUENCE.md", quiet=args.quiet)
    )
    failures.extend(_check_readme(launch_prep / "README.md", quiet=args.quiet))

    if failures:
        for f in failures:
            print(f"[check_launch_docs] FAIL: {f}", file=sys.stderr)
        return 1
    if not args.quiet:
        print("[check_launch_docs] OK — all gates pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
