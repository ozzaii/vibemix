# SPDX-License-Identifier: Apache-2.0
"""Phase 13-05 Task 1 — compute_downbeat_phase pure function.

Anti-hallucination contract (CONTEXT.md Open Q 4):
 - Invalid BPM (0, negative, NaN, > 220) → (0.0, 0.0). Never fake confidence.
 - Insufficient onsets (<4 peaks in the analysis window) → (prior_phase, 0.0).
   The renderer reads bpm_confidence < 0.6 and skips beat-lock entirely.
 - Determinism: same audio + same prior_phase → same (phase, confidence).
 - Synthetic ideal kick-train @ matching BPM → phase ∈ [0, 1), confidence > 0.5.

This function is pure (no global state) so tests can drive it with synthetic
numpy buffers and pin behavior without standing up the whole audio package.
"""

from __future__ import annotations

import math

import numpy as np

from vibemix.audio.features import compute_downbeat_phase

SR = 16000


def _silent_audio(seconds: float = 4.0) -> np.ndarray:
    return np.zeros(int(SR * seconds), dtype=np.float32)


def _synthetic_kick_train(bpm: float, seconds: float = 4.0) -> np.ndarray:
    """Build a synthetic onset train at `bpm`: short Gaussian-ish kicks every beat.

    Returns mono float32 in roughly [-1, 1]. Each kick is ~10ms long; gap between
    kicks = (60 / bpm) seconds. The onset envelope this produces is clean enough
    that compute_downbeat_phase should report confidence > 0.5.
    """
    n_samples = int(SR * seconds)
    samples_per_beat = int((60.0 / bpm) * SR)
    audio = np.zeros(n_samples, dtype=np.float32)
    kick_len = int(SR * 0.010)  # 10ms kick
    # Half-sine envelope * sinusoid to make a sub-thump
    t = np.arange(kick_len, dtype=np.float32)
    env = np.sin(np.pi * t / kick_len)
    carrier = np.sin(2 * np.pi * 60.0 * t / SR)
    kick = (env * carrier * 0.9).astype(np.float32)
    pos = 0
    while pos + kick_len < n_samples:
        audio[pos : pos + kick_len] += kick
        pos += samples_per_beat
    return audio


def test_silent_audio_returns_zero_phase_zero_confidence():
    audio = _silent_audio()
    phase, conf = compute_downbeat_phase(audio, bpm=120.0, sample_rate=SR)
    assert phase == 0.0
    assert conf == 0.0


def test_zero_bpm_returns_zero_zero():
    """Invalid BPM (zero) → no fake confidence. This is the anti-hallucination
    guard from the threat model (T-13-05-02)."""
    audio = _synthetic_kick_train(120.0)
    phase, conf = compute_downbeat_phase(audio, bpm=0.0, sample_rate=SR)
    assert phase == 0.0
    assert conf == 0.0


def test_negative_bpm_returns_zero_zero():
    audio = _synthetic_kick_train(120.0)
    phase, conf = compute_downbeat_phase(audio, bpm=-1.0, sample_rate=SR)
    assert phase == 0.0
    assert conf == 0.0


def test_nan_bpm_returns_zero_zero():
    audio = _synthetic_kick_train(120.0)
    phase, conf = compute_downbeat_phase(audio, bpm=float("nan"), sample_rate=SR)
    assert phase == 0.0
    assert conf == 0.0


def test_excessive_bpm_returns_zero_zero():
    """BPM > 220 is outside the supported range — return (0.0, 0.0)
    rather than fabricating a phase from probably-aliased onsets."""
    audio = _synthetic_kick_train(120.0)
    phase, conf = compute_downbeat_phase(audio, bpm=400.0, sample_rate=SR)
    assert phase == 0.0
    assert conf == 0.0


def test_synthetic_kick_train_produces_valid_phase_and_confidence():
    """The classic happy-path case: ideal kicks at 120 BPM. The function
    should lock onto the beat and return a usable confidence."""
    audio = _synthetic_kick_train(120.0, seconds=4.0)
    phase, conf = compute_downbeat_phase(audio, bpm=120.0, sample_rate=SR)
    assert 0.0 <= phase < 1.0, f"phase out of range: {phase}"
    assert conf > 0.5, f"confidence too low for ideal synthetic kicks: {conf}"


def test_prior_phase_preserved_when_too_few_peaks():
    """If fewer than 4 peaks are detected (e.g. quiet/sparse audio), return
    (prior_phase, 0.0) — preserve the last known phase but signal zero
    confidence so the renderer skips beat-lock."""
    # A very short snippet with at most 2-3 onsets.
    audio = np.zeros(int(SR * 1.0), dtype=np.float32)
    # Add two tiny clicks
    audio[100] = 0.5
    audio[200] = 0.5
    phase, conf = compute_downbeat_phase(audio, bpm=120.0, sample_rate=SR, prior_phase=0.42)
    assert math.isclose(phase, 0.42, abs_tol=1e-9), (
        f"prior_phase not preserved: got {phase}, expected 0.42"
    )
    assert conf == 0.0


def test_pure_function_determinism():
    """Same audio + same prior_phase MUST return the same (phase, confidence)
    on repeated calls. No hidden state. Catches accidental global caches."""
    audio = _synthetic_kick_train(128.0, seconds=4.0)
    r1 = compute_downbeat_phase(audio, bpm=128.0, sample_rate=SR, prior_phase=0.1)
    r2 = compute_downbeat_phase(audio, bpm=128.0, sample_rate=SR, prior_phase=0.1)
    assert r1 == r2, f"determinism violation: {r1} vs {r2}"
