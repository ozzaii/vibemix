# SPDX-License-Identifier: Apache-2.0
"""Synthetic 4-on-floor kick WAV generator (Plan 17-06 fixture helper).

Mirrors ``tests/state/detectors/test_phrase_dsp.py::_synth_kick_pattern`` —
ports it into a shared, reusable shape so ``scripts/tune_detectors.py``
smoke tests + any future Phase 17 / Phase 16 reference-WAV harness tests
can build deterministic input without recording real audio.

Why a separate copy + not a refactor of the phrase_dsp helper? The
phrase_dsp helper is in-test scope (test module local) and returns an
``np.ndarray``; this helper writes to disk and returns a Path. Keeping
both avoids importing test internals from another test file (pytest
doesn't promise stable test-module import semantics across collection).

Uses stdlib ``wave`` for WAV I/O (no ``soundfile`` dep — see CLAUDE.md
project tech-stack: soundfile is NOT a project dep, ``wave`` is what
``scripts/gen_sine.py`` uses).

Pattern shape (verbatim from Plan 17-04 helper):
    - 60Hz sine kick pulses every (60/bpm) seconds.
    - Each pulse: 10ms linear attack into 100ms exponential decay.
    - Sum of pulses on a zero buffer, normalized to ±0.6 peak.
    - Optional ``breakdown_at_s`` zeros samples in
      [breakdown_at_s, breakdown_at_s + breakdown_duration_s].

Output: int16 mono WAV at the requested sample rate.
"""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np


def _synth_kick_pattern(
    bpm: float,
    duration_s: float,
    sr: int,
    *,
    kick_freq_hz: float = 60.0,
    attack_ms: float = 10.0,
    decay_ms: float = 100.0,
) -> np.ndarray:
    """Build a 4-on-floor synthetic kick pattern; returns float32 in [-0.6, 0.6].

    Verbatim port of ``tests/state/detectors/test_phrase_dsp.py::_synth_kick_pattern``
    so the autocorr-locked downbeat math behaves identically here.
    """
    n = int(sr * duration_s)
    out = np.zeros(n, dtype=np.float32)
    beat_period_s = 60.0 / bpm
    samples_per_beat = int(beat_period_s * sr)

    attack_n = int((attack_ms / 1000.0) * sr)
    decay_n = int((decay_ms / 1000.0) * sr)
    pulse_n = attack_n + decay_n

    # Build one canonical kick pulse and copy-paste it onto every beat slot.
    t_pulse = np.arange(pulse_n, dtype=np.float32) / float(sr)
    sine = np.sin(2.0 * np.pi * kick_freq_hz * t_pulse)
    env = np.zeros(pulse_n, dtype=np.float32)
    if attack_n > 0:
        env[:attack_n] = np.linspace(0.0, 1.0, attack_n, dtype=np.float32)
    if decay_n > 0:
        # Exponential decay over the decay segment: amp * exp(-5 * x/decay_n)
        x = np.arange(decay_n, dtype=np.float32) / float(decay_n)
        env[attack_n:] = np.exp(-5.0 * x)
    pulse = (sine * env).astype(np.float32)

    # Drop a kick on every beat boundary (skip the first sample so the
    # autocorr peak isn't dominated by the lag-0 self-match).
    for beat_idx in range(int(duration_s / beat_period_s)):
        start = beat_idx * samples_per_beat
        end = start + pulse_n
        if end > n:
            break
        out[start:end] += pulse
    # Normalize to avoid clip when summed pulses overlap on short patterns.
    peak = float(np.max(np.abs(out)))
    if peak > 0.0:
        out = out / peak * 0.6
    return out


def write_synth_kick_wav(
    path: Path,
    *,
    bpm: float = 130.0,
    duration_s: float = 8.0,
    sample_rate: int = 16000,
    breakdown_at_s: float | None = None,
    breakdown_duration_s: float = 2.0,
) -> Path:
    """Write a synthetic 4-on-floor kick WAV at ``path``; return ``path``.

    Args:
        path: Output WAV path. Parent directory must exist.
        bpm: Beats-per-minute for the 4-on-floor pattern.
        duration_s: Total WAV duration in seconds.
        sample_rate: Sample rate in Hz (16000 = matches AudioBuffer ring).
        breakdown_at_s: If not None, zero the slice
            ``[breakdown_at_s, breakdown_at_s + breakdown_duration_s]``
            after the kick pattern is generated. This produces a deterministic
            "kick disappears" event for ``BreakdownKickKillDetector`` smoke
            tests.
        breakdown_duration_s: Length of the breakdown window in seconds.

    Returns:
        ``path`` (for fluent test assertions).

    File format: int16 mono WAV via stdlib ``wave``. Matches the format
    ``scripts/gen_sine.py`` writes — no soundfile dep needed.
    """
    samples = _synth_kick_pattern(bpm, duration_s, sample_rate)

    if breakdown_at_s is not None:
        bd_lo = int(breakdown_at_s * sample_rate)
        bd_hi = int((breakdown_at_s + breakdown_duration_s) * sample_rate)
        # Clamp to buffer bounds; a breakdown that extends past the WAV end
        # is still valid (just truncates).
        bd_hi = min(bd_hi, samples.size)
        if bd_lo < samples.size:
            samples[bd_lo:bd_hi] = 0.0

    # Convert float32 [-1, 1] to int16 — same convention as gen_sine.py.
    int16 = (samples * 32767.0).astype(np.int16)

    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(int16.tobytes())

    return path
