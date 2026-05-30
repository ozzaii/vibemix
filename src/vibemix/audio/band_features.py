# SPDX-License-Identifier: Apache-2.0
"""Per-lane band-energy ratios for the Vibe Judge's bass-collision signal.

Torch-free / librosa-free: reuses the existing Hanning-windowed rfft primitive
(state.detectors._dsp._windowed_spectrum). Operates on a single deck lane's PCM
(int16 from AudioBuffer.snapshot, or float32 in [-1,1]). Returns normalized
energy RATIOS per band, or None when the lane is silent (honest-null) — NEVER a
fabricated band split during a breakdown.
"""
from __future__ import annotations

import numpy as np

from vibemix.state.detectors._dsp import _windowed_spectrum

# Band edges (Hz) mirror the master snapshot_features split (features.py:75-79),
# collapsed to the four the Judge cares about. sub+low = the bass region where
# two simultaneous basslines mask each other into mud.
_BANDS: tuple[tuple[str, float, float], ...] = (
    ("sub", 20.0, 100.0),
    ("low", 100.0, 300.0),
    ("mid", 300.0, 4000.0),
    ("high", 4000.0, 8000.0),
)

# Below this total in-band magnitude the lane is effectively silent -> abstain.
_SILENCE_FLOOR = 1e-6


def band_energy_ratios(samples: np.ndarray, sample_rate: int) -> dict[str, float] | None:
    """Return {sub,low,mid,high} energy ratios summing to ~1.0, or None if silent.

    Args:
        samples: int16 PCM (AudioBuffer.snapshot dtype) or float32 in [-1,1].
        sample_rate: Hz (16000 for the canonical per-lane buffer).
    """
    if samples is None or samples.size == 0:
        return None
    mag, freqs = _windowed_spectrum(samples, sample_rate)
    power = mag * mag
    out: dict[str, float] = {}
    total = 0.0
    for name, lo, hi in _BANDS:
        mask = (freqs >= lo) & (freqs < hi)
        energy = float(power[mask].sum())
        out[name] = energy
        total += energy
    if total <= _SILENCE_FLOOR:
        return None
    return {name: energy / total for name, energy in out.items()}
