# SPDX-License-Identifier: Apache-2.0
"""KickSwapDetector — fires when 40-120Hz spectral centroid shifts >= 12Hz
across two consecutive 4s windows (within-track kick character change).

Anti-double-fire contract with TRACK_CHANGE: KICK_SWAP only catches WITHIN-track
character changes; cross-track centroid jumps are claimed by TRACK_CHANGE first
(per the existing v4 detect ordering — TRACK_CHANGE has its own 6s cooldown +
fires before KICK_SWAP in the GenreRouter chain Plan 05 wires up).
"""

from __future__ import annotations

import numpy as np

from tests.state.detectors.conftest import _audio_sine, _state
from vibemix.audio.constants import LOW_RMS
from vibemix.state.detectors.kick_swap import KickSwapDetector


class _FakeAudioBuf:
    """Tiny AudioBuffer surrogate — only ``.snapshot(n)`` and ``._sr`` are
    consumed by KickSwapDetector. We hand back a pre-built sine PCM array
    truncated to the requested length so tests can drive the detector
    deterministically without standing up the ring-buffer machinery."""

    def __init__(self, samples: np.ndarray, sr: int = 16000) -> None:
        self._samples = samples
        self._sr = sr

    def snapshot(self, n: int) -> np.ndarray:
        # Mirror AudioBuffer: return at most n samples; cold-start callers can
        # ask for more than we have.
        if self._samples.size <= n:
            return self._samples
        return self._samples[-n:]


# 4 seconds of audio at 16kHz = 64000 samples — matches the detector's
# `audio_buf.snapshot(int(sr * 4.0))` window.
_4S_SAMPLES = 16000 * 4


def _buf_sine(freq_hz: float) -> _FakeAudioBuf:
    return _FakeAudioBuf(_audio_sine(freq_hz, _4S_SAMPLES, 16000))


# ---------- Test 1: fires on centroid shift >= 12Hz ----------


def test_kick_swap_fires_on_centroid_shift():
    d = KickSwapDetector()
    ms = _state(rms=0.06)

    # Seed baseline at t=1000.0 with a 60Hz kick character.
    ev = d.detect(ms, _buf_sine(60.0), now=1000.0)
    assert ev is None, "first call seeds baseline, must not fire"

    # 4.5s later, kick character shifts to 100Hz (Δ ≈ 40Hz, well above 12Hz).
    ev = d.detect(ms, _buf_sine(100.0), now=1004.5)
    assert ev is not None
    assert ev.type == "KICK_SWAP"
    assert "prev_centroid_hz" in ev.extra
    assert "new_centroid_hz" in ev.extra
    assert "delta_hz" in ev.extra
    assert ev.extra["delta_hz"] >= 12.0


# ---------- Test 2: no fire on small shift ----------


def test_kick_swap_no_fire_on_small_shift():
    d = KickSwapDetector()
    ms = _state(rms=0.06)
    # Seed at 60Hz
    d.detect(ms, _buf_sine(60.0), now=1000.0)
    # 4.5s later: centroid drifts to 65Hz (Δ ≈ 5Hz, below 12Hz threshold).
    ev = d.detect(ms, _buf_sine(65.0), now=1004.5)
    assert ev is None


# ---------- Test 3: silence gate ----------


def test_kick_swap_no_fire_on_silent_audio():
    d = KickSwapDetector()
    # rms below LOW_RMS (0.040) — silence gate must reject before computing centroid.
    ms = _state(rms=LOW_RMS - 0.005)
    ev = d.detect(ms, _buf_sine(60.0), now=1000.0)
    assert ev is None
    # State unchanged: detector did not seed baseline either.
    assert d.last_centroid_hz is None


# ---------- Test 4: cooldown blocks repeat fire ----------


def test_kick_swap_cooldown_blocks_repeat_fire():
    d = KickSwapDetector()
    ms = _state(rms=0.06)

    # Seed
    d.detect(ms, _buf_sine(60.0), now=1000.0)
    # Fire
    ev1 = d.detect(ms, _buf_sine(100.0), now=1004.5)
    assert ev1 is not None and ev1.type == "KICK_SWAP"

    # Within 14s of fire (KICK_SWAP cooldown) — second shift must be blocked.
    ev2 = d.detect(ms, _buf_sine(60.0), now=1010.0)  # 5.5s after fire, still < 14s
    assert ev2 is None

    # After cooldown clears (>14s), a new shift can fire.
    # First seed a fresh baseline (the cooldown-blocked call rotated baseline).
    d.detect(ms, _buf_sine(60.0), now=1020.0)  # baseline reset @ 60Hz
    ev3 = d.detect(ms, _buf_sine(100.0), now=1025.0)  # Δ=40, > 14s after first fire
    assert ev3 is not None and ev3.type == "KICK_SWAP"


# ---------- Test 5: first call seeds baseline, no fire ----------


def test_kick_swap_first_call_seeds_baseline_no_fire():
    d = KickSwapDetector()
    ms = _state(rms=0.06)
    # First call ever — no baseline yet.
    ev = d.detect(ms, _buf_sine(60.0), now=1000.0)
    assert ev is None
    assert d.last_centroid_hz is not None  # baseline now set
    # Second call with shifted centroid > 4s later: fires.
    ev2 = d.detect(ms, _buf_sine(100.0), now=1004.5)
    assert ev2 is not None
    assert ev2.type == "KICK_SWAP"


# ---------- Test 6: extra dict shape ----------


def test_kick_swap_extra_dict_keys_and_types():
    d = KickSwapDetector()
    ms = _state(rms=0.06)
    d.detect(ms, _buf_sine(60.0), now=1000.0)
    ev = d.detect(ms, _buf_sine(100.0), now=1004.5)
    assert ev is not None
    extra = ev.extra
    assert set(extra.keys()) == {"prev_centroid_hz", "new_centroid_hz", "delta_hz"}
    assert isinstance(extra["prev_centroid_hz"], float)
    assert isinstance(extra["new_centroid_hz"], float)
    assert isinstance(extra["delta_hz"], float)
    assert extra["delta_hz"] >= 0.0  # delta is absolute


# ---------- Test 7: re-export ----------


def test_kick_swap_detector_is_re_exported_from_subpackage():
    from vibemix.state.detectors import KickSwapDetector as Re

    assert Re is KickSwapDetector
