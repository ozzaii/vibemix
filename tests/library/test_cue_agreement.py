# SPDX-License-Identifier: Apache-2.0
"""Tests for the cue-agreement INSTRUMENT (Phase-A flywheel).

`cue_agreement` is a PURE deterministic MEASUREMENT: given a DJ's own anchors
(hand-set / Rekordbox ANLZ, ``source`` dj/anlz) and the auto-cue engine's
anchors (``source="auto"``) for the SAME track, it reports how much the engine
agrees with the human. Disagreements are free weak labels for improving the
cue engine.

These tests use SYNTHETIC :class:`CueAnchor` lists only — no DB, no audio, no
ONNX. The instrument reads no DB; it takes two anchor lists as inputs.

Contract pins exercised here:
  * perfect agreement → score 1.0, no dj_only / auto_only
  * partial agreement → a matched pair + a miss (dj_only) + an extra (auto_only)
  * tolerance boundary → just-inside matches, just-outside does not
  * empty-input honest-null → no labels exist → score is None (NEVER 0.0/1.0)
  * label-mismatch-but-time-match → time proximity defines a match; a label
    difference is RECORDED, not disqualifying
"""

from __future__ import annotations

import pytest

from vibemix.library.cue_agreement import CueAgreement, cue_agreement, weak_labels
from vibemix.library.cue_types import CueAnchor


def _dj(label: str, start_s: float, *, conf: float = 0.9) -> CueAnchor:
    return CueAnchor(
        label=label,  # type: ignore[arg-type]
        start_s=start_s,
        end_s=start_s + 8.0,
        confidence=conf,
        source="dj",
    )


def _auto(label: str, start_s: float, *, conf: float = 0.65) -> CueAnchor:
    return CueAnchor(
        label=label,  # type: ignore[arg-type]
        start_s=start_s,
        end_s=start_s + 8.0,
        confidence=conf,
        source="auto",
    )


def test_perfect_agreement_scores_one_no_disagreements() -> None:
    """Every DJ anchor has an exact auto match → score 1.0, zero misses/extras."""
    dj = [_dj("intro", 5.0), _dj("drop", 64.0), _dj("outro", 200.0)]
    auto = [_auto("intro", 5.0), _auto("drop", 64.0), _auto("outro", 200.0)]

    result = cue_agreement(dj, auto)

    assert isinstance(result, CueAgreement)
    assert len(result.matched) == 3
    assert result.dj_only == []
    assert result.auto_only == []
    assert result.agreement_score == 1.0
    assert result.mean_abs_offset_s == 0.0


def test_partial_agreement_one_match_one_miss_one_extra() -> None:
    """A matched pair, a DJ anchor with no auto (engine MISS = dj_only), and an
    auto anchor with no DJ (engine EXTRA = auto_only)."""
    dj = [_dj("intro", 5.0), _dj("drop", 64.0)]  # 64.0 is the miss
    auto = [_auto("intro", 5.5), _auto("breakdown", 120.0)]  # 120.0 is the extra

    result = cue_agreement(dj, auto)

    # 5.0<->5.5 matched (|Δ|=0.5 <= 2.0); 64.0 unmatched; 120.0 unmatched.
    assert len(result.matched) == 1
    assert len(result.dj_only) == 1
    assert result.dj_only[0].start_s == 64.0
    assert len(result.auto_only) == 1
    assert result.auto_only[0].start_s == 120.0
    # score = matched / (matched + dj_only + auto_only) = 1 / 3.
    assert result.agreement_score == 1 / 3
    assert result.mean_abs_offset_s == 0.5


def test_tolerance_boundary_just_inside_matches_just_outside_does_not() -> None:
    """At tolerance_s=2.0 a 2.0s gap matches (<=), a 2.01s gap does not."""
    dj = [_dj("drop", 60.0), _dj("drop", 100.0)]
    # 62.0 is exactly on the boundary (matches 60.0); 102.01 is just outside.
    auto = [_auto("drop", 62.0), _auto("drop", 102.01)]

    result = cue_agreement(dj, auto, tolerance_s=2.0)

    assert len(result.matched) == 1  # only 60.0<->62.0
    # 100.0 is a miss, 102.01 is an extra.
    assert [a.start_s for a in result.dj_only] == [100.0]
    assert [a.start_s for a in result.auto_only] == [102.01]
    assert result.mean_abs_offset_s == 2.0


def test_greedy_match_prefers_closest_auto_anchor() -> None:
    """When two auto anchors are in range of one DJ anchor, the closest wins."""
    dj = [_dj("drop", 60.0)]
    auto = [_auto("drop", 61.5), _auto("drop", 60.4)]  # 60.4 is closer

    result = cue_agreement(dj, auto)

    assert len(result.matched) == 1
    assert result.mean_abs_offset_s == pytest.approx(0.4)  # matched against 60.4
    # the farther in-range auto (61.5) is left as an extra.
    assert [a.start_s for a in result.auto_only] == [61.5]


def test_empty_dj_input_is_honest_null_not_fabricated_score() -> None:
    """No DJ labels → there is nothing to agree with → score is None, never 1.0/0.0."""
    auto = [_auto("intro", 5.0), _auto("drop", 64.0)]

    result = cue_agreement([], auto)

    assert result.matched == []
    assert result.dj_only == []
    # every auto anchor is unmatched, but with no DJ reference there is no score.
    assert [a.start_s for a in result.auto_only] == [5.0, 64.0]
    assert result.agreement_score is None
    assert result.mean_abs_offset_s is None


def test_empty_auto_input_is_honest_null_not_fabricated_score() -> None:
    """No auto cues → the engine found no structure → score is None, never 0.0."""
    dj = [_dj("intro", 5.0), _dj("drop", 64.0)]

    result = cue_agreement(dj, [])

    assert result.matched == []
    assert [a.start_s for a in result.dj_only] == [5.0, 64.0]
    assert result.auto_only == []
    assert result.agreement_score is None
    assert result.mean_abs_offset_s is None


def test_both_empty_is_honest_null() -> None:
    """No anchors at all → no labels → score None."""
    result = cue_agreement([], [])
    assert result.matched == []
    assert result.dj_only == []
    assert result.auto_only == []
    assert result.agreement_score is None
    assert result.mean_abs_offset_s is None


def test_label_mismatch_but_time_match_still_counts_as_match() -> None:
    """Match is defined by TIME proximity. A label difference on a time-match is
    RECORDED in the pair, not disqualifying."""
    dj = [_dj("drop", 64.0)]
    auto = [_auto("breakdown", 64.3)]  # different label, same moment

    result = cue_agreement(dj, auto)

    assert len(result.matched) == 1
    assert result.dj_only == []
    assert result.auto_only == []
    assert result.agreement_score == 1.0
    # the pair carries both anchors so the label disagreement is observable.
    pair = result.matched[0]
    assert pair.dj.label == "drop"
    assert pair.auto.label == "breakdown"
    assert pair.label_match is False


def test_weak_labels_emit_missed_and_spurious_disagreements() -> None:
    """weak_labels turns dj_only into 'missed' and auto_only into 'spurious' —
    the items a future calibration loop learns from."""
    dj = [_dj("intro", 5.0), _dj("drop", 64.0)]  # 64.0 missed by the engine
    auto = [_auto("intro", 5.4), _auto("breakdown", 150.0)]  # 150.0 spurious

    result = cue_agreement(dj, auto)
    labels = weak_labels(result)

    kinds = sorted((label_item.kind, label_item.anchor.start_s) for label_item in labels)
    assert kinds == [("missed", 64.0), ("spurious", 150.0)]


def test_weak_labels_empty_when_perfect_agreement() -> None:
    """Perfect agreement leaves nothing to learn from."""
    dj = [_dj("intro", 5.0)]
    auto = [_auto("intro", 5.0)]
    result = cue_agreement(dj, auto)
    assert weak_labels(result) == []
