# SPDX-License-Identifier: Apache-2.0
"""AcidLineEntryDetector — fires on TB-303-style 200-800Hz formant sweep
combined with resonance-Q rise from low (<3) to high (>8) over a 3s
evaluation window (Phase 30 SENSE-18).

Synthetic fixtures: per-tick we synthesise a 1.5s snapshot of a narrow
sinusoid at the current instantaneous formant frequency mixed with a
controlled white-noise floor (Q rises as the noise floor falls).
"""

from __future__ import annotations

import numpy as np

from tests.state.detectors.conftest import _state
from vibemix.audio.constants import (
    LOW_RMS,
    MIN_EVENT_GAP_PER_TYPE,
)
from vibemix.state.detectors.acid_line_entry import AcidLineEntryDetector

_SR = 16000
_SNAP_SAMPLES = int(_SR * 1.5)


class _FakeAudioBuf:
    def __init__(self, samples: np.ndarray, sr: int = _SR) -> None:
        self._samples = samples
        self._sr = sr

    def snapshot(self, n: int) -> np.ndarray:
        if self._samples.size <= n:
            return self._samples
        return self._samples[-n:]


def _resonant_tone(
    freq_hz: float,
    tone_amp: float,
    noise_amp: float = 1.0,
    n_samples: int = _SNAP_SAMPLES,
) -> np.ndarray:
    """Synthesize a tone + band noise mix.

    Behaviour:
        - ``tone_amp=0.0`` → pure noise (Q proxy ≈ 1-3, dominant freq random).
        - ``tone_amp=0.3`` → emerging resonance (Q ≈ 15-20).
        - ``tone_amp >= 1.0`` → strong resonance (Q ≈ 100+).
    """
    t = np.arange(n_samples, dtype=np.float32) / float(_SR)
    tone = np.sin(2.0 * np.pi * freq_hz * t).astype(np.float32)
    # Seed is freq-dependent so noise patterns rotate across the sweep
    # without making one tick's noise dominate another.
    rng = np.random.default_rng(seed=int(freq_hz * 1000) % 10000)
    noise = rng.standard_normal(n_samples).astype(np.float32)
    mix = tone_amp * tone + noise_amp * noise
    return (mix * 8000.0).astype(np.int16)


def test_acid_line_entry_fires_on_sweep_plus_resonance():
    """Walk an upward formant sweep 250 → 600Hz over 2.4s with tone amplitude
    rising from 0.05 (noise-dominant, Q ≈ 2) to 0.5 (tone-dominant, Q ≈ 40)
    — both detector gates pass."""
    d = AcidLineEntryDetector()
    ms = _state(rms=0.08)

    fired = None
    # 12 ticks at 200ms cadence = 2.4s span. Plenty for slope + Q-half split.
    n_ticks = 12
    f_start, f_end = 250.0, 600.0
    tone_start, tone_end = 0.05, 0.5
    for i in range(n_ticks):
        u = i / (n_ticks - 1)
        freq = f_start * (f_end / f_start) ** u  # log-linear sweep
        tone_amp = tone_start + (tone_end - tone_start) * u
        buf = _FakeAudioBuf(_resonant_tone(freq, tone_amp))
        ev = d.detect(ms, buf, now=1000.0 + i * 0.2)
        if ev is not None:
            fired = ev
            break

    assert fired is not None, "expected ACID_LINE_ENTRY on rising-Q sweep"
    assert fired.type == "ACID_LINE_ENTRY"
    assert "formant_hz" in fired.extra
    assert "resonance_q" in fired.extra
    # Sweep midpoint must land in the 200-800Hz band.
    assert 200.0 <= fired.extra["formant_hz"] <= 800.0
    # Peak Q must exceed 8.0 (resonance gate).
    assert fired.extra["resonance_q"] > 8.0


def test_acid_line_entry_no_fire_on_silence():
    """rms below LOW_RMS — silence gate rejects + clears history."""
    d = AcidLineEntryDetector()
    ms = _state(rms=LOW_RMS - 0.001)
    buf = _FakeAudioBuf(_resonant_tone(400.0, tone_amp=0.5))
    ev = d.detect(ms, buf, now=1000.0)
    assert ev is None
    assert len(d._freq_history) == 0


def test_acid_line_entry_no_fire_when_audio_buf_none():
    d = AcidLineEntryDetector()
    ms = _state(rms=0.08)
    ev = d.detect(ms, None, now=1000.0)
    assert ev is None


def test_acid_line_entry_no_fire_on_flat_tone():
    """Constant 400Hz, tone amp rising — slope gate must reject (no sweep)."""
    d = AcidLineEntryDetector()
    ms = _state(rms=0.08)

    n_ticks = 12
    tone_start, tone_end = 0.05, 0.5
    for i in range(n_ticks):
        u = i / (n_ticks - 1)
        tone_amp = tone_start + (tone_end - tone_start) * u
        buf = _FakeAudioBuf(_resonant_tone(400.0, tone_amp))
        ev = d.detect(ms, buf, now=1000.0 + i * 0.2)
        assert ev is None, f"unexpected fire at tick {i} on flat-tone signal"


def test_acid_line_entry_no_fire_without_resonance_rise():
    """Sweep present but tone amp stays low (Q stays < 8) — resonance gate
    must reject."""
    d = AcidLineEntryDetector()
    ms = _state(rms=0.08)

    n_ticks = 12
    f_start, f_end = 250.0, 600.0
    for i in range(n_ticks):
        u = i / (n_ticks - 1)
        freq = f_start * (f_end / f_start) ** u
        # Constant low tone amp — never crosses the Q > 8.0 high threshold
        # (noise dominates the spectrum).
        buf = _FakeAudioBuf(_resonant_tone(freq, tone_amp=0.05))
        ev = d.detect(ms, buf, now=1000.0 + i * 0.2)
        assert ev is None, f"unexpected fire at tick {i} without resonance rise"


def test_acid_line_entry_cooldown_blocks_repeat():
    """Fire then refire within cooldown — second call returns None."""
    d = AcidLineEntryDetector()
    ms = _state(rms=0.08)

    fired_ev = None
    fire_at = None
    n_ticks = 12
    for i in range(n_ticks):
        u = i / (n_ticks - 1)
        freq = 250.0 * (600.0 / 250.0) ** u
        tone_amp = 0.05 + (0.5 - 0.05) * u
        buf = _FakeAudioBuf(_resonant_tone(freq, tone_amp))
        ev = d.detect(ms, buf, now=1000.0 + i * 0.2)
        if ev is not None:
            fired_ev = ev
            fire_at = 1000.0 + i * 0.2
            break
    assert fired_ev is not None

    # Push 5 more ticks at high Q — must stay quiet inside cooldown.
    cooldown = MIN_EVENT_GAP_PER_TYPE["ACID_LINE_ENTRY"]
    for i in range(5):
        u = i / 4
        freq = 250.0 * (600.0 / 250.0) ** u
        tone_amp = 0.05 + (0.5 - 0.05) * u
        buf = _FakeAudioBuf(_resonant_tone(freq, tone_amp))
        t = fire_at + 1.0 + i * 0.2
        assert t < fire_at + cooldown, "test ticks should stay inside cooldown"
        ev = d.detect(ms, buf, now=t)
        assert ev is None
