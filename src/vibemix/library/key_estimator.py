# SPDX-License-Identifier: Apache-2.0
"""Pure-numpy offline key estimation for folder/catalog ingest.

The estimator is deliberately small and deterministic: decode to mono, fold an
FFT magnitude spectrogram into 12 pitch classes, then compare the chroma profile
against the Krumhansl-Kessler major/minor templates. It is an ingest-time
metadata aid for next-song/Viber scoring, not live deck proof.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from vibemix.library.audio_decode import load_audio_mono
from vibemix.library.audio_features import window_function
from vibemix.state import harmonics

logger = logging.getLogger(__name__)

KEY_CONF_FLOOR = 0.12
DEFAULT_SR = 22_050
FFT_SIZE = 4096
HOP_LENGTH = 2048
MIN_KEY_FREQ_HZ = 55.0
MAX_KEY_FREQ_HZ = 5000.0
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

# Chroma bins are A-indexed because the FFT-bin conversion is anchored on A4.
_KK_MAJOR = np.asarray([_KK_MAJOR_C_INDEX[(idx + 9) % 12] for idx in range(12)])
_KK_MINOR = np.asarray([_KK_MINOR_C_INDEX[(idx + 9) % 12] for idx in range(12)])

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

    scores: list[tuple[float, int, str]] = []
    for mode, base in (("major", _KK_MAJOR), ("minor", _KK_MINOR)):
        for tonic_pc in range(12):
            template = np.roll(base, tonic_pc - _C_PC)
            scores.append((_pearson(chroma, template), tonic_pc, mode))
    scores.sort(key=lambda item: item[0], reverse=True)
    if not scores:
        return None

    best_corr, tonic_pc, mode = scores[0]
    best_other_mode = max((score for score, _pc, m in scores if m != mode), default=0.0)
    confidence = max(0.0, min(1.0, best_corr - best_other_mode))
    if confidence < confidence_floor:
        return None

    musical = _musical_name(tonic_pc, mode)
    camelot = harmonics.to_camelot(musical)
    if camelot is None:
        return None
    return KeyEstimate(camelot=camelot, musical=musical, confidence=round(confidence, 4))


def chroma_from_audio(samples: np.ndarray, *, sr: int = DEFAULT_SR) -> np.ndarray | None:
    """Fold FFT-bin magnitudes into a 12-bin pitch-class profile."""
    audio = np.asarray(samples, dtype=np.float64)
    if audio.ndim != 1:
        audio = np.mean(audio.reshape(audio.shape[0], -1), axis=1)
    if audio.size == 0:
        return None
    audio = np.nan_to_num(audio, copy=False)
    if float(np.max(np.abs(audio))) < 1e-6:
        return None
    if audio.size < FFT_SIZE:
        audio = np.pad(audio, (0, FFT_SIZE - audio.size))

    freqs = np.fft.rfftfreq(FFT_SIZE, d=1.0 / float(sr))
    freq_mask = (freqs >= MIN_KEY_FREQ_HZ) & (freqs <= min(MAX_KEY_FREQ_HZ, sr / 2.0))
    if not np.any(freq_mask):
        return None
    pcs = np.rint(12.0 * np.log2(freqs[freq_mask] / _A4_HZ)).astype(np.int16) % 12
    window = window_function(FFT_SIZE, "hann").astype(np.float64, copy=False)
    chroma = np.zeros(12, dtype=np.float64)

    for start in range(0, audio.size - FFT_SIZE + 1, HOP_LENGTH):
        frame = audio[start : start + FFT_SIZE]
        mag = np.abs(np.fft.rfft(frame * window))[freq_mask]
        if mag.size:
            np.add.at(chroma, pcs, mag)

    total = float(chroma.sum())
    if total <= 1e-9:
        return None
    return chroma / total


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

