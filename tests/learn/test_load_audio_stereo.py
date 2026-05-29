# SPDX-License-Identifier: Apache-2.0
"""EXEMPLAR-04 ``load_audio_stereo()`` stereo decode regression tests.

The existing ``library/audio_decode.py::load_audio_mono`` decodes to MONO
float32. ``ExemplarPlayer`` needs STEREO float32 at the track's native
sample rate so the CC-BY bank tracks (mostly stereo) and library tracks
play at full fidelity.

Contract (from 93-RESEARCH.md §Pattern 7):

    samples, sr = load_audio_stereo(path)
    samples.shape == (N, 2)   # stereo planar → interleaved transpose
    samples.dtype == np.float32
    sr is the native sample rate of the source file (no resampling).
    Mono inputs are duplicated across both channels.
    Empty / unreadable inputs raise ValueError("...no audio frames...").

REQ-ID: EXEMPLAR-04 (stereo decode for headphone playback).
"""
from __future__ import annotations

import math
import wave
from pathlib import Path

import numpy as np
import pytest

try:
    from vibemix.library.audio_decode import load_audio_stereo
except ImportError:
    pytest.skip(
        "load_audio_stereo is unavailable in this partial Learn build.",
        allow_module_level=True,
    )


def _write_synthetic_wav(path: Path, sample_rate: int, duration_s: float) -> Path:
    """Write a 1-channel (mono) 60 Hz sine wave WAV to ``path``.

    Stdlib :mod:`wave` write path — mirrors the pattern at
    ``tests/library/test_audio_decode.py::_write_stereo_wav``. Mono on
    purpose so the test exercises the mono → stereo upmix branch of
    :func:`load_audio_stereo` (the contract under test). PyAV decodes
    WAV via FFmpeg the same way it decodes mp3 / m4a / flac, so this
    stdlib-only fixture covers the production codec path.
    """
    n = int(sample_rate * duration_s)
    with wave.open(str(path), "wb") as fh:
        fh.setnchannels(1)
        fh.setsampwidth(2)
        fh.setframerate(sample_rate)
        frames = bytearray()
        for i in range(n):
            val = int(0.4 * 32767 * math.sin(2 * math.pi * 60 * i / sample_rate))
            frames.extend(val.to_bytes(2, "little", signed=True))
        fh.writeframes(bytes(frames))
    return path


def test_load_audio_stereo_returns_n2_float32(tmp_path: Path) -> None:
    """A mono input file decodes to ``(N, 2)`` float32 — the mono → stereo
    upmix duplicates the single channel across both stereo channels.
    """
    fixture = _write_synthetic_wav(tmp_path / "mono_60hz.wav", 44100, 1.0)
    samples, _sr = load_audio_stereo(fixture)
    assert samples.ndim == 2, (
        f"load_audio_stereo must return a 2-D array; got ndim={samples.ndim}"
    )
    assert samples.shape[1] == 2, (
        f"second axis must be channels=2; got shape={samples.shape!r}"
    )
    assert samples.dtype == np.float32, (
        f"dtype must be float32 (matches sd.OutputStream(dtype='float32')); "
        f"got {samples.dtype!r}"
    )


def test_load_audio_stereo_preserves_native_sample_rate(tmp_path: Path) -> None:
    """The returned ``sr`` reflects the source file's native sample rate —
    no resampling. Tested at both 44100 and 48000 Hz fixtures."""
    fx_44k = _write_synthetic_wav(tmp_path / "f44k.wav", 44100, 1.0)
    fx_48k = _write_synthetic_wav(tmp_path / "f48k.wav", 48000, 1.0)

    _, sr_44k = load_audio_stereo(fx_44k)
    _, sr_48k = load_audio_stereo(fx_48k)

    assert sr_44k == 44100, f"44100 Hz fixture should decode to 44100; got {sr_44k}"
    assert sr_48k == 48000, f"48000 Hz fixture should decode to 48000; got {sr_48k}"


def test_load_audio_stereo_raises_on_empty_input(tmp_path: Path) -> None:
    """An empty / broken audio file raises ``ValueError`` carrying the
    substring ``"no audio frames"`` so callers can distinguish empty-file
    errors from format-mismatch errors."""
    broken = tmp_path / "broken.wav"
    broken.write_bytes(b"")  # zero-byte file

    with pytest.raises(ValueError, match="no audio frames"):
        load_audio_stereo(broken)
