# SPDX-License-Identifier: Apache-2.0
"""Phase 93 Plan 02 — EXEMPLAR-01 ``compute_band_shares()`` helper.

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

Plan 93-02 fixture: synthetic WAV files written via stdlib ``wave`` (no PyAV
write-path dependency). The PyAV decoder in ``library/audio_decode.py``
decodes WAV via FFmpeg the same way it decodes mp3/m4a/flac — the file
extension does not gate decoder selection.

REQ-ID: EXEMPLAR-01 (band-share scalar persistence at ingest time).
"""
from __future__ import annotations

import math
import wave
from pathlib import Path

import numpy as np
import pytest

try:
    from vibemix.learn.exemplar import compute_band_shares  # Plan 93-02
except ImportError:
    pytest.skip(
        "tests/learn/test_compute_band_shares.py awaiting Plan 93-02 — "
        "compute_band_shares helper in src/vibemix/learn/exemplar.py.",
        allow_module_level=True,
    )


_FIXTURE_SR: int = 48000
_FIXTURE_DUR_S: float = 3.0


def _write_wav(path: Path, samples: np.ndarray, sr: int = _FIXTURE_SR) -> None:
    """Write a mono int16 PCM WAV file at ``sr`` to ``path``.

    Stdlib-only (no scipy / PyAV write-path dependency). Same shape as the
    helper in ``tests/library/test_audio_decode.py::_write_stereo_wav`` but
    mono — ``compute_band_shares`` downmixes to mono internally via
    ``load_audio_mono`` so a mono input is identity-decoded.
    """
    # Clip-BEFORE-cast to avoid int16 overflow (audio/features.py Pitfall 4).
    int16 = np.clip(samples * 32767.0, -32768, 32767).astype(np.int16)
    with wave.open(str(path), "wb") as fh:
        fh.setnchannels(1)
        fh.setsampwidth(2)
        fh.setframerate(sr)
        fh.writeframes(int16.tobytes())


def _synthetic_60hz_fixture(tmp_path: Path) -> Path:
    """Render a small synthetic .wav file with a 60 Hz sub-heavy waveform.

    Mirrors the synthetic kick fixture from ``test_exemplar_kick_guard.py``
    (smooth-envelope 60 Hz kicks @ 130 BPM, no transient broadband artifacts)
    so ``compute_band_shares`` returns realistic non-zero band shares.
    """
    path = tmp_path / "synthetic_60hz.wav"
    n = int(_FIXTURE_SR * _FIXTURE_DUR_S)
    t = np.arange(n, dtype=np.float32) / _FIXTURE_SR
    period_s = 60.0 / 130.0
    # Smooth-envelope kicks (25 ms attack + 150 ms decay).
    kick_env = np.zeros(n, dtype=np.float32)
    attack_len = int(0.025 * _FIXTURE_SR)
    decay_len = int(0.15 * _FIXTURE_SR)
    attack_curve = 0.5 - 0.5 * np.cos(
        np.linspace(0, math.pi, attack_len, dtype=np.float32)
    )
    decay_curve = np.exp(
        -np.arange(decay_len, dtype=np.float32) / (0.05 * _FIXTURE_SR)
    )
    one_hit = np.concatenate([attack_curve, decay_curve]).astype(np.float32)
    for hit in range(int(_FIXTURE_DUR_S / period_s) + 1):
        start = int(hit * period_s * _FIXTURE_SR)
        end = min(start + one_hit.size, n)
        kick_env[start:end] += one_hit[: end - start]
    samples = (np.sin(2 * np.pi * 60 * t) * kick_env).astype(np.float32)
    _write_wav(path, samples)
    return path


def _silent_fixture(tmp_path: Path) -> Path:
    """Render a 3 s silent .wav file (all-zero samples)."""
    path = tmp_path / "silent.wav"
    n = int(_FIXTURE_SR * _FIXTURE_DUR_S)
    _write_wav(path, np.zeros(n, dtype=np.float32))
    return path


def test_compute_band_shares_returns_5_key_dict(tmp_path: Path) -> None:
    """Result must be a dict with exactly the 5 documented keys, all floats."""
    fixture = _synthetic_60hz_fixture(tmp_path)
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
    ``audio/features.py:43-44`` short-circuits to zeros."""
    fixture = _silent_fixture(tmp_path)
    result = compute_band_shares(str(fixture))
    for k in ("sub_share", "low_share", "mid_share", "high_share", "kick_corr"):
        assert abs(result[k]) < 1e-6, (
            f"silent track expected {k}≈0.0, got {result[k]!r}"
        )


def test_compute_band_shares_normalized_sub_low_mid_high_sum_one(
    tmp_path: Path,
) -> None:
    """The four ``*_share`` floats must sum to ~1.0 (within 1e-2 to absorb
    the per-band 2-decimal rounding in ``audio/features.py:86-89``) for a
    real-looking synthetic track.

    The existing ``audio/features.py:88-89`` aggregates two FFT bands into
    ``mid_share = (mid_low + mid_hi) / total`` so the four share columns
    cover the full 20-8000 Hz spectrum and sum to 1.0 modulo the existing
    2-decimal rounding at the v4 port site.
    """
    fixture = _synthetic_60hz_fixture(tmp_path)
    result = compute_band_shares(str(fixture))
    band_sum = (
        result["sub_share"]
        + result["low_share"]
        + result["mid_share"]
        + result["high_share"]
    )
    # 1e-2 tolerance: each of the 4 *_share values comes from
    # round(band/total, 2) so the sum has 4 × 5e-3 = ~2e-2 worst-case drift.
    assert abs(band_sum - 1.0) < 2e-2, (
        f"4 band-shares must sum to ~1.0 (within 2e-2); got {band_sum!r}"
    )
