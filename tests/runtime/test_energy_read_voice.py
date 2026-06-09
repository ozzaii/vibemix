# SPDX-License-Identifier: Apache-2.0
"""Producer-level tests for the master-mix energy receipt.

Iter5 of the 2026-06-09/10 bench campaign: the judge scored every spoken
steady-read line as filler — iter3 (audio-only corpus, n=1): "Generic filler
telling the DJ to do nothing; should stay silent."; iter4 (synth-MIDI corpus):
the one steady line was the only friend=0 / should_speak=False line in an
otherwise passing set. The steady/no-information forward bodies therefore no
longer EARN a voice receipt: a receipt exists to carry a point, and "keep
doing what you're doing" is not a point. Change reads (lifting, breathing
space, delta-driven bodies) and scorer-transition receipts are untouched —
those are the lines the judge marked should_speak=True.
"""

from __future__ import annotations

from vibemix.intel.transition_scorer import LIVE_SELECT_CONFIDENCE_FLOOR
from vibemix.runtime.energy_read_voice import build_energy_read_voice_line
from vibemix.state import MusicState
from vibemix.state.evidence_registry import EvidenceRegistry


def _state(
    *,
    curve: list[float] | None = None,
    phase: str = "groove",
    buildup: float = 0.0,
) -> MusicState:
    state = MusicState()
    state.audible = True
    state.phase = phase
    state.buildup_score = buildup
    if curve is not None:
        state.energy_curve = curve
    return state


def _suggestion(confidence: float) -> dict:
    return {
        "title": "Neon Tide",
        "artist": "Velvet Mirage",
        "track_id": "velvet-mirage-neon-tide",
        "transition": {
            "confidence": confidence,
            "score": 0.81,
            "to_track_id": "velvet-mirage-neon-tide",
            "candidate_id": "cand_neon_tide_01",
            "reasons": ["camelot adjacent"],
            "risk_flags": [],
        },
    }


def test_settled_read_without_transition_yields_no_receipt() -> None:
    """The measured-filler body ('holding the groove steady') no longer earns
    a receipt on its own — judged friend 0 / should_speak False on both
    corpora. No receipt → the speak gate's describe-bank rule holds the event
    silent, which is the product-correct outcome for 'keep doing nothing'."""
    line = build_energy_read_voice_line(
        None,
        event_type="PHASE",
        evidence_registry=EvidenceRegistry(),
        state=_state(curve=[0.50, 0.50, 0.40, 0.40]),  # settling arc
    )
    assert line is None


def test_pure_fallback_reads_yield_no_receipt() -> None:
    """The two pure-fallback bodies ('the current phrase direction' / 'the
    current master-mix energy') carry zero information by construction —
    same hold."""
    line = build_energy_read_voice_line(
        None,
        event_type="PHASE",
        evidence_registry=EvidenceRegistry(),
        state=_state(phase="peak"),  # no arc, no deltas → phrase fallback only
    )
    assert line is None


def test_lifting_read_still_yields_receipt() -> None:
    """A CHANGE read keeps its receipt — 'lifting the next phrase' carries a
    real directive and is the register the judge passes."""
    reg = EvidenceRegistry()
    line = build_energy_read_voice_line(
        None,
        event_type="PHASE",
        evidence_registry=reg,
        state=_state(curve=[0.30, 0.30, 0.45, 0.50]),  # lifting arc
    )
    assert isinstance(line, str)
    assert "lifting the next phrase without rushing it" in line
    assert "energy" in reg.snapshot()  # citation key registered at build time


def test_breathing_space_read_still_yields_receipt() -> None:
    """'Letting the current space breathe' carries a directive (add nothing)
    — kept, distinct from the steady family."""
    # buildup 0.3 keeps the arc clause neutral (a default-0.0 buildup on a
    # groove/low/breakdown phase reads as a SETTLED arc — the steady family).
    line = build_energy_read_voice_line(
        None,
        event_type="PHASE",
        evidence_registry=EvidenceRegistry(),
        state=_state(phase="breakdown", buildup=0.3),
    )
    assert isinstance(line, str)
    assert "letting the current space breathe" in line


def test_settling_arc_with_sub_fell_delta_yields_earned_receipt() -> None:
    """Deltas outrank arcs: a settling arc + a live 'sub fell' delta is NOT a
    steady read — the delta carries the point ('leave low-end space'). Before
    the iter6a reorder this combination hit the settled branch first and was
    silenced as filler, shadowing an EARNED line (auditor follow-up a)."""
    reg = EvidenceRegistry()
    line = build_energy_read_voice_line(
        None,
        event_type="PHASE",
        evidence_registry=reg,
        state=_state(curve=[0.50, 0.50, 0.40, 0.40]),  # settling arc
        audio_delta_items=["sub energy fell 0.21 -> 0.09"],
    )
    assert isinstance(line, str)
    assert "leaving low-end space before the next push" in line
    assert "energy" in reg.snapshot()


def test_lifting_arc_with_sub_rose_delta_prefers_delta_body() -> None:
    """Same precedence on the lifting side: the measured delta is fresher and
    more specific than the windowed arc, so its body leads the nudge."""
    line = build_energy_read_voice_line(
        None,
        event_type="PHASE",
        evidence_registry=EvidenceRegistry(),
        state=_state(curve=[0.30, 0.30, 0.45, 0.50]),  # lifting arc
        audio_delta_items=["sub energy rose 0.10 -> 0.24"],
    )
    assert isinstance(line, str)
    assert "controlling the added weight in the next phrase" in line


def test_unmatched_deltas_fall_to_no_info_body_and_stay_silent() -> None:
    """Auditor follow-up (b): pin the third no-info body. Deltas that match no
    rule ('stereo width rose'), no arc, no phase read → 'the current
    master-mix energy' → held silent like the other no-info bodies."""
    line = build_energy_read_voice_line(
        None,
        event_type="PHASE",
        evidence_registry=EvidenceRegistry(),
        state=_state(phase=""),
        audio_delta_items=["stereo width rose 0.40 -> 0.55"],
    )
    assert line is None


def test_settled_read_with_transition_context_keeps_receipt() -> None:
    """A scorer-transition receipt survives a settled arc — the point is the
    suggested track, not the steady read."""
    reg = EvidenceRegistry()
    line = build_energy_read_voice_line(
        _suggestion(confidence=max(0.9, LIVE_SELECT_CONFIDENCE_FLOOR)),
        event_type="PHASE",
        evidence_registry=reg,
        state=_state(curve=[0.50, 0.50, 0.40, 0.40]),  # settling arc
    )
    assert isinstance(line, str)
    assert "Neon Tide" in line
    assert "track" in reg.snapshot()
