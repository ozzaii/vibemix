# SPDX-License-Identifier: Apache-2.0
"""Per-lane band-energy ratios — torch-free, honest-null on silence."""
from __future__ import annotations

import numpy as np

from vibemix.audio.band_features import band_energy_ratios

SR = 16000


def _tone(hz: float, n: int = 16384, amp: float = 0.5) -> np.ndarray:
    t = np.arange(n) / SR
    return (amp * np.sin(2 * np.pi * hz * t)).astype(np.float32)


def test_silence_returns_none_not_a_band():
    # Anti-hallucination: silence MUST abstain, never fake "energy in the sub".
    assert band_energy_ratios(np.zeros(16384, dtype=np.float32), SR) is None


def test_empty_returns_none():
    assert band_energy_ratios(np.zeros(0, dtype=np.float32), SR) is None


def test_sub_bass_tone_dominates_sub_band():
    bands = band_energy_ratios(_tone(60.0), SR)
    assert bands is not None
    assert set(bands.keys()) == {"sub", "low", "mid", "high"}
    assert bands["sub"] > bands["mid"]
    assert bands["sub"] > bands["high"]
    # ratios normalized to ~1.0
    assert abs(sum(bands.values()) - 1.0) < 1e-6


def test_high_tone_dominates_high_band():
    bands = band_energy_ratios(_tone(6000.0), SR)
    assert bands is not None
    assert bands["high"] > bands["sub"]


def test_accepts_int16_pcm():
    # AudioBuffer.snapshot() returns int16 — the producer must accept it.
    pcm = (_tone(60.0) * 32767.0).astype(np.int16)
    bands = band_energy_ratios(pcm, SR)
    assert bands is not None
    assert bands["sub"] > bands["mid"]
