# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import numpy as np

from vibemix.library.key_estimator import KEY_CONF_FLOOR, estimate_key_from_audio

SR = 22_050


def _synth(parts: list[tuple[float, float]], *, seconds: float = 3.0) -> np.ndarray:
    t = np.arange(int(SR * seconds), dtype=np.float64) / SR
    out = np.zeros_like(t)
    total_weight = sum(weight for _freq, weight in parts)
    for freq, weight in parts:
        out += weight * np.sin(2.0 * np.pi * freq * t)
    return (out / max(total_weight, 1e-9)).astype(np.float32)


def test_estimates_tonic_weighted_c_major() -> None:
    # Equal C/E/G is legitimately close to A-minor. Tonic + scale context
    # should clear the confidence floor and resolve C major -> 8B.
    audio = _synth(
        [
            (261.63, 1.5),
            (293.66, 0.4),
            (329.63, 1.0),
            (349.23, 0.4),
            (392.00, 1.0),
            (440.00, 0.4),
            (493.88, 0.4),
            (523.25, 1.0),
        ]
    )

    estimate = estimate_key_from_audio(audio, sr=SR)

    assert estimate is not None
    assert estimate.musical == "C"
    assert estimate.camelot == "8B"
    assert estimate.confidence >= KEY_CONF_FLOOR


def test_estimates_a_minor() -> None:
    audio = _synth(
        [
            (110.00, 1.4),
            (220.00, 1.0),
            (261.63, 0.8),
            (329.63, 0.9),
            (440.00, 0.7),
        ]
    )

    estimate = estimate_key_from_audio(audio, sr=SR)

    assert estimate is not None
    assert estimate.musical == "Am"
    assert estimate.camelot == "8A"


def test_equal_relative_triad_abstains_instead_of_overclaiming() -> None:
    audio = _synth([(261.63, 1.0), (329.63, 1.0), (392.00, 1.0)])

    assert estimate_key_from_audio(audio, sr=SR) is None


def test_white_noise_abstains() -> None:
    rng = np.random.default_rng(0)
    noise = rng.normal(0.0, 1.0, SR * 4).astype(np.float32)

    assert estimate_key_from_audio(noise, sr=SR) is None


def test_silence_abstains() -> None:
    assert estimate_key_from_audio(np.zeros(SR, dtype=np.float32), sr=SR) is None

