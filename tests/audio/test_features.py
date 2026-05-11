# SPDX-License-Identifier: Apache-2.0
"""Tests for vibemix.audio.features — DSP free functions.

Verbatim math port of cohost_v4.py:304-436; tests pin the dict shape (Phase 3
EventDetector consumer contract), peak-normalize correctness (RESEARCH.md
Pitfall 4), BPM autocorr aliveness, and energy curve lengths.
"""

from __future__ import annotations

import numpy as np

from vibemix.audio import (
    AudioBuffer,
    energy_curve,
    estimate_bpm,
    long_arc_curve,
    snapshot_features,
    snapshot_wav,
)

# ===== FEAT-01: silent early-out =====


def test_snapshot_features_empty_buffer_silent_early_out() -> None:
    """Fewer than sr/4 samples → early-out shape `{silent: True, rms: 0.0}`. v4:335-336."""
    buf = AudioBuffer(seconds=10.0, sr=16000)
    buf.push(np.zeros(100, dtype=np.int16))  # 100 < 16000/4 = 4000
    f = snapshot_features(buf, seconds=5.0)
    assert f == {"silent": True, "rms": 0.0}


# ===== FEAT-02: full dict shape =====


def test_snapshot_features_full_dict_shape() -> None:
    """≥ sr/4 samples → 7-key dict shape per v4:373-381. Phase 3 consumer contract."""
    buf = AudioBuffer(seconds=10.0, sr=16000)
    rng = np.random.default_rng(42)
    buf.push((rng.standard_normal(80000) * 8000).astype(np.int16))
    f = snapshot_features(buf, seconds=5.0)
    assert set(f.keys()) == {
        "silent",
        "rms",
        "onsets_per_sec",
        "sub_share",
        "low_share",
        "mid_share",
        "high_share",
    }
    # share fields are normalized to total — should sum to ~1.0
    share_sum = f["sub_share"] + f["low_share"] + f["mid_share"] + f["high_share"]
    assert 0.95 < share_sum < 1.05


# ===== FEAT-03: silent flag respects SILENT_RMS =====


def test_snapshot_features_silent_flag_matches_silent_rms_constant() -> None:
    """Low-amplitude noise yields `silent=True` when RMS < SILENT_RMS=0.012."""
    buf = AudioBuffer(seconds=10.0, sr=16000)
    rng = np.random.default_rng(0)
    # amplitude 100/32768 ≈ 0.003 < SILENT_RMS
    buf.push((rng.standard_normal(80000) * 100).astype(np.int16))
    f = snapshot_features(buf, seconds=5.0)
    assert f["silent"] is True


# ===== FEAT-04: snapshot_wav RIFF header =====


def test_snapshot_wav_riff_header_valid() -> None:
    """RIFF + WAVE chunk IDs at offsets 0 + 8 (standard 44-byte WAV header)."""
    buf = AudioBuffer(seconds=2.0, sr=16000)
    buf.push(np.full(16000, 12345, dtype=np.int16))
    wav = snapshot_wav(buf, seconds=1.0)
    assert wav[0:4] == b"RIFF"
    assert wav[8:12] == b"WAVE"


# ===== FEAT-05: peak-normalize int16 no overflow =====


def test_snapshot_wav_peak_normalize_no_int16_overflow() -> None:
    """Full-scale input + peak-normalize must clip BEFORE int16 cast. RESEARCH.md Pitfall 4.

    If the order is inverted, the resulting int16 has -32768 values (silent
    integer overflow). The test asserts min > -32768 — anything == -32768
    means the clip-before-cast invariant regressed.
    """
    buf = AudioBuffer(seconds=1.0, sr=16000)
    buf.push(np.full(16000, 32767, dtype=np.int16))
    wav = snapshot_wav(buf, seconds=1.0, normalize_peak_dbfs=-3.0)
    pcm = np.frombuffer(wav[44:], dtype=np.int16)
    assert pcm.min() > -32768


# ===== FEAT-06: peak-normalize disabled =====


def test_snapshot_wav_normalize_disabled() -> None:
    """`normalize_peak_dbfs=None` → no scaling; output PCM equals input bytes."""
    buf = AudioBuffer(seconds=1.0, sr=16000)
    samples = np.arange(16000, dtype=np.int16)  # mixed signs after wrap
    buf.push(samples)
    wav = snapshot_wav(buf, seconds=1.0, normalize_peak_dbfs=None)
    pcm = np.frombuffer(wav[44:], dtype=np.int16)
    np.testing.assert_array_equal(pcm, samples)


# ===== FEAT-07: estimate_bpm aliveness =====


def test_estimate_bpm_returns_float_in_range() -> None:
    """Synthetic pulse train yields a float in [0, 200]. Loose aliveness check —
    autocorr is not high-precision. v4:412-438."""
    sr = 16000
    buf = AudioBuffer(seconds=10.0, sr=sr)
    # Build a pulse train: short bursts every ~480ms (~125 BPM)
    t = np.arange(sr * 8, dtype=np.float32) / sr
    pulse_freq = 125.0 / 60.0  # Hz
    env = (np.sin(2 * np.pi * pulse_freq * t) > 0.9).astype(np.float32)
    audio = (env * np.sin(2 * np.pi * 80.0 * t)).astype(np.float32)
    buf.push((audio * 16000).astype(np.int16))
    bpm = estimate_bpm(buf, seconds=6.0)
    assert isinstance(bpm, float)
    assert 0.0 <= bpm <= 200.0


# ===== FEAT-08: estimate_bpm short buffer returns 0.0 =====


def test_estimate_bpm_short_buffer_returns_zero() -> None:
    """< 2 seconds of audio → 0.0 (v4:415-417)."""
    buf = AudioBuffer(seconds=10.0, sr=16000)
    buf.push(np.zeros(1000, dtype=np.int16))  # < 2*16000
    assert estimate_bpm(buf, seconds=6.0) == 0.0


# ===== FEAT-09: energy_curve length =====


def test_energy_curve_length_matches_seconds_over_hop() -> None:
    """12s of data + hop=1.0 → 12 values (each is one 1s window's RMS)."""
    buf = AudioBuffer(seconds=20.0, sr=16000)
    buf.push((np.arange(16000 * 12) % 32767).astype(np.int16))
    ec = energy_curve(buf, seconds=12.0, hop=1.0)
    assert len(ec) == 12
    assert all(isinstance(x, float) for x in ec)


# ===== FEAT-10: long_arc_curve length =====


def test_long_arc_curve_length_matches_120s_over_10s_hop() -> None:
    """120s of data + hop=10.0 → 12 values."""
    buf = AudioBuffer(seconds=150.0, sr=16000)
    buf.push((np.arange(16000 * 120) % 32767).astype(np.int16))
    arc = long_arc_curve(buf, seconds=120.0, hop=10.0)
    assert len(arc) == 12


def test_long_arc_curve_too_short_returns_empty() -> None:
    """< 5s of audio → empty list (v4:403-404)."""
    buf = AudioBuffer(seconds=10.0, sr=16000)
    buf.push(np.zeros(16000 * 2, dtype=np.int16))  # 2s
    assert long_arc_curve(buf, seconds=120.0) == []


def test_energy_curve_too_short_returns_empty() -> None:
    """< 0.5s of audio → empty list (v4:387-388)."""
    buf = AudioBuffer(seconds=10.0, sr=16000)
    buf.push(np.zeros(1000, dtype=np.int16))  # < 8000
    assert energy_curve(buf) == []
