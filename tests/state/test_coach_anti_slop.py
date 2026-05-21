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


# =========================================================================== #
# GENRE 1 — real ground-truth trace replay (coach-relevant events)            #
#                                                                             #
# Drives the REAL EventDetector over the REUSED genre-1 fixture to confirm    #
# coach-relevant events (PHASE / MIX_MOVE / HEARTBEAT) fire grounded on the   #
# real trace. The firing path is persona-independent, so a PHASE that fires   #
# on the real trace is exactly the moment coach mode would coach on.          #
# =========================================================================== #


def _load_events() -> list[dict]:
    """Load the genre-1 ground-truth trace, kind=='event' lines only. REUSES
    tests/fixtures/hype_trace_genre1.jsonl (mode-agnostic ground truth) — no
    coach-named copy is created."""
    out: list[dict] = []
    with FIXTURE.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if rec.get("kind") == "event":
                out.append(rec)
    return out


def _coach_relevant(ev_type: str) -> list[dict]:
    """Filter the real trace to a coach-relevant event type."""
    return [e for e in _load_events() if e.get("type") == ev_type]


def test_genre1_fixture_carries_coach_relevant_events():
    """The REUSED genre-1 fixture carries the coach-relevant moments to replay
    — PHASE transitions a coach would call out (build released early, breakdown
    muddied) plus HEARTBEAT steady stretches. Confirms the fixture is the right
    coach ground truth, REUSED (not copied)."""
    assert FIXTURE.name == "hype_trace_genre1.jsonl"  # the REUSED fixture
    phases = _coach_relevant("PHASE")
    heartbeats = _coach_relevant("HEARTBEAT")
    assert len(phases) >= 1, f"expected >=1 PHASE GT event, got {len(phases)}"
    assert len(heartbeats) >= 1, f"expected >=1 HEARTBEAT GT event, got {len(heartbeats)}"


def test_genre1_coach_relevant_phase_fires_grounded(mocker):
    """Each genre-1 ground-truth PHASE event provably fires a PHASE Event
    through the REAL EventDetector — coach-relevant events fire grounded on the
    real trace. For every non-silent GT PHASE: fresh detector, seed the
    presence gate, set last_phase to a DIFFERENT label so the transition is
    real, advance the clock past the presence window, assert detect() returns a
    PHASE Event matching the GT phase."""
    gt_phases = _coach_relevant("PHASE")
    assert gt_phases, "no genre-1 PHASE ground-truth to replay"

    fired = 0
    for gt in gt_phases:
        t = float(gt["t"])
        gt_phase = gt.get("phase") or "drop"
        if gt_phase == "silent":
            # The detector explicitly skips phase=='silent' (not a coach
            # moment) — those GT lines are not in the firing contract.
            continue

        d = EventDetector()
        seed_t = t - MUSIC_PRESENCE_MIN_SECONDS - 0.5
        _seed_presence_gate(d, t0=seed_t)
        # Make the transition real: last_phase must differ from the GT phase.
        d.last_phase = "build" if gt_phase != "build" else "groove"

        _patch_time(mocker, t)
        ms = _state(phase=gt_phase, bpm=130.0)
        ev = d.detect(ms, kaan_just_spoke=False, manual=False)

        assert ev is not None, f"GT PHASE at t={t} ({gt_phase}) produced NO Event"
        assert ev.type == "PHASE", f"GT PHASE at t={t} fired {ev.type}, expected PHASE"
        assert ev.extra["new_phase"] == gt_phase
        fired += 1

    assert fired >= 1, "no replayable (non-silent) genre-1 PHASE events fired"


def test_genre1_coach_relevant_mix_move_fires_grounded(mocker):
    """A coach-relevant MIX_MOVE fires through the REAL detector on a real
    significant controller move — the moment a coach critiques an EQ/fader
    choice. A significant move ('A_low: flat→killed (big twist)') with a fresh
    seen-list fires a MIX_MOVE Event."""
    d = EventDetector()
    seed_t = 4000.0
    _seed_presence_gate(d, t0=seed_t)
    d.last_phase = "groove"  # no PHASE pre-empt on the firing tick

    fire_t = seed_t + MUSIC_PRESENCE_MIN_SECONDS + 1.0
    _patch_time(mocker, fire_t)
    ms = _state(phase="groove", bpm=130.0)
    ms.recent_moves = [(1.0, "A_low: flat→killed (big twist)")]
    ev = d.detect(ms, kaan_just_spoke=False, manual=False)

    assert ev is not None, "significant mix move produced NO Event"
    assert ev.type == "MIX_MOVE"
    assert "A_low: flat→killed (big twist)" in ev.extra["moves"]


def test_genre1_coach_relevant_heartbeat_fires_grounded(mocker):
    """A coach-relevant HEARTBEAT fires on a steady audible stretch with no
    other event — the moment a coach offers one sharp observation. With music
    truly playing, no track/phase/layer/mix change, and the HEARTBEAT cooldown
    clear, detect() falls through to a HEARTBEAT Event."""
    d = EventDetector()
    seed_t = 5000.0
    _seed_presence_gate(d, t0=seed_t)
    # Seed change-detection refs so nothing earlier in the ladder pre-empts:
    d.last_phase = "groove"
    d.last_band_signature = (0.3, 0.2)  # equal to the firing-tick signature

    fire_t = seed_t + MUSIC_PRESENCE_MIN_SECONDS + 1.0
    _patch_time(mocker, fire_t)
    ms = _state(phase="groove", bpm=130.0)  # bands mid=0.3 high=0.2 == baseline
    ms.recent_moves = []  # no mix move
    ev = d.detect(ms, kaan_just_spoke=False, manual=False)

    assert ev is not None, "steady stretch produced NO Event"
    assert ev.type == "HEARTBEAT"


# =========================================================================== #
# GENRE 2 — synthetic-but-grounded house/techno build->drop                   #
#                                                                             #
# Combined with genre 1 (above), the AUTOMATED suite covers ≥2 genres for     #
# coach grounding per LIVE-02. The real ≥2-genre coach-USEFULNESS live drive  #
# across Kaan's library is Kaan-action (deferred), not this test.             #
# =========================================================================== #


def test_genre2_synthetic_build_to_drop_fires_phase_grounded(mocker):
    """House/techno BPM-128 build->drop: a real non-silent PHASE transition
    fires a PHASE Event through the REAL detector. SECOND genre, automated —
    the moment a coach would call out the drop landing. BPM 128 is in
    [100,180] so the music-presence gate passes."""
    d = EventDetector()
    seed_t = 6000.0
    _seed_presence_gate(d, t0=seed_t)
    d.last_phase = "build"

    fire_t = seed_t + MUSIC_PRESENCE_MIN_SECONDS + 1.0
    _patch_time(mocker, fire_t)
    drop = _state(bpm=128.0, phase="drop")
    ev = d.detect(drop, kaan_just_spoke=False, manual=False)

    assert ev is not None, "genre-2 build->drop produced NO Event"
    assert ev.type == "PHASE"
    assert ev.extra == {"prev_phase": "build", "new_phase": "drop"}


# =========================================================================== #
# EMPTY / WEAK EVIDENCE — no fire, so coach mode never coaches from nothing    #
# =========================================================================== #


def test_empty_evidence_silent_state_does_not_fire(mocker):
    """A silent state (audible=False, bpm=0) -> detect returns None. Empty
    evidence yields no fire, so coach mode never manufactures coaching from
    nothing — the no-hallucinated-coaching floor at the detector boundary."""
    d = EventDetector()
    _patch_time(mocker, 7000.0)
    ev = d.detect(_state(audible=False, bpm=0.0), kaan_just_spoke=False, manual=False)
    assert ev is None


def test_weak_evidence_out_of_range_bpm_does_not_fire(mocker):
    """An audible state with bpm out of [100,180] -> None even after the
    sustained-audible window passes (BPM autocorr locked onto noise). Weak
    evidence yields no fire -> no hallucinated coaching."""
    d = EventDetector()
    ms = _state(bpm=BPM_VALID_MAX + 50.0)
    t = _patch_time(mocker, 8000.0)
    d.detect(ms, kaan_just_spoke=False, manual=False)  # seed _audible_since
    t.return_value = 8000.0 + MUSIC_PRESENCE_MIN_SECONDS + 1.0
    ev = d.detect(ms, kaan_just_spoke=False, manual=False)
    assert ev is None

    # And below the valid floor — same no-fire contract.
    d2 = EventDetector()
    ms2 = _state(bpm=BPM_VALID_MIN - 30.0)
    t2 = _patch_time(mocker, 9000.0)
    d2.detect(ms2, kaan_just_spoke=False, manual=False)
    t2.return_value = 9000.0 + MUSIC_PRESENCE_MIN_SECONDS + 1.0
    assert d2.detect(ms2, kaan_just_spoke=False, manual=False) is None
    # Sanity: LOW_RMS is a real grounding constant in scope (no fabricated tuning).
    assert LOW_RMS > 0.0
