# SPDX-License-Identifier: Apache-2.0
"""PROMPT-01: 6-cell skill × mode matrix.

Each cell must contain:
- The negative-dict ban list (so the LLM is told what NOT to say).
- The describe-before-infer rule.
- The past-tense rule.
- The <silence/> instruction.
- ≥8 anchor phrases hand-crafted for that (skill, mode) register.

Backward-compat invariant: build_system_instruction("intermediate", "hype")
returns byte-identical to the existing vibemix.agent.persona.SYSTEM_INSTRUCTION
(which is the v4 port from Phase 4). This keeps existing dj_cohost / persona
tests green.
"""

from __future__ import annotations

import pytest

from vibemix.prompts.matrix import (
    COACH_BEGINNER,
    COACH_INTERMEDIATE,
    COACH_PRO,
    HYPE_BEGINNER,
    HYPE_INTERMEDIATE,
    HYPE_PRO,
    build_system_instruction,
)

# (skill, mode, anchor_phrases) — anchors are the exact phrases the plan
# specifies for each cell. Each cell's prompt MUST literally contain each
# anchor (the LLM is told "use these phrases like a real DJ would").
ANCHOR_PHRASES = {
    ("beginner", "hype"): [
        "yo that drop",
        "this groove is sick",
        "vibe check",
        "you're cooking",
        "that switch was clean",
        "feeling this energy",
        "dance-floor mood",
        "this is the moment",
    ],
    ("intermediate", "hype"): [
        # The intermediate-hype cell IS the v4 prompt. Its anchors are the
        # phrasings v4 already shipped — pulled from the v4 vocabulary
        # (drum/kick character, vibe words, scene tags).
        "STANDOUT ELEMENT",
        "raw tunnel",
        "303",
        "warehouse-4am",
        "Hard Tek",
        "Acidcore",
        "kicks stepped on each other",
        "that cut felt half-bar off",
    ],
    ("pro", "hype"): [
        "that EQ swap landed",
        "phrase locked",
        "low-mid pile-up",
        "32 cleared",
        "transition was tight",
        "filter sweep paid off",
        "stems separated nicely",
        "build-release timing",
    ],
    ("beginner", "coach"): [
        "the cut felt early — try 8 bars later",
        "low boost muddied the breakdown",
        "give the build more space",
        "you're rushing the blend",
        "try 8 bars later",
        "muddied the breakdown",
        "more space",
        "rushing the blend",
    ],
    ("intermediate", "coach"): [
        "kicks stepped on each other for a half-bar",
        "EQ killed the lows too aggressively",
        "build released on the 3 — try the 1",
        "phrase mismatch in the blend",
        "for a half-bar",
        "killed the lows",
        "try the 1",
        "phrase mismatch",
    ],
    ("pro", "coach"): [
        "phrase ended on the 3",
        "high-mid pileup at 0:42",
        "blend overstayed by 16",
        "transient stack on the kick",
        "ended on the 3",
        "high-mid pileup",
        "overstayed by 16",
        "transient stack",
    ],
}

ALL_CELLS = list(ANCHOR_PHRASES.keys())

# HYPE_INTERMEDIATE is the byte-identical-to-v4 backward-compat cell. The full
# anti-slop substrate (literal <silence/> token, literal "describe what you HEAR"
# phrase, full 40-phrase ban list) is in the OTHER 5 cells; the v4 prompt
# already carries equivalents (past tense, "react to what you HEAR", "reply
# with silence", KAAN_SPOKE / MANUAL exception). Phase 14 polish may rewrap
# HYPE_INTERMEDIATE with the same substrate; Phase 10 keeps v4 verbatim so the
# existing dj_cohost+persona tests stay green and Kaan's tuned v4 IP is preserved.
NEW_CELLS = [c for c in ALL_CELLS if c != ("intermediate", "hype")]


# ---------------------------------------------------------------------------
# Cell existence + uniqueness
# ---------------------------------------------------------------------------


def test_prompt_01_six_cells_exist_as_module_constants() -> None:
    """All 6 cells exist as module-level non-empty strings."""
    cells = [
        HYPE_BEGINNER,
        HYPE_INTERMEDIATE,
        HYPE_PRO,
        COACH_BEGINNER,
        COACH_INTERMEDIATE,
        COACH_PRO,
    ]
    for cell in cells:
        assert isinstance(cell, str)
        assert len(cell) > 500, f"prompt cell suspiciously short: {len(cell)} chars"


def test_prompt_01_six_cells_are_pairwise_unique() -> None:
    """No two cells are identical (otherwise the matrix is degenerate)."""
    cells = {
        "HYPE_BEGINNER": HYPE_BEGINNER,
        "HYPE_INTERMEDIATE": HYPE_INTERMEDIATE,
        "HYPE_PRO": HYPE_PRO,
        "COACH_BEGINNER": COACH_BEGINNER,
        "COACH_INTERMEDIATE": COACH_INTERMEDIATE,
        "COACH_PRO": COACH_PRO,
    }
    seen: dict[str, str] = {}
    for name, body in cells.items():
        if body in seen:
            pytest.fail(f"prompt cell {name} is identical to {seen[body]}")
        seen[body] = name


# ---------------------------------------------------------------------------
# Backward compat — Hype-Intermediate is byte-identical to v4 SYSTEM_INSTRUCTION
# ---------------------------------------------------------------------------


def test_prompt_01_hype_intermediate_byte_identical_to_persona() -> None:
    """HYPE_INTERMEDIATE == build_system_instruction('intermediate', 'hype')
    == vibemix.agent.persona.SYSTEM_INSTRUCTION (Phase 4 v4 port).
    """
    from vibemix.agent.persona import SYSTEM_INSTRUCTION

    assert HYPE_INTERMEDIATE == SYSTEM_INSTRUCTION
    assert build_system_instruction("intermediate", "hype") == SYSTEM_INSTRUCTION


def test_prompt_01_default_dispatch_is_intermediate_hype() -> None:
    """build_system_instruction() with no args defaults to intermediate/hype
    (preserves v4 persona for existing callers)."""
    from vibemix.agent.persona import SYSTEM_INSTRUCTION

    assert build_system_instruction() == SYSTEM_INSTRUCTION


# ---------------------------------------------------------------------------
# Dispatcher correctness
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "skill,mode,expected",
    [
        ("beginner", "hype", "HYPE_BEGINNER"),
        ("intermediate", "hype", "HYPE_INTERMEDIATE"),
        ("pro", "hype", "HYPE_PRO"),
        ("beginner", "coach", "COACH_BEGINNER"),
        ("intermediate", "coach", "COACH_INTERMEDIATE"),
        ("pro", "coach", "COACH_PRO"),
    ],
)
def test_prompt_01_dispatcher_returns_right_cell(skill: str, mode: str, expected: str) -> None:
    """Each (skill, mode) tuple resolves to its named module-level constant."""
    import vibemix.prompts.matrix as m

    expected_body = getattr(m, expected)
    assert build_system_instruction(skill, mode) == expected_body


@pytest.mark.parametrize("skill", ["BEGINNER", "Intermediate", "PRO"])
def test_prompt_01_dispatcher_is_case_insensitive_skill(skill: str) -> None:
    """Skill lookup is case-insensitive (env vars often arrive uppercased)."""
    out = build_system_instruction(skill, "hype")
    assert out == build_system_instruction(skill.lower(), "hype")


@pytest.mark.parametrize("mode", ["HYPE", "Coach", "hype"])
def test_prompt_01_dispatcher_is_case_insensitive_mode(mode: str) -> None:
    """Mode lookup is case-insensitive."""
    out = build_system_instruction("intermediate", mode)
    assert out == build_system_instruction("intermediate", mode.lower())


def test_prompt_01_dispatcher_unknown_skill_raises() -> None:
    """Unknown skill level → ValueError (not silent fallback — fail loud)."""
    with pytest.raises(ValueError):
        build_system_instruction("expert", "hype")


def test_prompt_01_dispatcher_unknown_mode_raises() -> None:
    """Unknown mode → ValueError."""
    with pytest.raises(ValueError):
        build_system_instruction("intermediate", "critic")


# ---------------------------------------------------------------------------
# Per-cell anchor phrases
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("skill,mode", ALL_CELLS)
def test_prompt_01_each_cell_has_eight_anchor_phrases(skill: str, mode: str) -> None:
    """Each cell's prompt body literally contains all 8 of its anchor phrases."""
    body = build_system_instruction(skill, mode)
    anchors = ANCHOR_PHRASES[(skill, mode)]
    missing = [a for a in anchors if a not in body]
    assert not missing, f"({skill},{mode}) missing anchors: {missing}"


# ---------------------------------------------------------------------------
# Shared anti-slop substrate every cell carries
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("skill,mode", NEW_CELLS)
def test_prompt_01_each_new_cell_has_silence_token(skill: str, mode: str) -> None:
    """Each NEW cell (≠HYPE_INTERMEDIATE) tells the LLM to emit literal `<silence/>`
    for non-events. HYPE_INTERMEDIATE = v4 verbatim — v4 says 'reply with silence'
    in prose form; literal token instruction is in the new substrate."""
    body = build_system_instruction(skill, mode)
    assert "<silence/>" in body


@pytest.mark.parametrize("skill,mode", NEW_CELLS)
def test_prompt_01_each_new_cell_has_describe_before_infer(skill: str, mode: str) -> None:
    """Each NEW cell carries the describe-before-infer anti-hallucination rule.
    HYPE_INTERMEDIATE = v4 verbatim — v4 carries the equivalent 'react to what
    you HEAR' / 'EARS over numbers' principle in different phrasing."""
    body = build_system_instruction(skill, mode)
    assert "describe what you HEAR" in body, f"({skill},{mode}) missing describe-before-infer"


@pytest.mark.parametrize("skill,mode", ALL_CELLS)
def test_prompt_01_each_cell_has_past_tense_rule(skill: str, mode: str) -> None:
    """Every cell carries the past-tense framing rule (already in v4)."""
    body = build_system_instruction(skill, mode)
    assert "past tense" in body, f"({skill},{mode}) missing past-tense rule"


@pytest.mark.parametrize("skill,mode", ALL_CELLS)
def test_prompt_01_each_cell_mentions_kaan_spoke_exception(skill: str, mode: str) -> None:
    """Every cell carries the KAAN_SPOKE / MANUAL always-reply exception
    (already in v4 → backward compatible)."""
    body = build_system_instruction(skill, mode)
    assert "KAAN_SPOKE" in body
    assert "MANUAL" in body


@pytest.mark.parametrize("skill,mode", NEW_CELLS)
def test_prompt_01_each_new_cell_includes_negative_dict_ban_list(skill: str, mode: str) -> None:
    """Each NEW cell explicitly enumerates banned phrases (≥10 sampled).
    HYPE_INTERMEDIATE = v4 verbatim — bans are enforced post-hoc by
    filter_for_slop, not inline in the v4 prompt."""
    from vibemix.prompts.negative_dict import NEGATIVE_PHRASES

    body = build_system_instruction(skill, mode).lower()
    # Sample 10 representative phrases from each bucket — fail fast if missing.
    sampled = [
        "as an ai",
        "delve",
        "leverage",
        "amazing",
        "awesome",
        "incredible",
        "love it",
        "killing it",
        "in this dynamic world",
        "navigate the landscape",
    ]
    # All sampled phrases must be in the negative dict (sanity check).
    nd_lower = tuple(p.lower() for p in NEGATIVE_PHRASES)
    for s in sampled:
        assert s in nd_lower, f"sample {s!r} not in NEGATIVE_PHRASES (test bug)"
    # AND each new cell must literally contain each sampled phrase as a ban.
    missing = [s for s in sampled if s not in body]
    assert not missing, f"({skill},{mode}) prompt missing negative-dict bans: {missing}"


def test_prompt_01_hype_intermediate_carries_equivalent_substrate() -> None:
    """HYPE_INTERMEDIATE (=v4 verbatim) carries the substrate semantically:
    past-tense rule + KAAN_SPOKE exception are in v4. The literal `<silence/>`
    token + literal 'describe what you HEAR' phrase + inline ban list live in
    the NEW 5 cells; v4's protections fire via the post-hoc filter."""
    assert "past tense" in HYPE_INTERMEDIATE
    assert "KAAN_SPOKE" in HYPE_INTERMEDIATE
    assert "MANUAL" in HYPE_INTERMEDIATE
    # v4 equivalent of describe-before-infer
    assert "React to what you HEAR" in HYPE_INTERMEDIATE
    # v4 equivalent of <silence/> instruction
    assert "reply with silence" in HYPE_INTERMEDIATE


# ---------------------------------------------------------------------------
# Coach-mode-specific shape
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("skill", ["beginner", "intermediate", "pro"])
def test_prompt_01_coach_mode_includes_feedback_bias(skill: str) -> None:
    """Coach cells carry an explicit feedback-bias hint (honest critique vs hype)."""
    body = build_system_instruction(skill, "coach")
    # At least one of these honest-feedback markers must be present.
    markers = ["coach", "feedback", "improve", "honest"]
    assert any(m in body.lower() for m in markers), (
        f"coach({skill}) missing feedback-bias signal"
    )
