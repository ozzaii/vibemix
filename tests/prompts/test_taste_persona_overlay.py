# SPDX-License-Identifier: Apache-2.0
"""One Mind S2 — taste → persona overlay tests.

``build_system_instruction(..., taste_persona_tags=...)`` injects a FIXED,
allowlisted coaching overlay derived from the DJ's revealed taste. These tests
pin the four properties that keep it safe:

  1. Default / empty tags are byte-identical to no overlay (the v4-byte-identity
     invariant + every existing matrix test never pass this kwarg).
  2. Only allowlisted tags resolve to fixed phrases (anti-injection) — a foreign
     tag is silently dropped.
  3. The overlay reaffirms "never invent a move to match it" (Invariant #3:
     trust the audio; taste is context, not a script).
  4. The overlay is task-framing prose, never an audio DSL tag or a citation.
"""

from __future__ import annotations

from vibemix.prompts.matrix import (
    TASTE_PERSONA_TAG_PHRASES,
    build_system_instruction,
)


def test_s2_default_none_is_byte_identical() -> None:
    """No kwarg / None → byte-identical to the same call without the overlay."""
    base = build_system_instruction("intermediate", "coach", "coach")
    with_none = build_system_instruction(
        "intermediate", "coach", "coach", taste_persona_tags=None
    )
    assert base == with_none


def test_s2_empty_tuple_is_byte_identical() -> None:
    base = build_system_instruction("pro", "coach", "coach")
    with_empty = build_system_instruction(
        "pro", "coach", "coach", taste_persona_tags=()
    )
    assert base == with_empty


def test_s2_byte_identity_callers_unaffected() -> None:
    """The triple-opt-out byte-identity caller stays byte-identical even if a
    tag were passed — but the production path never does. Here we assert the
    overlay only ADDS its block as a strict suffix, leaving the prefix intact."""
    base = build_system_instruction("intermediate", "coach", "coach")
    with_tag = build_system_instruction(
        "intermediate", "coach", "coach", taste_persona_tags=("vocal_avoidant",)
    )
    assert with_tag.startswith(base), "overlay must be a strict suffix"
    assert len(with_tag) > len(base)


def test_s2_known_tag_injects_fixed_phrase() -> None:
    out = build_system_instruction(
        "intermediate", "coach", "coach", taste_persona_tags=("long_phrase_blends",)
    )
    assert "REVEALED TASTE" in out
    assert TASTE_PERSONA_TAG_PHRASES["long_phrase_blends"] in out


def test_s2_multiple_tags_all_present() -> None:
    tags = ("energy_lifts", "breakdown_resets", "tooly_intros")
    out = build_system_instruction(
        "pro", "coach", "coach", taste_persona_tags=tags
    )
    for t in tags:
        assert TASTE_PERSONA_TAG_PHRASES[t] in out


def test_s2_unknown_tag_silently_dropped() -> None:
    """A foreign / fabricated tag never reaches the prompt (anti-injection)."""
    out = build_system_instruction(
        "intermediate",
        "coach",
        "coach",
        taste_persona_tags=("not_a_real_tag", "[track:evil]", "drop table"),
    )
    base = build_system_instruction("intermediate", "coach", "coach")
    # No allowlisted phrase resolved → no overlay → byte-identical to base.
    assert out == base
    assert "not_a_real_tag" not in out
    assert "[track:evil]" not in out


def test_s2_mixed_known_and_unknown_keeps_only_known() -> None:
    out = build_system_instruction(
        "intermediate",
        "coach",
        "coach",
        taste_persona_tags=("vocal_avoidant", "garbage_tag"),
    )
    assert TASTE_PERSONA_TAG_PHRASES["vocal_avoidant"] in out
    assert "garbage_tag" not in out


def test_s2_overlay_reaffirms_never_invent() -> None:
    """Invariant #3 — the overlay must subordinate itself to the live audio."""
    out = build_system_instruction(
        "intermediate", "coach", "coach", taste_persona_tags=("energy_holds",)
    )
    lowered = out.lower()
    assert "never invent" in lowered
    assert "live audio" in lowered


def test_s2_overlay_carries_no_audio_dsl_tags() -> None:
    """The taste phrases must never smuggle a TTS DSL tag (e.g. [whisper])."""
    for phrase in TASTE_PERSONA_TAG_PHRASES.values():
        assert "[" not in phrase and "]" not in phrase
