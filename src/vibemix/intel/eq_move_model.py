# SPDX-License-Identifier: Apache-2.0
"""Clean-room EQ/filter move response predictor.

The live co-host can only claim a controller move changed the sound when two
things agree: the move's expected EQ/filter direction and the measured band
delta. This module provides the tiny deterministic producer for the first half.
It does not inspect audio and does not vendor any DJ-app source.
"""

from __future__ import annotations

import math
import re

import numpy as np

LO_MID_CORNER = 246.0
MID_HI_CORNER = 2484.0
LOW_KILL_FC = 99.0
HIGH_KILL_FC = 3700.0
KILL_GAIN_DB = -23.0
BOOST_GAIN_DB = 9.0
Q_KILL = 0.9
Q_SHELF = 0.4
Q_BOOST = 0.3

BAND_WINDOWS: tuple[tuple[str, float, float], ...] = (
    ("sub", 20.0, 100.0),
    ("low", 100.0, 300.0),
    ("mid", 300.0, 4000.0),
    ("high", 4000.0, 8000.0),
)

_KNOWN_MOVES = {
    "low_kill",
    "low_boost",
    "mid_kill",
    "mid_boost",
    "high_kill",
    "high_boost",
    "filter_hp",
    "filter_lp",
}


def predicted_band_gains(move: str, fs: int) -> dict[str, float]:
    """Return predicted per-band gain in dB for a known EQ/filter move.

    The band windows mirror ``audio.band_features.band_energy_ratios``. Unknown
    moves return ``{}``; callers must treat that as "no proof".
    """
    canonical = canonical_eq_move(move)
    if canonical is None:
        return {}
    sample_rate = _valid_sample_rate(fs)

    if canonical == "low_kill":
        b, a = _low_shelf(sample_rate, LO_MID_CORNER, KILL_GAIN_DB, Q_SHELF)
    elif canonical == "low_boost":
        b, a = _low_shelf(sample_rate, LO_MID_CORNER, BOOST_GAIN_DB, Q_BOOST)
    elif canonical == "mid_kill":
        b, a = _peaking(sample_rate, math.sqrt(LO_MID_CORNER * MID_HI_CORNER), KILL_GAIN_DB, Q_KILL)
    elif canonical == "mid_boost":
        b, a = _peaking(sample_rate, math.sqrt(LO_MID_CORNER * MID_HI_CORNER), BOOST_GAIN_DB, Q_BOOST)
    elif canonical == "high_kill":
        b, a = _high_shelf(sample_rate, MID_HI_CORNER, KILL_GAIN_DB, Q_SHELF)
    elif canonical == "high_boost":
        b, a = _high_shelf(sample_rate, MID_HI_CORNER, BOOST_GAIN_DB, Q_BOOST)
    elif canonical == "filter_hp":
        b, a = _high_pass(sample_rate, LOW_KILL_FC, Q_KILL)
    elif canonical == "filter_lp":
        b, a = _low_pass(sample_rate, HIGH_KILL_FC, Q_KILL)
    else:  # pragma: no cover - canonical_eq_move guards this.
        return {}

    return {name: _band_gain_db(b, a, lo, hi, sample_rate) for name, lo, hi in BAND_WINDOWS}


def canonical_eq_move(move: str) -> str | None:
    """Map a raw controller move label to the small EQ/filter vocabulary."""
    raw = " ".join(str(move or "").strip().lower().split())
    if not raw:
        return None
    token = raw.replace("→", "->")
    compact = re.sub(r"[^a-z0-9_:+-]+", "_", token)
    if compact in _KNOWN_MOVES:
        return compact

    is_kill = bool(re.search(r"\b(?:killed?|kill|deep[-_ ]?cut|cut)\b", token))
    is_boost = bool(re.search(r"\b(?:boost(?:ed)?|raise(?:d)?|up)\b", token))
    if "_low:" in token or " low:" in token:
        return _kill_or_boost("low", is_kill, is_boost)
    if "_mid:" in token or " mid:" in token:
        return _kill_or_boost("mid", is_kill, is_boost)
    if "_hi:" in token or "_high:" in token or " high:" in token:
        return _kill_or_boost("high", is_kill, is_boost)
    if "_filter:" in token or " filter:" in token or token.startswith("filter_"):
        if re.search(r"\b(?:hp|high[-_ ]?pass|left|low[-_ ]?cut)\b", token) or is_kill:
            return "filter_hp"
        if re.search(r"\b(?:lp|low[-_ ]?pass|right|high[-_ ]?cut)\b", token) or is_boost:
            return "filter_lp"
    return None


def _kill_or_boost(control: str, is_kill: bool, is_boost: bool) -> str | None:
    if is_kill:
        return f"{control}_kill"
    if is_boost:
        return f"{control}_boost"
    return None


def _valid_sample_rate(fs: int) -> int:
    try:
        value = int(fs)
    except (TypeError, ValueError):
        value = 48_000
    return max(8_000, min(value, 384_000))


def _normalize(b: tuple[float, float, float], a: tuple[float, float, float]) -> tuple[np.ndarray, np.ndarray]:
    a0 = a[0] if a[0] else 1.0
    return (
        np.asarray([b[0] / a0, b[1] / a0, b[2] / a0], dtype=np.float64),
        np.asarray([1.0, a[1] / a0, a[2] / a0], dtype=np.float64),
    )


def _peaking(fs: int, f0: float, gain_db: float, q: float) -> tuple[np.ndarray, np.ndarray]:
    a_gain = 10.0 ** (gain_db / 40.0)
    w0 = 2.0 * math.pi * min(f0, fs * 0.49) / fs
    cos_w0 = math.cos(w0)
    alpha = math.sin(w0) / (2.0 * max(q, 1e-6))
    return _normalize(
        (1.0 + alpha * a_gain, -2.0 * cos_w0, 1.0 - alpha * a_gain),
        (1.0 + alpha / a_gain, -2.0 * cos_w0, 1.0 - alpha / a_gain),
    )


def _low_shelf(fs: int, f0: float, gain_db: float, slope: float) -> tuple[np.ndarray, np.ndarray]:
    a_gain = 10.0 ** (gain_db / 40.0)
    w0 = 2.0 * math.pi * min(f0, fs * 0.49) / fs
    cos_w0 = math.cos(w0)
    sqrt_a = math.sqrt(a_gain)
    alpha = _shelf_alpha(a_gain, w0, slope)
    return _normalize(
        (
            a_gain * ((a_gain + 1.0) - (a_gain - 1.0) * cos_w0 + 2.0 * sqrt_a * alpha),
            2.0 * a_gain * ((a_gain - 1.0) - (a_gain + 1.0) * cos_w0),
            a_gain * ((a_gain + 1.0) - (a_gain - 1.0) * cos_w0 - 2.0 * sqrt_a * alpha),
        ),
        (
            (a_gain + 1.0) + (a_gain - 1.0) * cos_w0 + 2.0 * sqrt_a * alpha,
            -2.0 * ((a_gain - 1.0) + (a_gain + 1.0) * cos_w0),
            (a_gain + 1.0) + (a_gain - 1.0) * cos_w0 - 2.0 * sqrt_a * alpha,
        ),
    )


def _high_shelf(fs: int, f0: float, gain_db: float, slope: float) -> tuple[np.ndarray, np.ndarray]:
    a_gain = 10.0 ** (gain_db / 40.0)
    w0 = 2.0 * math.pi * min(f0, fs * 0.49) / fs
    cos_w0 = math.cos(w0)
    sqrt_a = math.sqrt(a_gain)
    alpha = _shelf_alpha(a_gain, w0, slope)
    return _normalize(
        (
            a_gain * ((a_gain + 1.0) + (a_gain - 1.0) * cos_w0 + 2.0 * sqrt_a * alpha),
            -2.0 * a_gain * ((a_gain - 1.0) + (a_gain + 1.0) * cos_w0),
            a_gain * ((a_gain + 1.0) + (a_gain - 1.0) * cos_w0 - 2.0 * sqrt_a * alpha),
        ),
        (
            (a_gain + 1.0) - (a_gain - 1.0) * cos_w0 + 2.0 * sqrt_a * alpha,
            2.0 * ((a_gain - 1.0) - (a_gain + 1.0) * cos_w0),
            (a_gain + 1.0) - (a_gain - 1.0) * cos_w0 - 2.0 * sqrt_a * alpha,
        ),
    )


def _shelf_alpha(a_gain: float, w0: float, slope: float) -> float:
    safe_slope = max(slope, 1e-6)
    return math.sin(w0) / 2.0 * math.sqrt((a_gain + 1.0 / a_gain) * (1.0 / safe_slope - 1.0) + 2.0)


def _low_pass(fs: int, f0: float, q: float) -> tuple[np.ndarray, np.ndarray]:
    w0 = 2.0 * math.pi * min(f0, fs * 0.49) / fs
    cos_w0 = math.cos(w0)
    alpha = math.sin(w0) / (2.0 * max(q, 1e-6))
    return _normalize(
        ((1.0 - cos_w0) / 2.0, 1.0 - cos_w0, (1.0 - cos_w0) / 2.0),
        (1.0 + alpha, -2.0 * cos_w0, 1.0 - alpha),
    )


def _high_pass(fs: int, f0: float, q: float) -> tuple[np.ndarray, np.ndarray]:
    w0 = 2.0 * math.pi * min(f0, fs * 0.49) / fs
    cos_w0 = math.cos(w0)
    alpha = math.sin(w0) / (2.0 * max(q, 1e-6))
    return _normalize(
        ((1.0 + cos_w0) / 2.0, -(1.0 + cos_w0), (1.0 + cos_w0) / 2.0),
        (1.0 + alpha, -2.0 * cos_w0, 1.0 - alpha),
    )


def _band_gain_db(b: np.ndarray, a: np.ndarray, lo: float, hi: float, fs: int) -> float:
    nyquist = fs / 2.0
    lo_hz = max(1.0, lo)
    hi_hz = min(hi, nyquist * 0.999)
    if hi_hz <= lo_hz:
        return 0.0
    freqs = np.linspace(lo_hz, hi_hz, 128, dtype=np.float64)
    z = np.exp(-1j * 2.0 * np.pi * freqs / float(fs))
    numerator = b[0] + b[1] * z + b[2] * z * z
    denominator = a[0] + a[1] * z + a[2] * z * z
    power = np.abs(numerator / denominator) ** 2
    mean_power = float(np.mean(power))
    if not math.isfinite(mean_power) or mean_power <= 0.0:
        return 0.0
    return round(10.0 * math.log10(mean_power), 2)
