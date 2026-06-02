# SPDX-License-Identifier: Apache-2.0
"""BS.1770 short-term loudness receipt tests."""

from __future__ import annotations

import math

import numpy as np

from vibemix.audio.lufs import short_term_lufs


def _tone(sample_rate: int, *, hz: float = 997.0, amp: float = 1.0, seconds: float = 3.0):
    t = np.arange(int(sample_rate * seconds), dtype=np.float32) / float(sample_rate)
    return (amp * np.sin(2.0 * math.pi * hz * t)).astype(np.float32)


def test_full_scale_997hz_tone_matches_bs1770_reference_at_48k() -> None:
    assert short_term_lufs(_tone(48_000), 48_000) == -3.01


def test_full_scale_997hz_tone_matches_bs1770_reference_after_441_resample() -> None:
    assert short_term_lufs(_tone(44_100), 44_100) == -3.02


def test_amplitude_change_tracks_loudness_units() -> None:
    loud = short_term_lufs(_tone(48_000, amp=1.0), 48_000)
    quiet = short_term_lufs(_tone(48_000, amp=0.5), 48_000)

    assert loud is not None
    assert quiet is not None
    assert loud - quiet == 6.02


def test_silence_and_short_windows_abstain() -> None:
    assert short_term_lufs(np.zeros(48_000 * 3, dtype=np.float32), 48_000) is None
    assert short_term_lufs(_tone(48_000, seconds=1.0), 48_000) is None
