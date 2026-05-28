# SPDX-License-Identifier: Apache-2.0
"""TONE-03 tutor-slop CI gate for v9.0 "Lesson One".

Phase 94 / Plan 94-02 Task 1: scans every hand-authored lesson fixture
under ``src/vibemix/learn/transcripts/**.json`` for tutor-tic blocklist
tokens. Sibling to ``scripts/launch/check_no_ai_slop.py`` (Phase 44's
SHIP-TWEET copy gate) — same architectural shape (module-level constants
+ ``check_*`` function returning exit code + ``main(argv)`` entry) but a
different domain (JSON lesson fixtures vs flat launch-copy text, and the
tutor-tic blocklist is a different forbidden-move family).

The gate enforces the four forbidden tutor moves from
``src/vibemix/learn/prompts.py::_FORBIDDEN_TUTOR_MOVES_LOCK``:

1. **Compliment-tic** — "great question!", "you crushed it!", etc.
2. **Summary-tic** — "you just learned X", "you've now mastered X", etc.
3. **Preview-tic** — "now let's", "next we'll", "coming up", etc.
4. **Upbeat-hook-tic** — "exciting, right?", "buckle up", etc.

The blocklist mirrors the Khanmigo / Duolingo / coding-bootcamp tutor
voice — the v9.0 release gate is "real DJ friend in your ear, no AI
slop"; a bare-fact ``"this is the high EQ knob."`` is in-voice, a
``"great question! today we'll be learning the high EQ knob!"`` is not.

Iconic-dialog exception: L1.01's verbatim line
``"Oh bestie, don't worry. You know why? Because I'm the beginner module
of vibemix. Let's go."`` is the ONE permitted exclamation-equivalent in
v9.0 (per CONTEXT.md §iconic-dialog + REQUIREMENTS.md TONE-01). The
blocklist's preview-tic tokens are deliberately multi-word
(``"now let's"``, ``"later we'll"``, ``"today we'll be learning"``) so
the bare ``Let's go.`` closer DOES NOT match — no special-case
exclusion needed; the token design IS the exclusion.

Diagnostic shape (CI-scrapeable, one line per offending file × token):

::

    FAIL: tutor-slop gate found 2 hit(s) under src/vibemix/learn/transcripts
      src/vibemix/learn/transcripts/X/foo.json: 'great question' (compliment)
      src/vibemix/learn/transcripts/X/foo.json: 'you crushed it' (compliment)

Malformed JSON is reported as a separate ``JSON_PARSE_ERROR`` failure
category (T-94-02-04 mitigation) — the gate never crashes on a bad fixture;
it gates red with a clear error message instead.

Run from repo root::

    uv run python scripts/launch/check_no_tutor_slop.py
    uv run python scripts/launch/check_no_tutor_slop.py --dir path/to/transcripts
    uv run python scripts/launch/check_no_tutor_slop.py --quiet

Exit 0 = no slop tokens in any scanned fixture. Exit 1 = at least one hit
or at least one JSON parse error.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Pinned constants — TONE-03 binding. Single source of truth: the test
# ``tests/learn/test_no_tutor_slop_blocklist.py`` imports these directly so
# that "the blocklist is what the gate enforces" is mechanically pinned.
# ---------------------------------------------------------------------------

TRANSCRIPTS_DIR: Path = Path("src/vibemix/learn/transcripts")

# Tutor-tic blocklist — case-insensitive substring match. Multi-word tokens
# are intentional: a bare ``Let's go.`` (the L1.01 iconic dialog exception)
# must NOT trip a preview-tic match, so the preview tokens use ``now let's``
# / ``later we'll`` / ``today we'll be learning`` (with the verb-attached
# tail) rather than the bare contraction.
TUTOR_SLOP_BLOCKLIST: tuple[str, ...] = (
    # Compliment-tic — forbidden move #1: NO complimenting user actions.
    "great question",
    "great job",
    "nice job",
    "awesome",
    "you crushed it",
    "you got it",
    "way to go",
    "well done",
    "perfect",
    "amazing",
    "fantastic",
    "excellent",
    # Summary-tic — forbidden move #2: NO summarizing what just happened.
    "you just learned",
    "you've now mastered",
    "you've just done",
    "you just did",
    "now you've learned",
    # Preview-tic — forbidden move #3: NO previewing what's next. Multi-word
    # ``now let's`` / ``later we'll`` / etc. so bare ``Let's go.`` is safe.
    "now let's",
    "next we'll",
    "coming up",
    "in the next lesson",
    "soon you'll",
    "later we'll",
    "today we'll be learning",
    # Upbeat-hook-tic — forbidden move #4: NO upbeat closer / motivator.
    "exciting, right",
    "this is where it gets fun",
    "you're going to love",
    "get ready to be amazed",
    "buckle up",
    "keep going",
    "you got this",
    "almost there",
    "you're doing great",
    "let's dive in",
    "don't worry, you'll get the hang of it",
    "don't forget",
)

# Category map — every blocklist token mirrored to its forbidden-move
# category. Used by the diagnostic message so a CI failure log names not
# just the offending token but WHICH forbidden move it represents (i.e. the
# self-improving agent / future planner gets actionable feedback).
_CATEGORY: dict[str, str] = {
    "great question": "compliment",
    "great job": "compliment",
    "nice job": "compliment",
    "awesome": "compliment",
    "you crushed it": "compliment",
    "you got it": "compliment",
    "way to go": "compliment",
    "well done": "compliment",
    "perfect": "compliment",
    "amazing": "compliment",
    "fantastic": "compliment",
    "excellent": "compliment",
    "you just learned": "summary",
    "you've now mastered": "summary",
    "you've just done": "summary",
    "you just did": "summary",
    "now you've learned": "summary",
    "now let's": "preview",
    "next we'll": "preview",
    "coming up": "preview",
    "in the next lesson": "preview",
    "soon you'll": "preview",
    "later we'll": "preview",
    "today we'll be learning": "preview",
    "exciting, right": "upbeat",
    "this is where it gets fun": "upbeat",
    "you're going to love": "upbeat",
    "get ready to be amazed": "upbeat",
    "buckle up": "upbeat",
    "keep going": "upbeat",
    "you got this": "upbeat",
    "almost there": "upbeat",
    "you're doing great": "upbeat",
    "let's dive in": "upbeat",
    "don't worry, you'll get the hang of it": "upbeat",
    "don't forget": "upbeat",
}

# Sanity invariant: every blocklist token must have a category entry.
# Caught at import time so a future planner who appends a token without
# wiring its category trips the test (rather than landing as silently
# uncategorized in the gate-failure message).
assert set(TUTOR_SLOP_BLOCKLIST) == set(_CATEGORY), (
    "TUTOR_SLOP_BLOCKLIST and _CATEGORY drift — every token must have a "
    "category. Missing from _CATEGORY: "
    f"{set(TUTOR_SLOP_BLOCKLIST) - set(_CATEGORY)!r}. "
    "Extra in _CATEGORY: "
    f"{set(_CATEGORY) - set(TUTOR_SLOP_BLOCKLIST)!r}."
)

# Documented copy fields a lesson fixture may carry (informational — the
# gate's deep-scan walks ALL string descendants regardless, so adding a new
# field shape automatically inherits the gate). Mirrors the field set Plan
# 94-01 + P92 + Plan 94-03 actually use; future planners append here for
# documentation parity.
_COPY_FIELDS: tuple[str, ...] = (
    "tutor_speak",       # list[{text, ...}] OR scalar str (L1.14 exemplar_cycle)
    "hints",             # list[{text, ...}]
    "recital_pool",      # list[{prompt, ...}]
    "recital_outcomes",  # dict[{pass: str, fail: str}]
    "exemplar_cycle",    # list[{tutor_speak: str | list, ...}]
)


# ---------------------------------------------------------------------------
# Walkers + scanners.
# ---------------------------------------------------------------------------


def _walk_string_values(node: Any) -> Iterator[str]:
    """Depth-first yield every string descendant of ``node``.

    For dicts: recurse into values. For lists/tuples: recurse into
    elements. For strings: yield the string. Booleans / ints / floats /
    None are skipped (bool is a subclass of int — explicit isinstance(str)
    check keeps that ergonomic).
    """
    if isinstance(node, str):
        yield node
        return
    if isinstance(node, dict):
        for v in node.values():
            yield from _walk_string_values(v)
        return
    if isinstance(node, (list, tuple)):
        for item in node:
            yield from _walk_string_values(item)
        return
    # Scalars (int, float, bool, None) — skip.


def _scan_text(text: str) -> set[str]:
    """Return the set of blocklist tokens that case-insensitively
    substring-match ``text``. One file can match a token in multiple
    string descendants — collapse to a per-string set so the diagnostic
    isn't duplicated.
    """
    lower = text.lower()
    return {tok for tok in TUTOR_SLOP_BLOCKLIST if tok in lower}


def _scan_fixture(path: Path) -> tuple[set[str], str | None]:
    """Scan a single JSON fixture. Return (hits, parse_error).

    On JSON parse error: returns (empty set, error message). On success:
    returns (set of token hits across all string descendants, None).
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        return set(), f"read failure: {exc!s}"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return set(), f"JSON parse error: {exc!s}"
    hits: set[str] = set()
    for s in _walk_string_values(data):
        hits.update(_scan_text(s))
    return hits, None


# ---------------------------------------------------------------------------
# Top-level gate.
# ---------------------------------------------------------------------------


def check_no_tutor_slop(
    transcripts_dir: Path,
    *,
    quiet: bool = False,
) -> int:
    """Walk ``transcripts_dir`` for every ``**/*.json`` fixture, scan each
    for tutor-slop tokens, and gate red on any hit OR any parse error.

    Returns 0 on full pass; 1 on any failure. Prints one stderr line per
    offending (file, token, category) tuple — sorted for determinism.
    Parse errors are reported under a separate category for clarity.
    """
    if not transcripts_dir.exists():
        # An empty / missing dir is not a slop-gate failure — the SHIP-TWEET
        # sibling treats missing files as a separate "presence" gate, but
        # this gate's scope is content quality, not directory existence.
        # A future caller who needs presence wraps this check with their
        # own existence assertion (Plan 94-02 test does this).
        if not quiet:
            print(
                f"PASS: {transcripts_dir} does not exist — 0 fixtures scanned",
                file=sys.stderr,
            )
        return 0

    fixtures = sorted(transcripts_dir.rglob("*.json"))
    if not fixtures:
        if not quiet:
            print(
                f"PASS: {transcripts_dir} — 0 fixtures (empty corpus)",
            )
        return 0

    slop_hits: list[tuple[Path, str, str]] = []   # (path, token, category)
    parse_errors: list[tuple[Path, str]] = []

    for fpath in fixtures:
        hits, err = _scan_fixture(fpath)
        if err is not None:
            parse_errors.append((fpath, err))
            continue
        for tok in sorted(hits):
            slop_hits.append((fpath, tok, _CATEGORY[tok]))

    if slop_hits or parse_errors:
        if not quiet:
            n_hits = len(slop_hits)
            n_errs = len(parse_errors)
            print(
                f"FAIL: tutor-slop gate found {n_hits} hit(s) and "
                f"{n_errs} parse error(s) under {transcripts_dir}",
                file=sys.stderr,
            )
            for path, tok, cat in slop_hits:
                print(f"  {path}: '{tok}' ({cat})", file=sys.stderr)
            for path, err in parse_errors:
                print(f"  {path}: JSON_PARSE_ERROR — {err}", file=sys.stderr)
        return 1

    if not quiet:
        n = len(fixtures)
        print(
            f"PASS: {transcripts_dir} — {n} fixture(s) scanned, "
            "0 slop hits, 0 parse errors"
        )
    return 0


# ---------------------------------------------------------------------------
# CLI entry.
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dir",
        type=Path,
        default=TRANSCRIPTS_DIR,
        help=(
            "Directory to recursively scan for **/*.json lesson fixtures "
            f"(default: {TRANSCRIPTS_DIR})"
        ),
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress stdout/stderr (CI piping mode).",
    )
    args = parser.parse_args(argv)
    return check_no_tutor_slop(args.dir, quiet=args.quiet)


if __name__ == "__main__":
    sys.exit(main())
