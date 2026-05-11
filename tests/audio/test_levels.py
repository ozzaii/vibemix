# SPDX-License-Identifier: Apache-2.0
"""Tests for vibemix.audio.Levels — EMA-smoothed RMS for music / voice / mic.

Verbatim port from cohost_v4.py:255-286. Coefficients are LOAD-BEARING per
02-PATTERNS.md — these tests pin them.
"""

from __future__ import annotations

import numpy as np

from tests.audio.conftest import int16_sine
from vibemix.audio import Levels


def test_initial_state_zero() -> None:
    """Fresh Levels has all three fields at 0.0."""
    lv = Levels()
    assert lv.music == 0.0
    assert lv.voice == 0.0
    assert lv.mic == 0.0


def test_update_music_int16_full_scale_yields_nonzero() -> None:
    """Music EMA after one full-scale push (RMS≈1.0 normalized) gives 0.4 (the EMA coefficient).

    v4:267: `self.music = self.music * 0.6 + rms * 0.4`. With rms≈1.0 (full-scale int16
    of 32767 normalized by /32768), one update yields ~0.4.
    """
    lv = Levels()
    lv.update_music(np.full(1024, 32767, dtype=np.int16))
    assert lv.music > 0.3, f"expected EMA > 0.3, got {lv.music}"
    assert lv.music < 0.5


def test_update_voice_bytes_path() -> None:
    """update_voice consumes bytes (int16 LE) and normalizes by /32768. v4:269-275."""
    lv = Levels()
    pcm = np.full(2048, 16384, dtype=np.int16).tobytes()
    lv.update_voice(pcm)
    # rms_normalized = 16384/32768 = 0.5 → EMA: 0.5 * 0.5 = 0.25
    assert 0.2 < lv.voice < 0.3, f"expected 0.2-0.3, got {lv.voice}"


def test_update_voice_empty_bytes_no_op() -> None:
    """update_voice with empty bytes early-returns without touching state. v4:270-271."""
    lv = Levels()
    lv.voice = 0.123
    lv.update_voice(b"")
    assert lv.voice == 0.123


def test_update_mic_float32_no_32768_divide() -> None:
    """Mic samples come from sounddevice float32 stream (already in -1..1) — RMS
    is NOT divided by 32768 (unlike update_music's int16 path). v4:277-280.

    A float32 array of constant 0.5 has RMS = 0.5. EMA after one push: 0.5 * 0.5 = 0.25.
    """
    lv = Levels()
    lv.update_mic(np.full(480, 0.5, dtype=np.float32))
    assert 0.2 < lv.mic < 0.3, f"expected 0.2-0.3 (NOT ~7.6e-6), got {lv.mic}"


def test_decay_voice_multiplies_by_0_7() -> None:
    """decay_voice multiplies by 0.7. Called from PlaybackQueue.pull on empty buffer. v4:282-284."""
    lv = Levels()
    pcm = np.full(2048, 32767, dtype=np.int16).tobytes()
    lv.update_voice(pcm)  # set voice to a known nonzero value
    v0 = lv.voice
    for _ in range(5):
        lv.decay_voice()
    expected = v0 * (0.7**5)
    assert abs(lv.voice - expected) < 0.01, f"expected ~{expected}, got {lv.voice}"


def test_snapshot_returns_fresh_dict_not_view() -> None:
    """snapshot() returns a fresh dict — mutating it doesn't affect Levels state. v4:286-288."""
    lv = Levels()
    lv.update_music(np.full(1024, 32767, dtype=np.int16))
    snap = lv.snapshot()
    music_before = lv.music
    snap["music"] = -999.0
    assert lv.music == music_before


def test_update_music_int16_sine_known_rms() -> None:
    """Sanity check the sine helper produces a buffer with the expected RMS shape."""
    lv = Levels()
    sine = int16_sine(freq_hz=440.0, duration_sec=0.1, sample_rate=16000, amplitude=0.5)
    lv.update_music(sine)
    # amp=0.5 sine has RMS = 0.5/sqrt(2) ≈ 0.354 → EMA: 0.354 * 0.4 ≈ 0.141
    assert 0.1 < lv.music < 0.2, f"expected ~0.14, got {lv.music}"
