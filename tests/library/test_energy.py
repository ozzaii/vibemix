# SPDX-License-Identifier: Apache-2.0
"""Tests for the perceived-dancefloor-energy module (vibemix.library.energy).

The make-or-break property is GENRE ROBUSTNESS — a quiet hypnotic after-hours
track must NOT read low, and a loud-but-sparse intro must NOT read high. So
beyond unit-pinning each feature on known signals, the load-bearing tests are
the PAIRWISE-RANKING and WITHIN-TRACK-MONOTONICITY checks.

All audio here is SYNTHESISED with numpy — no real files, no ffmpeg, no API
key. ``score_energy`` is exercised by monkeypatching ``decode_to_mono`` to
return a synthetic array, so the public entrypoint is covered without I/O.
"""

from __future__ import annotations

import numpy as np
import pytest

from vibemix.library import energy
from vibemix.library.energy import EnergyScore, score_energy, spectral_flux

SR = 16000


# ─── Synthetic signal helpers ─────────────────────────────────────────────────


def _sine(freq: float, seconds: float, sr: int = SR, amp: float = 0.5) -> np.ndarray:
    t = np.arange(int(seconds * sr), dtype=np.float32) / sr
    return (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def _white_noise(seconds: float, sr: int = SR, amp: float = 0.5, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return (amp * rng.standard_normal(int(seconds * sr))).astype(np.float32)


def _square(freq: float, seconds: float, sr: int = SR, amp: float = 0.5) -> np.ndarray:
    s = _sine(freq, seconds, sr, amp=1.0)
    return (amp * np.sign(s)).astype(np.float32)


def _kick_train(
    bpm: float, seconds: float, sr: int = SR, amp: float = 0.7, decay: float = 0.08
) -> np.ndarray:
    """A 4-on-the-floor sub-kick train — periodic 60Hz decaying bursts."""
    out = np.zeros(int(seconds * sr), dtype=np.float32)
    step = int((60.0 / bpm) * sr)
    burst_len = int(decay * sr)
    t = np.arange(burst_len, dtype=np.float32) / sr
    env = np.exp(-t / (decay / 4.0))
    burst = (amp * np.sin(2 * np.pi * 60.0 * t) * env).astype(np.float32)
    for start in range(0, out.size - burst_len, step):
        out[start : start + burst_len] += burst
    return out


# ─── spectral_flux helper unit pins ───────────────────────────────────────────


def test_spectral_flux_pure_sine_is_low():
    """A steady sine barely changes spectrum frame-to-frame → near-zero flux."""
    f = spectral_flux(_sine(440.0, 4.0))
    assert f < 0.05


def test_spectral_flux_white_noise_is_high():
    """White noise churns the spectrum every frame → high flux, well above a sine."""
    quiet_sine = spectral_flux(_sine(440.0, 4.0))
    noise = spectral_flux(_white_noise(4.0))
    assert noise > quiet_sine
    assert noise > 0.05


def test_spectral_flux_empty_is_zero():
    assert spectral_flux(np.zeros(0, dtype=np.float32)) == 0.0


def test_spectral_flux_silent_is_zero():
    """All-zero audio has no spectral motion AND no magnitude → 0.0 (honest)."""
    assert spectral_flux(np.zeros(SR * 2, dtype=np.float32)) == 0.0


def test_spectral_flux_loudness_invariant():
    """Flux is magnitude-normalised: a louder copy of the SAME signal must give
    the same flux (else loudness leaks into the 'drive' feature)."""
    sig = _white_noise(4.0, amp=0.2, seed=7)
    quiet = spectral_flux(sig)
    loud = spectral_flux(sig * 3.0)
    assert quiet == pytest.approx(loud, rel=1e-6)


# ─── full-score smoke + honest-null ───────────────────────────────────────────


def _patch_decode(monkeypatch, arr: np.ndarray) -> None:
    monkeypatch.setattr(energy, "decode_to_mono", lambda path, sample_rate=SR: arr)


def test_score_energy_returns_energyscore(monkeypatch):
    _patch_decode(monkeypatch, _kick_train(128.0, 12.0))
    res = score_energy("fake.wav")
    assert isinstance(res, EnergyScore)
    assert 0.0 <= res.score <= 100.0
    # breakdown must expose every weighted feature, each normalised to [0,1].
    for name in (
        "loudness",
        "sub_share",
        "onset_rate",
        "spectral_flux",
        "brightness",
        "beat_regularity",
        "dynamic_range",
    ):
        assert name in res.breakdown
        assert 0.0 <= res.breakdown[name] <= 1.0


def test_score_energy_frozen_slots():
    res = EnergyScore(score=50.0, breakdown={"loudness": 0.5})
    with pytest.raises(Exception):
        res.score = 1.0  # frozen


def test_score_energy_empty_audio_is_none(monkeypatch):
    """Undecodable / empty → honest-null, never a raise, never a fake 0."""
    _patch_decode(monkeypatch, np.zeros(0, dtype=np.float32))
    assert score_energy("empty.wav") is None


def test_score_energy_silent_audio_is_none(monkeypatch):
    """All-silence (no busy frames) → honest-null."""
    _patch_decode(monkeypatch, np.zeros(SR * 5, dtype=np.float32))
    assert score_energy("silent.wav") is None


def test_score_energy_decode_failure_is_none(monkeypatch):
    """A decode that raises (corrupt file / no ffmpeg) → None, not a crash."""

    def _boom(path, sample_rate=SR):
        raise RuntimeError("ffmpeg blew up")

    monkeypatch.setattr(energy, "decode_to_mono", _boom)
    assert score_energy("garbage.bin") is None


def test_score_energy_decode_returns_none_is_none(monkeypatch):
    monkeypatch.setattr(energy, "decode_to_mono", lambda path, sample_rate=SR: None)
    assert score_energy("nope.wav") is None


# ─── GENRE ROBUSTNESS: pairwise ranking (the hypnotic-regression guard) ────────


def test_quiet_busy_outscores_loud_sparse(monkeypatch):
    """The core thesis. A QUIET, BUSY track (low RMS, high flux + onsets — a
    hypnotic after-hours roller) must out-score a LOUD, SPARSE one (high RMS,
    near-zero flux/onsets — a loud sustained drone / intro pad).
    """
    # Loud sparse: a fat, loud, *static* sustained pad — high amplitude, no
    # motion / onsets. (A sustained 220Hz tone — a held synth chord root —
    # rather than a sub-bass sine, whose per-window RMS jitters at low freq.)
    loud_sparse = _sine(220.0, 12.0, amp=0.9)

    # Quiet busy: a quiet kick roller + churning hats — lots of spectral motion
    # and onsets, but at a low overall level.
    quiet_busy = 0.18 * _kick_train(130.0, 12.0, amp=1.0) + 0.12 * _white_noise(12.0, amp=1.0, seed=3)
    quiet_busy = quiet_busy.astype(np.float32)

    _patch_decode(monkeypatch, loud_sparse)
    s_loud = score_energy("loud_sparse.wav")
    _patch_decode(monkeypatch, quiet_busy)
    s_busy = score_energy("quiet_busy.wav")

    assert s_loud is not None and s_busy is not None
    # Sanity: the quiet track really is quieter (lower RMS), and really is
    # busier (higher flux) — proves the fixtures embody the named tension.
    assert s_busy.breakdown["spectral_flux"] > s_loud.breakdown["spectral_flux"]
    assert s_busy.breakdown["onset_rate"] > s_loud.breakdown["onset_rate"]
    assert s_busy.breakdown["loudness"] < s_loud.breakdown["loudness"]
    # The verdict: drive beats loudness.
    assert s_busy.score > s_loud.score


# ─── GENRE ROBUSTNESS: within-track monotonicity (build → drop) ────────────────


def test_drop_window_outscores_breakdown_window():
    """A synthetic build→drop array, scored with a rolling window: the DROP
    section (full kick + busy spectrum) must score higher than the BREAKDOWN
    section (sparse, filtered pad). Exercises the internal scorer on raw arrays.
    """
    # Breakdown: quiet, sparse, filtered — a soft mid pad, low motion.
    breakdown = 0.15 * _sine(300.0, 8.0, amp=1.0)
    # Drop: full kick + churning broadband content — the floor-filler.
    drop = (0.5 * _kick_train(130.0, 8.0, amp=1.0) + 0.25 * _white_noise(8.0, amp=1.0, seed=11)).astype(
        np.float32
    )

    s_breakdown = energy._score_array(breakdown, SR)
    s_drop = energy._score_array(drop, SR)

    assert s_breakdown is not None and s_drop is not None
    assert s_drop.score > s_breakdown.score


def test_busy_frame_mask_ignores_dead_air():
    """Padding a busy track with a long silent intro+outro must NOT materially
    drop its score — the busy-frame mask describes the ACTIVE character.
    """
    core = (0.4 * _kick_train(128.0, 10.0, amp=1.0) + 0.2 * _white_noise(10.0, amp=1.0, seed=5)).astype(
        np.float32
    )
    silence = np.zeros(SR * 8, dtype=np.float32)
    padded = np.concatenate([silence, core, silence]).astype(np.float32)

    s_core = energy._score_array(core, SR)
    s_padded = energy._score_array(padded, SR)

    assert s_core is not None and s_padded is not None
    # Dead air should be masked out → scores within a small tolerance.
    assert abs(s_core.score - s_padded.score) <= 6.0


# ─── normalisation discipline ─────────────────────────────────────────────────


def test_all_breakdown_features_clamped(monkeypatch):
    """Even on an extreme signal (loud full-scale broadband noise), every
    normalised feature stays inside [0,1] — proving the fixed-window clip, not
    an unbounded ratio.
    """
    _patch_decode(monkeypatch, _white_noise(12.0, amp=0.99, seed=99))
    res = score_energy("extreme.wav")
    assert res is not None
    for v in res.breakdown.values():
        assert 0.0 <= v <= 1.0
    assert 0.0 <= res.score <= 100.0
