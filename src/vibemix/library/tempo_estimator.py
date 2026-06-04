# SPDX-License-Identifier: Apache-2.0
"""Offline BPM estimation for library ingest.

This is an ingest-time metadata helper for Viber / AutoCrate, not live deck
proof. It reuses the cue engine's kick-band autocorrelation so BPM only lands
when the same offline cue path sees a convincing beat.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from vibemix.library.cue_detect import ANALYSIS_SR, _estimate_bpm, decode_to_mono

logger = logging.getLogger(__name__)

DEFAULT_CONFIDENCE_FLOOR = 1.0


@dataclass(frozen=True, slots=True)
class BpmEstimate:
    bpm: float
    confidence: float
    source: str = "kick_ac"


def estimate_bpm(path: str | Path, *, confidence_floor: float = DEFAULT_CONFIDENCE_FLOOR) -> BpmEstimate | None:
    """Estimate track BPM from local audio, returning ``None`` on uncertainty."""
    try:
        samples = decode_to_mono(Path(path), sample_rate=ANALYSIS_SR)
    except Exception as exc:
        logger.warning("[bpm-estimate err] %s: %s", path, exc)
        return None
    return estimate_bpm_from_audio(samples, sr=ANALYSIS_SR, confidence_floor=confidence_floor)


def estimate_bpm_from_audio(
    samples: np.ndarray,
    *,
    sr: int = ANALYSIS_SR,
    confidence_floor: float = DEFAULT_CONFIDENCE_FLOOR,
) -> BpmEstimate | None:
    """Estimate BPM from mono samples, or honest-``None`` below the floor."""
    audio = np.asarray(samples, dtype=np.float32)
    if audio.ndim != 1:
        audio = np.mean(audio.reshape(audio.shape[0], -1), axis=1).astype(np.float32)
    if audio.size == 0:
        return None
    bpm, confidence = _estimate_bpm(audio, int(sr))
    if bpm <= 0.0 or confidence < confidence_floor:
        return None
    return BpmEstimate(bpm=round(float(bpm), 1), confidence=round(float(confidence), 4))
