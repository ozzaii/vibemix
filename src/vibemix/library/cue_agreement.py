# SPDX-License-Identifier: Apache-2.0
"""cue_agreement — a Phase-A flywheel INSTRUMENT, not a model.

This module measures how much the auto-cue engine (``source="auto"`` anchors
from :mod:`vibemix.library.cue_engine`) DISAGREES with a DJ's own cues
(hand-set / Rekordbox ANLZ, ``source`` dj/anlz) for the SAME track. The
disagreements are free *weak labels* a future calibration loop can learn from:

    * a DJ anchor with no auto match  → the engine MISSED a real cue (``dj_only``)
    * an auto anchor with no DJ match  → the engine placed a SPURIOUS cue
      (``auto_only``)

It is a PURE deterministic measurement: two :class:`CueAnchor` lists in, a
frozen :class:`CueAgreement` out. It reads no DB, decodes no audio, loads no
ONNX model. It is a PRODUCER ONLY — nothing here is wired into ``ingest.py``
(that live call-site is deliberately deferred).

Matching contract
-----------------
A DJ anchor matches an auto anchor when they are close in TIME:
``|dj.start_s - auto.start_s| <= tolerance_s``. Matching is greedy and
nearest-first — DJ anchors are considered in time order, and each takes the
closest still-unused auto anchor in range. Each auto anchor is consumed at most
once, so a match is a 1:1 pairing.

Match is defined by TIME proximity ALONE. A *label* difference on a time-match
(e.g. the DJ called it ``"drop"`` and the engine called it ``"breakdown"``) is
RECORDED on the pair (``label_match=False``), NOT treated as a disagreement —
the two engines clearly agree that *something structural happens here*, and the
position is the load-bearing signal; the label vocabulary is best-effort on both
sides (see ``excerpt._label_for_cue``). Recording it lets a later loop study
label confusion separately from position misses.

Honest-null contract (project Invariant #3 — "trust the audio", never invent)
----------------------------------------------------------------------------
If EITHER input list is empty there are NO labels to learn from, so
``agreement_score`` is ``None`` — never a fabricated ``0.0`` or ``1.0``. An
empty DJ list does not mean the engine is perfectly wrong (0.0); an empty auto
list does not mean it is perfectly right (1.0). With no DJ reference there is
simply no agreement to measure. ``mean_abs_offset_s`` is likewise ``None`` when
nothing matched.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from vibemix.library.cue_types import CueAnchor

__all__ = [
    "CueAgreement",
    "MatchedPair",
    "WeakLabel",
    "cue_agreement",
    "weak_labels",
]

# Default time window for calling a DJ cue and an auto cue "the same moment".
# Two seconds is a few beats at house/techno tempos — wide enough to forgive the
# engine landing on the bar edge a beat early/late, tight enough that a genuine
# extra/missed cue stays unmatched. Tunable per call via ``tolerance_s``.
_DEFAULT_TOLERANCE_S: float = 2.0


@dataclass(frozen=True, slots=True)
class MatchedPair:
    """A DJ anchor paired with the auto anchor that landed on the same moment.

    ``offset_s`` is the signed ``auto.start_s - dj.start_s`` (auto-late is
    positive). ``label_match`` records whether the two engines also agreed on
    the structural *label* — a time-match with a label difference is still a
    match (position is authoritative), but the disagreement is observable here.
    """

    dj: CueAnchor
    auto: CueAnchor
    offset_s: float
    label_match: bool


@dataclass(frozen=True, slots=True)
class WeakLabel:
    """One disagreement item a future cue-engine calibration loop learns from.

    ``kind="missed"`` → a DJ anchor the engine failed to place (a false
    negative). ``kind="spurious"`` → an auto anchor with no DJ counterpart (a
    likely false positive). ``anchor`` is the offending :class:`CueAnchor`.
    """

    kind: Literal["missed", "spurious"]
    anchor: CueAnchor


@dataclass(frozen=True, slots=True)
class CueAgreement:
    """The measured agreement between a DJ's cues and the auto-cue engine's.

    ``matched`` — the 1:1 time-matched pairs.
    ``dj_only`` — DJ anchors with no auto match (engine MISSES).
    ``auto_only`` — auto anchors with no DJ match (engine EXTRAS).
    ``agreement_score`` — ``matched / (matched + dj_only + auto_only)`` in
        ``[0, 1]``, or ``None`` when either input was empty (honest-null: no
        labels → no score, never a fabricated 0.0/1.0).
    ``mean_abs_offset_s`` — mean ``|Δstart_s|`` over matched pairs, or ``None``
        when nothing matched.
    """

    matched: list[MatchedPair]
    dj_only: list[CueAnchor]
    auto_only: list[CueAnchor]
    agreement_score: float | None
    mean_abs_offset_s: float | None


def cue_agreement(
    dj_anchors: list[CueAnchor],
    auto_anchors: list[CueAnchor],
    *,
    tolerance_s: float = _DEFAULT_TOLERANCE_S,
) -> CueAgreement:
    """Measure how much the auto-cue engine agrees with a DJ's own cues.

    Greedily nearest-matches each DJ anchor (in time order) to the closest
    still-unused auto anchor within ``tolerance_s``. Unmatched DJ anchors are
    engine misses; unmatched auto anchors are engine extras.

    Args:
        dj_anchors: the DJ's own anchors (``source`` dj/anlz). Order-independent
            (sorted internally).
        auto_anchors: the auto-cue engine's anchors (``source="auto"``).
        tolerance_s: the max ``|Δstart_s|`` (seconds) for a time-match.

    Returns:
        A :class:`CueAgreement`. ``agreement_score`` / ``mean_abs_offset_s`` are
        ``None`` under the honest-null contract (see module docstring).
    """
    tol = float(tolerance_s)

    # Honest-null: with no anchors on one side there is no agreement to measure.
    # Surface the non-empty side's anchors (all unmatched) but withhold a score.
    if not dj_anchors or not auto_anchors:
        return CueAgreement(
            matched=[],
            dj_only=list(dj_anchors),
            auto_only=list(auto_anchors),
            agreement_score=None,
            mean_abs_offset_s=None,
        )

    # Consider DJ anchors in time order; greedily take the closest in-range auto.
    dj_sorted = sorted(dj_anchors, key=lambda a: float(a.start_s))
    remaining = list(auto_anchors)
    used: set[int] = set()

    matched: list[MatchedPair] = []
    dj_only: list[CueAnchor] = []

    for dj in dj_sorted:
        best_idx: int | None = None
        best_delta: float | None = None
        for idx, auto in enumerate(remaining):
            if idx in used:
                continue
            delta = abs(float(auto.start_s) - float(dj.start_s))
            if delta > tol:
                continue
            if best_delta is None or delta < best_delta:
                best_delta = delta
                best_idx = idx
        if best_idx is None:
            dj_only.append(dj)
            continue
        used.add(best_idx)
        auto = remaining[best_idx]
        matched.append(
            MatchedPair(
                dj=dj,
                auto=auto,
                offset_s=float(auto.start_s) - float(dj.start_s),
                label_match=dj.label == auto.label,
            )
        )

    auto_only = [auto for idx, auto in enumerate(remaining) if idx not in used]

    total = len(matched) + len(dj_only) + len(auto_only)
    # ``total`` is >0 here: both inputs were non-empty, so each anchor lands in
    # exactly one of the three buckets.
    score = len(matched) / total

    mean_abs_offset = (
        sum(abs(p.offset_s) for p in matched) / len(matched) if matched else None
    )

    return CueAgreement(
        matched=matched,
        dj_only=dj_only,
        auto_only=auto_only,
        agreement_score=score,
        mean_abs_offset_s=mean_abs_offset,
    )


def weak_labels(result: CueAgreement) -> list[WeakLabel]:
    """Extract the disagreement items a calibration loop learns from.

    ``dj_only`` anchors become ``"missed"`` weak labels (the engine should have
    placed a cue here); ``auto_only`` anchors become ``"spurious"`` (the engine
    placed a cue a human did not). Matched pairs — even with a label
    disagreement — are NOT emitted: position-wise the engine was right.
    """
    labels: list[WeakLabel] = [
        WeakLabel(kind="missed", anchor=a) for a in result.dj_only
    ]
    labels.extend(WeakLabel(kind="spurious", anchor=a) for a in result.auto_only)
    return labels
