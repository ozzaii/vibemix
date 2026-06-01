# SPDX-License-Identifier: Apache-2.0
"""Beatmatch Judge — grade a beatmatch attempt against owned-deck ground truth.

This is the moat. Because the learning module OWNS both decks (it loaded the
tracks and drives the playhead), it knows each deck's exact beat phase at every
sample — so it can grade tempo-match and phase-alignment exactly, where a
live-co-host observer could only infer.

The math is ported verbatim from Mixxx sync (scar dossier 07), facts re-derived
clean-room (C1 numpy-only, no GPL):
  * modular-1.0 beat-phase error  ``(target-cur+0.5) % 1 - 0.5``  (bpmcontrol.cpp:479, B1)
  * √2 octave-fold tempo multiplier ``2 / 0.5 / 1``               (synccontrol.cpp:290, A1)
  * phase dead-band 0.01 beat / trainwreck 0.2 beat               (bpmcontrol.cpp:608, B2)
  * 1/8-beat past-beat forgiveness (match the prev beat behind)   (bpmcontrol.cpp:41, E)
"""

from __future__ import annotations

from dataclasses import dataclass

from vibemix.audio.grid import BeatGrid
from vibemix.audio.miniplayer import DeckState

# --- scar constants (dossier 07) -------------------------------------------------
_FOLD_DOUBLE = 2.0  # kBpmDouble (synccontrol.cpp:17, A1)
_FOLD_HALVE = 0.5  # kBpmHalve  (synccontrol.cpp:18, A1)
_PHASE_LOCK_TOL = 0.01  # kErrorThreshold — within this, in sync (bpmcontrol.cpp:608, B2)
_PHASE_TRAINWRECK_TOL = 0.2  # kTrainWreckThreshold — beyond, ahead/behind ambiguous (B2)
_PAST_BEAT_FORGIVE = 1.0 / 8.0  # kPastBeatMatchThreshold — match prev beat if just behind (E)

# vibemix grading choices (not Mixxx scars — tunable rubric):
_TEMPO_MATCH_TOL = 0.01  # effective BPMs within 1% after the octave fold == "matched"
_TEMPO_ZERO_SCORE = 0.06  # tempo error that drives the tempo score component to 0
_MIN_PLAY_RATE = 0.01  # below this a deck is stopped -> nothing to grade, abstain


def _phase_error(cur_distance: float, target_distance: float) -> float:
    """Signed shortest beat-phase error in ``[-0.5, 0.5]`` (Mixxx ``shortestPercentageChange``).

    Beat distance is modular in ``[0, 1)``, so the error must take the shorter of
    the forward vs wrapped path — a 0.99→0.01 pair is 0.02 apart, not a near-full
    beat. THE primitive for comparing two beat phases (scar 07 B1).
    """
    return (target_distance - cur_distance + 0.5) % 1.0 - 0.5


def _octave_fold_multiplier(ratio: float) -> float:
    """√2 octave fold (scar 07 A1): ``2.0`` if ``r²>2``, ``0.5`` if ``r²<0.5``, else ``1.0``.

    The decision is on the SQUARE of the ratio vs 2.0 / 0.5 — so the real
    crossover is √2 ≈ 1.414, the unbiased split where a 70-vs-140 pair folds
    symmetrically. Unity is inclusive at the edge (exactly √2 stays 1.0). This is
    the "should I beatmatch 128↔64 as the same tempo?" test.
    """
    square = ratio * ratio
    if square > _FOLD_DOUBLE:
        return _FOLD_DOUBLE
    if square < _FOLD_HALVE:
        return _FOLD_HALVE
    return 1.0


@dataclass(frozen=True)
class BeatmatchGrade:
    """The graded verdict of a beatmatch attempt (deck B matched against deck A).

    ``abstain`` is the calibrated "don't grade" escape (C3): when a deck is
    stopped there is no attempt to judge, so the Judge stays silent rather than
    emit a bogus score. All other fields are meaningful only when not abstaining
    (they are ``nan`` while abstaining).
    """

    abstain: bool
    tempo_error: float  # |folded_ratio - 1.0|, 0 == octave-matched tempo
    phase_error_beats: float  # signed [-0.5, 0.5]; >0 = B behind A, <0 = B ahead
    tempo_matched: bool
    phase_locked: bool
    recoverable_late: bool  # B behind by <= 1/8 beat -> catch the previous beat
    verdict: str  # abstain | tempo_off | locked | drifting | trainwreck
    score: float  # 0..1


def grade_beatmatch(grid_a: BeatGrid, grid_b: BeatGrid, state: DeckState) -> BeatmatchGrade:
    """Grade deck B's beatmatch against the reference deck A, from exact deck state.

    Owns-the-deck grading: ``state`` carries each deck's exact frame cursor and
    rate, and the grids give exact beat phase — so tempo-match and phase-alignment
    are measured, not inferred. Tempo must match first (an octave fold away counts);
    phase is then graded against the 0.01-beat lock band and the 0.2-beat
    trainwreck band, with 1/8-beat forgiveness for being slightly behind.
    """
    nan = float("nan")
    if abs(state.rate_a) < _MIN_PLAY_RATE or abs(state.rate_b) < _MIN_PLAY_RATE:
        return BeatmatchGrade(
            abstain=True,
            tempo_error=nan,
            phase_error_beats=nan,
            tempo_matched=False,
            phase_locked=False,
            recoverable_late=False,
            verdict="abstain",
            score=0.0,
        )

    # --- tempo agreement, octave-folded (A1) ---
    eff_a = grid_a.bpm * abs(state.rate_a)
    eff_b = grid_b.bpm * abs(state.rate_b)
    ratio = eff_b / eff_a
    folded_ratio = ratio / _octave_fold_multiplier(ratio)
    tempo_error = abs(folded_ratio - 1.0)
    tempo_matched = tempo_error <= _TEMPO_MATCH_TOL

    # --- phase alignment, modular on the beat circle (B1) ---
    phase = _phase_error(grid_b.beat_distance(state.b_frame), grid_a.beat_distance(state.a_frame))
    phase_locked = abs(phase) <= _PHASE_LOCK_TOL
    recoverable_late = 0.0 < phase <= _PAST_BEAT_FORGIVE

    if not tempo_matched:
        verdict = "tempo_off"
    elif phase_locked:
        verdict = "locked"
    elif abs(phase) <= _PHASE_TRAINWRECK_TOL:
        verdict = "drifting"
    else:
        verdict = "trainwreck"

    # Score: tempo and phase each in [0,1]; a high grade needs BOTH (multiplicative
    # so a tempo miss can't be masked by good phase, and vice versa).
    tempo_score = max(0.0, 1.0 - tempo_error / _TEMPO_ZERO_SCORE)
    phase_score = max(0.0, 1.0 - abs(phase) / _PHASE_TRAINWRECK_TOL)
    score = round(tempo_score * phase_score, 4)

    return BeatmatchGrade(
        abstain=False,
        tempo_error=tempo_error,
        phase_error_beats=phase,
        tempo_matched=tempo_matched,
        phase_locked=phase_locked,
        recoverable_late=recoverable_late,
        verdict=verdict,
        score=score,
    )


def grade_to_event_extra(grade: BeatmatchGrade) -> dict[str, object]:
    """The canonical ``BEATMATCH_GRADED`` event ``extra`` payload for the recognizer.

    The owned-deck Judge is the tempo/phase signal the v11.0 skill recognizer was
    explicitly waiting for (``skill_recognizer._HONEST_UNCREDITABLE_V11`` —
    *"Stays uncreditable until the deferred beatmatch_phase Judge signal ships."*).
    A future owned-deck practice loop must fire a ``BEATMATCH_GRADED`` event
    carrying this payload AND register the matching
    ``("ev", "BEATMATCH_GRADED", t_session)`` citation; once that producer exists,
    ``skill_recognizer.recognize`` credits beatmatching ONLY on a cited,
    non-abstain, LOCKED grade (tempo matched AND phase locked) — a trainwreck /
    drift / abstain credits nothing (it proves the opposite, anti-slop).

    Only the load-bearing fields the recognizer reads ride the event; the full
    grade (errors, score) is for the coach narration, not the credit gate.
    """
    return {
        "abstain": grade.abstain,
        "tempo_matched": grade.tempo_matched,
        "phase_locked": grade.phase_locked,
        "verdict": grade.verdict,
        "score": grade.score,
    }
