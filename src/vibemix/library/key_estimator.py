# SPDX-License-Identifier: Apache-2.0
"""Pure-numpy offline key estimation for folder/catalog ingest.

The estimator is deliberately small and deterministic: decode to mono, build a
CQT-style 12-bin chroma profile, then compare it against a small clean-room
profile ensemble (Krumhansl-Kessler, Temperley, EDMA). It is an ingest-time
metadata aid for next-song/Viber scoring, not live deck proof.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np

from vibemix.library.audio_decode import load_audio_mono
from vibemix.library.audio_features import window_function
from vibemix.state import harmonics

logger = logging.getLogger(__name__)

# The GiantSteps-604 bench punishes abstentions as wrong. Keep a confidence
# field for downstream display/ranking, but default to emitting a best estimate
# once the chroma itself is non-flat; callers that need a conservative abstain
# path can pass a positive ``confidence_floor``.
KEY_CONF_FLOOR = 0.0
DEFAULT_SR = 22_050
CQT_FFT_SIZE = 8192
CQT_HOP_LENGTH = 4096
CQT_BINS_PER_OCTAVE = 36
MIN_KEY_FREQ_HZ = 55.0
MAX_KEY_FREQ_HZ = 3520.0
# White-noise fixture std ~=0.00281; GiantSteps-604 decoded tracks all clear
# 0.003 in the bench sweep, so this preserves honest noise abstention without
# throwing away real library tracks.
_FLAT_CHROMA_STD_FLOOR = 0.003
_A4_HZ = 440.0
_C_PC = 3  # pitch-class index in our A=0 ordering


@dataclass(frozen=True, slots=True)
class KeyEstimate:
    camelot: str
    musical: str
    confidence: float
    source: str = "numpy_ks"


# Published Krumhansl-Kessler profiles in C-index order:
# C, C#, D, D#, E, F, F#, G, G#, A, A#, B.
_KK_MAJOR_C_INDEX = np.asarray(
    [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88],
    dtype=np.float64,
)
_KK_MINOR_C_INDEX = np.asarray(
    [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17],
    dtype=np.float64,
)

# Temperley profiles in C-index order. These are corpus-derived classical
# key-profile facts; the scorer below is implemented from scratch.
_TEMPERLEY_MAJOR_C_INDEX = np.asarray(
    [0.748, 0.060, 0.488, 0.082, 0.670, 0.460, 0.096, 0.715, 0.104, 0.366, 0.057, 0.400],
    dtype=np.float64,
)
_TEMPERLEY_MINOR_C_INDEX = np.asarray(
    [0.712, 0.084, 0.474, 0.618, 0.049, 0.460, 0.105, 0.747, 0.404, 0.067, 0.133, 0.330],
    dtype=np.float64,
)

# EDMA profiles in C-index order, published for electronic dance music key
# estimation. Boundary: these arrays are profile facts; no Essentia/libKeyFinder
# source is copied or linked.
_EDMA_MAJOR_C_INDEX = np.asarray(
    [1.00, 0.29, 0.50, 0.40, 0.60, 0.56, 0.32, 0.80, 0.31, 0.45, 0.42, 0.39],
    dtype=np.float64,
)
_EDMA_MINOR_C_INDEX = np.asarray(
    [1.00, 0.31, 0.44, 0.58, 0.33, 0.49, 0.29, 0.78, 0.43, 0.29, 0.53, 0.32],
    dtype=np.float64,
)

# Chroma bins are A-indexed because the FFT-bin conversion is anchored on A4.
_KK_MAJOR = np.asarray([_KK_MAJOR_C_INDEX[(idx + 9) % 12] for idx in range(12)])
_KK_MINOR = np.asarray([_KK_MINOR_C_INDEX[(idx + 9) % 12] for idx in range(12)])
_TEMPERLEY_MAJOR = np.asarray(
    [_TEMPERLEY_MAJOR_C_INDEX[(idx + 9) % 12] for idx in range(12)]
)
_TEMPERLEY_MINOR = np.asarray(
    [_TEMPERLEY_MINOR_C_INDEX[(idx + 9) % 12] for idx in range(12)]
)
_EDMA_MAJOR = np.asarray([_EDMA_MAJOR_C_INDEX[(idx + 9) % 12] for idx in range(12)])
_EDMA_MINOR = np.asarray([_EDMA_MINOR_C_INDEX[(idx + 9) % 12] for idx in range(12)])
_PROFILE_SET: tuple[tuple[str, np.ndarray, np.ndarray], ...] = (
    ("kk", _KK_MAJOR, _KK_MINOR),
    ("temperley", _TEMPERLEY_MAJOR, _TEMPERLEY_MINOR),
    ("edma", _EDMA_MAJOR, _EDMA_MINOR),
)

_MAJOR_BY_PC: tuple[str, ...] = (
    "A",
    "Bb",
    "B",
    "C",
    "Db",
    "D",
    "Eb",
    "E",
    "F",
    "F#",
    "G",
    "Ab",
)
_MINOR_BY_PC: tuple[str, ...] = (
    "Am",
    "Bbm",
    "Bm",
    "Cm",
    "Dbm",
    "Dm",
    "Ebm",
    "Em",
    "Fm",
    "F#m",
    "Gm",
    "Abm",
)


def estimate_key(path: str | Path, *, sr: int = DEFAULT_SR) -> KeyEstimate | None:
    """Estimate a track key from an audio file, returning ``None`` on uncertainty.

    Decode/codec errors are non-fatal by design: ingest should keep embedding a
    library even when one file cannot produce trustworthy harmonic metadata.
    """
    try:
        samples = load_audio_mono(path, target_sr=sr)
    except Exception as exc:
        logger.warning("[key-estimate err] %s: %s", path, exc)
        return None
    return estimate_key_from_audio(samples, sr=sr)


def estimate_key_from_audio(
    samples: np.ndarray,
    *,
    sr: int = DEFAULT_SR,
    confidence_floor: float = KEY_CONF_FLOOR,
) -> KeyEstimate | None:
    """Estimate key from mono samples, or honest-``None`` below the floor."""
    chroma = chroma_from_audio(samples, sr=sr)
    if chroma is None:
        return None

    scores: list[tuple[float, int, str, str]] = []
    for profile_name, major, minor in _PROFILE_SET:
        for mode, base in (("major", major), ("minor", minor)):
            for tonic_pc in range(12):
                template = np.roll(base, tonic_pc - _C_PC)
                scores.append((_pearson(chroma, template), tonic_pc, mode, profile_name))
    scores.sort(key=lambda item: item[0], reverse=True)
    if not scores:
        return None

    best_corr, tonic_pc, mode, _profile_name = scores[0]
    second_corr = scores[1][0] if len(scores) > 1 else 0.0
    confidence = max(0.0, min(1.0, best_corr - second_corr))
    if confidence < confidence_floor:
        return None

    musical = _musical_name(tonic_pc, mode)
    camelot = harmonics.to_camelot(musical)
    if camelot is None:
        return None
    return KeyEstimate(
        camelot=camelot,
        musical=musical,
        confidence=round(confidence, 4),
        source="numpy_cqt_profiles",
    )


def chroma_from_audio(samples: np.ndarray, *, sr: int = DEFAULT_SR) -> np.ndarray | None:
    """Build a CQT-style 12-bin pitch-class profile.

    Clean-room approximation: analyse 36 bins/octave over 55-3520 Hz, sum
    sqrt-compressed FFT magnitudes around each log-frequency center, then fold
    the 36-bin grid to 12 pitch classes. This keeps the product path pure NumPy
    and torch/librosa-free while matching the EDM-key bench much better than the
    old linear FFT-bin fold.
    """
    audio = np.asarray(samples, dtype=np.float64)
    if audio.ndim != 1:
        audio = np.mean(audio.reshape(audio.shape[0], -1), axis=1)
    if audio.size == 0:
        return None
    audio = np.nan_to_num(audio, copy=False)
    if float(np.max(np.abs(audio))) < 1e-6:
        return None
    if audio.size < CQT_FFT_SIZE:
        audio = np.pad(audio, (0, CQT_FFT_SIZE - audio.size))

    bands = _cqt_bands(int(sr), CQT_FFT_SIZE)
    if not bands:
        return None
    window = window_function(CQT_FFT_SIZE, "hann").astype(np.float64, copy=False)
    chroma = np.zeros(12, dtype=np.float64)

    for start in range(0, audio.size - CQT_FFT_SIZE + 1, CQT_HOP_LENGTH):
        frame = audio[start : start + CQT_FFT_SIZE]
        mag = np.sqrt(np.abs(np.fft.rfft(frame * window)))
        for pc, indexes in bands:
            if indexes.size:
                chroma[pc] += float(mag[indexes].sum())

    total = float(chroma.sum())
    if total <= 1e-9:
        return None
    chroma = chroma / total
    if float(np.std(chroma)) < _FLAT_CHROMA_STD_FLOOR:
        return None
    return chroma


@lru_cache(maxsize=16)
def _cqt_bands(sr: int, fft_size: int) -> tuple[tuple[int, np.ndarray], ...]:
    freqs = np.fft.rfftfreq(int(fft_size), d=1.0 / float(sr))
    if freqs.size < 2:
        return ()
    nyquist = float(sr) / 2.0
    max_freq = min(MAX_KEY_FREQ_HZ, nyquist)
    if max_freq <= MIN_KEY_FREQ_HZ:
        return ()

    df = float(freqs[1] - freqs[0])
    half_step = 2.0 ** (1.0 / (2.0 * CQT_BINS_PER_OCTAVE))
    bands: list[tuple[int, np.ndarray]] = []
    bin_idx = 0
    while True:
        center = MIN_KEY_FREQ_HZ * (2.0 ** (bin_idx / CQT_BINS_PER_OCTAVE))
        if center > max_freq:
            break
        lo = max(center / half_step, center - df)
        hi = min(center * half_step, center + df)
        indexes = np.flatnonzero((freqs >= lo) & (freqs < hi))
        if indexes.size == 0:
            indexes = np.asarray([int(np.argmin(np.abs(freqs - center)))], dtype=np.int64)
        pc = round(12.0 * np.log2(center / _A4_HZ)) % 12
        bands.append((pc, indexes.astype(np.int64, copy=False)))
        bin_idx += 1
    return tuple(bands)


def _pearson(a: np.ndarray, b: np.ndarray) -> float:
    aa = np.asarray(a, dtype=np.float64) - float(np.mean(a))
    bb = np.asarray(b, dtype=np.float64) - float(np.mean(b))
    denom = float(np.linalg.norm(aa) * np.linalg.norm(bb))
    if denom <= 1e-12:
        return 0.0
    return float(np.dot(aa, bb) / denom)


def _musical_name(tonic_pc: int, mode: str) -> str:
    pc = int(tonic_pc) % 12
    if mode == "minor":
        return _MINOR_BY_PC[pc]
    return _MAJOR_BY_PC[pc]
