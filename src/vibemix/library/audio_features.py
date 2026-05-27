# SPDX-License-Identifier: Apache-2.0
"""Narrow numpy audio-feature primitives for CLAP/CUE local models."""

from __future__ import annotations

import numpy as np


def hertz_to_mel(freq: float | np.ndarray) -> float | np.ndarray:
    """Convert Hz to Slaney mel scale."""
    min_log_hz = 1000.0
    min_log_mel = 15.0
    logstep = 27.0 / np.log(6.4)
    mels = 3.0 * freq / 200.0
    if isinstance(freq, np.ndarray):
        log_region = freq >= min_log_hz
        mels[log_region] = min_log_mel + np.log(freq[log_region] / min_log_hz) * logstep
    elif freq >= min_log_hz:
        mels = min_log_mel + np.log(freq / min_log_hz) * logstep
    return mels


def mel_to_hertz(mels: float | np.ndarray) -> float | np.ndarray:
    """Convert Slaney mel scale to Hz."""
    min_log_hz = 1000.0
    min_log_mel = 15.0
    logstep = np.log(6.4) / 27.0
    freq = 200.0 * mels / 3.0
    if isinstance(mels, np.ndarray):
        log_region = mels >= min_log_mel
        freq[log_region] = min_log_hz * np.exp(logstep * (mels[log_region] - min_log_mel))
    elif mels >= min_log_mel:
        freq = min_log_hz * np.exp(logstep * (mels - min_log_mel))
    return freq


def window_function(window_length: int, name: str = "hann") -> np.ndarray:
    """Return the periodic Hann window used by CLAP/CUE preprocessing."""
    if name != "hann":
        raise ValueError(f"unsupported window function: {name}")
    return np.hanning(window_length + 1)[:-1]


def mel_filter_bank(
    *,
    num_frequency_bins: int,
    num_mel_filters: int,
    min_frequency: float,
    max_frequency: float,
    sampling_rate: int,
    norm: str | None = "slaney",
) -> np.ndarray:
    """Return a Slaney-normalized triangular mel filter bank."""
    if norm not in (None, "slaney"):
        raise ValueError('norm must be None or "slaney"')
    mel_min = hertz_to_mel(float(min_frequency))
    mel_max = hertz_to_mel(float(max_frequency))
    mel_freqs = np.linspace(mel_min, mel_max, num_mel_filters + 2)
    filter_freqs = mel_to_hertz(mel_freqs)
    fft_freqs = np.linspace(0, sampling_rate // 2, num_frequency_bins)

    filter_diff = np.diff(filter_freqs)
    slopes = np.expand_dims(filter_freqs, 0) - np.expand_dims(fft_freqs, 1)
    down_slopes = -slopes[:, :-2] / filter_diff[:-1]
    up_slopes = slopes[:, 2:] / filter_diff[1:]
    mel_filters = np.maximum(np.zeros(1), np.minimum(down_slopes, up_slopes))

    if norm == "slaney":
        enorm = 2.0 / (filter_freqs[2 : num_mel_filters + 2] - filter_freqs[:num_mel_filters])
        mel_filters *= np.expand_dims(enorm, 0)
    return mel_filters


def _power_to_db(
    spec: np.ndarray,
    *,
    reference: float = 1.0,
    min_value: float = 1e-10,
    db_range: float | None = None,
) -> np.ndarray:
    out = 10.0 * np.log10(np.maximum(spec, min_value))
    out -= 10.0 * np.log10(max(min_value, float(reference)))
    if db_range is not None:
        out = np.maximum(out, out.max() - db_range)
    return out


def spectrogram(
    waveform: np.ndarray,
    window: np.ndarray,
    *,
    frame_length: int,
    hop_length: int,
    fft_length: int | None = None,
    power: float | None = 1.0,
    center: bool = True,
    pad_mode: str = "reflect",
    mel_filters: np.ndarray | None = None,
    mel_floor: float = 1e-10,
    log_mel: str | None = None,
    reference: float = 1.0,
    min_value: float = 1e-10,
    db_range: float | None = None,
    dtype: np.dtype = np.float32,
) -> np.ndarray:
    """Compute the small STFT/mel subset needed by CLAP and CUE."""
    if fft_length is None:
        fft_length = frame_length
    if waveform.ndim != 1:
        raise ValueError(f"waveform must be mono 1-D, got {waveform.shape}")
    if len(window) != frame_length:
        raise ValueError("window length must match frame_length")
    if center:
        pad = frame_length // 2
        waveform = np.pad(waveform, [(pad, pad)], mode=pad_mode)

    waveform = waveform.astype(np.float64, copy=False)
    window = window.astype(np.float64, copy=False)
    num_frames = int(1 + np.floor((waveform.size - frame_length) / hop_length))
    num_bins = (fft_length // 2) + 1
    out = np.empty((num_frames, num_bins), dtype=np.complex64)
    buffer = np.zeros(fft_length, dtype=np.float64)

    offset = 0
    for idx in range(num_frames):
        buffer.fill(0.0)
        buffer[:frame_length] = waveform[offset : offset + frame_length]
        buffer[:frame_length] *= window
        out[idx] = np.fft.rfft(buffer)
        offset += hop_length

    spec: np.ndarray
    if power is None:
        spec = out.T
    else:
        spec = np.abs(out).astype(np.float64, copy=False) ** power
        spec = spec.T

    if mel_filters is not None:
        if power is None:
            raise ValueError("mel spectrogram requires power to be set")
        spec = np.maximum(mel_floor, np.dot(mel_filters.T, spec))

    if power is not None and log_mel is not None:
        if log_mel == "dB":
            if power != 2.0:
                raise ValueError("dB log_mel currently supports power=2.0 only")
            spec = _power_to_db(
                spec,
                reference=reference,
                min_value=min_value,
                db_range=db_range,
            )
        elif log_mel == "log":
            spec = np.log(spec)
        elif log_mel == "log10":
            spec = np.log10(spec)
        else:
            raise ValueError(f"unsupported log_mel mode: {log_mel}")
        spec = np.asarray(spec, dtype=dtype)

    return spec
