# SPDX-License-Identifier: Apache-2.0
"""vibemix.library.cue_refine — phrase-lock + dedup for externally-produced cue positions.

The auto-cue ENGINE is two stages:

  1. a POSITION producer — CUE-DETR (ETH-DISCO, ISMIR 2024, MIT; DETR object-detection
     on log-Mel spectrograms) emits raw candidate cue *timestamps* from audio. It is
     genre-general and the positions are good, but its peak-picker is crude: with no
     beat grid, a low confidence threshold floods the output with near-duplicate,
     off-grid candidates (empirically 32–55 per house track, with exact-duplicate
     timestamps). The production producer is the local ONNX export under
     ``cue_detr.py``; torch is only needed for the historical export/reference path.

  2. this REFINE stage (pure numpy, dep-free, client-side) — snaps each candidate
     to the track's downbeat/phrase grid and collapses near-coincident hits to one cue
     per phrase. It turns the producer's noisy positions into clean, mixable,
     beat-locked cue points.

Empirically (2026-05-26, real DJ library): CUE-DETR @ sensitivity 0.5 produced 32–55 raw
candidates per house track with exact-duplicate timestamps; this refine stage collapsed
them to 11–14 phrase-locked cues (~one per 8 bars), all on the downbeat. See the design
spec ``docs/superpowers/specs/2026-05-26-auto-cue-engine-design.md``.

This module reuses the dep-free autocorr BPM estimate + downbeat-phase lock already in
``cue_detect`` / ``_phrase_dsp`` (no torch, no madmom) so it ships in the light client;
madmom is the optional server-side grid-quality upgrade, not a requirement here.

The pipeline is ``producer positions → refine → CueAnchor``. Labelling each refined
position (intro / build / breakdown / drop / outro) is a SEPARATE stage (Zehren-style
multi-feature classifier), deliberately deferred — this stage emits positions only.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from vibemix.library.cue_detect import (
    _MIN_SECTION_S,
    _SNAP_CONF_MIN,
    ANALYSIS_SR,
    MIN_TRACK_S,
    _estimate_bpm,
    _snap_to_phrase_grid,
    decode_to_mono,
)

# One cue per this many bars when a downbeat grid is found. 8 bars is the
# tightest standard dance phrase — collapsing within it removes the producer's
# duplicate/near-coincident hits without merging genuinely separate sections.
DEFAULT_PHRASE_BARS: int = 8

# A near-coincident merge keeps cues this fraction of a phrase apart. Slightly
# under 1.0 so a cue landing one bar shy of the next phrase still merges rather
# than surviving as a near-duplicate.
_MERGE_FRACTION: float = 0.9

__all__ = ["DEFAULT_PHRASE_BARS", "RefinedCue", "refine_cue_positions"]


@dataclass(frozen=True, slots=True)
class RefinedCue:
    """A producer candidate after phrase-snapping + dedup.

    ``snapped`` is True only when the downbeat lock cleared ``_SNAP_CONF_MIN`` and
    actually moved the candidate onto the grid — when False the position is the raw
    candidate (no grid was found / lock too weak), and a consumer must NOT promise a
    beatmatched entry on it (the same honesty contract as ``cue_detect``'s internal
    ``snapped`` flag).
    """

    position_s: float
    snapped: bool
    snap_confidence: float


def _clean_candidates(candidates_s: object, duration_s: float) -> list[float]:
    """Finite, in-bounds, ascending candidate seconds (defensive on external input)."""
    out: list[float] = []
    for c in candidates_s or []:
        try:
            v = float(c)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(v) or v < 0.0 or v > duration_s:
            continue
        out.append(v)
    out.sort()
    return out


def refine_cue_positions(
    audio_path: Path | str,
    candidates_s: object,
    *,
    phrase_bars: int = DEFAULT_PHRASE_BARS,
) -> list[RefinedCue]:
    """Snap externally-produced cue candidates to the phrase grid + dedup per phrase.

    Args:
        audio_path: the track the candidates came from (decoded for the beat grid).
        candidates_s: raw candidate cue positions in seconds (e.g. CUE-DETR output).
            Defensive: non-finite / out-of-bounds / non-numeric entries are dropped.
        phrase_bars: cues closer than this many bars collapse to one (default 8).

    Returns:
        Ascending ``RefinedCue`` list. Empty when there are no usable candidates or
        the track is too short to cue. When no downbeat grid is found (``bpm <= 0``)
        the candidates are still de-duplicated by a time floor (``_MIN_SECTION_S``)
        but returned unsnapped (``snapped=False``) — never snapped onto a fabricated
        grid (anti-hallucination, mirrors ``cue_detect``).
    """
    if phrase_bars <= 0:
        raise ValueError(f"phrase_bars must be positive, got {phrase_bars}")

    samples = decode_to_mono(audio_path)
    duration_s = samples.size / float(ANALYSIS_SR) if samples.size else 0.0
    if duration_s < MIN_TRACK_S:
        return []

    cands = _clean_candidates(candidates_s, duration_s)
    if not cands:
        return []

    bpm, _ratio = _estimate_bpm(samples, ANALYSIS_SR)
    if bpm > 0.0:
        bar_s = 4.0 * 60.0 / bpm
        merge_gap = phrase_bars * bar_s * _MERGE_FRACTION
        snapped = [
            _snap_one(c, samples, bpm) for c in cands
        ]
    else:
        # No grid — dedup by a musical-section time floor, leave unsnapped.
        merge_gap = _MIN_SECTION_S
        snapped = [RefinedCue(c, False, 0.0) for c in cands]

    return _dedup_per_phrase(snapped, merge_gap)


def _snap_one(candidate_s: float, samples: np.ndarray, bpm: float) -> RefinedCue:
    pos, conf = _snap_to_phrase_grid(candidate_s, samples, ANALYSIS_SR, bpm)
    return RefinedCue(pos, conf >= _SNAP_CONF_MIN, conf)


def _dedup_per_phrase(cues: list[RefinedCue], merge_gap: float) -> list[RefinedCue]:
    """Greedy left-to-right merge; within ``merge_gap`` keep the higher-confidence cue."""
    kept: list[RefinedCue] = []
    for cue in sorted(cues, key=lambda c: c.position_s):
        if kept and (cue.position_s - kept[-1].position_s) < merge_gap:
            # Same phrase as the last kept cue — keep whichever locked better.
            if cue.snap_confidence > kept[-1].snap_confidence:
                kept[-1] = cue
            continue
        kept.append(cue)
    return kept
