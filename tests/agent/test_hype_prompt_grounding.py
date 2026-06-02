# SPDX-License-Identifier: Apache-2.0
"""LIVE-01 grounded HYPE persona regression (Phase 54 Plan 03).

Pins that the hype reaction is built FROM the HYPE persona + real grounded
state, never a generic template:

- build_system_instruction(skill, 'hype') returns the HYPE_* cell for
  beginner / intermediate / pro (three distinct, non-empty cells); the
  intermediate cell is the v4-grounded one (a stable v4 substring).
- AICoach.build_prompt(Event('PHASE', state)) embeds the grounded evidence_line
  (real rms/bpm/bands from the MusicState) + event=PHASE + the PHASE task tail.
- The load-bearing 'no phase= field' anti-hallucination invariant holds — the
  RMS-derived phase label primed the AI to invent kicks/drops; the prompt must
  NOT contain 'phase=' (the AI hears the phase from the audio, isn't told a
  label). (coach.py:14-18, 85-86.)

No source behavior is modified — this plan ADDS tests only.
"""

from __future__ import annotations

from vibemix.prompts.matrix import build_system_instruction
from vibemix.state import Event, MusicState
from vibemix.state.prompt_builder import AICoach


def _grounded_state(*, bpm: float = 130.0, rms: float = 0.06) -> MusicState:
    """A grounded 'music truly playing' MusicState with real numbers — mirrors
    the _state helper field set in tests/state/test_event_detector.py."""
    ms = MusicState()
    ms.audible = True
    ms.bpm = bpm
    ms.rms = rms
    ms.bands = {"sub": 0.25, "low": 0.30, "mid": 0.25, "high": 0.20}
    ms.phase = "drop"
    return ms


# =========================================================================== #
# HYPE persona selection per skill                                            #
# =========================================================================== #


def test_hype_cells_per_skill_are_nonempty_and_distinct():
    """The three (skill, 'hype') cells are non-empty and distinct — the hype
    persona is selected per skill level (beginner / intermediate / pro)."""
    beginner = build_system_instruction("beginner", "hype")
    intermediate = build_system_instruction("intermediate", "hype")
    pro = build_system_instruction("pro", "hype")

    for cell in (beginner, intermediate, pro):
        assert isinstance(cell, str) and cell.strip()

    assert beginner != intermediate
    assert intermediate != pro
    assert beginner != pro


def test_intermediate_hype_cell_is_v4_grounded():
    """The intermediate HYPE cell is the v4-tuned, load-bearing one — assert a
    stable v4 substring ('friend in his studio') rather than the whole body, so
    the test survives appended grammar/DSL blocks but pins the v4 IP."""
    intermediate = build_system_instruction("intermediate", "hype")
    assert "friend in his studio" in intermediate


# =========================================================================== #
# Grounded evidence — build_prompt is built FROM real state                   #
# =========================================================================== #


def test_build_prompt_embeds_grounded_evidence_line():
    """AICoach.build_prompt(Event('PHASE', grounded_state)) embeds the grounded
    evidence_line — real rms/bpm rendered from the MusicState — plus the
    event=PHASE tag and the PHASE task tail. The reaction is built from real
    state, not a generic template."""
    state = _grounded_state(bpm=130.0, rms=0.06)
    ev = Event("PHASE", state, extra={"prev_phase": "build", "new_phase": "drop"})
    prompt = AICoach.build_prompt(ev)

    assert "hearing[rms=" in prompt  # real audio numbers embedded
    assert "bpm=130" in prompt  # the real BPM rendered
    assert "event=PHASE" in prompt  # the event tag
    # The PHASE task tail (built from the event, not a template).
    assert "React to what the new section" in prompt
    assert "FEELS like" in prompt


def test_build_prompt_does_not_contain_phase_field_invariant():
    """The load-bearing anti-hallucination invariant: the built prompt MUST NOT
    contain 'phase=' (coach.py:85-86). The RMS-derived phase label primed the
    AI to invent kicks/drops when the audio was atmospheric; the AI must hear
    the phase from the audio, not be handed a label."""
    state = _grounded_state()
    ev = Event("PHASE", state, extra={"prev_phase": "build", "new_phase": "drop"})
    prompt = AICoach.build_prompt(ev)
    assert "phase=" not in prompt


def test_evidence_line_does_not_contain_phase_field_invariant():
    """The same no-phase= invariant at the evidence_line source — the
    grounded-state string itself never carries a 'phase=' field."""
    line = AICoach.evidence_line(_grounded_state())
    assert "hearing[rms=" in line
    assert "phase=" not in line
