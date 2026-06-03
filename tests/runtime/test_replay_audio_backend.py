# SPDX-License-Identifier: Apache-2.0
"""Replay capture backend unit coverage."""

from __future__ import annotations

import time
import wave
from pathlib import Path

import numpy as np
import pytest

from vibemix.platform._audio_replay import (
    ReplayAudioBackend,
    maybe_wrap_replay_audio_backend,
    replay_session_from_env,
)


class _Delegate:
    def find_device(self, name_substring: str, kind: str) -> int:
        return 123

    def describe_capture_input(
        self,
        device_index: int,
        *,
        requested_device: str,
        opened_channels: int,
    ) -> dict[str, object]:
        return {
            "requested_device": requested_device,
            "device_name": "delegate",
            "input_channels": 2,
            "opened_channels": opened_channels,
            "sample_rate": 48000,
        }


def _write_wav(path: Path, *, sample_rate: int = 1000, channels: int = 1) -> None:
    t = np.linspace(0.0, 0.04, 40, endpoint=False, dtype=np.float32)
    mono = (0.25 * np.sin(2.0 * np.pi * 100.0 * t)).astype(np.float32)
    if channels == 1:
        pcm = mono[:, None]
    else:
        pcm = np.repeat(mono[:, None], channels, axis=1)
    data = np.clip(pcm * 32767.0, -32768, 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(data.tobytes())


def test_replay_session_env_gate_default_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VIBEMIX_REPLAY_SESSION", raising=False)
    delegate = _Delegate()

    assert replay_session_from_env() is None
    assert maybe_wrap_replay_audio_backend(delegate) is delegate


def test_replay_session_env_gate_wraps_backend(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    session = tmp_path / "session"
    session.mkdir()
    _write_wav(session / "input.wav")
    delegate = _Delegate()

    monkeypatch.setenv("VIBEMIX_REPLAY_SESSION", str(session))
    wrapped = maybe_wrap_replay_audio_backend(delegate)

    assert replay_session_from_env() == session
    assert isinstance(wrapped, ReplayAudioBackend)
    assert wrapped._delegate is delegate


def test_replay_backend_describes_input_wav(tmp_path: Path) -> None:
    session = tmp_path / "session"
    session.mkdir()
    _write_wav(session / "input.wav", sample_rate=22050, channels=2)

    backend = ReplayAudioBackend(_Delegate(), session_dir=session)

    assert backend.find_device("BlackHole", "input") == backend._REPLAY_DEVICE_INDEX
    assert backend.find_device("anything", "output") == 123
    assert backend.describe_capture_input(
        -1,
        requested_device="BlackHole 2ch",
        opened_channels=4,
    ) == {
        "requested_device": "BlackHole 2ch",
        "device_name": "Replay Session (session)",
        "input_channels": 2,
        "opened_channels": 4,
        "sample_rate": 22050,
        "replay_session": str(session),
        "replay_input_wav": str(session / "input.wav"),
    }


def test_replay_capture_stream_feeds_callback_blocks(tmp_path: Path) -> None:
    session = tmp_path / "session"
    session.mkdir()
    _write_wav(session / "input.wav", sample_rate=1000, channels=1)
    backend = ReplayAudioBackend(_Delegate(), session_dir=session)
    seen: list[np.ndarray] = []

    def callback(indata, frames, time_info, status):
        seen.append(np.array(indata, copy=True))
        assert frames == 10
        assert status is None

    stream = backend.open_capture(
        -1,
        sample_rate=1000,
        channels=2,
        block_size=10,
        callback=callback,
    )

    stream.start()
    deadline = time.time() + 1.0
    while len(seen) < 4 and time.time() < deadline:
        time.sleep(0.01)
    stream.stop()

    assert len(seen) >= 4
    assert all(block.shape == (10, 2) for block in seen[:4])
    assert all(block.dtype == np.float32 for block in seen[:4])
    assert max(float(np.max(np.abs(block[:, 0]))) for block in seen[:4]) > 0.1
    assert all(float(np.max(np.abs(block[:, 1]))) == 0.0 for block in seen[:4])


def test_replay_backend_requires_input_wav(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        ReplayAudioBackend(_Delegate(), session_dir=tmp_path / "missing")
