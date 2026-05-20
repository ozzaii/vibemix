# SPDX-License-Identifier: Apache-2.0
"""Feature-range grounding regression (BRINGUP-02).

Phases 54/55 (hype/coach) react to the per-tick features. If a NaN band, an inf
RMS, or an out-of-range onset density leaks into MusicState, every downstream
reaction is hallucinated. This test replays a synthetic "full-set" (silence ->
quiet sine -> loud sine -> frequency sweep) through ``_tick_once`` and asserts
every audio-derived field that reaches the wire is finite, non-negative, and in
its valid range — no NaN, no inf, no out-of-range spike.

The bar: "the AI never sees a value that did not happen."
"""

from __future__ import annotations

import math

import numpy as np

from vibemix.audio import AudioBuffer
from vibemix.audio.constants import SILENT_RMS
from vibemix.state import MusicState
from vibemix.state.refresh import _tick_once

from tests.audio.conftest import int16_sine
from tests.state.test_refresh import _ctrl_mock, _track_mock


def _buf_with(pcm: np.ndarray) -> AudioBuffer:
    buf = AudioBuffer(seconds=140.0, sr=16000)
    if pcm.size:
        buf.push(pcm)
    return buf


def _sweep_pcm() -> np.ndarray:
    """A rising-frequency sweep: stitch several int16_sine segments at climbing
    freqs into one buffer (energy spread across bands over the window)."""
    segs = [
        int16_sine(freq_hz=f, duration_sec=1.0, sample_rate=16000, amplitude=0.5)
        for f in (60.0, 200.0, 800.0, 3000.0, 6000.0)
    ]
    return np.concatenate(segs)


def _assert_state_features_grounded(state: MusicState) -> None:
    # RMS: finite, non-negative.
    assert isinstance(state.rms, float)
    assert math.isfinite(state.rms), f"state.rms not finite: {state.rms}"
    assert state.rms >= 0.0, f"state.rms negative: {state.rms}"

    # Band shares: finite, in [0, 1].
    assert set(state.bands.keys()) == {"sub", "low", "mid", "high"}
    for band, share in state.bands.items():
        assert math.isfinite(share), f"band {band} not finite: {share}"
        assert 0.0 <= share <= 1.0, f"band {band} out of [0,1]: {share}"

    # Onset density: finite, non-negative.
    assert math.isfinite(state.onset_density), f"onset_density not finite: {state.onset_density}"
    assert state.onset_density >= 0.0, f"onset_density negative: {state.onset_density}"


def _drive(buf: AudioBuffer, state: MusicState, now: float) -> None:
    _tick_once(
        state,
        buf,
        _ctrl_mock(),
        _track_mock(),
        now=now,
        last_audible_high=0.0,
        last_audible_low=0.0,
        bpm_cache=0.0,
        last_bpm_at=0.0,
    )


def test_features_grounded_across_synthetic_set():
    """Silence -> quiet sine -> loud sine -> sweep: every tick's features are
    finite + in-range on MusicState. No NaN/inf, no out-of-range band."""
    state = MusicState()
    stages = [
        _buf_with(np.array([], dtype=np.int16)),  # silence
        _buf_with(int16_sine(220.0, 6.0, 16000, amplitude=0.05)),  # quiet sine
        _buf_with(int16_sine(440.0, 6.0, 16000, amplitude=0.8)),  # loud sine
        _buf_with(_sweep_pcm()),  # frequency sweep
    ]
    now = 1000.0
    for buf in stages:
        now += 3.5
        _drive(buf, state, now)
        _assert_state_features_grounded(state)


def test_silence_tick_is_near_zero_no_nan():
    """A silence tick: state.rms below SILENT_RMS, all bands 0, no NaN."""
    state = MusicState()
    _drive(_buf_with(np.array([], dtype=np.int16)), state, 1003.5)
    _assert_state_features_grounded(state)
    assert state.rms < SILENT_RMS, f"silence rms not near-zero: {state.rms}"
    for band, share in state.bands.items():
        assert share == 0.0, f"silent band {band} nonzero: {share}"


def test_loud_tick_has_positive_rms_and_bounded_band_sum():
    """A loud sine tick: rms > 0, band shares in [0,1], and their sum is
    plausible (<= ~1.05 allowing rounding)."""
    state = MusicState()
    _drive(_buf_with(int16_sine(440.0, 6.0, 16000, amplitude=0.8)), state, 1003.5)
    _assert_state_features_grounded(state)
    assert state.rms > 0.0, "loud tick rms should be > 0"
    band_sum = sum(state.bands.values())
    assert math.isfinite(band_sum)
    assert band_sum <= 1.05, f"band shares sum implausibly high: {band_sum}"
