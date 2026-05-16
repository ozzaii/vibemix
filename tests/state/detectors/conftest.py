# SPDX-License-Identifier: Apache-2.0
"""Shared fixtures for Phase 17 detector tests.

The ``_state(...)`` builder is COPIED VERBATIM from
``tests/state/test_event_detector.py`` rather than imported because pytest
discovery treats each test directory independently — relying on cross-directory
imports of helpers makes the suite fragile to ``--rootdir`` changes. The
fixture is light enough to duplicate.

The ``_audio_sine(...)`` helper synthesizes a single-tone PCM array used by
``test_dsp_primitives`` and ``test_kick_swap`` to drive ``kick_band_centroid``
deterministically.
"""

from __future__ import annotations

import numpy as np

from vibemix.state import MusicState


def _state(
    *,
    audible: bool = True,
    bpm: float = 130.0,
    audible_track: str | None = None,
    audible_track_confidence: float = 0.0,
    phase: str = "groove",
    bands: dict | None = None,
    rms: float = 0.06,
    onset_density: float = 0.0,
    recent_moves: list | None = None,
) -> MusicState:
    """Build a MusicState pre-populated with 'music truly playing' defaults.
    Tests opt INTO silence / bpm-edge by overriding the defaults.

    Mirrors ``tests/state/test_event_detector.py::_state`` plus the
    ``onset_density`` parameter needed by ``KickDensityShiftDetector`` tests.
    """
    ms = MusicState()
    ms.audible = audible
    ms.bpm = bpm
    ms.audible_track = audible_track
    ms.audible_track_confidence = audible_track_confidence
    ms.phase = phase
    ms.bands = bands if bands is not None else {"sub": 0.2, "low": 0.3, "mid": 0.3, "high": 0.2}
    ms.rms = rms
    ms.onset_density = onset_density
    ms.recent_moves = recent_moves if recent_moves is not None else []
    return ms


def _audio_sine(freq_hz: float, n_samples: int, sample_rate: int = 16000) -> np.ndarray:
    """Generate a unit-amplitude float32 sine of `freq_hz` for `n_samples` at `sample_rate`.

    Returns int16 PCM (matching ``AudioBuffer.snapshot()`` dtype) so detector
    tests can pass it through ``kick_band_centroid`` without a manual cast.
    """
    t = np.arange(n_samples, dtype=np.float32) / float(sample_rate)
    sine = np.sin(2.0 * np.pi * freq_hz * t)
    # Scale to int16 range with comfortable headroom (no clipping on sums)
    return (sine * 16384.0).astype(np.int16)
