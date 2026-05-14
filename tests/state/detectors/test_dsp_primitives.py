# SPDX-License-Identifier: Apache-2.0
"""Phase 17 SENSE-12 — shared kick-side DSP primitives.

Locks the contract that ``kick_band_centroid`` and ``sub_share`` are pure,
band-limited, anti-hallucination-safe (silent input → 0.0, never a fabricated
frequency or fraction). These primitives are the load-bearing math for the
KICK_SWAP / SUB_LAYER_ARRIVAL detectors — if they drift, detector behavior
silently breaks.
"""

from __future__ import annotations

import numpy as np

from tests.state.detectors.conftest import _audio_sine
from vibemix.state.detectors._dsp import kick_band_centroid, sub_share


# ---------- kick_band_centroid ----------


def test_kick_band_centroid_returns_hz_in_kick_band():
    """Synthetic 60Hz sine → centroid ≈ 60Hz; 100Hz sine → centroid ≈ 100Hz;
    equal-amplitude 60+100Hz mix → centroid ≈ 80Hz (magnitude-weighted mean)."""
    sr = 16000
    n = 4096

    sine_60 = _audio_sine(60.0, n, sr)
    centroid_60 = kick_band_centroid(sine_60, sr)
    assert abs(centroid_60 - 60.0) < 10.0, f"60Hz sine → {centroid_60}Hz (expected ~60)"

    sine_100 = _audio_sine(100.0, n, sr)
    centroid_100 = kick_band_centroid(sine_100, sr)
    assert abs(centroid_100 - 100.0) < 10.0, f"100Hz sine → {centroid_100}Hz (expected ~100)"

    mix = (_audio_sine(60.0, n, sr).astype(np.int32) + _audio_sine(100.0, n, sr).astype(np.int32))
    mix = np.clip(mix, -32768, 32767).astype(np.int16)
    centroid_mix = kick_band_centroid(mix, sr)
    assert abs(centroid_mix - 80.0) < 10.0, f"60+100Hz mix → {centroid_mix}Hz (expected ~80)"


def test_kick_band_centroid_silence_returns_zero():
    """All-zero buffer → 0.0 (anti-hallucination per 'trust the audio' rule)."""
    silent = np.zeros(4096, dtype=np.int16)
    assert kick_band_centroid(silent, 16000) == 0.0


def test_kick_band_centroid_band_limited_to_40_120hz():
    """1kHz sine (out-of-band) → centroid ≈ 0.0 (filtered out)."""
    sr = 16000
    sine_1k = _audio_sine(1000.0, 4096, sr)
    centroid = kick_band_centroid(sine_1k, sr)
    assert centroid == 0.0, f"1kHz sine should be filtered out, got {centroid}Hz"


# ---------- sub_share ----------


def test_sub_share_returns_normalized_fraction():
    """``sub_share(samples, sr)`` returns ``sub_band_energy / total_band_energy`` ∈ [0, 1].

    A pure 30Hz sine is 100% sub (well below 60Hz) → fraction near 1.0.
    A pure 1kHz sine has zero sub content → fraction near 0.0.
    Silence returns 0.0 (no fabricated fraction).
    """
    sr = 16000
    n = 16384  # match snapshot_features spec window so FFT bins align

    sub_only = _audio_sine(30.0, n, sr)
    share_sub = sub_share(sub_only, sr)
    assert 0.0 <= share_sub <= 1.0
    assert share_sub > 0.7, f"30Hz sine should be mostly sub, got {share_sub}"

    high_only = _audio_sine(1000.0, n, sr)
    share_high = sub_share(high_only, sr)
    assert 0.0 <= share_high <= 1.0
    assert share_high < 0.05, f"1kHz sine should have ~0 sub content, got {share_high}"

    silent = np.zeros(n, dtype=np.int16)
    assert sub_share(silent, sr) == 0.0


# ---------- Constants exposure (cooldown + threshold extension) ----------


def test_constants_module_exposes_three_phase_17_thresholds():
    from vibemix.audio.constants import (
        KICK_DENSITY_SHIFT_DELTA,
        KICK_SWAP_CENTROID_DELTA_HZ,
        SUB_JUMP_THRESHOLD,
    )

    assert KICK_SWAP_CENTROID_DELTA_HZ == 12.0
    assert SUB_JUMP_THRESHOLD == 0.10
    assert KICK_DENSITY_SHIFT_DELTA == 1.5


def test_min_event_gap_per_type_extended_with_three_kick_side_entries():
    from vibemix.audio.constants import MIN_EVENT_GAP_PER_TYPE

    assert MIN_EVENT_GAP_PER_TYPE["KICK_SWAP"] == 14.0
    assert MIN_EVENT_GAP_PER_TYPE["SUB_LAYER_ARRIVAL"] == 16.0
    assert MIN_EVENT_GAP_PER_TYPE["KICK_DENSITY_SHIFT"] == 18.0
    # Don't break v4 entries
    assert MIN_EVENT_GAP_PER_TYPE["TRACK_CHANGE"] == 6.0
    assert MIN_EVENT_GAP_PER_TYPE["LAYER_ARRIVAL"] == 16.0
