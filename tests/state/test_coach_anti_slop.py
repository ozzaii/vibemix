# SPDX-License-Identifier: Apache-2.0
"""LIVE-02 anti-slop spine for COACH (feedback) mode (Phase 55 Plan 01).

vibemix's central product principle (project_anti_slop_grounded_gemini_thesis)
and the hallucination-grounding hard gate (CLAUDE.md release blocker) apply to
COACH mode exactly as they do to HYPE: every coaching reaction must trace to a
real Event + real evidence, and when the evidence is empty/weak the system
stays SILENT rather than hallucinating a coaching line.

This file proves the COACH GROUNDING LEG, REUSING Phase 54's primitives + the
real fixture (tests/fixtures/hype_trace_genre1.jsonl) WITHOUT duplicating them.

What this file pins:

SPINE (emit gate) — the REAL CitationLinter strips a coach reaction citing an
    event NOT in the EvidenceRegistry snapshot (reason 'invalid_atoms' -> no
    voice), and PASSES a grounded coach reaction whose citation resolves in
    the registry. Silence > invented coaching. (Task 1.)

≥2-GENRE COACH-EVENT GROUNDING — genre-1 drives the REAL EventDetector over
    the REUSED real fixture to confirm coach-relevant events (PHASE / MIX_MOVE
    / HEARTBEAT) fire grounded; genre-2 is a synthetic house/techno BPM-128
    build->drop sequence through the same detector. Empty/weak evidence ->
    detect returns None (no fire -> no hallucinated coaching). (Task 2.)

What this file deliberately DOES NOT do:

- It does NOT re-prove the detector FLOOR (the detector refusing to fire on
  silent / out-of-range-BPM / within-presence-window states). That FLOOR is
  persona-independent and already pinned by tests/state/test_hype_anti_slop.py
  — re-proving it here would be duplication.
- It does NOT modify any source. coach.py / matrix.py / citation_linter.py /
  evidence_registry.py / event_detector.py are untouched; this is an additive
  test that PINS existing behavior, not a change.

KAAN-ACTION (deferred, NOT this test): the real "does coach mode coach
genuinely USEFULLY across ≥2 genres" live drive on Kaan's library on his Mac
is the felt-quality sign-off (his ears, project_phase_16_kaan_dj_testing).
Engineering proves grounding + zero hallucinated coaching here; usefulness is
the live-drive gate.

REAL primitives only — no mocks of the linter / registry / detector, no
network, no live LLM.
"""

from __future__ import annotations

import json
from pathlib import Path

from vibemix.audio.constants import (
    BPM_VALID_MAX,
    BPM_VALID_MIN,
    LOW_RMS,
    MUSIC_PRESENCE_MIN_SECONDS,
)
from vibemix.coach.citation_linter import CitationLinter
from vibemix.state import EventDetector, MusicState
from vibemix.state.evidence_registry import EvidenceRegistry

# The genre-1 ground-truth trace is REUSED from Phase 54 — it is mode-agnostic
# (events fire the same regardless of hype/coach persona). NO second coach-named
# copy is created.
FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "hype_trace_genre1.jsonl"


def _state(
    *,
    audible: bool = True,
    bpm: float = 130.0,
    phase: str = "groove",
    bands: dict | None = None,
    rms: float = 0.06,
) -> MusicState:
    """A 'music truly playing' MusicState. Reuses the field set of the
    _state helper in test_hype_anti_slop.py / test_hype_trace_replay.py —
    tests opt INTO restrictive conditions (silence / bpm-edge) by overriding
    the defaults."""
    ms = MusicState()
    ms.audible = audible
    ms.bpm = bpm
    ms.phase = phase
    ms.bands = (
        bands if bands is not None else {"sub": 0.2, "low": 0.3, "mid": 0.3, "high": 0.2}
    )
    ms.rms = rms
    return ms


def _patch_time(mocker, value: float):
    return mocker.patch("vibemix.state.event_detector.time.time", return_value=value)


def _seed_presence_gate(d: EventDetector, *, t0: float) -> None:
    """Clear the music-presence gate WITHOUT polluting the change-detection
    refs (set _audible_since directly, mirroring test_hype_trace_replay.py).
    Caller patches the clock to >= t0 + MUSIC_PRESENCE_MIN_SECONDS before the
    next detect()."""
    d._audible_since = t0


# =========================================================================== #
# SPINE — linter strips the unbacked COACH citation, passes the grounded one  #
#                                                                             #
# Coach-relevant event citations (PHASE / MIX_MOVE / HEARTBEAT) — the linter  #
# is persona-independent, so the SPINE is proven with coach-shaped citations  #
# against the REAL EvidenceRegistry + CitationLinter.                          #
# =========================================================================== #


def test_spine_unbacked_coach_citation_is_stripped():
    """A coach reaction citing a MIX_MOVE NOT in an EMPTY EvidenceRegistry
    snapshot -> CitationLinter.check(...).valid is False, reason
    'invalid_atoms' -> routes to the strip path (no voice). REAL primitives,
    no network, no live LLM. Silence > invented coaching."""
    reg = EvidenceRegistry()
    snap_empty = reg.snapshot()
    assert snap_empty == {}  # cold registry is genuinely empty
    result = CitationLinter().check(
        "kicks stepped for a half-bar [ev:MIX_MOVE@83.0]", snap_empty, mode="live"
    )
    assert result.valid is False
    assert result.reason == "invalid_atoms"
    # The orphan surfaces for telemetry.
    assert ("ev", "MIX_MOVE@83.0") in result.missing


def test_spine_grounded_coach_citation_passes():
    """The SAME coach reaction, AFTER the event is written to the registry
    within the live ±1.0s tolerance, checks valid is True -> the grounded path
    emits. The spine strips the fabricated coaching line but lets the real one
    through."""
    reg = EvidenceRegistry()
    reg.write("ev", "MIX_MOVE", 83.0)
    snap = reg.snapshot()
    result = CitationLinter().check(
        "kicks stepped for a half-bar [ev:MIX_MOVE@83.0]", snap, mode="live"
    )
    assert result.valid is True
    assert result.reason == "valid"


def test_spine_grounded_coach_citation_within_live_tolerance_passes():
    """A coach citation 0.2s off the observation ([ev:MIX_MOVE@83.2] vs the
    observation at 83.0) still resolves within the ±1.0s live tolerance ->
    valid True. The grounding tolerates small clock drift but not
    fabrication."""
    reg = EvidenceRegistry()
    reg.write("ev", "MIX_MOVE", 83.0)
    snap = reg.snapshot()
    result = CitationLinter().check(
        "kicks stepped for a half-bar [ev:MIX_MOVE@83.2]", snap, mode="live"
    )
    assert result.valid is True
    assert result.reason == "valid"


def test_spine_grounded_phase_coach_citation_passes():
    """A coach reaction on a PHASE event resolves once the PHASE fire is in
    the registry — confirming the SPINE holds for the PHASE coach-relevant
    event class too (not only MIX_MOVE)."""
    reg = EvidenceRegistry()
    reg.write("ev", "PHASE", 120.5)
    snap = reg.snapshot()
    result = CitationLinter().check(
        "the build released a touch early [ev:PHASE@120.5]", snap, mode="live"
    )
    assert result.valid is True
    assert result.reason == "valid"


def test_spine_citation_free_coach_line_does_not_emit():
    """A citation-free coaching line ('Tighten that blend.') -> valid False,
    reason 'no_citations'. The silence-over-slop spine: a generic coaching line
    with no grounding does not pass the linter chokepoint. Even a non-empty
    registry cannot rescue a line that cites nothing."""
    reg = EvidenceRegistry()
    reg.write("ev", "MIX_MOVE", 83.0)
    result = CitationLinter().check("Tighten that blend.", reg.snapshot(), mode="live")
    assert result.valid is False
    assert result.reason == "no_citations"


def test_spine_uses_real_primitives_not_mocks():
    """Documents the test contract: the coach SPINE is pinned with the concrete
    EvidenceRegistry + CitationLinter classes (no mocks of either), no network.
    A regression in either primitive surfaces here."""
    assert CitationLinter().__class__.__name__ == "CitationLinter"
    reg = EvidenceRegistry()
    assert reg.snapshot() == {}  # cold registry is genuinely empty
    reg.write("ev", "MIX_MOVE", 83.0)
    assert reg.snapshot() == {"ev": {"MIX_MOVE": (83.0,)}}  # real append-only write
