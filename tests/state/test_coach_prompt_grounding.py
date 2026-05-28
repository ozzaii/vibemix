# SPDX-License-Identifier: Apache-2.0
"""Phase 59 (DECK-01) — evidence_line golden-equivalence under the additive
deck_state field (Pitfall 5).

The deck_state field is added to MusicState as an ADDITIVE, default-empty
field. This phase does NOT touch evidence_line (the deck block lands in Plan
59-04). The contract this file pins: introducing deck_state — and even
populating it — leaves evidence_line BYTE-IDENTICAL to the pre-Phase-59
baseline, because evidence_line does not read deck_state yet.

Plan 59-04 wires the deck block into evidence_line, so:
- byte-identity-WHEN-EMPTY still holds (empty deck_state → no deck output,
  mirroring the existing track=unknown gate — these tests stay green);
- a POPULATED + resolved deck_state now renders ``decks[A='..' 8A 128bpm]``;
- a populated-but-unresolved deck_state renders honest ``decks=unknown``.
"""

from __future__ import annotations

from vibemix.state.coach import AICoach
from vibemix.state.deck_state import DeckState, DeckTrack
from vibemix.state.music_state import MusicState


def _grounded_state(*, bpm: float = 128.0, rms: float = 0.06) -> MusicState:
    """A 'music truly playing' MusicState with real numbers (mirrors the
    helper in tests/agent/test_coach_prompt_grounding.py)."""
    ms = MusicState()
    ms.audible = True
    ms.bpm = bpm
    ms.rms = rms
    ms.bands = {"sub": 0.25, "low": 0.30, "mid": 0.25, "high": 0.20}
    ms.phase = "drop"
    return ms


# The pre-Phase-59 evidence_line for a freshly-constructed (silent) MusicState.
# Captured by hand from the v4 evidence_line shape (hearing[silent] |
# track=unknown | deck=none | set_time=0:00 | recent_moves[8s]: NONE). The
# additive deck_state field must NOT perturb this.
_BASELINE_SILENT = (
    "hearing[silent] | track=unknown | deck=none | set_time=0:00 | "
    "recent_moves[8s]: NONE"
)


def test_empty_deck_state_evidence_line_matches_baseline():
    """A bare MusicState (empty deck_state) yields the exact pre-Phase-59
    evidence_line — the additive field adds nothing until populated."""
    assert AICoach.evidence_line(MusicState()) == _BASELINE_SILENT


def test_deck_state_does_not_appear_in_evidence_line_when_empty():
    """No 'deck_state'/'decks[' substring leaks into the prompt for an empty
    deck_state (golden-equivalence; the deck block is Plan 59-04)."""
    line = AICoach.evidence_line(_grounded_state())
    assert "decks[" not in line
    assert "deck_state" not in line


def test_resolved_deck_state_renders_deck_block():
    """Plan 59-04: a resolved deck_state (camelot + confidence>=0.3) now renders
    a grounded decks[...] block — title, Camelot, bpm."""
    populated = _grounded_state()
    populated.deck_state = DeckState(
        decks={"A": DeckTrack(title="Strobe", key="Am", camelot="8A",
                              bpm=128.0, confidence=0.8, source="rekordbox_xml")},
        updated_at=12.5,
    )
    line = AICoach.evidence_line(populated)
    assert "decks[A='Strobe' 8A 128bpm]" in line


def test_populated_but_unresolved_deck_state_renders_unknown():
    """A deck_state present but with NO resolved deck (camelot None / sub-0.3
    confidence) renders honest decks=unknown — never a fabricated key."""
    populated = _grounded_state()
    populated.deck_state = DeckState(
        decks={"A": DeckTrack(title="Mystery", key=None, camelot=None,
                              bpm=0.0, confidence=0.0, source="unknown")},
        updated_at=12.5,
    )
    line = AICoach.evidence_line(populated)
    assert "decks=unknown" in line
    assert "decks[" not in line


def test_grounded_baseline_unchanged_by_deck_state():
    """The grounded (audible) evidence_line still opens with the real audio
    numbers and carries no deck output — the additive field is invisible."""
    line = AICoach.evidence_line(_grounded_state(bpm=128.0, rms=0.06))
    assert line.startswith("hearing[rms=")
    assert "bpm=128" in line
    assert "deck=none" in line  # the EXISTING audible_deck field, not deck_state
    assert "decks[" not in line


# --- One Mind S1 — validated blend relation between two loaded decks -------


def _two_deck_state(*, a_camelot: str, b_camelot: str, a_bpm: float, b_bpm: float):
    return DeckState(
        decks={
            "A": DeckTrack(
                title="OutA", key="x", camelot=a_camelot, bpm=a_bpm,
                confidence=0.8, source="rekordbox_xml",
            ),
            "B": DeckTrack(
                title="InB", key="y", camelot=b_camelot, bpm=b_bpm,
                confidence=0.8, source="rekordbox_xml",
            ),
        },
        updated_at=12.5,
    )


def test_s1_two_resolved_decks_emit_compatible_blend_relation():
    """With two loaded decks resolved, the prompt states the VALIDATED relation
    (Camelot arrow + BPM delta + harmonic verdict) — the brain no longer has to
    infer compatibility from two bare keys."""
    populated = _grounded_state()
    populated.deck_state = _two_deck_state(
        a_camelot="8A", b_camelot="9A", a_bpm=128.0, b_bpm=130.0
    )
    line = AICoach.evidence_line(populated)
    assert "blend[8A→9A, +2 BPM harmonic-ok]" in line


def test_s1_clashing_decks_flagged_harmonic_clash():
    """A real Camelot clash is stated as such — closes the 'brain calls a clash
    a smooth mix' failure deterministically."""
    populated = _grounded_state()
    populated.deck_state = _two_deck_state(
        a_camelot="8A", b_camelot="3A", a_bpm=128.0, b_bpm=128.0
    )
    line = AICoach.evidence_line(populated)
    assert "harmonic-clash" in line
    assert "blend[8A→3A, same BPM harmonic-clash]" in line


def test_s1_single_deck_emits_no_blend_relation():
    """One resolved deck → no blend token (needs a pair). Byte-identical to the
    existing single-deck deck block."""
    populated = _grounded_state()
    populated.deck_state = DeckState(
        decks={"A": DeckTrack(title="Strobe", key="Am", camelot="8A",
                              bpm=128.0, confidence=0.8, source="rekordbox_xml")},
        updated_at=12.5,
    )
    line = AICoach.evidence_line(populated)
    assert "blend[" not in line
