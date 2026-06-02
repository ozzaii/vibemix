# SPDX-License-Identifier: Apache-2.0

from vibemix.coach.prompt_fragments import render_coaching_aim_fragment
from vibemix.prompts.matrix import COACH_CLOSING_BLOCK, build_system_instruction


def test_coaching_aim_fragment_is_fixed_and_guarded() -> None:
    fragment = render_coaching_aim_fragment("harmonic_mixing")

    assert "smoother harmonic blends" in fragment
    assert "relevance frame ONLY" in fragment
    assert "does not lower the grounding bar" in fragment
    assert "Frame the move, never the person" in fragment
    assert render_coaching_aim_fragment("bad skill text") == ""


def test_coaching_aim_renders_only_in_coach_mode_before_closing() -> None:
    coach = build_system_instruction(
        "intermediate",
        "coach",
        "coach",
        include_tag_dsl=False,
        include_audio_vibe_contract=False,
        include_coach_closing=True,
        coaching_aim_skill="eq_mixing",
    )
    hype = build_system_instruction(
        "intermediate",
        "hype",
        "hype-man",
        include_tag_dsl=False,
        include_audio_vibe_contract=False,
        include_coach_closing=True,
        coaching_aim_skill="eq_mixing",
    )

    assert "cleaner EQ swaps" in coach
    assert "LIVE COACHING AIM" in coach
    assert coach.index("LIVE COACHING AIM") < coach.index("ABOVE ALL: BE A REAL COACH")
    assert COACH_CLOSING_BLOCK in coach
    assert "LIVE COACHING AIM" not in hype
