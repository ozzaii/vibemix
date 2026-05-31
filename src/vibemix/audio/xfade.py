# SPDX-License-Identifier: Apache-2.0
"""Crossfader transfer function — the AutoDJ scalar → two per-deck gains.

Clean-room port of Mixxx ``EngineXfader`` (scar 20 §3.7 / scar 21 §3.3, GPLv2 —
facts re-derived, no source copied). The crossfader is ONE scalar ``x ∈ [-1, 1]``
(−1 = fully deck 1, +1 = fully deck 2, 0 = center); the engine turns it into a
per-deck gain pair. vibemix uses this two ways:

  * the transition/Beatmatch Judge grades a blend against the real constant-power
    curve ("our AI grades your transition with Mixxx's curve"), and
  * the co-host estimates *perceived* per-track loudness during a mix ("the old
    track's ducking out now") instead of assuming a linear fade.

The constant-power curve's defining property is ``g1² + g2² == 1`` (equal loudness
for uncorrelated signals; −3 dB ≈ 0.707 at the center). Empirically (Mixxx
``enginexfader.cpp:66-77``, 30 s snippets ReplayGain 2.0) the crossover ratio sat
near ``sqrt(0.5)=0.707`` for almost everything and ``0.66`` only for two parts of
the SAME track; the uncorrelated normalization is the chosen default.
"""
from __future__ import annotations

# scar constants (enginexfader.cpp/.h)
TRANSFORM_DEFAULT = 1.0  # kTransformDefault (:7) — fade sharpness exponent
TRANSFORM_MIN = 0.6  # kTransformMin (:9) — softest/slowest fade
TRANSFORM_MAX = 1000.0  # kTransformMax (:8) — sharpest, ≈ hard cut
CURVE_CONSTANT_POWER = "constpwr"  # MIXXX_XFADER_CONSTPWR (enginexfader.h:7)
CURVE_ADDITIVE = "additive"  # MIXXX_XFADER_ADDITIVE (enginexfader.h:6)


def power_calibration(transform: float) -> float:
    """The −3 dB power calibration root for the constant-power curve (:13).

    ``0.5 ** (1/transform)`` places the crossover at 0.5 power (−3 dB per channel)
    for the default ``transform == 1.0``.
    """
    return 0.5 ** (1.0 / transform)


def xfade_gains(
    x: float,
    *,
    transform: float = TRANSFORM_DEFAULT,
    curve: str = CURVE_CONSTANT_POWER,
    reverse: bool = False,
) -> tuple[float, float]:
    """Crossfader scalar ``x ∈ [-1, 1]`` → ``(gain_deck1, gain_deck2)`` (:16).

    ``curve == "constpwr"`` (default) normalizes so ``g1² + g2² == 1`` (equal
    perceived loudness, −3 dB at center); ``"additive"`` is the plain
    ``1 - |x|**transform`` linear blend with no normalization. Gains are clamped
    to ``>= 0`` (no phase reversal). ``reverse`` swaps the pair ("hamster mode").
    """
    pc = power_calibration(transform)
    xl = xr = x
    if curve == CURVE_CONSTANT_POWER:
        x *= pc
        xl = x - pc
        xr = x + pc

    g2 = 1.0 - abs(xl) ** transform if xl < 0.0 else 1.0  # deck2 (left/+side source)
    g1 = 1.0 - xr ** transform if xr > 0.0 else 1.0  # deck1 (right/−side source)
    g1 = max(g1, 0.0)
    g2 = max(g2, 0.0)

    if curve == CURVE_CONSTANT_POWER:
        # complete the pair, then normalize to the unit power circle.
        if g1 > g2:
            g2 = 1.0 - g1
        else:
            g1 = 1.0 - g2
        norm = (g1 * g1 + g2 * g2) ** 0.5
        g1 /= norm
        g2 /= norm

    return (g2, g1) if reverse else (g1, g2)
