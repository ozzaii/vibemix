# SPDX-License-Identifier: Apache-2.0
"""LIVE-01 anti-slop spine for hype mode (Phase 54 Plan 03).

vibemix's central product principle (project_anti_slop_grounded_gemini_thesis)
and the hallucination-grounding hard gate (CLAUDE.md release blocker): every
hype reaction must trace to a real Event + real evidence, and when the evidence
is empty/weak the system stays SILENT rather than hallucinating a hype line.
This makes that a regression, not a hope.

TWO gates pinned with the REAL primitives (no network, no live LLM):

FLOOR (detector) — the REAL EventDetector refuses to fire on silent / out-of-
    range-BPM / within-music-presence-window states. Hype mode does NOT
    manufacture a reaction from nothing.

SPINE (emit gate) — the REAL CitationLinter strips a reaction citing an event
    NOT in the EvidenceRegistry snapshot (reason 'invalid_atoms' -> no voice),
    and PASSES a grounded reaction whose citation resolves in the registry.
    Silence > invented citation.

No source behavior is modified — the strip-on-unbacked-citation behavior is
PINNED, not changed.
"""

from __future__ import annotations

from vibemix.audio.constants import MUSIC_PRESENCE_MIN_SECONDS
from vibemix.coach.citation_linter import CitationLinter
from vibemix.state import EventDetector, MusicState
from vibemix.state.evidence_registry import EvidenceRegistry


def _state(
    *,
    audible: bool = True,
    bpm: float = 130.0,
    phase: str = "groove",
) -> MusicState:
    ms = MusicState()
    ms.audible = audible
    ms.bpm = bpm
    ms.phase = phase
    ms.bands = {"sub": 0.2, "low": 0.3, "mid": 0.3, "high": 0.2}
    ms.rms = 0.06
    return ms


def _patch_time(mocker, value: float):
    return mocker.patch("vibemix.state.event_detector.time.time", return_value=value)


# =========================================================================== #
# FLOOR — detector refuses to fire on empty / weak evidence                   #
# =========================================================================== #


def test_floor_silent_state_does_not_fire(mocker):
    """A silent state (audible=False, bpm=0) -> detect returns None. The
    music-presence gate stops at not-audible — no auto-event from nothing."""
    d = EventDetector()
    _patch_time(mocker, 1000.0)
    ev = d.detect(_state(audible=False, bpm=0.0), kaan_just_spoke=False, manual=False)
    assert ev is None


def test_floor_out_of_range_bpm_does_not_fire(mocker):
    """An audible state with bpm=300 (out of [100,180]) -> None even after the
    sustained-audible window passes (BPM autocorr locked onto noise)."""
    d = EventDetector()
    ms = _state(bpm=300.0)
    t = _patch_time(mocker, 1000.0)
    d.detect(ms, kaan_just_spoke=False, manual=False)  # seed _audible_since
    t.return_value = 1000.0 + MUSIC_PRESENCE_MIN_SECONDS + 1.0
    ev = d.detect(ms, kaan_just_spoke=False, manual=False)
    assert ev is None


def test_floor_within_music_presence_window_does_not_fire(mocker):
    """An audible state still inside the music-presence window -> None. First
    detect seeds _audible_since; a detect at +1s (before 4s elapse) still
    returns None — the AI stays quiet until music is truly playing."""
    d = EventDetector()
    ms = _state(bpm=130.0)
    t = _patch_time(mocker, 1000.0)
    ev1 = d.detect(ms, kaan_just_spoke=False, manual=False)
    assert ev1 is None
    assert d._audible_since == 1000.0
    t.return_value = 1001.0  # +1s, still < MUSIC_PRESENCE_MIN_SECONDS (4.0)
    ev2 = d.detect(ms, kaan_just_spoke=False, manual=False)
    assert ev2 is None


# =========================================================================== #
# SPINE — linter strips the unbacked citation, passes the grounded one        #
# =========================================================================== #


def test_spine_unbacked_citation_is_stripped():
    """A reaction citing an event NOT in an EMPTY EvidenceRegistry snapshot ->
    CitationLinter.check(...).valid is False, reason 'invalid_atoms' -> routes
    to the strip path (no voice). REAL EvidenceRegistry + CitationLinter, no
    network, no live LLM."""
    reg = EvidenceRegistry()
    snap_empty = reg.snapshot()
    result = CitationLinter().check(
        "Massive drop! [ev:DROP@45.2]", snap_empty, mode="live"
    )
    assert result.valid is False
    assert result.reason == "invalid_atoms"


def test_spine_grounded_citation_passes():
    """The SAME reaction text, AFTER the event is written to the registry within
    the live +-1.0s tolerance, checks valid is True -> the grounded path emits.
    The spine strips the fabricated line but lets the real one through."""
    reg = EvidenceRegistry()
    reg.write("ev", "DROP", 45.2)
    snap = reg.snapshot()
    result = CitationLinter().check(
        "Massive drop! [ev:DROP@45.2]", snap, mode="live"
    )
    assert result.valid is True
    assert result.reason == "valid"


def test_spine_grounded_citation_within_live_tolerance_passes():
    """A citation 0.2s off the observation still resolves within the +-1.0s live
    tolerance -> valid True. The grounding is tolerant of small clock drift but
    not of fabrication."""
    reg = EvidenceRegistry()
    reg.write("ev", "DROP", 45.2)
    snap = reg.snapshot()
    result = CitationLinter().check(
        "Massive drop! [ev:DROP@45.0]", snap, mode="live"
    )
    assert result.valid is True


def test_spine_citation_free_hype_line_does_not_emit_in_wired_path():
    """A citation-free hype line ('Massive energy here!') -> valid False,
    reason 'no_citations'. Documents that the wired emit path requires grounded
    citations — the strip is the silence-over-slop spine: a generic hype line
    with no grounding does not pass the linter chokepoint."""
    reg = EvidenceRegistry()
    reg.write("ev", "DROP", 45.2)
    result = CitationLinter().check(
        "Massive energy here!", reg.snapshot(), mode="live"
    )
    assert result.valid is False
    assert result.reason == "no_citations"


def test_spine_uses_real_primitives_not_mocks():
    """Documents the test contract: the spine is pinned with the concrete
    EvidenceRegistry + CitationLinter classes (no mocks of either), no network.
    A regression in either primitive surfaces here."""
    assert CitationLinter().__class__.__name__ == "CitationLinter"
    reg = EvidenceRegistry()
    assert reg.snapshot() == {}  # cold registry is genuinely empty
    reg.write("ev", "DROP", 1.0)
    assert reg.snapshot() == {"ev": {"DROP": (1.0,)}}  # real append-only write
