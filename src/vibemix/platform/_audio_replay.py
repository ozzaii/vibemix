# SPDX-License-Identifier: Apache-2.0
"""Env-gated replay capture backend for QA runs.

This module is deliberately narrow: it only substitutes the *input capture*
stream when ``VIBEMIX_REPLAY_SESSION`` points at a recorded session directory.
The replay stream feeds the same sounddevice-shaped callback the live CoreAudio
stream would have called, so the normal audio buffers, deck-audio splitter, and
state refresh loop remain the only downstream writers.
"""

from __future__ import annotations

import os
import threading
import time
import wave
from pathlib import Path
from typing import Any

import numpy as np

from vibemix.audio.resample import resample_audio
from vibemix.platform.audio import AudioCallback, AudioStream, Kind


def replay_session_from_env(environ: dict[str, str] | None = None) -> Path | None:
    """Return the replay session dir when the hard env gate is enabled."""

    env = os.environ if environ is None else environ
    raw = str(env.get("VIBEMIX_REPLAY_SESSION") or "").strip()
    return Path(raw).expanduser() if raw else None


def maybe_wrap_replay_audio_backend(backend: Any) -> Any:
    """Wrap ``backend`` only when ``VIBEMIX_REPLAY_SESSION`` is set."""

    session_dir = replay_session_from_env()
    if session_dir is None:
        return backend
    return ReplayAudioBackend(backend, session_dir=session_dir)


class ReplayAudioBackend:
    """Delegate everything except input capture to a real audio backend."""

    _REPLAY_DEVICE_INDEX = -911

    def __init__(self, delegate: Any, *, session_dir: Path) -> None:
        self._delegate = delegate
        self.session_dir = Path(session_dir).expanduser()
        self.input_wav = self.session_dir / "input.wav"
        self._info = _wav_info(self.input_wav)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._delegate, name)

    def find_device(self, name_substring: str, kind: Kind) -> int:
        if kind == "input":
            return self._REPLAY_DEVICE_INDEX
        return self._delegate.find_device(name_substring, kind)

    def describe_capture_input(
        self,
        device_index: int,
        *,
        requested_device: str,
        opened_channels: int,
    ) -> dict[str, object]:
        return {
            "requested_device": requested_device,
            "device_name": f"Replay Session ({self.session_dir.name})",
            "input_channels": int(self._info["channels"]),
            "opened_channels": int(opened_channels),
            "sample_rate": int(self._info["sample_rate"]),
            "replay_session": str(self.session_dir),
            "replay_input_wav": str(self.input_wav),
        }

    def open_capture(
        self,
        device_index: int,
        *,
        sample_rate: int,
        channels: int,
        block_size: int,
        callback: AudioCallback,
    ) -> AudioStream:
        return ReplayCaptureStream(
            self.input_wav,
            sample_rate=sample_rate,
            channels=channels,
            block_size=block_size,
            callback=callback,
        )


class ReplayCaptureStream:
    """AudioStream that feeds ``input.wav`` into the existing capture callback."""

    def __init__(
        self,
        wav_path: Path,
        *,
        sample_rate: int,
        channels: int,
        block_size: int,
        callback: AudioCallback,
    ) -> None:
        self._wav_path = Path(wav_path)
        self._sample_rate = max(1, int(sample_rate))
        self._channels = max(1, int(channels))
        self._block_size = max(1, int(block_size))
        self._callback = callback
        self._closed = threading.Event()
        self._started = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def latency_ms(self) -> float:
        return 0.0

    def start(self) -> None:
        if self._started.is_set():
            return
        self._started.set()
        self._thread = threading.Thread(
            target=self._run,
            name="vibemix-replay-capture",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._closed.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=1.0)

    def close(self) -> None:
        self.stop()

    def _run(self) -> None:
        audio = _read_wav_float32(
            self._wav_path,
            target_sample_rate=self._sample_rate,
            target_channels=self._channels,
        )
        if audio.size == 0:
            return
        total = int(audio.shape[0])
        for start in range(0, total, self._block_size):
            if self._closed.is_set():
                return
            block = audio[start : start + self._block_size]
            if block.shape[0] < self._block_size:
                pad = np.zeros(
                    (self._block_size - block.shape[0], self._channels),
                    dtype=np.float32,
                )
                block = np.concatenate([block, pad], axis=0)
            self._callback(block, int(block.shape[0]), {}, None)
            time.sleep(block.shape[0] / float(self._sample_rate))


def _wav_info(path: Path) -> dict[str, int]:
    if not path.exists():
        raise FileNotFoundError(f"VIBEMIX_REPLAY_SESSION missing input.wav: {path}")
    with wave.open(str(path), "rb") as wf:
        return {
            "channels": int(wf.getnchannels()),
            "sample_rate": int(wf.getframerate()),
            "frames": int(wf.getnframes()),
        }


def _read_wav_float32(
    path: Path,
    *,
    target_sample_rate: int,
    target_channels: int,
) -> np.ndarray:
    with wave.open(str(path), "rb") as wf:
        source_sr = int(wf.getframerate())
        source_channels = int(wf.getnchannels())
        sample_width = int(wf.getsampwidth())
        raw = wf.readframes(wf.getnframes())

    if sample_width == 2:
        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    elif sample_width == 4:
        samples = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
    elif sample_width == 1:
        samples = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    else:
        raise ValueError(f"unsupported WAV sample width {sample_width} in {path}")

    if source_channels > 1:
        samples = samples.reshape(-1, source_channels)
    else:
        samples = samples.reshape(-1, 1)

    if source_sr != target_sample_rate:
        resampled = [
            resample_audio(
                samples[:, idx],
                source_sr=source_sr,
                target_sr=target_sample_rate,
            ).astype(np.float32, copy=False)
            for idx in range(samples.shape[1])
        ]
        min_len = min((arr.size for arr in resampled), default=0)
        samples = (
            np.stack([arr[:min_len] for arr in resampled], axis=1)
            if min_len > 0
            else np.zeros((0, samples.shape[1]), dtype=np.float32)
        )

    if samples.shape[1] > target_channels:
        samples = samples[:, :target_channels]
    elif samples.shape[1] < target_channels:
        pad = np.zeros(
            (samples.shape[0], target_channels - samples.shape[1]),
            dtype=np.float32,
        )
        samples = np.concatenate([samples, pad], axis=1)
    return np.clip(samples, -1.0, 1.0).astype(np.float32, copy=False)
