# SPDX-License-Identifier: Apache-2.0
"""Narrow audio decode/DSP helper tests."""

from __future__ import annotations

import math
import wave
from pathlib import Path

import numpy as np
import pytest

from vibemix.library.audio_decode import (
    cue_log_mel_spectrogram_db,
    frames_to_time,
    load_audio_mono,
    power_to_db,
)
from vibemix.library.audio_features import (
    mel_filter_bank,
    spectrogram,
    window_function,
)


def _write_stereo_wav(path: Path, *, sr: int = 44100, seconds: float = 0.1) -> None:
    n = int(sr * seconds)
    with wave.open(str(path), "wb") as fh:
        fh.setnchannels(2)
        fh.setsampwidth(2)
        fh.setframerate(sr)
        frames = bytearray()
        for i in range(n):
            left = int(0.4 * 32767 * math.sin(2 * math.pi * 440 * i / sr))
            right = int(0.2 * 32767 * math.sin(2 * math.pi * 440 * i / sr))
            frames.extend(left.to_bytes(2, "little", signed=True))
            frames.extend(right.to_bytes(2, "little", signed=True))
        fh.writeframes(bytes(frames))


def test_load_audio_mono_decodes_and_resamples_with_pyav(tmp_path: Path) -> None:
    src = tmp_path / "tone.wav"
    _write_stereo_wav(src)

    audio = load_audio_mono(src, target_sr=22050)

    assert audio.dtype == np.float32
    assert 2200 <= audio.shape[0] <= 2210
    assert 0.05 < float(np.max(np.abs(audio))) < 0.5


def test_power_to_db_matches_expected_reference_shape() -> None:
    spec = np.asarray([[1.0, 0.01], [0.0001, 0.0]], dtype=np.float32)

    db = power_to_db(spec, ref=np.max)

    assert db.shape == spec.shape
    assert float(db.max()) == 0.0
    assert float(db.min()) >= -80.0


def test_cue_log_mel_spectrogram_db_is_finite() -> None:
    sr = 22050
    t = np.arange(sr // 2, dtype=np.float32) / sr
    audio = 0.2 * np.sin(2 * np.pi * 220 * t)

    mel = cue_log_mel_spectrogram_db(
        audio,
        sr=sr,
        n_fft=2048,
        hop_length=512,
        n_mels=128,
    )

    assert mel.shape[0] == 128
    assert mel.shape[1] > 0
    assert np.isfinite(mel).all()


def test_local_audio_features_match_transformers_reference() -> None:
    hf_audio = pytest.importorskip("transformers.audio_utils")
    rng = np.random.default_rng(42)
    samples = rng.normal(0.0, 0.1, size=4096).astype(np.float32)
    n_fft = 512
    hop = 128
    local_filters = mel_filter_bank(
        num_frequency_bins=(n_fft // 2) + 1,
        num_mel_filters=32,
        min_frequency=50.0,
        max_frequency=7000.0,
        sampling_rate=22050,
        norm="slaney",
    )
    hf_filters = hf_audio.mel_filter_bank(
        num_frequency_bins=(n_fft // 2) + 1,
        num_mel_filters=32,
        min_frequency=50.0,
        max_frequency=7000.0,
        sampling_rate=22050,
        norm="slaney",
        mel_scale="slaney",
    )
    np.testing.assert_allclose(local_filters, hf_filters, rtol=1e-7, atol=1e-9)

    local = spectrogram(
        samples,
        window_function(n_fft, "hann"),
        frame_length=n_fft,
        hop_length=hop,
        power=2.0,
        mel_filters=local_filters,
        log_mel="dB",
    )
    ref = hf_audio.spectrogram(
        samples.astype(np.float64),
        hf_audio.window_function(n_fft, "hann"),
        frame_length=n_fft,
        hop_length=hop,
        power=2.0,
        mel_filters=hf_filters,
        log_mel="dB",
    )
    np.testing.assert_allclose(local, ref, rtol=1e-6, atol=1e-5)


def test_frames_to_time_uses_default_librosa_hop_formula() -> None:
    out = frames_to_time([0, 1, 10], sr=22050, hop_length=512)
    np.testing.assert_allclose(out, [0.0, 512 / 22050, 5120 / 22050])
