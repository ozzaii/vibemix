# SPDX-License-Identifier: Apache-2.0
"""DistortionClimbDetector — fires on combined band-limited flatness rise,
odd-harmonic-energy spike, and sustained kick density (Phase 30 SENSE-17).

Synthetic fixtures: each tick supplies a 4s int16 PCM array that combines a
clipped 60Hz square (rich odd harmonics) with a controlled amount of
white-noise floor (drives band-limited spectral flatness).
"""

from __future__ import annotations

import numpy as np

from tests.state.detectors.conftest import _state
from vibemix.audio.constants import (
    DISTORTION_KICK_DENSITY_MIN,
    LOW_RMS,
    MIN_EVENT_GAP_PER_TYPE,
)
from vibemix.state.detectors.distortion_climb import DistortionClimbDetector

_SR = 16000
_4S_SAMPLES = _SR * 4


class _FakeAudioBuf:
    """Tiny AudioBuffer surrogate — ``.snapshot(n)`` + ``._sr``. Tests hand
    different signals per tick by reassigning ``._samples``."""

    def __init__(self, samples: np.ndarray, sr: int = _SR) -> None:
        self._samples = samples
        self._sr = sr

    def snapshot(self, n: int) -> np.ndarray:
        if self._samples.size <= n:
            return self._samples
        return self._samples[-n:]


def _clipped_square_kick(noise_share: float, n_samples: int = _4S_SAMPLES) -> np.ndarray:
    """Build a heavily-clipped 60Hz kick-like signal mixed with white noise.

    ``noise_share`` in [0, 1] controls how much white noise is added — higher
    noise → higher spectral flatness in the 200-2000Hz band. The square wave
    carries strong odd-harmonic content (3rd, 5th of 60Hz = 180Hz, 300Hz)
    that drives ``harmonic_distortion_proxy`` above the 1.5 threshold.
    """
    t = np.arange(n_samples, dtype=np.float32) / float(_SR)
    # Square wave at 60 Hz — saturated/clipped kick simulation. sign() gives
    # a perfect ±1 square so the odd harmonics dominate.
    square = np.sign(np.sin(2.0 * np.pi * 60.0 * t)).astype(np.float32)
    # White noise centered at 0 with unit variance, scaled down.
    rng = np.random.default_rng(seed=42)
    noise = rng.standard_normal(n_samples).astype(np.float32)
    # Mix: square dominates at noise_share=0, noise dominates at noise_share=1.
    mix = (1.0 - noise_share) * square + noise_share * noise
    # Scale to int16 with headroom.
    return (mix * 12000.0).astype(np.int16)


def test_distortion_climb_fires_on_combined_signal():
    """Drive the detector with rising flatness (more noise per tick), high
    odd-harmonic energy (clipped square persists), and sustained density.
    Expect a single fire after the 4-window history fills AND the density
    streak has aged past 4s."""
    d = DistortionClimbDetector()
    ms = _state(rms=0.10, onset_density=DISTORTION_KICK_DENSITY_MIN + 1.0)

    # Walk 9 ticks 1s apart. Density-streak gate needs >= 4s of sustained
    # onset_density, AND the 4-sample flatness history needs to fill, AND
    # the rising-noise tail must keep the harmonic ratio > 1.5.
    # Plateau at noise_share=0.6 (flat ~0.83, harm ~14) for the last 4 ticks
    # so the delta from 0.05 → 0.6 stays in the history while the harmonic
    # ratio doesn't collapse.
    noise_schedule = [0.05, 0.15, 0.3, 0.45, 0.6, 0.6, 0.6, 0.6, 0.6]
    fired = None
    for i, noise_share in enumerate(noise_schedule):
        buf = _FakeAudioBuf(_clipped_square_kick(noise_share))
        ev = d.detect(ms, buf, now=1000.0 + i * 1.0)
        if ev is not None:
            fired = ev
            break

    assert fired is not None, "expected a DISTORTION_CLIMB on rising-flatness signal"
    assert fired.type == "DISTORTION_CLIMB"
    assert "chain_position" in fired.extra
    assert fired.extra["chain_position"] == 1
    assert "distortion_db" in fired.extra
    # Square wave at 60Hz with strong odd content → ratio >> 1.5 → dB > +3.5
    assert fired.extra["distortion_db"] > 3.0


def test_distortion_climb_no_fire_on_silence():
    """rms below LOW_RMS — silence gate rejects + clears density streak."""
    d = DistortionClimbDetector()
    ms_quiet = _state(rms=LOW_RMS - 0.001, onset_density=DISTORTION_KICK_DENSITY_MIN + 2.0)
    buf = _FakeAudioBuf(_clipped_square_kick(0.5))
    ev = d.detect(ms_quiet, buf, now=1000.0)
    assert ev is None
    assert d._density_streak_start is None


def test_distortion_climb_no_fire_when_audio_buf_none():
    """Graceful no-op when audio_buf is None (Plan 17-05 contract)."""
    d = DistortionClimbDetector()
    ms = _state(rms=0.10, onset_density=DISTORTION_KICK_DENSITY_MIN + 1.0)
    ev = d.detect(ms, None, now=1000.0)
    assert ev is None


def test_distortion_climb_cooldown_blocks_repeat():
    """Fire then refire within cooldown — second call returns None."""
    d = DistortionClimbDetector()
    ms = _state(rms=0.10, onset_density=DISTORTION_KICK_DENSITY_MIN + 1.0)

    fired_ev = None
    fire_at = None
    noise_schedule = [0.05, 0.15, 0.3, 0.45, 0.6, 0.6, 0.6, 0.6, 0.6]
    for i, noise_share in enumerate(noise_schedule):
        buf = _FakeAudioBuf(_clipped_square_kick(noise_share))
        ev = d.detect(ms, buf, now=1000.0 + i * 1.0)
        if ev is not None:
            fired_ev = ev
            fire_at = 1000.0 + i * 1.0
            break
    assert fired_ev is not None

    # 2s later (well inside the 6s cooldown) — must NOT refire.
    cooldown = MIN_EVENT_GAP_PER_TYPE["DISTORTION_CLIMB"]
    buf2 = _FakeAudioBuf(_clipped_square_kick(0.6))
    ev2 = d.detect(ms, buf2, now=fire_at + cooldown - 1.0)
    assert ev2 is None


def test_distortion_climb_requires_density_gate():
    """All three gates required — strip the density gate, no fire even with
    rising flatness + clipped square content."""
    d = DistortionClimbDetector()
    # Density BELOW the floor — streak never accumulates.
    ms = _state(rms=0.10, onset_density=DISTORTION_KICK_DENSITY_MIN - 2.0)

    noise_schedule = [0.05, 0.15, 0.3, 0.45, 0.6, 0.6, 0.6, 0.6, 0.6]
    for i, noise_share in enumerate(noise_schedule):
        buf = _FakeAudioBuf(_clipped_square_kick(noise_share))
        ev = d.detect(ms, buf, now=1000.0 + i * 1.0)
        assert ev is None, f"unexpected fire at tick {i} when density gate not met"


def test_distortion_climb_chain_position_increments_across_fires():
    """Two separate fires → chain_position 1 then 2 (after cooldown elapses)."""
    d = DistortionClimbDetector()
    ms = _state(rms=0.10, onset_density=DISTORTION_KICK_DENSITY_MIN + 1.0)

    # Fire 1.
    fire1 = None
    fire1_t = None
    noise_schedule = [0.05, 0.15, 0.3, 0.45, 0.6, 0.6, 0.6, 0.6, 0.6]
    for i, noise_share in enumerate(noise_schedule):
        buf = _FakeAudioBuf(_clipped_square_kick(noise_share))
        ev = d.detect(ms, buf, now=1000.0 + i * 1.0)
        if ev is not None:
            fire1 = ev
            fire1_t = 1000.0 + i * 1.0
            break
    assert fire1 is not None
    assert fire1.extra["chain_position"] == 1

    # Walk past the cooldown + give the flatness history a fresh climb.
    cooldown = MIN_EVENT_GAP_PER_TYPE["DISTORTION_CLIMB"]
    base = fire1_t + cooldown + 0.5
    fire2 = None
    for i, noise_share in enumerate(noise_schedule):
        buf = _FakeAudioBuf(_clipped_square_kick(noise_share))
        ev = d.detect(ms, buf, now=base + i * 1.0)
        if ev is not None:
            fire2 = ev
            break
    assert fire2 is not None
    assert fire2.extra["chain_position"] == 2
