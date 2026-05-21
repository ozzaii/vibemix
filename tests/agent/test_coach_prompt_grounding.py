# SPDX-License-Identifier: Apache-2.0
"""LIVE-02 grounded COACH persona regression (Phase 55 Plan 01).

Parallel to Phase 54's HYPE prompt-grounding (test_hype_prompt_grounding.py),
this pins that the COACH (feedback) reaction is built FROM the COACH persona +
real grounded state, with the same anti-slop scaffold HYPE carries:

- build_system_instruction(skill, 'coach') returns a COACH_* cell for
  beginner / intermediate / pro, each carrying the citation-grammar marker AND
  the anti-slop-footer marker — proving the COACH cell carries the same
  grounding scaffold HYPE does.
- AICoach.build_prompt(coach_event, registry_snapshot=<non-empty>) embeds the
  grounded evidence_line (real rms/bpm/bands from the MusicState), ends with
  the event's coach task tail, AND carries the evidence-corpus footer when the
  snapshot is non-empty.
- The footer gate holds for coach too: registry_snapshot=None / empty -> NO
  'evidence_corpus[' in the prompt.
- The load-bearing 'no phase= field' anti-hallucination invariant holds for
  the coach prompt (coach.py:14-18, 85-86).

No source behavior is modified — this plan ADDS tests only. matrix.py /
coach.py are untouched; this PINS their existing grounding contract.
"""

from __future__ import annotations

from vibemix.prompts.matrix import build_system_instruction
from vibemix.state import Event, MusicState
from vibemix.state.coach import AICoach
from vibemix.state.evidence_registry import EvidenceRegistry

# The citation-grammar marker (matrix.CITATION_GRAMMAR_BLOCK header) + the
# anti-slop-footer marker (the ban-block header inside matrix._ANTI_SLOP_FOOTER).
# Asserting the markers (not the whole block) keeps these tests robust against
# appended grammar/DSL blocks while pinning that the scaffold is present.
CITATION_GRAMMAR_MARKER = "--- CITATION GRAMMAR"
ANTI_SLOP_FOOTER_MARKER = "DO NOT SAY"


def _grounded_state(*, bpm: float = 128.0, rms: float = 0.06) -> MusicState:
    """A grounded 'music truly playing' MusicState with real numbers — mirrors
    the _grounded_state helper in tests/agent/test_hype_prompt_grounding.py."""
    ms = MusicState()
    ms.audible = True
    ms.bpm = bpm
    ms.rms = rms
    ms.bands = {"sub": 0.25, "low": 0.30, "mid": 0.25, "high": 0.20}
    ms.phase = "drop"
    return ms


def _nonempty_snapshot() -> dict:
    """A non-empty snapshot from a REAL EvidenceRegistry (no mock) so the
    evidence-corpus footer gate fires. Two ev observations + one mix obs."""
    reg = EvidenceRegistry()
    reg.write("ev", "PHASE", 120.5)
    reg.write("ev", "MIX_MOVE", 83.0)
    reg.write("mix", "audible_deck=A", 0.0)
    return reg.snapshot()


# =========================================================================== #
# COACH persona cells carry the citation grammar + anti-slop footer            #
# =========================================================================== #


def test_coach_intermediate_cell_carries_grammar_and_footer():
    """The intermediate COACH cell carries the citation-grammar marker AND the
    anti-slop-footer marker — the COACH path is grounded with the same scaffold
    HYPE is. Markers, not whole blocks, so appended DSL/grammar can't break it."""
    cell = build_system_instruction("intermediate", "coach")
    assert CITATION_GRAMMAR_MARKER in cell
    assert ANTI_SLOP_FOOTER_MARKER in cell


def test_coach_cells_per_skill_carry_grammar_and_footer():
    """beginner + pro COACH cells ALSO carry both markers — every coach skill
    level gets the citation grammar + anti-slop footer, not just intermediate."""
    for skill in ("beginner", "pro"):
        cell = build_system_instruction(skill, "coach")
        assert CITATION_GRAMMAR_MARKER in cell, f"{skill} coach missing citation grammar"
        assert ANTI_SLOP_FOOTER_MARKER in cell, f"{skill} coach missing anti-slop footer"


def test_coach_cells_per_skill_are_nonempty_and_distinct():
    """The three (skill, 'coach') cells are non-empty and distinct — the coach
    persona is selected per skill level (beginner / intermediate / pro)."""
    beginner = build_system_instruction("beginner", "coach")
    intermediate = build_system_instruction("intermediate", "coach")
    pro = build_system_instruction("pro", "coach")

    for cell in (beginner, intermediate, pro):
        assert isinstance(cell, str) and cell.strip()

    assert beginner != intermediate
    assert intermediate != pro
    assert beginner != pro


# =========================================================================== #
# Grounded build_prompt — evidence_line + coach task tail + corpus footer      #
# =========================================================================== #


def test_build_prompt_phase_grounded_with_corpus_footer():
    """AICoach.build_prompt(Event('PHASE', grounded_state), registry_snapshot=
    <non-empty>) embeds the grounded evidence_line (real rms/bpm), ends with
    the PHASE coach task tail, and carries the evidence-corpus footer because
    the snapshot is non-empty."""
    state = _grounded_state(bpm=128.0, rms=0.06)
    ev = Event("PHASE", state, extra={"prev_phase": "build", "new_phase": "drop"})
    prompt = AICoach.build_prompt(ev, registry_snapshot=_nonempty_snapshot())

    assert prompt.startswith("[")  # evidence opens the string
    assert "hearing[rms=" in prompt  # real audio numbers embedded
    assert "bpm=128" in prompt  # the real BPM rendered
    assert "deck=" in prompt  # grounded deck field
    assert "event=PHASE" in prompt
    # The PHASE coach task tail (built from the event, not a template).
    assert "React to what the new section" in prompt
    assert prompt.endswith("FEELS like, not the label.")
    # Evidence-corpus footer present because the snapshot is non-empty
    # (2 ev obs + 1 mix obs).
    assert "evidence_corpus[ev=2,aud=0,mix=1]" in prompt


def test_build_prompt_mix_move_grounded_with_task_tail():
    """A MIX_MOVE coach prompt: grounded evidence_line + the MIX_MOVE task tail
    (change-point grounding on the move's audible result) + the evidence-corpus
    footer on a non-empty snapshot."""
    state = _grounded_state(bpm=130.0, rms=0.07)
    ev = Event(
        "MIX_MOVE",
        state,
        extra={"moves": ["A_low: flat→killed (big twist)"]},
    )
    prompt = AICoach.build_prompt(ev, registry_snapshot=_nonempty_snapshot())

    assert "hearing[rms=" in prompt
    assert "event=MIX_MOVE" in prompt
    assert "CHANGE point" in prompt
    assert "evidence_corpus[" in prompt


def test_build_prompt_corpus_footer_absent_on_empty_snapshot():
    """The footer gate holds for coach too: registry_snapshot=None and an empty
    snapshot both yield NO 'evidence_corpus[' — the corpus footer is only added
    when there's a real corpus to reference."""
    state = _grounded_state()
    ev = Event("PHASE", state, extra={"prev_phase": "build", "new_phase": "drop"})

    prompt_none = AICoach.build_prompt(ev, registry_snapshot=None)
    assert "evidence_corpus[" not in prompt_none

    prompt_empty = AICoach.build_prompt(ev, registry_snapshot={})
    assert "evidence_corpus[" not in prompt_empty

    # Default (no kwarg) matches the None path — backward-compat invariant.
    assert AICoach.build_prompt(ev) == prompt_none


def test_build_prompt_coach_no_phase_field_invariant():
    """The load-bearing anti-hallucination invariant holds for the coach
    prompt: the built prompt MUST NOT contain 'phase=' (coach.py:85-86). The
    RMS-derived phase label primed the AI to invent kicks/drops; the AI must
    hear the phase from the audio, not be handed a label. (The 'event=PHASE'
    tag and 'phase_age=' field are distinct and allowed.)"""
    state = _grounded_state()
    ev = Event("PHASE", state, extra={"prev_phase": "build", "new_phase": "drop"})
    prompt = AICoach.build_prompt(ev, registry_snapshot=_nonempty_snapshot())
    assert "phase=" not in prompt


def test_build_prompt_uses_real_evidence_registry_not_mocks():
    """Documents the contract: the corpus footer is driven by a REAL
    EvidenceRegistry snapshot (no mock), so a regression in the registry
    snapshot shape or the coach footer gate surfaces here."""
    reg = EvidenceRegistry()
    assert reg.snapshot() == {}  # cold registry genuinely empty
    reg.write("ev", "HEARTBEAT", 45.0)
    snap = reg.snapshot()
    assert snap == {"ev": {"HEARTBEAT": (45.0,)}}  # real append-only write

    ev = Event("HEARTBEAT", _grounded_state())
    prompt = AICoach.build_prompt(ev, registry_snapshot=snap)
    assert "evidence_corpus[ev=1,aud=0,mix=0]" in prompt
    assert prompt.endswith("don't go silent.")  # the HEARTBEAT coach task tail
