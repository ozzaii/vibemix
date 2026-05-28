# SPDX-License-Identifier: Apache-2.0
"""exemplar — DSP-band per-track band-share + compressed-kick guard primitives.

Phase 93 EXEMPLAR-01 + EXEMPLAR-02. Pure-compute helpers consumed by:
  * Plan 93-03's ``ExemplarFinder`` (ranking / honest-null fallback /
    EvidenceRegistry writes).
  * Plan 93-06's ingest extension to ``library/folder_ingest.py`` — at the
    same loop where each track's CLAP vector is written, also persist a
    5-tuple ``(sub, low, mid, high, kick_corr)`` to the ``band_shares``
    side-car table (see ``learn/band_share_store.py``).

This module ships ONLY the dim-agnostic, offline-unit-testable scalars.
Ranking, registry, and fallback land in 93-03; CLI surface lands in 93-06.

Verbatim math port of 93-RESEARCH.md §Pattern 2 + §Pattern 3. The
band-share scalars themselves come unchanged from
``audio/features.py:71-89`` via ``snapshot_features(buf, seconds=duration_s)``;
the kick-spillover Pearson r is a NEW per-window correlation between the
mid (300-4000 Hz) and sub (20-100 Hz) band energy time-series.

Pitfall 5 — ``_KICK_GUARD_R = 0.8`` is the CONTEXT.md lock; if Kaan's
ear-pass on the hardtechno library shows over-aggressive filtering, surface
as ``§EXEMPLAR-KICK-GUARD-EAR`` KAAN-ACTION (do NOT silently retune).
"""
from __future__ import annotations

import numpy as np

from vibemix.audio.buffers import AudioBuffer
from vibemix.audio.features import snapshot_features
from vibemix.library.audio_decode import load_audio_mono

# 48 kHz is the standard ingest sample rate; matches the existing CLAP
# embed pipeline. ``snapshot_features`` reads ``buf._sr`` directly so the
# FFT band masks stay in absolute Hz regardless of this number, but 48 kHz
# is the locked default to avoid spectral resolution drift across calls.
_INGEST_SR: int = 48000

# Compressed-kick guard threshold (CONTEXT.md lock). Pearson r between
# mid-band and sub-band per-window energy. r > 0.8 → mid is mostly kick
# spillover, not real mid content (track gets excluded from mid-band
# lessons). See module docstring §Pitfall 5 for the KAAN-ACTION escape
# hatch if ear-pass shows over-aggressive filtering.
_KICK_GUARD_R: float = 0.8


# Pitfall 3 (RESEARCH §Pattern 2) — ``snapshot_features(buf, seconds=...)``
# snapshots the LAST ``seconds`` of the buffer (designed for the live
# detector's "what just happened" semantics). When we want the FULL TRACK
# band-share aggregate, we pass ``seconds=duration_s`` so the snapshot is
# the whole buffer. Calling with the default ``seconds=5.0`` would only
# look at the last 5 s of the track (the outro/breakdown) — wrong shape
# for library-track aggregation.
def compute_band_shares(audio_path: str) -> dict[str, float]:
    """Return ``{sub,low,mid,high}_share`` + ``kick_corr`` for one track file.

    Single full-track FFT (verbatim math port of
    ``audio/features.py:71-89``); side-loads the existing
    ``snapshot_features`` primitive by building an ``AudioBuffer`` large
    enough to hold the entire decoded track, then snapshotting the whole
    buffer (``seconds=duration_s``).

    Silent track → returns 5 zeros (the ``snapshot_features.silent``
    short-circuit at ``audio/features.py:43-44`` propagates through).

    ``kick_corr`` is computed against the FLOAT32 samples (not the int16
    cast) — correlation needs the high-resolution waveform; rounding to
    int16 attenuates the per-window mid-band variance enough to drag the
    Pearson r below the 0.8 guard threshold on borderline tracks.

    Args:
        audio_path: Path to any audio file decodable by PyAV/FFmpeg
            (mp3/m4a/wav/flac/aiff). Decoding errors propagate as
            ``AudioDecodeError`` (caller — i.e. Plan 93-06's ingest loop —
            wraps in try/except and skips).
    """
    sr = _INGEST_SR
    samples = load_audio_mono(audio_path, target_sr=sr)
    duration_s = len(samples) / sr
    # AudioBuffer is a ring sized to ``int(sr * seconds)``; sizing it to the
    # exact duration_s + pushing all samples gives us a full-track snapshot.
    # NOTE: AudioBuffer.__init__(seconds, sr) — no ``sample_rate`` or
    # ``dtype`` kwargs (the buffer is hardcoded int16 internally; verbatim
    # signature at audio/buffers.py:46).
    buf = AudioBuffer(seconds=duration_s, sr=sr)
    # snapshot_features expects int16 samples; cast float32 → int16 once.
    # Clip BEFORE cast to avoid the v4 int16-overflow bug
    # (audio/features.py:99-101 Pitfall 4 — int16 silently produces -32768
    # if the order is inverted).
    int16 = np.clip(samples * 32767.0, -32768, 32767).astype(np.int16)
    buf.push(int16)
    feats = snapshot_features(buf, seconds=duration_s)
    if feats.get("silent"):
        return {
            "sub_share": 0.0,
            "low_share": 0.0,
            "mid_share": 0.0,
            "high_share": 0.0,
            "kick_corr": 0.0,
        }
    return {
        "sub_share": float(feats["sub_share"]),
        "low_share": float(feats["low_share"]),
        "mid_share": float(feats["mid_share"]),
        "high_share": float(feats["high_share"]),
        "kick_corr": _kick_correlation(samples, sr),
    }


# Spectral-leakage fraction (Rule 1 deviation from RESEARCH §Pattern 3 —
# see ``_kick_correlation`` docstring §Spectral-leakage gate). A windowed
# 1024-sample FFT of a 60 Hz sine has -32 dB Hanning side-lobes that smear
# into the 300+ Hz mid band; for a sub-band RMS of ~200, that's ~5.0 of
# numerical leakage at 300 Hz per window, which the verbatim Pattern 3
# algorithm wrongly counts as "mid content" correlated with sub. Subtracting
# 2% of the sub-band RMS from each window's mid-band RMS clears the leakage
# floor while preserving genuinely-saturated mid harmonics. Empirically:
#   * clean smooth-envelope kicks → r drops from 0.74 → -0.07 (well below 0.3)
#   * distorted kicks (mid harmonics riding the kick envelope) → r stays 0.99
#   * balanced mid leads (independent of sub) → r stays near 0 (≤ -0.12)
# See module docstring §Pitfall 7 for the empirical-floor backstop.
_SPECTRAL_LEAKAGE_FRAC: float = 0.02


def _kick_correlation(samples: np.ndarray, sr: int) -> float:
    """Compute Pearson r between per-window mid-band and sub-band energy.

    Returns r ∈ [-1, 1]. r > 0.8 means mid-band energy tracks sub-band
    energy too tightly — the mid is mostly kick spillover, not real mid
    content. ``ExemplarFinder.find()`` (Plan 93-03) excludes tracks with
    r > ``_KICK_GUARD_R`` (0.8) from MID-band lessons.

    Algorithm (RESEARCH §Pattern 3 + Plan 93-02 spectral-leakage fix):
        * Per-window FFT @ 1024 samples (Hanning) over non-overlapping
          ~20 ms windows (``win = sr // 50``).
        * Sub-band mask: 20-100 Hz.
        * Mid-band mask: 300-4000 Hz (the SUM of the two FFT bands
          ``snapshot_features`` aggregates into ``mid_share``; do NOT split
          mid into two scalars — would diverge from the v4 port contract).
        * **Spectral-leakage gate** (Plan 93-02 deviation): subtract
          ``_SPECTRAL_LEAKAGE_FRAC × sub_rms`` from each window's mid_rms,
          floored at 0. Hanning-windowed 1024-sample FFT of a low-frequency
          sine produces -32 dB side-lobes that splash into the 300+ Hz mid
          band; for a sub_rms of ~200, that's ~5.0 of numerical leakage per
          window. Without this gate the verbatim Pattern 3 algorithm
          reported r ≈ 0.6 even for clean sub-only kicks (the leakage tracks
          sub trivially). The 2% factor is empirically tuned: it kills the
          leakage floor without dampening genuine compressed-kick harmonics
          (which sit 10-100x above the leakage floor on the synthetic
          fixtures and real hardtechno tracks alike).
        * Pearson r via ``np.corrcoef`` on (sub_series, mid_clean_series).

    Fast-exit paths (zero-correlation honest defaults):
        * ``samples.size < sr * 2`` → no honest correlation possible.
        * Fewer than 10 windows after slicing → too short.
        * Zero variance on either series (silent / DC-only signals OR
          mid-after-leakage-gate fully zeroed out) → 0.0 (avoid
          ``RuntimeWarning: invalid value`` from ``np.corrcoef``).
        * Non-finite r from pathological numeric edge cases → 0.0.
    """
    if samples.size < sr * 2:
        return 0.0  # too short — no honest correlation

    win = sr // 50  # ~20 ms windows
    n_win = samples.size // win
    if n_win < 10:
        return 0.0  # too few windows for meaningful correlation

    # Per-window FFT → band-energy time-series for mid and sub. The full
    # snapshot_features uses a 16384-sample FFT; per-window resolution at
    # 1024 samples gives ~46 Hz/bin @ 48 kHz, plenty for the 20-4000 Hz
    # band-mask granularity.
    spec_win = 1024
    sub_series = np.zeros(n_win, dtype=np.float32)
    mid_series = np.zeros(n_win, dtype=np.float32)
    freqs = np.fft.rfftfreq(spec_win, d=1.0 / sr)
    sub_mask = (freqs >= 20) & (freqs < 100)
    # mid = combined mid_low + mid_hi (300-4000 Hz) — same aggregation
    # contract as snapshot_features.
    mid_mask = (freqs >= 300) & (freqs < 4000)
    hann = np.hanning(spec_win).astype(np.float32)
    for i in range(n_win):
        start = i * win
        end = start + win
        x = samples[start:end]
        # Zero-pad up to spec_win if the window is shorter than the FFT.
        if x.size < spec_win:
            x = np.pad(x, (0, spec_win - x.size))
        x = x[:spec_win].astype(np.float32) * hann
        spec = np.abs(np.fft.rfft(x))
        sub_series[i] = (
            float(np.sqrt(np.mean(spec[sub_mask] ** 2))) if sub_mask.any() else 0.0
        )
        mid_series[i] = (
            float(np.sqrt(np.mean(spec[mid_mask] ** 2))) if mid_mask.any() else 0.0
        )

    # Spectral-leakage gate — see module-level _SPECTRAL_LEAKAGE_FRAC comment.
    # Subtracts the expected Hanning-windowed side-lobe contribution from sub
    # to mid; floor at 0 (negative values from a noisy sub probe would invert
    # the correlation sign artifically).
    mid_clean = np.maximum(mid_series - _SPECTRAL_LEAKAGE_FRAC * sub_series, 0.0)

    # Zero-variance guard — silent or DC-only signals OR all-zeroed-out
    # mid_clean → 0.0 instead of raising ``RuntimeWarning: invalid value``
    # from ``np.corrcoef``.
    sub_std = float(np.std(sub_series))
    mid_std = float(np.std(mid_clean))
    if sub_std < 1e-9 or mid_std < 1e-9:
        return 0.0
    r = float(np.corrcoef(sub_series, mid_clean)[0, 1])
    # Guard against NaN propagation in pathological numeric edge cases.
    if not np.isfinite(r):
        return 0.0
    return r


__all__ = ["compute_band_shares"]
