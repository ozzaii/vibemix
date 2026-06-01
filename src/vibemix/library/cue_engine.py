# SPDX-License-Identifier: Apache-2.0
"""vibemix.library.cue_engine — assemble the auto-cue pipeline into CueAnchors.

The auto-cue engine, end to end:

    audio ──▶ cue_detr.detect_cue_positions   (CUE-DETR ONNX, local, no torch)
          ──▶ cue_refine.refine_cue_positions  (downbeat-snap + dedup per phrase)
          ──▶ build_cue_anchors                (label + mixable window → CueAnchor)

``detect_cues_auto`` is the single entry point: it runs the ONNX producer when available
and falls back to the dep-free ``cue_detect.detect_cues`` heuristic when it is not (no
onnxruntime / model / preprocessing dep). The ``CueAnchor`` seam (cross-session contract)
is unchanged — both paths return the same shape.

Labelling note: positions + mixable windows are the solid, validated product. Labels here
are a COARSE energy read (intro/outro by position; drop/breakdown/build by normalized
energy + slope) — a documented interim until the Zehren-style downbeat-quantized classifier
lands. The confidence reflects the downbeat-lock quality, NOT label certainty.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from vibemix.library.cue_detect import (
    _DEDUP_S,
    _MAX_WINDOW_S,
    _WINDOW_BARS,
    ANALYSIS_SR,
    FRAME_HOP_S,
    MIN_TRACK_S,
    _estimate_bpm,
    _rms_curve,
    _sub_energy_curve,
    audible_bounds_s,
    decode_to_mono,
    detect_cues,
)
from vibemix.library.cue_detr import (
    DEFAULT_RADIUS,
    DEFAULT_SENSITIVITY,
    CueProducerUnavailable,
    detect_cue_positions,
)
from vibemix.library.cue_refine import refine_cue_positions
from vibemix.library.cue_types import CueAnchor

# Positional bands for intro/outro labelling (fraction of track duration).
_INTRO_FRAC = 0.10
_OUTRO_FRAC = 0.88
# Normalized-energy thresholds for the coarse middle label.
_DROP_E = 0.66
_BREAKDOWN_E = 0.40
_BUILD_SLOPE = 0.20

__all__ = ["build_cue_anchors", "detect_cues_auto"]


def _coarse_label(frac: float, e: float, slope: float) -> str:
    """Interim energy/position label (Zehren classifier replaces this)."""
    if frac < _INTRO_FRAC:
        return "intro"
    if frac > _OUTRO_FRAC:
        return "outro"
    if e >= _DROP_E:
        return "drop"
    if e <= _BREAKDOWN_E and slope <= 0.05:
        return "breakdown"
    if slope >= _BUILD_SLOPE:
        return "build"
    return "drop" if e >= 0.5 else "breakdown"


def build_cue_anchors(
    audio_path: Path | str,
    positions: object,
    *,
    max_cues: int = 12,
) -> list[CueAnchor]:
    """Refine raw producer positions and assemble ``source="auto"`` CueAnchors.

    Refines (downbeat-snap + dedup per phrase) then labels each cue + sizes a phrase-aligned
    mixable window (≤80s). Returns ascending-by-``start_s`` anchors; ``[]`` when the track is
    too short or there are no usable positions.
    """
    samples = decode_to_mono(audio_path)
    duration_s = samples.size / float(ANALYSIS_SR) if samples.size else 0.0
    if duration_s < MIN_TRACK_S:
        return []
    audible_bounds = audible_bounds_s(samples, ANALYSIS_SR)
    if audible_bounds is None:
        return []
    first_sound_s, last_sound_s = audible_bounds

    refined = refine_cue_positions(audio_path, positions)
    if not refined:
        return []

    bpm, _ratio = _estimate_bpm(samples, ANALYSIS_SR)
    bar_s = (4.0 * 60.0 / bpm) if bpm > 0.0 else 0.0
    phrase_bars = 16
    if bpm > 0.0:
        from vibemix.state.detectors._phrase_dsp import estimate_phrase_length_bars

        sub_curve = _sub_energy_curve(samples, ANALYSIS_SR)
        phrase_bars = estimate_phrase_length_bars(
            sub_curve.tolist(), bpm, hop_seconds=FRAME_HOP_S
        )

    rms = _rms_curve(samples, ANALYSIS_SR, _sub_energy_curve(samples, ANALYSIS_SR).size)
    n = rms.size
    p30, p95 = np.percentile(rms, 30), np.percentile(rms, 95)
    band = max(1e-9, float(p95 - p30))

    anchors: list[CueAnchor] = []
    for cue in refined:
        raw_start_s = cue.position_s
        if raw_start_s > last_sound_s:
            continue
        start_s = max(first_sound_s, raw_start_s)
        if start_s >= duration_s:
            continue
        i = min(int(start_s / FRAME_HOP_S), n - 1)
        j = min(i + 12, n - 1)
        e = float((rms[i] - p30) / band)
        slope = float((rms[j] - rms[i]) / band)
        label = _coarse_label(start_s / duration_s, e, slope)

        target_bars = _WINDOW_BARS.get(label, 16)
        if bar_s > 0.0 and phrase_bars > 0:
            max_phrases = math.floor(_MAX_WINDOW_S / bar_s / phrase_bars)
            bars = min(target_bars, max(phrase_bars, max_phrases * phrase_bars))
            window_s = bars * bar_s
        else:
            window_s = _MAX_WINDOW_S
        end_s = min(start_s + window_s, last_sound_s, duration_s, start_s + _MAX_WINDOW_S)
        if end_s <= start_s:
            continue

        # Confidence = downbeat-lock quality (position trust). Label is coarse → not folded in.
        conf = min(1.0, 0.5 + 0.4 * cue.snap_confidence) if cue.snapped else 0.45
        anchors.append(
            CueAnchor(
                label=label,  # type: ignore[arg-type]
                start_s=round(float(start_s), 3),
                end_s=round(float(end_s), 3),
                confidence=round(float(conf), 4),
                source="auto",
            )
        )

    anchors.sort(key=lambda a: a.start_s)
    deduped: list[CueAnchor] = []
    for anc in anchors:
        if deduped and abs(anc.start_s - deduped[-1].start_s) < _DEDUP_S:
            continue
        deduped.append(anc)
    return deduped[:max_cues]


def detect_cues_auto(
    audio_path: Path | str,
    *,
    max_cues: int = 12,
    sensitivity: float = DEFAULT_SENSITIVITY,
    radius: int = DEFAULT_RADIUS,
) -> list[CueAnchor]:
    """Auto-cue with the ONNX producer, falling back to the dep-free heuristic.

    Tries CUE-DETR ONNX → refine → CueAnchor. On ``CueProducerUnavailable`` (no
    onnxruntime / model / preprocessing dep) OR when the producer yields nothing usable,
    falls back to ``cue_detect.detect_cues``. The ``CueAnchor`` seam is identical both ways.
    """
    try:
        positions = detect_cue_positions(
            audio_path, sensitivity=sensitivity, radius=radius
        )
        anchors = build_cue_anchors(audio_path, positions, max_cues=max_cues)
        if anchors:
            return anchors
    except CueProducerUnavailable:
        pass
    return detect_cues(audio_path, max_cues=max_cues)
