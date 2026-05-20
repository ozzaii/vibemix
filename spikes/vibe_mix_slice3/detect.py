# SPDX-License-Identifier: Apache-2.0
"""Structural cue detection from raw audio — numpy/scipy only.

Pipeline:
    audio -> onset envelope (spectral flux) -> tempo + beat grid (autocorr)
          -> smoothed energy curve -> intro / breakdown / drop
          -> snap each to nearest beat -> CueCandidate with confidence

Conservative by design (anti-slop): magnitudes map to confidence, and the
caller's gate drops anything weak. A wrong cue is worse than no cue.
"""
from __future__ import annotations

import subprocess

import numpy as np
from scipy.ndimage import uniform_filter1d

from spikes.vibe_mix_slice0.types import CueCandidate

SR = 22050
_WIN = 2048
_HOP = 512
_ENV_RATE = SR / _HOP            # onset-envelope frames per second (~43 Hz)


def decode_mono(path: str, sr: int = SR) -> np.ndarray:
    """Decode any audio file to mono float32 PCM at ``sr`` via ffmpeg."""
    out = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(sr),
         "-f", "f32le", "-"],
        capture_output=True, check=True,
    ).stdout
    return np.frombuffer(out, dtype=np.float32).copy()


def onset_envelope(x: np.ndarray) -> np.ndarray:
    """Spectral-flux onset strength per STFT frame (>=0)."""
    n = 1 + (len(x) - _WIN) // _HOP
    if n <= 1:
        return np.zeros(1, dtype=np.float64)
    window = np.hanning(_WIN)
    frames = np.stack([x[i * _HOP : i * _HOP + _WIN] * window for i in range(n)])
    mag = np.abs(np.fft.rfft(frames, axis=1))
    flux = np.diff(mag, axis=0)
    flux[flux < 0] = 0.0                       # half-wave rectify: onsets only
    env = flux.sum(axis=1)
    return np.concatenate([[0.0], env])


def estimate_tempo(env: np.ndarray, bpm_range=(70, 180)) -> float:
    """Tempo (BPM) from the autocorrelation peak of the onset envelope."""
    e = env - env.mean()
    ac = np.correlate(e, e, mode="full")[len(e) - 1 :]
    lo = int(_ENV_RATE * 60.0 / bpm_range[1])  # smallest lag (fastest BPM)
    hi = int(_ENV_RATE * 60.0 / bpm_range[0])  # largest lag (slowest BPM)
    hi = min(hi, len(ac) - 1)
    if hi <= lo:
        return 0.0
    lag = lo + int(np.argmax(ac[lo:hi]))
    return float(60.0 * _ENV_RATE / lag) if lag else 0.0


def _beat_grid(env: np.ndarray, bpm: float, duration_s: float) -> np.ndarray:
    """Beat times (s) from tempo + the strongest onset as phase anchor."""
    if bpm <= 0:
        return np.array([0.0])
    period = 60.0 / bpm
    anchor = float(np.argmax(env)) / _ENV_RATE
    first = anchor - period * np.floor(anchor / period)
    return np.arange(first, duration_s, period)


def _snap(t: float, beats: np.ndarray) -> float:
    if len(beats) == 0:
        return t
    return float(beats[int(np.argmin(np.abs(beats - t)))])


def energy_curve(x: np.ndarray, sr: int = SR, hop_s: float = 0.5):
    """Smoothed normalized RMS energy curve. Returns (times_s, energy[0..1])."""
    hop = max(1, int(sr * hop_s))
    n = len(x) // hop
    if n < 1:
        return np.array([0.0]), np.array([0.0])
    rms = np.sqrt(np.mean(x[: n * hop].reshape(n, hop) ** 2, axis=1) + 1e-12)
    rms = uniform_filter1d(rms, size=3)
    times = np.arange(n) * hop_s
    peak = rms.max()
    return times, (rms / peak if peak > 0 else rms)


def detect_cues(path: str, track_location: str | None = None) -> list[CueCandidate]:
    """Detect intro / breakdown / drop cues for one track file (ffmpeg-decoded).

    Returns CueCandidates (confidence-scored, unsorted). The caller applies the
    confidence gate. ``track_location`` defaults to ``path``.
    """
    return detect_from_samples(decode_mono(path), SR, track_location or path)


def detect_from_samples(
    x: np.ndarray, sr: int, track_location: str
) -> list[CueCandidate]:
    """Core detection on an in-memory mono signal (no ffmpeg; unit-testable)."""
    loc = track_location
    dur = len(x) / sr
    env = onset_envelope(x)
    bpm = estimate_tempo(env)
    beats = _beat_grid(env, bpm, dur)
    times, e = energy_curve(x, sr)
    cues: list[CueCandidate] = []

    # INTRO — first beat where sound actually begins (energy crosses in).
    intro_t = _snap(0.0, beats)
    cues.append(CueCandidate(loc, "INTRO", "cue", intro_t, 1, 0.95))

    if len(e) < 6:
        return cues

    # BREAKDOWN — deepest sustained energy dip in the body of the track
    # (ignore the head/tail). Confidence = how far below the median it sits.
    body = slice(max(2, len(e) // 10), len(e) - len(e) // 10)
    med = float(np.median(e))
    idx = np.arange(len(e))[body]
    if len(idx):
        bd_local = int(idx[np.argmin(e[body])])
        depth = max(0.0, med - e[bd_local]) / (med + 1e-9)
        bd_t = _snap(float(times[bd_local]), beats)
        cues.append(CueCandidate(loc, "BREAKDOWN", "cue", bd_t, 2,
                                 float(np.clip(depth, 0, 1))))

        # DROP — the steepest energy surge AFTER the breakdown (the re-entry).
        post = e[bd_local:]
        if len(post) >= 3:
            jumps = post[2:] - post[:-2]            # rise over ~1s
            j = int(np.argmax(jumps))
            surge = max(0.0, float(jumps[j]))
            drop_idx = bd_local + j + 2
            drop_t = _snap(float(times[min(drop_idx, len(times) - 1)]), beats)
            cues.append(CueCandidate(loc, "DROP", "cue", drop_t, 3,
                                     float(np.clip(surge * 1.5, 0, 1))))
    return cues
