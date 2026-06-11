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


def load_audio_mono(
    path: str | Path,
    *,
    target_sr: int,
    offset_s: float = 0.0,
    duration_s: float | None = None,
) -> np.ndarray:
    """Decode an audio file to mono float32 at ``target_sr``.

    PyAV rides on FFmpeg, so this covers common DJ library files (mp3/m4a/wav/
    flac/aiff) without pulling librosa, numba, llvmlite, or scikit-learn into
    the frozen sidecar.

    ``offset_s``/``duration_s`` slice ``[offset_s, offset_s + duration_s)`` with
    ffmpeg's accurate ``-ss`` output-seek semantics: a keyframe seek lands at or
    before the offset, then the first decoded frame's timestamp anchors a
    sample-precise trim of the overshoot. This is the packaged-app replacement
    for the retired ffmpeg-binary window slicers (no subprocess, no system
    ffmpeg). A slice that reaches past end-of-file returns the shorter honest
    tail; a slice entirely past EOF raises :class:`AudioDecodeError`.
    """
    try:
        import av
    except ImportError as exc:  # pragma: no cover - packaging/runtime drift
        raise AudioDecodeError(f"missing runtime dependency: {exc}") from exc

    offset = max(0.0, float(offset_s))
    limit_samples: int | None = None
    if duration_s is not None:
        limit_samples = int(round(max(0.0, float(duration_s)) * int(target_sr)))
        if limit_samples == 0:
            raise AudioDecodeError(f"empty slice requested from {path!s}")

    decoded: list[np.ndarray] = []
    total = 0
    # Actual decode-start time on the source timeline. 0.0 when reading from
    # the top; after a seek it is the first decoded frame's timestamp, which
    # is what makes the post-decode trim precise instead of keyframe-coarse.
    anchor_s: float | None = 0.0
    stop_at: int | None = None  # decoded-sample count at which the slice is full
    try:
        resampler = av.audio.resampler.AudioResampler(
            format="flt",
            layout="mono",
            rate=int(target_sr),
        )
        with av.open(str(Path(path).expanduser())) as container:
            if offset > 0.0:
                anchor_s = None  # resolved from the first post-seek frame
                stream = container.streams.audio[0]
                try:
                    if stream.time_base is not None:
                        container.seek(int(offset / stream.time_base), stream=stream)
                    else:  # pragma: no cover - container without a time base
                        container.seek(int(offset / av.time_base))
                except Exception:
                    # Unseekable container — decode from the top and trim; the
                    # result is identical, just slower.
                    anchor_s = 0.0
            for frame in container.decode(audio=0):
                if anchor_s is None:
                    # Degenerate timestamp-less frame after a seek: assume the
                    # seek landed exactly at the request (best available truth).
                    anchor_s = float(frame.time) if frame.time is not None else offset
                if stop_at is None and limit_samples is not None:
                    skip = max(0, int(round((offset - anchor_s) * int(target_sr))))
                    stop_at = skip + limit_samples
                for out in resampler.resample(frame):
                    mono = _frame_to_float_mono(out)
                    if mono.size:
                        decoded.append(mono)
                        total += mono.size
                if stop_at is not None and total >= stop_at:
                    break
            if stop_at is None or total < stop_at:
                for out in resampler.resample(None):
                    mono = _frame_to_float_mono(out)
                    if mono.size:
                        decoded.append(mono)
    except Exception as exc:  # pragma: no cover - bad file/codec dependent
        raise AudioDecodeError(f"failed to decode audio file {path!s}: {exc}") from exc

    if not decoded:
        raise AudioDecodeError(f"no audio frames decoded from {path!s}")

    samples = np.concatenate(decoded).astype(np.float32, copy=False)
    if offset > 0.0 or limit_samples is not None:
        skip = max(0, int(round((offset - float(anchor_s or 0.0)) * int(target_sr))))
        end = None if limit_samples is None else skip + limit_samples
        sliced = samples[skip:end]
        if sliced.size == 0:
            raise AudioDecodeError(
                f"slice at {offset:.3f}s is past the end of {path!s}"
            )
        return np.ascontiguousarray(sliced)
    return samples


def pcm16_wav_bytes(samples: np.ndarray, *, sr: int) -> bytes:
    """Encode mono float32 samples as PCM16 WAV bytes (stdlib-only).

    Lets byte-contract embedders (the legacy cloud path, duck-typed fakes)
    consume a PyAV-decoded slice without any external encoder binary — the
    replacement for the old ffmpeg libmp3lame re-encode on slicer paths.
    """
    import io
    import wave

    mono = np.asarray(samples, dtype=np.float32).reshape(-1)
    pcm16 = (np.clip(mono, -1.0, 1.0) * 32767.0).astype("<i2")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as fh:
        fh.setnchannels(1)
        fh.setsampwidth(2)
        fh.setframerate(int(sr))
        fh.writeframes(pcm16.tobytes())
    return buf.getvalue()


def load_audio_stereo(path: str | Path) -> tuple[np.ndarray, int]:
    """Decode an audio file to stereo float32 at native sample rate.

    Returns ``(samples, sr)`` where ``samples.shape == (N, 2)``,
    ``samples.dtype == np.float32``, and ``sr`` is the source file's
    native sample rate (no resampling). Mono inputs are duplicated
    across both channels (PyAV's ``AudioResampler(layout="stereo")``
    does the upmix). Stereo inputs pass through preserving sample rate.

    Phase 93 Plan 03 — EXEMPLAR-04. Used by
    :class:`vibemix.learn.audio_cue.ExemplarPlayer` to load the
    packaged CC-BY exemplar bank + DJ-library tracks for headphone
    tutor playback. Stereo (not mono) because the bank tracks + most
    library tracks are stereo and we don't want to collapse them to
    mono for headphone fidelity.

    Mirrors :func:`load_audio_mono`'s PyAV pattern (existing pinned dep
    via the ``[ai-local]`` extra). Raises :class:`ValueError` with the
    substring ``"no audio frames"`` for empty / unreadable inputs so
    callers can distinguish empty-file errors from format-mismatch
    errors (the catch-all
    :class:`AudioDecodeError` used by :func:`load_audio_mono` is for the
    legacy CLAP/CUE ingest path; the lesson-runtime caller wants the
    standard :class:`ValueError` so its ``except (ValueError,)`` block
    surfaces a tighter user-facing reason).
    """
    try:
        import av
    except ImportError as exc:  # pragma: no cover — packaging/runtime drift
        raise AudioDecodeError(f"missing runtime dependency: {exc}") from exc

    chunks: list[np.ndarray] = []
    sr: int | None = None
    try:
        with av.open(str(Path(path).expanduser())) as container:
            stream = container.streams.audio[0]
            sr = int(stream.sample_rate)
            # ``fltp`` (planar float32) over ``flt`` (interleaved): planar
            # gives ``r.to_ndarray()`` shape ``(channels, samples)`` which
            # transposes cleanly to ``(samples, channels)``. The interleaved
            # ``flt`` returns ``(1, channels * samples)`` and requires an
            # extra reshape — same final shape, but planar is the cleaner
            # contract and matches PyAV's documented planar/non-planar
            # split (``av.AudioFormat("fltp").is_planar == True``).
            resampler = av.audio.resampler.AudioResampler(
                format="fltp",
                layout="stereo",
                rate=sr,
            )
            for frame in container.decode(audio=0):
                for r in resampler.resample(frame):
                    # Planar stereo float32 → shape ``(channels, samples)``;
                    # transpose to ``(samples, channels)`` so
                    # ``np.concatenate(axis=0)`` stacks chunks along the
                    # time axis without an extra reshape. The transpose is
                    # a view; ``.astype(..., copy=False)`` is a no-op when
                    # dtype already matches, and ``np.ascontiguousarray``
                    # decouples from PyAV's reused frame buffer.
                    arr = np.ascontiguousarray(r.to_ndarray().T)
                    chunks.append(arr.astype(np.float32, copy=False))
            # Flush any frames the resampler is still buffering on EOF.
            for r in resampler.resample(None):
                arr = np.ascontiguousarray(r.to_ndarray().T)
                chunks.append(arr.astype(np.float32, copy=False))
    except av.error.InvalidDataError as exc:
        # Empty / zero-byte / non-audio inputs: PyAV reports
        # InvalidDataError BEFORE we can probe the stream. Surface as
        # ValueError("no audio frames ...") per the contract.
        raise ValueError(f"load_audio_stereo: no audio frames in {str(path)!r}") from exc

    if not chunks or sr is None:
        raise ValueError(f"load_audio_stereo: no audio frames in {str(path)!r}")

    samples = np.concatenate(chunks, axis=0).astype(np.float32, copy=False)
    # Defensive: some PyAV builds yield shape ``(N,)`` for mono planar
    # despite ``layout="stereo"`` resample — duplicate channels in that
    # case so downstream ``samples[:, 0]`` indexing is consistent.
    if samples.ndim == 1:
        samples = np.stack([samples, samples], axis=1).astype(np.float32, copy=False)
    return samples, sr


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
