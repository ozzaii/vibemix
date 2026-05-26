# SPDX-License-Identifier: Apache-2.0
"""Perceived-dancefloor-energy scoring — ``score_energy(path) -> EnergyScore``.

A 0-100 score for "how hard does this track hit the floor" — NOT loudness. The
whole design intent is GENRE ROBUSTNESS: a quiet hypnotic after-hours roller
must not read low just because it's quiet, and a loud-but-sparse intro pad must
not read high just because it's loud. We get there by:

  * weighting SPECTRAL FLUX (frame-to-frame spectral motion = drive) the
    heaviest, and keeping loudness a modest contributor;
  * using SHARES / RATES (sub-bass share, onset rate, coefficient of variation)
    instead of absolute levels wherever possible, so level cancels out;
  * normalising the flux feature by per-frame magnitude so a louder copy of the
    same signal yields the same flux;
  * aggregating over BUSY frames only (RMS > a fraction of track peak) so a
    silent intro/outro can't drag the score toward zero.

Each of the 7 features is mapped to [0,1] through a FIXED perceptual window
(``np.clip``), never a corpus min-max — that keeps the score reproducible
run-to-run and stops one loud track from re-scaling the whole library. The
weights + windows live in ``vibemix.audio.constants`` (one-line-edit ethos).

Zero new dependencies. DSP is hand-rolled numpy/scipy. We REUSE the existing
primitives — ``cue_detect.decode_to_mono`` (ffmpeg offline decode),
``state.genre.crest_factor.crest_factor`` (peak/RMS), and
``state.detectors._dsp.sub_share`` (20-100Hz energy fraction) — rather than
re-implement them.

Anti-hallucination / honest-null: undecodable, empty, or all-silent audio
returns ``None`` — never a raise, never a fabricated 0.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from vibemix.audio.constants import (
    ENERGY_BEAT_REGULARITY_WINDOW,
    ENERGY_BRIGHTNESS_WINDOW,
    ENERGY_BUSY_RMS_FRAC,
    ENERGY_DYNAMIC_RANGE_WINDOW,
    ENERGY_EXCERPT_SECONDS,
    ENERGY_FLUX_FFT,
    ENERGY_FLUX_HOP,
    ENERGY_FLUX_WINDOW,
    ENERGY_LOUDNESS_WINDOW,
    ENERGY_ONSET_WINDOW,
    ENERGY_RMS_FRAME_S,
    ENERGY_SUB_SHARE_WINDOW,
    ENERGY_WEIGHTS,
)
from vibemix.library.cue_detect import decode_to_mono
from vibemix.state.detectors._dsp import sub_share

# Crest factor (peak/RMS) is used to *correct* the loudness feature: a squashed,
# loudness-war master and a dynamic one at the same perceived level should land
# together rather than the compressed one always reading hotter. ~3-5 is the
# normal compressed-dance-master band — we treat that as the neutral reference.
from vibemix.state.genre.crest_factor import crest_factor

__all__ = ["EnergyScore", "score_energy", "spectral_flux"]


@dataclass(frozen=True, slots=True)
class EnergyScore:
    """A perceived-dancefloor-energy verdict.

    Attributes:
        score: 0-100, rounded. Higher = hits the floor harder.
        breakdown: per-feature normalised values in [0,1] (the same keys as
            ``ENERGY_WEIGHTS``) — exposed for transparency and test pinning.
    """

    score: float
    breakdown: dict[str, float]


# ─── normalisation helper ─────────────────────────────────────────────────────


def _norm(value: float, window: tuple[float, float]) -> float:
    """Map ``value`` to [0,1] through a fixed (lo, hi) perceptual window.

    Linear between the edges, clamped outside. A FIXED window (not a fitted
    min-max) is what makes the score reproducible — see module docstring.
    """
    lo, hi = window
    if hi <= lo:
        return 0.0
    return float(np.clip((value - lo) / (hi - lo), 0.0, 1.0))


# ─── spectral flux (the heaviest-weighted feature) ────────────────────────────


def spectral_flux(
    samples: np.ndarray,
    sample_rate: int = 16000,
    *,
    n_fft: int = ENERGY_FLUX_FFT,
    hop: int = ENERGY_FLUX_HOP,
) -> float:
    """Mean magnitude-normalised spectral flux over the signal.

    Spectral flux = how much the magnitude spectrum *moves* frame-to-frame. For
    each successive pair of rfft magnitude frames we take the half-wave-rectified
    positive differences (energy ARRIVING — onsets, churn — not energy leaving),
    sum over bins, and normalise by the frame's total magnitude so the result is
    LEVEL-INVARIANT (a louder copy of the same signal yields the same flux). The
    per-frame fluxes are averaged.

    Returns 0.0 on empty / all-silent input (no spectrum to move) — honest-null,
    never a fabricated motion value.
    """
    if samples is None or samples.size < n_fft + hop:
        # Not enough samples for two overlapping frames → no measurable motion.
        if samples is None or samples.size == 0:
            return 0.0
        # Tiny-but-nonempty: fall back to a single-step compare if possible.
        if samples.size < n_fft:
            return 0.0

    window = np.hanning(n_fft).astype(np.float32)
    n_frames = 1 + (samples.size - n_fft) // hop
    if n_frames < 2:
        return 0.0

    prev_mag: np.ndarray | None = None
    flux_sum = 0.0
    counted = 0
    for i in range(n_frames):
        start = i * hop
        frame = samples[start : start + n_fft]
        if frame.size < n_fft:  # ragged tail guard
            break
        mag = np.abs(np.fft.rfft(frame * window))
        if prev_mag is not None:
            diff = mag - prev_mag
            diff = np.clip(diff, a_min=0.0, a_max=None)  # half-wave rectify
            total = float(mag.sum())
            if total > 0.0:
                # Normalise by current-frame magnitude → level-invariant flux.
                flux_sum += float(diff.sum()) / total
                counted += 1
        prev_mag = mag

    if counted == 0:
        return 0.0
    return flux_sum / counted


# ─── per-frame RMS curve + busy-frame mask ────────────────────────────────────


def _rms_curve(samples: np.ndarray, sample_rate: int, frame_s: float) -> np.ndarray:
    """Per-frame RMS over ``frame_s``-second non-overlapping windows."""
    win = max(1, int(frame_s * sample_rate))
    n = samples.size // win
    if n <= 0:
        return np.zeros(0, dtype=np.float32)
    framed = samples[: n * win].reshape(n, win)
    return np.sqrt(np.mean(framed * framed, axis=1)).astype(np.float32)


def _busy_excerpt(samples: np.ndarray, sample_rate: int) -> np.ndarray | None:
    """Centred ~80s excerpt (or whole track if shorter), with leading/trailing
    dead air trimmed to the first/last BUSY frame. Returns ``None`` when no
    frame is busy (all silence) — the honest-null trigger upstream.
    """
    max_n = int(ENERGY_EXCERPT_SECONDS * sample_rate)
    if samples.size > max_n:
        start = (samples.size - max_n) // 2
        samples = samples[start : start + max_n]

    rms = _rms_curve(samples, sample_rate, ENERGY_RMS_FRAME_S)
    if rms.size == 0:
        return None
    peak = float(rms.max())
    if peak <= 0.0:
        return None
    busy = rms > (ENERGY_BUSY_RMS_FRAC * peak)
    if not busy.any():
        return None
    win = max(1, int(ENERGY_RMS_FRAME_S * sample_rate))
    first = int(np.argmax(busy))
    last = busy.size - int(np.argmax(busy[::-1]))  # one-past-last busy frame
    return samples[first * win : last * win]


# ─── feature extraction over the busy excerpt ─────────────────────────────────


def _brightness(samples: np.ndarray, sample_rate: int) -> float:
    """Spectral centroid (Hz) = sum(freq*|S|)/sum(|S|) over a Hanning rfft."""
    n_fft = min(ENERGY_FLUX_FFT, samples.size)
    if n_fft < 2:
        return 0.0
    x = samples[:n_fft] * np.hanning(n_fft)
    mag = np.abs(np.fft.rfft(x))
    freqs = np.fft.rfftfreq(n_fft, d=1.0 / sample_rate)
    total = float(mag.sum())
    if total <= 0.0:
        return 0.0
    return float((freqs * mag).sum() / total)


def _onset_rate(samples: np.ndarray, sample_rate: int) -> float:
    """Onsets per second over a FINE (~20ms) RMS-delta envelope.

    Mirrors the ``snapshot_features`` onset heuristic verbatim (sr//50 windows,
    adaptive ``mean+std`` threshold on half-wave-rectified energy deltas). The
    fine window matters: a 0.25s frame averages a kick away, so onset density
    must be measured on a window short enough to resolve individual transients.
    """
    win = max(1, sample_rate // 50)  # ~20ms
    if samples.size <= win * 4:
        return 0.0
    energies = np.array(
        [
            float(np.sqrt(np.mean(samples[i : i + win] ** 2)))
            for i in range(0, samples.size - win, win)
        ]
    )
    deltas = np.diff(energies).clip(min=0)
    # Adaptive threshold (mean+std) catches real transients, BUT a pure
    # sustained tone has tiny incomplete-cycle RMS jitter that the adaptive
    # floor would chase down to — fabricating onsets on a static pad. Guard
    # with a RELATIVE floor: a delta only counts if it's also a meaningful
    # fraction of the median frame energy. A kick onset is a large fraction of
    # its own level; sustained-tone jitter is a tiny fraction. This is the
    # genre-robustness guard that keeps a loud static pad reading sparse.
    median_energy = float(np.median(energies))
    rel_floor = 0.10 * median_energy  # 10% of typical level = a real transient
    thr = max(0.005, float(deltas.mean() + deltas.std()), rel_floor)
    n_onsets = int(np.sum(deltas > thr))
    duration = samples.size / sample_rate
    if duration <= 0.0:
        return 0.0
    return n_onsets / duration


def _beat_regularity(rms: np.ndarray) -> float:
    """Autocorrelation peak prominence (z-score) of the RMS envelope.

    A steady 4/4 produces a sharp autocorr peak at the beat lag standing well
    above the surrounding noise floor; an arrhythmic / beatless signal does not.
    Returns the peak-vs-(mean+std) z-score, clamped at 0 — fed through the fixed
    perceptual window upstream.
    """
    if rms.size < 8:
        return 0.0
    env = rms - rms.mean()
    if not np.any(env):
        return 0.0
    ac = np.correlate(env, env, mode="full")
    ac = ac[ac.size // 2 :]
    if ac.size < 4 or ac[0] <= 0:
        return 0.0
    # Skip lag 0 (always the global max) — look at the periodic structure.
    tail = ac[1:]
    mean = float(tail.mean())
    std = float(tail.std()) or 1e-9
    prominence = (float(tail.max()) - mean) / std
    return max(0.0, prominence)


def _coeff_of_variation(rms: np.ndarray) -> float:
    """std/mean of the busy-frame RMS curve — the dynamic-range proxy."""
    if rms.size == 0:
        return 0.0
    mean = float(rms.mean())
    if mean <= 0.0:
        return 0.0
    return float(rms.std()) / mean


def _loudness_dbfs(rms: np.ndarray, samples: np.ndarray) -> float:
    """P80 of per-frame RMS, crest-corrected, in dBFS.

    P80 (not max) ignores the single hottest transient. Crest correction nudges
    a compressed master DOWN toward a dynamic one of the same perceived level so
    loudness-war squashing doesn't masquerade as energy: we divide the linear
    P80 by ``crest / reference_crest`` (reference = 4.0, mid of the normal
    compressed-dance band). Clamped to avoid amplifying near-silent input.
    """
    if rms.size == 0:
        return ENERGY_LOUDNESS_WINDOW[0]
    p80 = float(np.percentile(rms, 80))
    if p80 <= 0.0:
        return ENERGY_LOUDNESS_WINDOW[0]
    # crest_factor wants int16 magnitudes; samples are float [-1,1].
    cf = crest_factor((samples * 32767.0).astype(np.int16))
    if cf > 0.0:
        # Reference crest = 4.0 (mid of the 3-5 compressed-master band). A more
        # compressed master (lower crest) reads slightly quieter; a dynamic one
        # (higher crest) reads slightly louder — pulling them toward parity.
        p80 = p80 * (cf / 4.0)
    p80 = min(p80, 1.0)
    return 20.0 * np.log10(max(p80, 1e-6))


# ─── core scorer (operates on a decoded array) ────────────────────────────────


def _score_array(samples: np.ndarray, sample_rate: int) -> EnergyScore | None:
    """Score an already-decoded mono float32 array in [-1,1]. Returns None on
    empty / all-silent input (no busy frames)."""
    if samples is None or samples.size == 0:
        return None
    if samples.dtype != np.float32:
        samples = samples.astype(np.float32)

    excerpt = _busy_excerpt(samples, sample_rate)
    if excerpt is None or excerpt.size == 0:
        return None

    busy_rms = _rms_curve(excerpt, sample_rate, ENERGY_RMS_FRAME_S)
    if busy_rms.size == 0:
        return None

    raw_loudness_db = _loudness_dbfs(busy_rms, excerpt)
    raw_sub = sub_share(excerpt, sample_rate, sub_hz_max=100.0)
    raw_onset = _onset_rate(excerpt, sample_rate)
    raw_flux = spectral_flux(excerpt, sample_rate)
    raw_brightness = _brightness(excerpt, sample_rate)
    raw_regularity = _beat_regularity(busy_rms)
    raw_cov = _coeff_of_variation(busy_rms)

    breakdown = {
        "loudness": _norm(raw_loudness_db, ENERGY_LOUDNESS_WINDOW),
        "sub_share": _norm(raw_sub, ENERGY_SUB_SHARE_WINDOW),
        "onset_rate": _norm(raw_onset, ENERGY_ONSET_WINDOW),
        "spectral_flux": _norm(raw_flux, ENERGY_FLUX_WINDOW),
        "brightness": _norm(raw_brightness, ENERGY_BRIGHTNESS_WINDOW),
        "beat_regularity": _norm(raw_regularity, ENERGY_BEAT_REGULARITY_WINDOW),
        "dynamic_range": _norm(raw_cov, ENERGY_DYNAMIC_RANGE_WINDOW),
    }

    score = sum(ENERGY_WEIGHTS[k] * breakdown[k] for k in ENERGY_WEIGHTS) * 100.0
    score = float(round(min(100.0, max(0.0, score))))
    return EnergyScore(score=score, breakdown=breakdown)


# ─── public entrypoint ────────────────────────────────────────────────────────


def score_energy(audio_path: str, *, sample_rate: int = 16000) -> EnergyScore | None:
    """Score a track's perceived dancefloor energy from its file path.

    Decodes ``audio_path`` to mono via ffmpeg (``cue_detect.decode_to_mono``),
    then scores a centred ~80s busy excerpt. Returns ``None`` on any
    undecodable / empty / all-silent input — honest-null, never a raise.
    """
    try:
        samples = decode_to_mono(Path(audio_path), sample_rate)
    except Exception:
        # Corrupt file, missing ffmpeg, timeout — all collapse to honest-null.
        return None
    if samples is None or getattr(samples, "size", 0) == 0:
        return None
    return _score_array(samples, sample_rate)
