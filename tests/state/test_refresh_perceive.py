# SPDX-License-Identifier: Apache-2.0
"""Phase 78 PERCEIVE — single-writer + trajectory + genre-feed + reconciliation
Wave-0 RED scaffolds (ALL xfail-strict).

These pin the invariant-#1 (single-writer) contracts that Plans 02/04 must
satisfy: every new ``MusicState`` field (``prev_perceive``,
``trajectory_narrative``) and the embedding-genre value are written ONLY inside
``_tick_once``'s lock batch — never by a second writer. The genre-reconciliation
test is the flagged-risk pin (embedding-genre vs DSP-genre → one coherent label
per tick).

Every test is ``xfail(strict=True)`` today (the fields / reconciliation logic do
not exist yet) and flips to a real pass when Plan 02/04 lands — the moment one
silently passes early, strict-xfail turns it into a HARD failure (the Nyquist
safety net).

Honest green: synthetic ``MusicState`` + fake snapshots driven through
``_tick_once``. NO ``genai.Client``, NO ``GEMINI_API_KEY``, NO live API.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from tests.audio.conftest import int16_sine
from vibemix.audio import AudioBuffer
from vibemix.state import MusicState
from vibemix.state.refresh import _compose_trajectory, _tick_once


def _audible_buf() -> AudioBuffer:
    """6s of 440Hz sine → rms well above SILENT_RMS (the audible branch)."""
    buf = AudioBuffer(seconds=140.0, sr=16000)
    buf.push(int16_sine(freq_hz=440.0, duration_sec=6.0, sample_rate=16000, amplitude=0.5))
    return buf


def _ctrl_mock(connected: bool = True) -> MagicMock:
    m = MagicMock()
    m.deck_snapshot.return_value = {
        "A": {"vol": 127, "play": True, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64},
        "B": {"vol": 0, "play": False, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64},
        "xfader": 0,
        "connected": connected,
    }
    m.moves_since.return_value = []
    return m


def _track_mock(title: str = "") -> MagicMock:
    m = MagicMock()
    m.snapshot.return_value = {"title": title, "prev_title": "", "title_changed_at": 0.0}
    return m


def _tick(state: MusicState, *, now: float = 1000.0) -> None:
    """Drive one deterministic tick through the single-writer body."""
    _tick_once(
        state,
        _audible_buf(),
        _ctrl_mock(),
        _track_mock(),
        now=now,
        last_audible_high=now,
        last_audible_low=0.0,
        bpm_cache=126.0,
        last_bpm_at=now,
    )


# ---------- PERCEIVE-01 — prev-snapshot single-writer ----------


def test_prev_snapshot_written_in_lock():
    """After a ``_tick_once``, ``state.prev_perceive`` holds the just-written
    scalar set (rms/bands/onset_density/bpm/crest) — captured LAST inside the
    lock batch so the NEXT tick reads a consistent prior (single-writer).

    RED today: ``MusicState`` has no ``prev_perceive`` field (AttributeError) and
    ``_tick_once`` writes no snapshot.
    """
    state = MusicState()
    _tick(state)
    snap = state.prev_perceive
    assert isinstance(snap, dict) and snap, "prev_perceive must be captured after a tick"
    # The captured prior reflects THIS tick's writes (so next tick diffs against it).
    assert "rms" in snap
    assert "bpm" in snap
    assert snap["rms"] == pytest.approx(state.rms)


# ---------- PERCEIVE-02 — trajectory compose, bounded ----------


def test_trajectory_composed_bounded():
    """On a state with non-empty phase_history / recent_moves / buildup_score,
    ``_tick_once`` composes ``state.trajectory_narrative`` as a non-empty BOUNDED
    string — recomputed each tick, never accumulating across repeated ticks.

    RED today: no ``trajectory_narrative`` field; ``_tick_once`` composes nothing.
    """
    state = MusicState(
        phase_history=[(990.0, "intro", "build"), (995.0, "build", "drop")],
        recent_moves=[(3.0, "bass-swap")],
        buildup_score=0.7,
    )
    _tick(state, now=1000.0)
    narrative = state.trajectory_narrative
    assert isinstance(narrative, str) and narrative != ""
    bound = len(narrative)
    # Repeated ticks must NOT grow the string (recomputed, not appended).
    _tick(state, now=1001.0)
    _tick(state, now=1002.0)
    assert len(state.trajectory_narrative) <= bound + 64, "trajectory must stay bounded"


# ---------- PERCEIVE-03 — genre fed via single writer ----------


def test_genre_fed_single_writer():
    """``state.detected_genre`` / ``genre_confidence`` are written ONLY by
    ``_tick_once`` reading an off-loop embedding-genre holder (the deck-holder
    copy-in idiom) — never by a second writer.

    Smoke pin: after a tick that supplies a holder whose result is a confident
    genre, the committed ``detected_genre`` reflects the holder (reconciled, then
    hysteresis-debounced). RED today: ``_tick_once`` has no ``genre_source``
    holder kwarg (TypeError), so the embedding genre cannot be fed yet.
    """
    state = MusicState()
    holder = MagicMock()
    holder.get_latest.return_value = ("hardtechno", 0.82)
    _tick_once(
        state,
        _audible_buf(),
        _ctrl_mock(),
        _track_mock(),
        now=1000.0,
        last_audible_high=1000.0,
        last_audible_low=0.0,
        bpm_cache=126.0,
        last_bpm_at=1000.0,
        genre_source=holder,
    )
    # One coherent label, sourced from the holder via the single writer.
    assert state.detected_genre == "hardtechno"
    assert state.genre_confidence >= 0.5


def test_genre_reconciliation():
    """Embedding-genre vs DSP-genre reconcile to ONE coherent ``detected_genre``
    per tick (the flagged-risk pin):

    - DISAGREE + confident embedding → embedding wins.
    - sub-floor embedding → DSP fallback (the existing score_genre path).

    RED today: no ``genre_source`` reconciliation in ``_tick_once``.
    """
    # Confident embedding genre → embedding wins over whatever DSP scored.
    state_win = MusicState()
    holder_conf = MagicMock()
    holder_conf.get_latest.return_value = ("trance", 0.90)
    _tick_once(
        state_win,
        _audible_buf(),
        _ctrl_mock(),
        _track_mock(),
        now=1000.0,
        last_audible_high=1000.0,
        last_audible_low=0.0,
        bpm_cache=126.0,
        last_bpm_at=1000.0,
        genre_source=holder_conf,
    )
    assert state_win.detected_genre == "trance"

    # Sub-floor embedding → DSP fallback (embedding does not override).
    state_fallback = MusicState()
    holder_weak = MagicMock()
    holder_weak.get_latest.return_value = ("trance", 0.10)
    _tick_once(
        state_fallback,
        _audible_buf(),
        _ctrl_mock(),
        _track_mock(),
        now=1000.0,
        last_audible_high=1000.0,
        last_audible_low=0.0,
        bpm_cache=126.0,
        last_bpm_at=1000.0,
        genre_source=holder_weak,
    )
    # The weak embedding label must NOT be the committed label (DSP path owns it).
    assert state_fallback.detected_genre != "trance"
