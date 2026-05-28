# SPDX-License-Identifier: Apache-2.0
"""Phase 93 Plan 02 — EXEMPLAR-01 ``compute_band_shares()`` helper (RED-state stub).

``compute_band_shares(audio_path)`` is the per-track band-share computation
helper that the CLAP ingest path calls at ingest time to populate the
``band_shares`` side-car table. It returns a 5-key dict:

    {
        "sub_share":  float,   # ∈ [0, 1] — band-energy / total-energy
        "low_share":  float,
        "mid_share":  float,
        "high_share": float,
        "kick_corr":  float,   # ∈ [-1, 1] — Pearson r between mid + sub bands
    }

The four ``*_share`` values sum to ~1.0 (within float epsilon — the
existing ``audio/features.py:71-89`` rounding can drift the sum by ~0.01).

REQ-ID: EXEMPLAR-01 (band-share scalar persistence at ingest time).
Downstream plan that flips this skip: **Plan 93-02** (``vibemix.learn.exemplar``).
"""
from __future__ import annotations

from pathlib import Path

import pytest

try:
    from vibemix.learn.exemplar import compute_band_shares  # Plan 93-02
except ImportError:
    pytest.skip(
        "tests/learn/test_compute_band_shares.py awaiting Plan 93-02 — "
        "compute_band_shares helper in src/vibemix/learn/exemplar.py.",
        allow_module_level=True,
    )


def _synthetic_mp3_fixture(tmp_path: Path) -> Path:
    """Render a small synthetic mp3 file with a 60 Hz sub-heavy waveform.

    Plan 93-02 ships the real fixture-writer alongside ``compute_band_shares``
    (PyAV write path). Until then this helper is exercised only behind the
    module-level skip; we document the expected shape so the downstream
    implementer can wire it directly.
    """
    return tmp_path / "synthetic_60hz.mp3"


def test_compute_band_shares_returns_5_key_dict(tmp_path: Path) -> None:
    """Result must be a dict with exactly the 5 documented keys, all floats."""
    fixture = _synthetic_mp3_fixture(tmp_path)
    result = compute_band_shares(str(fixture))
    expected_keys = {"sub_share", "low_share", "mid_share", "high_share", "kick_corr"}
    assert set(result.keys()) == expected_keys, (
        f"compute_band_shares must return exactly 5 keys "
        f"{sorted(expected_keys)!r}; got {sorted(result.keys())!r}"
    )
    for k, v in result.items():
        assert isinstance(v, float), (
            f"compute_band_shares[{k!r}] must be float (got {type(v).__name__})"
        )


def test_compute_band_shares_silent_track_zero_floats(tmp_path: Path) -> None:
    """A silent track (all-zero samples) must yield band-shares ≈ 0.0
    for every band — the ``snapshot_features.silent`` branch at
    ``audio/features.py:65-70`` short-circuits to zeros."""
    fixture = tmp_path / "silent.mp3"
    # Plan 93-02 implementer writes the silent fixture via PyAV; for now
    # we document the contract — a silent buffer → all-zero output.
    result = compute_band_shares(str(fixture))
    for k in ("sub_share", "low_share", "mid_share", "high_share", "kick_corr"):
        assert abs(result[k]) < 1e-6, (
            f"silent track expected {k}≈0.0, got {result[k]!r}"
        )


def test_compute_band_shares_normalized_sub_low_mid_high_sum_one(
    tmp_path: Path,
) -> None:
    """The four ``*_share`` floats must sum to ~1.0 (within 1e-3) for a
    real-looking synthetic track.

    The existing ``audio/features.py:88-89`` aggregates two FFT bands into
    ``mid_share = (mid_low + mid_hi) / total`` so the four share columns
    cover the full 20-8000 Hz spectrum and sum to 1.0 modulo rounding.
    """
    fixture = _synthetic_mp3_fixture(tmp_path)
    result = compute_band_shares(str(fixture))
    band_sum = (
        result["sub_share"]
        + result["low_share"]
        + result["mid_share"]
        + result["high_share"]
    )
    assert abs(band_sum - 1.0) < 1e-3, (
        f"4 band-shares must sum to ~1.0 (within 1e-3); got {band_sum!r}"
    )
