# SPDX-License-Identifier: Apache-2.0
"""Phase 78 PERCEIVE — Wave-0 RED scaffolds + cold-path byte-identity pin.

Two contracts live here:

1. **Cold-path byte-identity (REAL GREEN — NOT xfail).** A default ``MusicState``
   and an audible ``MusicState`` with NO prior snapshot (``prev_perceive == {}``)
   and an empty ``trajectory_narrative`` produce evidence_line output BYTE-IDENTICAL
   to the v8.0 baseline — NO ``trajectory[`` token, NO ``Δ``/``rose``/``fell`` delta
   phrasing. This asserts the additive-design invariant that implementation
   (Plan 02/04) must preserve: the gated-off cold path adds zero bytes. It passes
   TODAY and must KEEP passing after PERCEIVE-01/02 land.

2. **PERCEIVE-01/02 render scaffolds (xfail-strict — flips when Plan 02 lands).**
   Each behavior that depends on a not-yet-existing ``MusicState`` field
   (``prev_perceive``, ``trajectory_narrative``) + a not-yet-written coach.py
   delta/trajectory render branch is marked ``xfail(strict=True)`` so it counts as
   an expected-fail today and a HARD failure the moment it silently flips green
   (the Nyquist safety net). Plan 02 deletes the marker and the test goes real green.

Honest green: pure dataclass construction + render assertions. NO ``genai.Client``,
NO ``GEMINI_API_KEY``, NO live API on any path.
"""

from __future__ import annotations

import pytest

from vibemix.state import AICoach, MusicState

# v8.0 baseline audible-block golden — copied VERBATIM from
# tests/state/test_coach.py::test_evidence_line_audible_no_recall_byte_identical_v5_baseline
# (the absolute-bytes pin). PERCEIVE adds fields with falsy defaults; the cold
# path (prev_perceive={}, trajectory_narrative="") must reproduce this exactly.
_V8_AUDIBLE_BASELINE = (
    "hearing[rms=0.094 sub=0.20 low=0.30 mid=0.30 high=0.20 bpm=126] | "
    "track='Daft Punk - Around the World' | deck=A | set_time=4:05 | "
    "recent_moves[8s]: NONE"
)


def _audible_baseline_state() -> MusicState:
    """The exact audible state the v8.0 baseline golden was captured against."""
    return MusicState(
        audible=True,
        rms=0.094,
        bands={"sub": 0.20, "low": 0.30, "mid": 0.30, "high": 0.20},
        bpm=126.0,
        audible_track="Daft Punk - Around the World",
        audible_track_confidence=0.6,
        audible_deck="A",
        set_start_at=755.0,  # now-set = 245s → 4:05
    )


# ---------- Pure render_delta unit coverage (PERCEIVE-01) ----------


def test_render_delta_rendered_above_floor():
    """A relative change clearing the floor renders ``<label> rose/fell N%``."""
    from vibemix.state.deltas import render_delta

    out = render_delta("kick density", 0.59, 0.50, floor=0.1)
    assert out is not None
    assert "kick density" in out
    assert "rose" in out
    out_down = render_delta("RMS", 0.04, 0.094, floor=0.1)
    assert out_down is not None and "fell" in out_down


def test_render_delta_abstains_cold():
    """``prev is None`` (cold) or ``prev == 0.0`` → abstain (None)."""
    from vibemix.state.deltas import render_delta

    assert render_delta("kick", 0.59, None, floor=0.1) is None
    assert render_delta("kick", 0.59, 0.0, floor=0.1) is None


def test_render_delta_abstains_below_floor():
    """A sub-floor relative change → abstain (None), never a 0% line."""
    from vibemix.state.deltas import render_delta

    assert render_delta("kick", 0.501, 0.500, floor=0.1) is None


def test_calibrate_confidence_monotone_buckets():
    """The calibration map is deterministic + monotone over rel-magnitude."""
    from vibemix.state.deltas import calibrate_confidence

    assert calibrate_confidence(0.50) == "strong"
    assert calibrate_confidence(0.20) == "clear"
    assert calibrate_confidence(0.11) == "slight"
    # symmetric in sign
    assert calibrate_confidence(-0.50) == "strong"


# ---------- Cold-path byte-identity (REAL GREEN pin) ----------


def test_cold_path_byte_identical(mocker):
    """A cold audible state (no prior snapshot, empty trajectory) renders the
    v8.0 baseline byte-for-byte — zero delta/trajectory bytes.

    This is the additive-design contract: PERCEIVE fields default falsy, every
    new render branch is ``if <field>:``-gated, so the cold path is unchanged.
    Passes today; MUST stay green after Plan 02/04 lands.
    """
    mocker.patch("vibemix.state.coach.time.time", return_value=1000.0)
    state = _audible_baseline_state()
    out = AICoach.evidence_line(state)

    # Absolute-bytes pin (the v8.0 baseline).
    assert out == _V8_AUDIBLE_BASELINE

    # Anti-regression: no trajectory token, no delta phrasing on the cold path.
    assert "trajectory[" not in out
    assert "Δ" not in out
    assert "rose" not in out
    assert "fell" not in out


def test_default_state_byte_identical():
    """The silent default ``MusicState()`` is byte-identical to the v8.0 silent
    golden — PERCEIVE adds nothing on the coldest path."""
    out = AICoach.evidence_line(MusicState())
    assert out == (
        "hearing[silent] | track=unknown | deck=none | set_time=0:00 | recent_moves[8s]: NONE"
    )
    assert "trajectory[" not in out
    assert "Δ" not in out


def test_empty_trajectory_omitted(mocker):
    """``trajectory_narrative`` cold (default "") → no ``trajectory[`` token.

    Real green TODAY (the substring is simply absent from the v8.0 output) and a
    standing pin for the gated render branch Plan 02 adds: when the field is the
    falsy default, the branch appends zero bytes. Phrased as a real green (not
    xfail) because it asserts an ABSENCE that holds on the current baseline — the
    cold byte-identity contract from the other angle.
    """
    mocker.patch("vibemix.state.coach.time.time", return_value=1000.0)
    state = _audible_baseline_state()
    out = AICoach.evidence_line(state)
    assert "trajectory[" not in out


# ---------- PERCEIVE-01/02 render scaffolds (xfail-strict) ----------


def test_delta_rendered_when_change_significant(mocker):
    """A state whose ``prev_perceive`` holds prior scalars + a current change
    above the floor renders DELTA phrasing in place of the bare scalar.

    RED today: ``MusicState`` has no ``prev_perceive`` field (TypeError on the
    kwarg) and coach.py has no delta branch. Plan 02 adds both → real pass.
    """
    mocker.patch("vibemix.state.coach.time.time", return_value=1000.0)
    state = MusicState(
        audible=True,
        rms=0.094,
        bands={"sub": 0.20, "low": 0.30, "mid": 0.30, "high": 0.20},
        bpm=126.0,
        # Prior tick: kick density / sub markedly lower → current shows a clear rise.
        prev_perceive={
            "rms": 0.040,
            "sub": 0.08,
            "low": 0.30,
            "mid": 0.30,
            "high": 0.20,
            "bpm": 126.0,
        },
    )
    out = AICoach.evidence_line(state)
    # Delta phrasing surfaces (rose/fell/Δ/% per the render-helper contract).
    assert ("rose" in out) or ("fell" in out) or ("Δ" in out) or ("%" in out)


def test_delta_abstains_below_floor(mocker):
    """Prior present but the change is BELOW the floor → abstain (omit), never a
    ``0%``/``Δ0`` delta line. Anti-slop contract (invariant #2/#3): a fact that
    didn't meaningfully move is NOT asserted as a delta.

    RED today (no ``prev_perceive`` field). Plan 02's render helper returns
    ``None`` below floor → the bare scalar stands, no delta line.
    """
    mocker.patch("vibemix.state.coach.time.time", return_value=1000.0)
    state = MusicState(
        audible=True,
        rms=0.094,
        bands={"sub": 0.20, "low": 0.30, "mid": 0.30, "high": 0.20},
        bpm=126.0,
        # Prior tick essentially identical → sub-floor change → abstain.
        prev_perceive={
            "rms": 0.093,
            "sub": 0.20,
            "low": 0.30,
            "mid": 0.30,
            "high": 0.20,
            "bpm": 126.0,
        },
    )
    out = AICoach.evidence_line(state)
    # Abstain = omit. No zero-delta noise.
    assert "0%" not in out
    assert "Δ0" not in out
    assert "rose 0" not in out
    assert "fell 0" not in out


def test_trajectory_rendered_when_warm(mocker):
    """A warm ``trajectory_narrative`` renders a gated ``trajectory[…]`` token.

    RED today: ``MusicState`` has no ``trajectory_narrative`` field (TypeError on
    the kwarg). Plan 02 adds the field + the ``if state.trajectory_narrative:``
    gated render branch → real pass.
    """
    mocker.patch("vibemix.state.coach.time.time", return_value=1000.0)
    state = MusicState(
        audible=True,
        rms=0.094,
        bands={"sub": 0.20, "low": 0.30, "mid": 0.30, "high": 0.20},
        bpm=126.0,
        trajectory_narrative="3rd phrase of an energy build; last move: bass-swap 20s ago",
    )
    out = AICoach.evidence_line(state)
    assert "trajectory[" in out
    assert "energy build" in out
