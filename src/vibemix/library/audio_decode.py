# SPDX-License-Identifier: Apache-2.0
"""Small audio decode/DSP helpers for local model paths.

This module replaces the previous librosa runtime dependency in CLAP/CUE. It is
intentionally narrow: PyAV/FFmpeg decodes and resamples files, while local
numpy helpers build the mel filterbank/STFT primitives needed by CLAP/CUE.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np


class AudioDecodeError(RuntimeError):
    """Audio could not be decoded into mono float32 samples."""


def _frame_to_float_mono(frame) -> np.ndarray:
    arr = frame.to_ndarray()
    dtype = arr.dtype
    channels = max(1, len(getattr(frame.layout, "channels", ()) or (None,)))
    samples = int(getattr(frame, "samples", 0) or 0)

    if arr.ndim == 1:
        shaped = arr.reshape(-1, channels) if channels > 1 else arr.reshape(-1, 1)
    elif getattr(frame.format, "is_planar", False):
        shaped = arr[:channels, :samples].T
    else:
        shaped = arr.reshape(-1).reshape(-1, channels)

    mono = shaped.astype(np.float32, copy=False)
    if np.issubdtype(dtype, np.unsignedinteger):
        info = np.iinfo(dtype)
        midpoint = (info.max + 1) / 2.0
        mono = (mono - midpoint) / midpoint
    elif np.issubdtype(dtype, np.signedinteger):
        info = np.iinfo(dtype)
        mono = mono / float(max(abs(info.min), info.max))

    return mono.mean(axis=1).astype(np.float32, copy=False)


def load_audio_mono(path: str | Path, *, target_sr: int) -> np.ndarray:
    """Decode an audio file to mono float32 at ``target_sr``.

    PyAV rides on FFmpeg, so this covers common DJ library files (mp3/m4a/wav/
    flac/aiff) without pulling librosa, numba, llvmlite, or scikit-learn into
    the frozen sidecar.
    """
    try:
        import av
    except ImportError as exc:  # pragma: no cover - packaging/runtime drift
        raise AudioDecodeError(f"missing runtime dependency: {exc}") from exc

    decoded: list[np.ndarray] = []
    try:
        resampler = av.audio.resampler.AudioResampler(
            format="flt",
            layout="mono",
            rate=int(target_sr),
        )
        with av.open(str(Path(path).expanduser())) as container:
            for frame in container.decode(audio=0):
                for out in resampler.resample(frame):
                    mono = _frame_to_float_mono(out)
                    if mono.size:
                        decoded.append(mono)
            for out in resampler.resample(None):
                mono = _frame_to_float_mono(out)
                if mono.size:
                    decoded.append(mono)
    except Exception as exc:  # pragma: no cover - bad file/codec dependent
        raise AudioDecodeError(f"failed to decode audio file {path!s}: {exc}") from exc

    if not decoded:
        raise AudioDecodeError(f"no audio frames decoded from {path!s}")

    return np.concatenate(decoded).astype(np.float32, copy=False)


def power_to_db(
    power: np.ndarray,
    *,
    ref=np.max,
    amin: float = 1e-10,
    top_db: float | None = 80.0,
) -> np.ndarray:
    """Librosa-compatible power spectrogram to dB conversion."""
    magnitude = np.maximum(np.asarray(power, dtype=np.float32), amin)
    ref_value = ref(power) if callable(ref) else ref
    log_spec = 10.0 * np.log10(magnitude)
    log_spec -= 10.0 * np.log10(max(amin, float(ref_value)))
    if top_db is not None:
        log_spec = np.maximum(log_spec, float(log_spec.max()) - float(top_db))
    return log_spec.astype(np.float32, copy=False)


def cue_log_mel_spectrogram_db(
    samples: np.ndarray,
    *,
    sr: int,
    n_fft: int,
    hop_length: int,
    n_mels: int,
) -> np.ndarray:
    """Return a librosa-style log-mel dB spectrogram for CUE-DETR."""
    from vibemix.library.audio_features import mel_filter_bank, spectrogram, window_function

    mel_filters = mel_filter_bank(
        num_frequency_bins=(n_fft // 2) + 1,
        num_mel_filters=n_mels,
        min_frequency=0.0,
        max_frequency=sr / 2.0,
        sampling_rate=sr,
        norm="slaney",
    )
    power = spectrogram(
        np.asarray(samples, dtype=np.float64),
        window_function(n_fft, "hann"),
        frame_length=n_fft,
        hop_length=hop_length,
        fft_length=n_fft,
        power=2.0,
        center=True,
        pad_mode="constant",
        mel_filters=mel_filters,
        log_mel=None,
        dtype=np.float32,
    )
    return power_to_db(power, ref=np.max)


def frames_to_time(frames: list[int] | np.ndarray, *, sr: int, hop_length: int) -> np.ndarray:
    """Convert frame indices to seconds using librosa's default formula."""
    return np.asarray(frames, dtype=np.float64) * float(hop_length) / float(sr)
