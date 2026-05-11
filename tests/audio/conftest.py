# SPDX-License-Identifier: Apache-2.0
"""Shared helpers for tests/audio/.

`int16_sine` is a plain function (NOT a fixture) — call it directly from test
bodies when you need a deterministic int16 sine for buffer / level / feature
testing. Plain function (vs @pytest.fixture) keeps tests readable: you pass the
shape arguments at the call site, no fixture-name ambiguity.
"""

from __future__ import annotations

import numpy as np


def int16_sine(
    freq_hz: float,
    duration_sec: float,
    sample_rate: int = 16000,
    amplitude: float = 0.5,
) -> np.ndarray:
    """Synthesize a known-RMS int16 sine wave.

    `amplitude` is in float-domain (0..1); the result is scaled to int16. For a
    pure sine the RMS is `amplitude / sqrt(2)` in float-domain or
    `amplitude * 32768 / sqrt(2)` in int16-domain — handy when asserting EMA
    behavior in Levels tests.
    """
    n = int(sample_rate * duration_sec)
    t = np.arange(n, dtype=np.float32) / sample_rate
    samples_f = amplitude * np.sin(2.0 * np.pi * freq_hz * t)
    return (samples_f * 32767.0).astype(np.int16)
