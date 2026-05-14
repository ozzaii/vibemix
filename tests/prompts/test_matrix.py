# SPDX-License-Identifier: Apache-2.0
"""PROMPT-01: 6-cell skill x mode matrix.

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
    MOOD_PERSONAS,
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
    """HYPE_INTERMEDIATE == build_system_instruction('intermediate', 'hype',
    include_citation_grammar=False) == vibemix.agent.persona.SYSTEM_INSTRUCTION
    (Phase 4 v4 port). Plan 18-03 adds the citation-grammar block by default;
    the v4-byte-identity invariant is preserved at the cell-constant boundary
    via include_citation_grammar=False (the persona re-export uses this same
    opt-out so SYSTEM_INSTRUCTION stays byte-identical to v4).
    """
    from vibemix.agent.persona import SYSTEM_INSTRUCTION

    assert HYPE_INTERMEDIATE == SYSTEM_INSTRUCTION
    assert (
        build_system_instruction("intermediate", "hype", include_citation_grammar=False)
        == SYSTEM_INSTRUCTION
    )


def test_prompt_01_default_dispatch_is_intermediate_hype() -> None:
    """build_system_instruction() with no args defaults to intermediate/hype
    (preserves v4 persona body for existing callers — the citation-grammar
    block is appended on top, but the v4 body stays byte-identical at the
    HYPE_INTERMEDIATE constant level)."""
    from vibemix.agent.persona import SYSTEM_INSTRUCTION

    out = build_system_instruction()
    # Plan 18-03 — default appends grammar block; assert v4 body is the prefix
    # AND the grammar block's signature substring (`[ev:`) is in the appended
    # tail. Locks "v4 byte-identity preserved at the constant level + grammar
    # block appended after."
    assert out.startswith(SYSTEM_INSTRUCTION)
    assert "[ev:" in out


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
    """Each (skill, mode) tuple resolves to its named module-level constant.

    Phase 13-05: COACH cells contain a ``{mood_persona}`` placeholder that
    the dispatcher substitutes (default mood 'hype-man'). Compare against the
    substituted form so the test reflects the actual dispatcher contract.

    Plan 18-03: v4-byte-identity is preserved at the cell-constant level when
    the new ``include_citation_grammar=False`` opt-out is passed. The default
    path appends the citation-grammar block; this test gates that with False
    so it locks the underlying cell selection (not the grammar append).
    """
    import vibemix.prompts.matrix as m

    expected_body = getattr(m, expected)
    if mode == "coach":
        expected_body = expected_body.replace(
            "{mood_persona}", MOOD_PERSONAS["hype-man"]
        )
    assert (
        build_system_instruction(skill, mode, include_citation_grammar=False)
        == expected_body
    )


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
    assert any(m in body.lower() for m in markers), f"coach({skill}) missing feedback-bias signal"


# ---------------------------------------------------------------------------
# Plan 18-03 — CITATION_GRAMMAR_BLOCK (GROUND-02 + GROUND-03 prompt-only seeding)
# ---------------------------------------------------------------------------


def test_o_citation_grammar_block_contains_seven_source_forms_and_multi_cite() -> None:
    """Test O — GROUND-02: CITATION_GRAMMAR_BLOCK enumerates all 7 EBNF source
    forms as literal substrings + the multi-citation form + the v1.0 fail-open
    phrase 'encouraged, not required'. Locks the prompt-side grammar surface."""
    from vibemix.prompts.matrix import CITATION_GRAMMAR_BLOCK

    # 7 single-citation forms (GROUND-02 lock)
    for prefix in ("[ev:", "[aud:", "[midi:", "[track:", "[screen:", "[mix:", "[tend:"):
        assert prefix in CITATION_GRAMMAR_BLOCK, f"missing source form {prefix!r}"

    # Multi-citation form — concrete example Gemini can pattern-match against
    assert "[ev:KICK_SWAP@45.2,aud:bpm@45.0]" in CITATION_GRAMMAR_BLOCK, (
        "multi-citation example missing"
    )

    # v1.0 fail-open semantic — Gemini must not over-cite (slop class of its own)
    assert "encouraged, not required" in CITATION_GRAMMAR_BLOCK


@pytest.mark.parametrize("skill,mode", ALL_CELLS)
def test_p_grammar_block_appended_to_every_cell(skill: str, mode: str) -> None:
    """Test P — GROUND-03: build_system_instruction(skill, mode) for each of
    the 6 cells × default mood returns a string CONTAINING
    CITATION_GRAMMAR_BLOCK. Default kwarg behavior is "include EBNF block"."""
    from vibemix.prompts.matrix import CITATION_GRAMMAR_BLOCK

    out = build_system_instruction(skill, mode)
    assert CITATION_GRAMMAR_BLOCK in out, f"({skill},{mode}) missing CITATION_GRAMMAR_BLOCK"


def test_q_v4_byte_identity_preserved_at_constant_level() -> None:
    """Test Q — HYPE_INTERMEDIATE constant string is byte-identical to the v4
    SYSTEM_INSTRUCTION (Phase 4 invariant + load-bearing IP per CLAUDE.md).
    The grammar block is appended via the dispatcher; the underlying constant
    body is untouched. Opt-out via include_citation_grammar=False also returns
    byte-identical to the constant."""
    from vibemix.agent.persona import SYSTEM_INSTRUCTION

    # Constant unchanged
    assert HYPE_INTERMEDIATE == SYSTEM_INSTRUCTION
    # Opt-out path returns the constant byte-for-byte
    assert (
        build_system_instruction("intermediate", "hype", include_citation_grammar=False)
        == HYPE_INTERMEDIATE
    )
    # Default path is a strict superset (constant + appended block)
    default_out = build_system_instruction("intermediate", "hype")
    assert default_out.startswith(HYPE_INTERMEDIATE)
    assert len(default_out) > len(HYPE_INTERMEDIATE)


def test_r_grammar_block_cross_validated_against_evidence_sources() -> None:
    """Test R — D-LOCKED contract: registry-vocabulary ↔ prompt-vocabulary.
    For each source in EVIDENCE_SOURCES (Plan 18-01), the literal `[<source>:`
    substring appears in CITATION_GRAMMAR_BLOCK. Locks the grammar contract
    so a future drift in either side surfaces as a test failure."""
    from vibemix.prompts.matrix import CITATION_GRAMMAR_BLOCK
    from vibemix.state import EVIDENCE_SOURCES

    for source in EVIDENCE_SOURCES:
        assert f"[{source}:" in CITATION_GRAMMAR_BLOCK, (
            f"EVIDENCE_SOURCES drift: source {source!r} not in prompt grammar block"
        )


def test_s_grammar_block_has_v1_no_enforcement_wording() -> None:
    """Test S — D-LOCKED v1.0 scope: explicit 'encouraged' or 'no penalty'
    wording so Gemini does not over-cite (which would be its own slop class).
    Phase 20 turns enforcement on; v1.0 is prompt-only seeding."""
    from vibemix.prompts.matrix import CITATION_GRAMMAR_BLOCK

    assert (
        "encouraged" in CITATION_GRAMMAR_BLOCK
        or "no penalty" in CITATION_GRAMMAR_BLOCK
    ), "v1.0 fail-open wording missing — Gemini may over-cite"


@pytest.mark.parametrize(
    "ev_type",
    ["KAAN_SPOKE", "MANUAL", "TRACK_CHANGE", "PHASE", "LAYER_ARRIVAL", "MIX_MOVE", "HEARTBEAT"],
)
def test_t_grammar_block_enumerates_v1_event_types(ev_type: str) -> None:
    """Test T — block contains explicit example for each event TYPE the v1.0
    EventDetector fires (Phase 17 will add KICK_SWAP / SUB_LAYER_ARRIVAL once
    those land — the v1.0 block enumerates only the v1.0 EventDetector
    surface)."""
    from vibemix.prompts.matrix import CITATION_GRAMMAR_BLOCK

    assert ev_type in CITATION_GRAMMAR_BLOCK, f"event type {ev_type!r} not enumerated"


# ---------------------------------------------------------------------------
# Plan 20-02 — IM_LISTENING_FRAGMENT integration
# ---------------------------------------------------------------------------


def test_default_path_includes_im_listening_fragment() -> None:
    """build_system_instruction() default kwargs append IM_LISTENING_FRAGMENT.

    GROUND-08 hard requirement — every live system instruction must carry the
    fail-soft rule so Gemini's failure mode shifts from stripped void to
    "I'm listening".
    """
    from vibemix.coach import IM_LISTENING_FRAGMENT

    out = build_system_instruction()
    assert IM_LISTENING_FRAGMENT in out


def test_default_path_includes_grammar_block_too() -> None:
    """Both Phase 18 grammar block AND Plan 20-02 fragment ride the default path.

    Default kwargs are include_citation_grammar=True + include_listening_fallback=True
    — the live agent gets both without explicit opt-in.
    """
    from vibemix.coach import IM_LISTENING_FRAGMENT
    from vibemix.prompts.matrix import CITATION_GRAMMAR_BLOCK

    out = build_system_instruction()
    assert CITATION_GRAMMAR_BLOCK in out
    assert IM_LISTENING_FRAGMENT in out


def test_grammar_after_cell_body_then_fragment() -> None:
    """Append order is: cell_body → CITATION_GRAMMAR_BLOCK → IM_LISTENING_FRAGMENT.

    The grammar block primes "if you cannot cite" — the fragment depends on
    that priming, so order is load-bearing.
    """
    from vibemix.coach import IM_LISTENING_FRAGMENT
    from vibemix.prompts.matrix import CITATION_GRAMMAR_BLOCK

    out = build_system_instruction("intermediate", "hype")
    body_idx = out.index(HYPE_INTERMEDIATE)
    grammar_idx = out.index(CITATION_GRAMMAR_BLOCK)
    fragment_idx = out.index(IM_LISTENING_FRAGMENT)

    assert body_idx < grammar_idx < fragment_idx, (
        f"append order drift: body={body_idx} grammar={grammar_idx} fragment={fragment_idx}"
    )


def test_opt_out_listening_fallback_alone() -> None:
    """include_listening_fallback=False suppresses the fragment but keeps the grammar.

    Backward-compat with Phase 18 callers that want the grammar block but not
    the Plan 20-02 fail-soft addition.
    """
    from vibemix.coach import IM_LISTENING_FRAGMENT
    from vibemix.prompts.matrix import CITATION_GRAMMAR_BLOCK

    out = build_system_instruction(include_listening_fallback=False)
    assert IM_LISTENING_FRAGMENT not in out
    assert CITATION_GRAMMAR_BLOCK in out


def test_double_opt_out_byte_identical_to_cell() -> None:
    """include_citation_grammar=False AND include_listening_fallback=False
    returns the underlying cell constant byte-for-byte. This is the path
    persona.SYSTEM_INSTRUCTION uses to keep the v4-byte-identity invariant."""
    out = build_system_instruction(
        "intermediate",
        "hype",
        include_citation_grammar=False,
        include_listening_fallback=False,
    )
    assert out == HYPE_INTERMEDIATE


def test_invalid_skill_still_raises() -> None:
    """Sanity — adding the new kwarg must not change ValueError surface."""
    with pytest.raises(ValueError, match="unknown skill"):
        build_system_instruction("nonsense", "hype", include_listening_fallback=True)


def test_persona_system_instruction_still_byte_equal_to_hype_intermediate() -> None:
    """persona.SYSTEM_INSTRUCTION === HYPE_INTERMEDIATE — byte-identity invariant.

    Pins the v4-port contract through the Plan 20-02 dispatcher change. If the
    persona opt-out drifts, the import-time assert in persona.py fires AND
    this test fails — double safety net.
    """
    from vibemix.agent.persona import SYSTEM_INSTRUCTION

    assert SYSTEM_INSTRUCTION == HYPE_INTERMEDIATE
