# SPDX-License-Identifier: Apache-2.0
"""crest_factor + EmaSmoother — Phase 6 Wave 2.

Crest factor (peak / RMS) flags compressed vs dynamic masters:
- ~1.4 (≈ √2) — pure sine wave
- ~1.0 — square wave / steady-state tone
- 3-5 — heavily compressed dance master (loudness war)
- 8-15 — dynamic acoustic/jazz master
- >20 — impulse / very sparse content

Math (06-CONTEXT.md §Crest Factor Detection):

    peak = max(abs(pcm))
    rms  = sqrt(mean(pcm**2))
    crest = peak / rms

Inputs are int16 magnitudes from ``AudioBuffer.snapshot``. The squared-sum is
cast to float64 to avoid int16 overflow when accumulating across thousands of
samples (Phase 2 Pitfall echo).

EmaSmoother cross-snapshot smoothing (alpha=0.3) — wave 3 ``state_refresh_loop``
holds one instance per session, calls ``update(raw_crest)`` each tick. The
first call passes the value through unchanged (no synthetic warm-up bias).
"""

from __future__ import annotations

import numpy as np


def crest_factor(pcm_int16: np.ndarray) -> float:
    """Return peak/RMS on int16 magnitudes. Returns 0.0 on empty, silent, or
    near-silent input (avoids div-by-zero)."""
    if pcm_int16.size == 0:
        return 0.0
    peak = float(np.abs(pcm_int16).max())
    if peak == 0.0:
        return 0.0
    # Cast to float64 BEFORE squaring — int16**2 can overflow at high amplitudes.
    rms = float(np.sqrt(np.mean(pcm_int16.astype(np.float64) ** 2)))
    if rms <= 1e-9:
        return 0.0
    return peak / rms


class EmaSmoother:
    """Exponential moving average. First update() passes the value through;
    subsequent updates blend with weight alpha.

        new_value = alpha * value + (1 - alpha) * old_value

    alpha=0.3 (default) keeps ~70% of prior signal — a 1.5-2s effective window
    at 10Hz tick cadence.
    """

    def __init__(self, alpha: float = 0.3, initial: float = 0.0):
        self.alpha = alpha
        self._value = initial
        self._has_seen = False

    def update(self, value: float) -> float:
        if not self._has_seen:
            self._value = value
            self._has_seen = True
            return value
        self._value = self.alpha * value + (1.0 - self.alpha) * self._value
        return self._value

    @property
    def value(self) -> float:
        return self._value
