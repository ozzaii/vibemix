# SPDX-License-Identifier: Apache-2.0
"""Constant-power crossfader gains — scar 20 §3.7 / scar 21 §3.3, clean-room.

``xfade_gains`` maps the AutoDJ crossfader scalar ``x ∈ [-1, 1]`` to two per-deck
gains. The load-bearing fact: the constant-power curve keeps ``g1² + g2² == 1``
(equal perceived loudness for uncorrelated signals, −3 dB at the center) — the
exact curve the Beatmatch/transition Judge grades a blend against, and the basis
for "the old track's ducking out now" with a real gain number.
"""
from __future__ import annotations

import math

from vibemix.audio.xfade import power_calibration, xfade_gains


def test_power_calibration_default_is_minus_3db() -> None:
    # transform 1.0 -> 0.5 power == -3 dB at the crossover (enginexfader.cpp:13)
    assert math.isclose(power_calibration(1.0), 0.5, rel_tol=1e-12)


def test_center_is_minus_3db_constant_power() -> None:
    g1, g2 = xfade_gains(0.0)
    assert math.isclose(g1, math.sqrt(0.5), rel_tol=1e-9)  # 0.707…
    assert math.isclose(g2, math.sqrt(0.5), rel_tol=1e-9)
    assert math.isclose(g1 * g1 + g2 * g2, 1.0, rel_tol=1e-9)


def test_full_sides_are_solo() -> None:
    g1, g2 = xfade_gains(-1.0)  # fully deck 1
    assert math.isclose(g1, 1.0, rel_tol=1e-9) and math.isclose(g2, 0.0, abs_tol=1e-9)
    g1, g2 = xfade_gains(1.0)  # fully deck 2
    assert math.isclose(g1, 0.0, abs_tol=1e-9) and math.isclose(g2, 1.0, rel_tol=1e-9)


def test_constant_power_invariant_across_sweep() -> None:
    # the defining property: g1² + g2² == 1 everywhere on the constant-power curve
    for i in range(-100, 101):
        x = i / 100.0
        g1, g2 = xfade_gains(x)
        assert math.isclose(g1 * g1 + g2 * g2, 1.0, rel_tol=1e-9), x
        assert 0.0 <= g1 <= 1.0 and 0.0 <= g2 <= 1.0  # no phase reversal


def test_reverse_swaps_the_two_gains() -> None:
    g1, g2 = xfade_gains(-0.5)
    assert xfade_gains(-0.5, reverse=True) == (g2, g1)


def test_additive_curve_has_no_normalization() -> None:
    # additive/linear: simple 1 - |x|^t with NO constant-power renorm
    g1, g2 = xfade_gains(0.0, curve="additive")
    assert g1 == 1.0 and g2 == 1.0
    g1, g2 = xfade_gains(-1.0, curve="additive")
    assert math.isclose(g1, 1.0, rel_tol=1e-9) and math.isclose(g2, 0.0, abs_tol=1e-9)


def test_sharper_transform_is_a_harder_cut() -> None:
    # a larger transform exponent makes the fade sharper (closer to a hard cut):
    # at a partial position the leading deck stays louder longer.
    g1_soft, _ = xfade_gains(-0.5, transform=0.6)
    g1_sharp, _ = xfade_gains(-0.5, transform=4.0)
    assert g1_sharp >= g1_soft
