# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import numpy as np

from vibemix.library.cue_detect import ANALYSIS_SR
from vibemix.library.tempo_estimator import DEFAULT_CONFIDENCE_FLOOR, estimate_bpm_from_audio


def _kick_track(bpm: float = 128.0, seconds: float = 90.0, sr: int = ANALYSIS_SR) -> np.ndarray:
    n = int(seconds * sr)
    out = np.zeros(n, dtype=np.float32)
    t = np.arange(n, dtype=np.float64) / sr
    out += (0.02 * np.sin(2.0 * np.pi * 220.0 * t)).astype(np.float32)
    kick_len = int(0.055 * sr)
    for beat_s in np.arange(0.0, seconds, 60.0 / bpm):
        start = int(beat_s * sr)
        end = min(n, start + kick_len)
        if end <= start:
            continue
        kt = np.arange(end - start, dtype=np.float64) / sr
        env = np.exp(-45.0 * kt)
        out[start:end] += (0.9 * env * np.sin(2.0 * np.pi * 60.0 * kt)).astype(np.float32)
    return out


def test_estimates_four_on_floor_bpm() -> None:
    estimate = estimate_bpm_from_audio(_kick_track(138.0), sr=ANALYSIS_SR)

    assert estimate is not None
    assert estimate.bpm == 138.0
    assert estimate.confidence >= DEFAULT_CONFIDENCE_FLOOR
    assert estimate.source == "kick_ac"


def test_beatless_audio_abstains() -> None:
    n = int(90.0 * ANALYSIS_SR)
    t = np.arange(n, dtype=np.float64) / ANALYSIS_SR
    drone = (0.3 * np.sin(2.0 * np.pi * 500.0 * t)).astype(np.float32)

    assert estimate_bpm_from_audio(drone, sr=ANALYSIS_SR) is None
