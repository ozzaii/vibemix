# SPDX-License-Identifier: Apache-2.0
"""SHIP-TWEET 5-channel AI-slop gate + anchor + signature-footer lock (LAUNCH-07).

Phase 44 Plan 44-05: enforces that the 5 launch-copy files under
``scripts/dayzero/launch_copy/`` stay free of AI-slop language, carry
the CONTEXT §specifics positive anchor phrases at least once across the
combined corpus, and ship with the Kaan + Francesco sign-off footer
markers required for the §LAUNCH-07 Kaan-discharge.

Four gates, single CI surface:

1. **Presence gate** — all 5 channel files
   (twitter / instagram / linkedin / reddit / discord) exist under the
   target directory.

2. **Signature footer gate** — each of the 5 files contains BOTH a
   ``Kaan signature:`` line AND a ``Francesco signature:`` line. The
   signature values themselves may be blank (that's the
   ``§LAUNCH-07`` Kaan + Francesco discharge — engineering's gate only
   pins that the FOOTER STRUCTURE is present, not that humans have
   signed yet).

3. **AI-slop blocklist gate** — none of the 16
   :data:`AI_SLOP_BLOCKLIST` tokens (CONTEXT §specifics verbatim,
   case-insensitive substring) appears in ANY of the 5 files; and the
   ``\\bdeeply\\s+\\w+`` regex matches zero times across the combined
   corpus.

4. **Anchor phrase gate** — across the 5 files COMBINED (not per-file),
   each of the 5 :data:`ANCHOR_PHRASES` from CONTEXT §specifics appears
   at least once (case-insensitive). ``open source`` / ``open-source``
   are accepted interchangeably.

The :data:`AI_SLOP_BLOCKLIST` and :data:`ANCHOR_PHRASES` constants are
exported as the single source of truth across the launch-check family
(must-haves truth: "AI-slop blocklist is a single source of truth —
exposed as a module-level tuple"). Sibling scripts (e.g.
``check_readme_hero_lock.py``) may keep their own local copies for
locality of reasoning but cross-channel sweeps re-import from here.

Run from repo root::

    uv run python scripts/launch/check_no_ai_slop.py
    uv run python scripts/launch/check_no_ai_slop.py --dir path/to/copy
    uv run python scripts/launch/check_no_ai_slop.py --quiet

Exit 0 = all 4 gates pass. Exit 1 = at least one gate failed (stderr
names which gate failed and on which file / phrase).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Pinned constants — CONTEXT §specifics verbatim. Do NOT extend or trim
# without a planner decision documented in the next phase's CONTEXT.md.
# ---------------------------------------------------------------------------

LAUNCH_COPY_DIR: Path = Path("scripts/dayzero/launch_copy")

# Ordered tuple so failure messages are deterministic.
LAUNCH_COPY_FILES: tuple[str, ...] = (
    "twitter.txt",
    "instagram.txt",
    "linkedin.txt",
    "reddit.txt",
    "discord.txt",
)

# AI-slop blocklist — CONTEXT §specifics negative list, verbatim 16 tokens.
# Case-insensitive substring match. The "deeply <word>" regex below catches
# adverb-construction slop ("deeply integrated", "deeply thoughtful") that
# the literal blocklist can't enumerate.
AI_SLOP_BLOCKLIST: tuple[str, ...] = (
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

# Anchor phrases — CONTEXT §specifics positive list. Each entry is a tuple
# of accepted spelling variants; the first variant is canonical. ``open
# source`` / ``open-source`` are accepted interchangeably because both are
# idiomatic.
ANCHOR_PHRASES: tuple[tuple[str, ...], ...] = (
    ("real DJ friend in your ear",),
    ("built by DJs",),
    ("your audio doesn't leave",),
    ("open source", "open-source"),
    ("Mac + Windows",),
)

# Signature footer markers — both must appear (in any order) in every file.
# The signature VALUES themselves may be blank (Kaan-discharge concern).
_KAAN_SIG_MARKER: str = "Kaan signature:"
_FRANCESCO_SIG_MARKER: str = "Francesco signature:"

# Regex for "deeply <word>" slop. \b matches word boundary; \s+ requires
# at least one whitespace; \w+ requires a word character following.
_DEEPLY_RE = re.compile(r"\bdeeply\s+\w+", re.IGNORECASE)


def _has_anchor(text_lower: str, variants: tuple[str, ...]) -> bool:
    """True if any variant of an anchor phrase appears in ``text_lower``."""
    return any(v.lower() in text_lower for v in variants)


def check_launch_copy(launch_dir: Path, *, quiet: bool = False) -> int:
    """Run all 4 gates against ``launch_dir``. Return exit code.

    Returns 0 on full pass; 1 on any gate failure. Prints gate-specific
    diagnostics to stderr unless ``quiet`` is True.
    """
    failures: list[str] = []

    # Gate 1: presence — all 5 files must exist
    present_files: dict[str, Path] = {}
    missing_files: list[str] = []
    for fname in LAUNCH_COPY_FILES:
        fpath = launch_dir / fname
        if fpath.exists():
            present_files[fname] = fpath
        else:
            missing_files.append(fname)
    if missing_files:
        failures.append(
            "PRESENCE gate: missing launch-copy file(s): "
            + ", ".join(missing_files)
        )

    # Read every file we have (even if some are missing) so we can still
    # report on signature / slop / anchor issues in the rest.
    file_texts: dict[str, str] = {
        fname: fpath.read_text(encoding="utf-8")
        for fname, fpath in present_files.items()
    }

    # Gate 2: signature footer — both markers in every present file
    missing_sigs: list[str] = []
    for fname, text in file_texts.items():
        has_kaan = _KAAN_SIG_MARKER in text
        has_fran = _FRANCESCO_SIG_MARKER in text
        if not (has_kaan and has_fran):
            missing = []
            if not has_kaan:
                missing.append(f"'{_KAAN_SIG_MARKER}'")
            if not has_fran:
                missing.append(f"'{_FRANCESCO_SIG_MARKER}'")
            missing_sigs.append(f"{fname} (missing {', '.join(missing)})")
    if missing_sigs:
        failures.append(
            "SIGNATURE_FOOTER gate: missing signature marker(s): "
            + "; ".join(missing_sigs)
        )

    # Gate 3a: AI-slop blocklist — no token may appear in ANY file
    slop_hits: list[str] = []
    for fname, text in file_texts.items():
        text_lower = text.lower()
        for token in AI_SLOP_BLOCKLIST:
            if token.lower() in text_lower:
                slop_hits.append(f"{fname}: '{token}'")
    if slop_hits:
        failures.append(
            "AI_SLOP_BLOCKLIST gate: found forbidden token(s): "
            + ", ".join(slop_hits)
        )

    # Gate 3b: "deeply <word>" regex across all files
    deeply_hits: list[str] = []
    for fname, text in file_texts.items():
        for hit in _DEEPLY_RE.findall(text):
            deeply_hits.append(f"{fname}: '{hit}'")
    if deeply_hits:
        failures.append(
            "AI_SLOP_DEEPLY gate: found 'deeply <word>' construction(s): "
            + ", ".join(deeply_hits)
        )

    # Gate 4: anchor phrases across the COMBINED corpus
    combined_lower = "\n".join(file_texts.values()).lower()
    missing_anchors: list[str] = []
    for variants in ANCHOR_PHRASES:
        if not _has_anchor(combined_lower, variants):
            missing_anchors.append(" OR ".join(f"'{v}'" for v in variants))
    if missing_anchors:
        failures.append(
            "ANCHOR_PHRASES gate: anchor phrase(s) absent from combined "
            "corpus: " + ", ".join(missing_anchors)
        )

    if failures:
        if not quiet:
            print(
                f"FAIL: launch-copy check failed ({launch_dir})",
                file=sys.stderr,
            )
            for f in failures:
                print(f"  - {f}", file=sys.stderr)
        return 1

    if not quiet:
        n = len(file_texts)
        print(
            f"PASS: {launch_dir} — {n}/5 files, all signatures present, "
            "all anchors present, 0 slop hits"
        )
    return 0


def _repo_root() -> Path:
    """Resolve repo root from this file's location."""
    return Path(__file__).resolve().parents[2]


def check_audit_md_scan(*, quiet: bool = False) -> int:
    """Phase 46 / DEPS-04 — blocklist + 'deeply <word>' gate against
    docs/AUDIT.md + scripts/audit/** + docs/dep-opportunities/** + README.md.

    Skips the presence / signature / anchor gates (those are SHIP-TWEET
    specific). Only the slop blocklist + deeply regex apply.
    """
    repo = _repo_root()
    files: list[Path] = [
        repo / "docs" / "AUDIT.md",
        repo / "scripts" / "audit" / "dep_ratings.yaml",
        repo / "README.md",
    ]
    files += sorted((repo / "scripts" / "audit").glob("*.py"))
    files += sorted((repo / "scripts" / "audit").glob("*.sh"))
    dep_opps = repo / "docs" / "dep-opportunities"
    if dep_opps.exists():
        files += sorted(dep_opps.glob("*.md"))

    slop_hits: list[str] = []
    deeply_hits: list[str] = []

    for fpath in files:
        if not fpath.exists():
            continue
        try:
            text = fpath.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        text_lower = text.lower()
        rel = fpath.relative_to(repo)
        for token in AI_SLOP_BLOCKLIST:
            if token.lower() in text_lower:
                slop_hits.append(f"{rel}: '{token}'")
        for hit in _DEEPLY_RE.findall(text):
            deeply_hits.append(f"{rel}: '{hit}'")

    if slop_hits or deeply_hits:
        if not quiet:
            print("FAIL: DEPS-04 audit-md scan", file=sys.stderr)
            if slop_hits:
                print(
                    "  AI_SLOP_BLOCKLIST gate: " + ", ".join(slop_hits),
                    file=sys.stderr,
                )
            if deeply_hits:
                print(
                    "  AI_SLOP_DEEPLY gate: " + ", ".join(deeply_hits),
                    file=sys.stderr,
                )
        return 1

    if not quiet:
        n = len([f for f in files if f.exists()])
        print(f"PASS: DEPS-04 audit-md scan — {n} files scanned, 0 slop hits")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dir",
        type=Path,
        default=LAUNCH_COPY_DIR,
        help=(
            "Directory containing the 5 launch-copy files "
            f"(default: {LAUNCH_COPY_DIR})"
        ),
    )
    parser.add_argument(
        "--audit-md",
        action="store_true",
        help=(
            "DEPS-04 mode: scan docs/AUDIT.md + scripts/audit/** + "
            "docs/dep-opportunities/** + README.md for the AI-slop "
            "blocklist + 'deeply <word>' regex only (skips the "
            "SHIP-TWEET presence/signature/anchor gates)."
        ),
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress stdout/stderr (CI piping mode).",
    )
    args = parser.parse_args(argv)
    if args.audit_md:
        return check_audit_md_scan(quiet=args.quiet)
    return check_launch_copy(args.dir, quiet=args.quiet)


if __name__ == "__main__":
    sys.exit(main())
