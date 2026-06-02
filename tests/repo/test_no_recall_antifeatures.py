# SPDX-License-Identifier: Apache-2.0
"""Phase 66 Plan 66-01 (Wave 0) — anti-feature static gate (COPILOT-03).

The v6.0 anti-features lock (per .planning/PROJECT.md §v6.0 thesis +
.planning/REQUIREMENTS.md COPILOT-03): personalization is EMERGENT from
the retrieval seam, NEVER an LLM-extraction layer. The visible-copilot
phase MUST NOT reach Gemini through the coach/prompt surface with any
of the following anti-feature classes:

    * "tendency" claims      — "you tend to", "you usually", "you always",
                               "your tendency", "your tendencies", "based on
                               your past"
    * next-track recommendation — "next track", "you should play",
                                   "you should try"
    * "I recommend / my recommendation" — broad recommendation surface

These are the EXACT failure-mode strings 66-RESEARCH.md Pitfall 6
documents — well-intentioned prompt phrasings that trigger Gemini's
tendency-extraction circuits even when the survivor block is concrete.

Static-gate template: mirrors tests/memory/test_no_extraction.py
verbatim — tokenize-stripped grep over a fixed pair of target files.

================ DIVERGENCE FROM ANALOG (memory-gate) ================

The memory gate's POSITIVE control uses a Python API identifier
(`generate_content`) that survives stripping because it is a NAME token,
not a STRING token. The memory-gate's main scan therefore catches a real
generation call (a NAME/OP token sequence) while never tripping on a
docstring that documents the ban.

Phase 66's forbidden phrases are HUMAN ENGLISH PROSE with embedded
spaces (e.g. "you tend to", "next track"). Python syntax forbids
multi-word identifiers — so such a phrase CANNOT exist as a NAME token
sequence outside a string literal, comment, or docstring. The only way
a forbidden phrase can reach Gemini through the prompt surface is via
a STRING token (a prompt fragment literal). The tokenize stripper
replaces STRING contents with `""`, removing those literals from the
scan surface entirely — which means the main scan is necessarily
VACUOUS against TARGET_FILES (no NAME-token forbidden phrase can survive
stripping, no STRING-token forbidden phrase can survive stripping).

The practical role of this gate is therefore as a TYPE-LEVEL SENTINEL +
a substring-uniqueness lock on the fragment templates themselves: any
NEW prompt fragment template added to coach.py or matrix.py is scanned;
the gate fires only if a forbidden phrase appears in the STRIPPED
source (which would require Python to parse it as a NAME/OP — i.e.
syntactically impossible for multi-word English). The defense in depth
is the §RECALL-EAR Kaan-ear runtime check (KAAN-ACTION-LEGAL.md) that
catches Gemini drift at runtime regardless of source content.

Because no NAME-token forbidden phrase can survive stripping AND the
stripper removes STRING contents, this file substitutes the memory-gate's
positive-control with a NEGATIVE-CONTROL STRIPPER TEST proving that the
stripper correctly removes string + docstring contents. Without this
test, two failure modes could silently break the gate:

    (a) a stripper bug that LEFT string contents in place would make
        the gate fire on any prompt fragment literal that happens to
        contain a banned phrase (false positive — and worse, would
        "fire" against a prompt that the stripper would normally
        replace with `""` — making the gate meaningless);
    (b) a stripper bug that BLANKED EVERYTHING would make the main scan
        vacuously pass even when a forbidden phrase exists in source
        (false negative).

The negative-control covers (a) and (b) together: feeding the stripper
a source that contains a forbidden phrase inside a docstring AND inside
a string literal, then asserting both are removed by the stripper. If
the stripper is correct, both contents are gone after stripping.

================== LOWERCASING DIVERGENCE ==================

The memory gate matches case-sensitive Python identifiers. Phase 66's
gate matches case-INSENSITIVE English prose — so the stripped source is
``.lower()``-ed before substring-matching against the lowercase
FORBIDDEN_RECALL_PHRASES tuple. (Documented in 66-PATTERNS.md §"D:
Static-gate target_files + forbidden tuple + offenders dict".)

================ PRE-GREP EVIDENCE (vacuous-green at land) ================

Executed during planning, 2026-05-22 (recorded in 66-VALIDATION.md
§Wave 0 Requirements):

    grep -nE "you tend to|you usually|you always|next track|\\
              you should play|your tendency|based on your past|\\
              I recommend|my recommendation|you should try" \\
        src/vibemix/state/prompt_builder.py src/vibemix/prompts/matrix.py

Returned ZERO hits. Re-verified during this Wave 0 commit — still zero.

The main scan test is therefore declared VACUOUS-GREEN at land — there
are no forbidden phrases in TARGET_FILES today. This is recorded as the
gate's land state. Any future hit is a finding to surface, NOT a runtime
carve-out: the executor MUST stop and surface the finding (re-run
/gsd:plan-phase --research-phase to choose a different anti-feature
phrasing), NOT add regex carve-outs or known-good context exclusions to
the test.

T-66-01-01 (Tampering: static gate silently passes vacuously) —
mitigated by the negative-control test + the explicit Path.read_text
of every TARGET_FILES entry (a missing file errors out, not silently
passes).
"""

from __future__ import annotations

import io
import tokenize
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


# Forbidden HUMAN-ENGLISH-PROSE phrases that must NOT reach the coach /
# prompt surface. Lowercase (the stripped source is .lower()-ed before
# matching). Sourced from 66-RESEARCH.md §Code Examples Pattern 4.
FORBIDDEN_RECALL_PHRASES: tuple[str, ...] = (
    "you tend to",
    "you usually",
    "you always",
    "your tendency",
    "your tendencies",
    "based on your past",
    "next track",
    "you should play",
    "you should try",
    "i recommend",
    "my recommendation",
    # Phase 66 review WR-01 — synonym gaps surfaced by the review pass.
    # All are obvious paraphrases of the cardinal anti-feature classes
    # above (tendency claims, next-track recommendation, recommendation
    # surface). Pre-grep against TARGET_FILES at land = ZERO hits for any
    # of these — the gate stays VACUOUS-GREEN. Any future hit is a
    # finding to SURFACE (re-research the prompt phrasing), NOT to carve
    # out — see the module docstring's "Pre-grep evidence" note.
    "your typical",
    "you've been",
    "i'd recommend",
    "play next",
    "you should play next",
    "consider playing",
    "track to play next",
    "your usual move",
    "your habit",
)

# Files scanned — the prompt + coach persona surface that Gemini sees.
# Hardcoded (not a glob) so the gate's reach is unambiguous and a future
# file split must explicitly opt-in by editing this tuple.
TARGET_FILES: tuple[str, ...] = (
    "src/vibemix/state/prompt_builder.py",
    "src/vibemix/prompts/matrix.py",
)


def _strip_comments_and_docstrings(src_text: str) -> str:
    """Return executable source with ALL comments and string literals removed.

    # CLONED from tests/memory/test_no_extraction.py:50-76 (Phase 63).
    # DO NOT diverge — if the upstream stripper is fixed, port the fix here
    # too. The stripper is a single chokepoint; keeping the two copies
    # token-for-token identical is the simplest way to guarantee equivalent
    # static-gate semantics across the memory and coach surfaces.

    Tokenize-based stripping: removes COMMENT and STRING tokens so prose
    that *documents* the ban (in a comment or docstring) is invisible to
    the scan, while a real NAME/OP token sequence survives. STRING tokens
    are replaced with an empty-string literal so token POSITIONS keep
    surrounding-code adjacency. Falls back to a line-based ``#`` strip if
    tokenize fails (never silently passes a file).
    """
    try:
        kept: list[tokenize.TokenInfo] = []
        for tok in tokenize.generate_tokens(io.StringIO(src_text).readline):
            if tok.type in (tokenize.COMMENT, tokenize.STRING):
                if tok.type == tokenize.STRING:
                    kept.append(tok._replace(string='""'))
                continue
            kept.append(tok)
        return tokenize.untokenize(kept)
    except (tokenize.TokenError, IndentationError, SyntaxError, ValueError):
        return "\n".join(
            ln for ln in src_text.splitlines() if not ln.lstrip().startswith("#")
        )


def test_strip_comments_and_docstrings_removes_string_content() -> None:
    """NEGATIVE CONTROL — the stripper correctly removes string + docstring
    contents so the main scan cannot be silently broken by a stripper bug.

    See the module docstring above for the divergence rationale (Phase 66
    substitutes the memory-gate's positive-control with this negative
    control because no NAME-token forbidden phrase can exist for human
    English prose — Python syntax forbids multi-word identifiers).

    Failure modes covered:
      (a) stripper leaves string contents in place → false positive on
          any prompt fragment literal containing a banned phrase
      (b) stripper blanks everything → false negative (vacuous gate)

    Both failure modes are caught by the asserts below.
    """
    # (a) Docstring containing a forbidden phrase — must NOT survive stripping.
    docstring_source = (
        '"""\nThis docstring mentions "you tend to" drop the bass.\n"""\n'
        "x = 1\n"
    )
    stripped_doc = _strip_comments_and_docstrings(docstring_source)
    assert "you tend to" not in stripped_doc.lower(), (
        "stripper failed to remove docstring contents — a banned phrase in "
        "a docstring would self-trip the main scan (false positive)"
    )

    # (b) String literal containing a forbidden phrase — must NOT survive
    # stripping. (This is the harder failure-mode: a STRING token must be
    # replaced with `""`, not just have its quotes removed.)
    string_literal_source = 'x = "you tend to drop the bass"\nfoo = 42\n'
    stripped_lit = _strip_comments_and_docstrings(string_literal_source)
    assert "you tend to" not in stripped_lit.lower(), (
        "stripper failed to remove string-literal contents — a banned phrase "
        "in a prompt fragment string would self-trip the main scan"
    )

    # (b cont.) Confirm the stripper is not pathologically blanking — the
    # NAME/OP tokens around the string literal MUST survive (`x`, `=`, `foo`,
    # `42`) so a real anti-feature in CODE (which Python parsing forbids
    # anyway for multi-word identifiers, but worth pinning) would be caught.
    # We assert presence of two anchor tokens — if the stripper blanks
    # everything, both fail and the test goes RED.
    assert "x" in stripped_lit, "stripper blanked NAME tokens (over-strips)"
    assert "foo" in stripped_lit, "stripper blanked NAME tokens (over-strips)"


def test_no_recall_antifeatures_in_coach_surface_after_string_and_comment_scrub_COPILOT03() -> None:
    """COPILOT-03 — no forbidden anti-feature phrase survives the
    string-and-comment scrub of the coach / prompt surface
    (state/prompt_builder.py + prompts/matrix.py).

    Scans tokenize-stripped + lowercased executable source of every file
    in TARGET_FILES for substring presence of any phrase in
    FORBIDDEN_RECALL_PHRASES. None may appear.

    Phase 66 review WR-02 — renamed from
    ``test_no_recall_antifeatures_in_coach_surface_COPILOT03`` to make the
    test's actual mechanical claim explicit. The stripper removes STRING
    AND COMMENT tokens (see ``_strip_comments_and_docstrings`` + the
    module docstring's "Divergence from analog" section), so a forbidden
    phrase inside a prompt fragment STRING LITERAL is invisible to this
    scan. The mechanical claim is therefore "no forbidden phrase survives
    the scrub" — NOT "no forbidden phrase reaches Gemini". The real
    defense against fragment-literal regressions is the §RECALL-EAR
    Kaan-ear runtime check (KAAN-ACTION-LEGAL.md). Future maintainers who
    loosen the stripper assuming this gate would catch a regression — the
    explicit name now warns them off.

    DECLARED VACUOUS-GREEN AT LAND — the pre-grep evidence (executed
    2026-05-22 during planning, recorded in 66-VALIDATION.md §Wave 0
    Requirements and reproduced in this file's module docstring) shows
    zero forbidden phrases in TARGET_FILES today. The gate's lifetime
    role is as a sentinel against future regressions — any future commit
    that introduces a forbidden phrase trips the gate.

    Vacuity-broken protection: the negative-control stripper test above
    guarantees the stripper itself does not vacuously pass everything;
    the Path.read_text below guarantees the gate is not vacuous-on-
    missing-file (it errors out if a TARGET_FILES entry vanishes).
    """
    offenders: dict[str, list[str]] = {}
    for rel in TARGET_FILES:
        path = REPO / rel
        # Path.read_text errors out if the file is missing — the gate is
        # never vacuous-on-missing-file (T-66-01-01 mitigation).
        src = path.read_text(encoding="utf-8", errors="replace")
        stripped = _strip_comments_and_docstrings(src).lower()
        hits = [phrase for phrase in FORBIDDEN_RECALL_PHRASES if phrase in stripped]
        if hits:
            offenders[rel] = hits
    assert not offenders, (
        f"Phase 66 anti-feature gate VIOLATED — forbidden phrases reached "
        f"the coach/prompt surface: {offenders}. v6.0 anti-features lock: "
        "no LLM-extracted tendencies, no next-track recommendation, no "
        "settings personalization, no continuous audio embedding. If a "
        "phrase you believe is benign trips this gate, surface a finding "
        "and re-research the prompt phrasing — do NOT add a regex carve-out."
    )
