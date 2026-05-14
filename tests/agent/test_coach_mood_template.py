# SPDX-License-Identifier: Apache-2.0
"""Phase 13-05 Task 3 — Coach prompt template gains {mood} placeholder.

The 6-cell matrix (Phase 10 baseline) gets a MOOD_PERSONAS dict that maps
each of the 3 moods (hype-man / teacher / coach) to a ~120-char persona
fragment. ``build_system_instruction`` gains a ``mood`` kwarg (default
"hype-man" for backward compat — Phase 10 byte-identical-to-v4 invariant
must still hold for HYPE_INTERMEDIATE @ default mood).
"""

from __future__ import annotations

import pytest

from vibemix.prompts import build_system_instruction
from vibemix.prompts.matrix import HYPE_INTERMEDIATE


def test_coach_mood_hype_man_contains_high_energy_marker():
    body = build_system_instruction("intermediate", "coach", mood="hype-man")
    assert "high-energy" in body, (
        "hype-man persona fragment missing 'high-energy' marker"
    )


def test_coach_mood_teacher_contains_patient_marker():
    body = build_system_instruction("intermediate", "coach", mood="teacher")
    assert "patient" in body, "teacher persona fragment missing 'patient' marker"


def test_coach_mood_coach_contains_post_mortem_marker():
    body = build_system_instruction("intermediate", "coach", mood="coach")
    assert "post-mortem" in body, "coach persona fragment missing 'post-mortem' marker"


def test_default_mood_is_hype_man():
    """build_system_instruction without mood kwarg defaults to hype-man.

    Backward-compat for Phase 10 call sites that pre-date the mood field.
    """
    body = build_system_instruction("intermediate", "coach")
    assert "high-energy" in body, (
        "default mood should be 'hype-man' (the high-energy persona)"
    )


def test_invalid_mood_raises():
    """Unknown mood must fail loud — silent fallback would mask bugs."""
    with pytest.raises((KeyError, ValueError)):
        build_system_instruction("intermediate", "coach", mood="party-rocker")


def test_no_literal_mood_placeholder_in_rendered_output():
    """The rendered prompt must NOT contain the literal ``{mood_persona}``
    string — placeholder substitution should happen at build time."""
    for mood in ("hype-man", "teacher", "coach"):
        body = build_system_instruction("intermediate", "coach", mood=mood)
        assert "{mood_persona}" not in body, (
            f"unsubstituted placeholder in coach/intermediate/{mood} prompt"
        )


def test_hype_intermediate_byte_identical_to_v4_invariant_holds_for_default_mood():
    """Phase 10 invariant — HYPE_INTERMEDIATE is byte-identical to the v4
    SYSTEM_INSTRUCTION (load-bearing IP per CLAUDE.md). When mood is the
    default ('hype-man'), ``build_system_instruction('intermediate', 'hype',
    include_citation_grammar=False)`` MUST still return that pinned golden,
    byte-for-byte.

    Phase 13-05 added the placeholder to all 6 templates but renders it only
    when mood != 'hype-man'. Plan 18-03 adds the citation-grammar block by
    default; the v4-byte-identity invariant is preserved at the cell-constant
    level via ``include_citation_grammar=False``.
    """
    out_default_optout = build_system_instruction(
        "intermediate", "hype", include_citation_grammar=False
    )
    out_explicit_default_mood = build_system_instruction(
        "intermediate", "hype", mood="hype-man", include_citation_grammar=False
    )
    # Both must equal the pinned HYPE_INTERMEDIATE golden.
    assert out_default_optout == HYPE_INTERMEDIATE
    assert out_explicit_default_mood == HYPE_INTERMEDIATE
