# SPDX-License-Identifier: Apache-2.0
"""Persona invariants — PERSONA-01/02/03.

Anti-hallucination invariants are load-bearing IP per CLAUDE.md.
PERSONA-02 pins the Sven coach-identity shape (size + section markers);
PERSONA-03 pins the specific forward-coaching grounding substrings that
paraphrasing would lose.

(Pre-2026-05-19 these tests pinned byte-equality against
``cohost_v4.py``. v4 has been retired into
``.planning/archive/2026-05-27-stale-v2-v3-research/v3-shipped/``; the
persona's source of truth is now the landed Sven coach identity exported by
``vibemix/agent/persona.py``.)
"""

from __future__ import annotations

from vibemix.agent.persona import SYSTEM_INSTRUCTION


def test_persona_01_resolves_as_str() -> None:
    """PERSONA-01: SYSTEM_INSTRUCTION resolves to a non-trivial str."""
    assert isinstance(SYSTEM_INSTRUCTION, str)
    # Sanity floor — the body is ~8KB of prose; <2000 chars means paraphrasing.
    assert len(SYSTEM_INSTRUCTION) > 2000


def test_persona_02_has_required_section_markers() -> None:
    """PERSONA-02: the persona retains its Sven coach section markers.

    Anchors that the build_prompt / cache wrapping logic rely on; if any
    of these slip away in a copy-edit the cache-key invariants and the
    in-prompt event scaffolding break.
    """
    markers = [
        "You're Sven — Kaan's DJ friend riding shotgun in the booth",
        "COACH THE FORWARD, NOT THE NOW.",
        "EARN YOUR SPECIFICS.",
        "ONE THING, TEASED.",
        "STAY IN CHARACTER.",
    ]
    for needle in markers:
        assert needle in SYSTEM_INSTRUCTION, f"missing section marker: {needle!r}"


def test_persona_03_anti_hallucination_substrings_present() -> None:
    """PERSONA-03: every Sven grounding invariant substring is present.

    Catches paraphrase drift in the load-bearing IP. Each entry below has
    a documented source incident (per CLAUDE.md "central product
    principle: grounded Gemini, not better prompting").
    """
    expected = [
        # The "no audience" rule — kills crowd/room slop.
        "no crowd, no audience",
        # The latency-aware coaching frame — drives forward-facing reactions.
        "Your voice reaches Kaan 5-10 seconds late",
        # The audio-first rule — biases toward what is actually heard.
        "YOUR EARS COME FIRST",
        # The master-output scope guard — kills fake separated-stem certainty.
        "The packet is one master signal, not separated stems",
        # The move grounding hard-gate — no invented controller action.
        "A move you didn't see in the packet didn't happen",
        # The 4th-wall/meta guard.
        "Never narrate your reasoning",
    ]
    for needle in expected:
        assert needle in SYSTEM_INSTRUCTION, f"missing anti-hallucination substring: {needle!r}"
