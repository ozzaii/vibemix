# SPDX-License-Identifier: Apache-2.0
"""Persona invariants — PERSONA-01/02/03.

Anti-hallucination invariants are load-bearing IP per CLAUDE.md.
PERSONA-02 pins overall persona shape (size + section markers); PERSONA-03
pins the specific anti-slop substrings that paraphrasing would lose.

(Pre-2026-05-19 these tests pinned byte-equality against
``cohost_v4.py``. v4 has been retired into
``.planning/research/v3-shipped/`` — the persona's source of truth is
now ``vibemix/agent/persona.py`` itself.)
"""

from __future__ import annotations

from vibemix.agent.persona import SYSTEM_INSTRUCTION


def test_persona_01_resolves_as_str() -> None:
    """PERSONA-01: SYSTEM_INSTRUCTION resolves to a non-trivial str."""
    assert isinstance(SYSTEM_INSTRUCTION, str)
    # Sanity floor — the body is ~8KB of prose; <2000 chars means paraphrasing.
    assert len(SYSTEM_INSTRUCTION) > 2000


def test_persona_02_has_required_section_markers() -> None:
    """PERSONA-02: the persona retains its top-level section markers.

    Anchors that the build_prompt / cache wrapping logic rely on; if any
    of these slip away in a copy-edit the cache-key invariants and the
    in-prompt event scaffolding break.
    """
    markers = [
        "ANTI HALLUCINATION RULES (HARD GATES)",
    ]
    for needle in markers:
        assert needle in SYSTEM_INSTRUCTION, f"missing section marker: {needle!r}"


def test_persona_03_anti_hallucination_substrings_present() -> None:
    """PERSONA-03: every anti-hallucination invariant substring is present.

    Catches paraphrase drift in the load-bearing IP. Each entry below has
    a documented source incident (per CLAUDE.md "central product
    principle: grounded Gemini, not better prompting").
    """
    expected = [
        # The "no audience" rule — kills "the crowd is loving it" slop.
        "THERE IS NO CROWD",
        # The "latency-aware" framing — drives past-tense reactions.
        "LATENCY IS BRUTAL",
        # The hard-gate section.
        "ANTI HALLUCINATION RULES (HARD GATES)",
        # The single most-cited anti-slop clause.
        "If you have NOTHING grounded to say, say NOTHING",
        # The 4th-wall rule — kills "as an AI" disclaimers.
        "NEVER break the 4th wall",
        # The "audio is ground truth" rule — biases toward what's heard.
        "Trust your EARS",
    ]
    for needle in expected:
        assert needle in SYSTEM_INSTRUCTION, f"missing anti-hallucination substring: {needle!r}"
