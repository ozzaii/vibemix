# SPDX-License-Identifier: Apache-2.0
"""One-shot synth seam — drive the existing live TTS chain for a single line.

The live co-host voice is a LiveKit ``tts.FallbackAdapter`` backed by the single
MOSS provider. The viral auto-mix demo has no room: it knows every reaction line
ahead of time and needs each one as a finished PCM buffer to mix over the deck.
``synthesize_line`` drives that exact adapter's ``.synthesize(text)`` once and
assembles the int16 frames into stereo float32 — reusing the live voice, not
rebuilding one.

These tests use a fake adapter so the seam is verified with no network / no key.
"""
from __future__ import annotations

import asyncio

import numpy as np

from vibemix.agent.line_voice import int16_frames_to_stereo, synthesize_line


class _FakeFrame:
    def __init__(self, samples_int16: np.ndarray, sample_rate: int, num_channels: int) -> None:
        self.data = samples_int16.astype(np.int16).tobytes()
        self.sample_rate = sample_rate
        self.num_channels = num_channels


class _FakeAudio:
    def __init__(self, frame: _FakeFrame) -> None:
        self.frame = frame


class _FakeStream:
    def __init__(self, frames: list[_FakeFrame]) -> None:
        self._frames = frames
        self.closed = False

    def __aiter__(self):
        async def _gen():
            for f in self._frames:
                yield _FakeAudio(f)

        return _gen()

    async def aclose(self) -> None:
        self.closed = True


class _FakeAdapter:
    def __init__(self, frames: list[_FakeFrame]) -> None:
        self._frames = frames
        self.last_text: str | None = None
        self.stream: _FakeStream | None = None

    def synthesize(self, text: str) -> _FakeStream:
        self.last_text = text
        self.stream = _FakeStream(self._frames)
        return self.stream


def test_int16_frames_to_stereo_mono_duplicates_channels() -> None:
    mono = np.array([16384, -16384, 0], dtype=np.int16)
    out = int16_frames_to_stereo([mono], num_channels=1)
    assert out.shape == (3, 2)
    assert out.dtype == np.float32
    assert np.allclose(out[:, 0], out[:, 1])
    assert np.allclose(out[0], 16384 / 32768.0, atol=1e-4)


def test_int16_frames_to_stereo_interleaved_stereo_reshapes() -> None:
    # L,R interleaved for 2 frames of stereo audio.
    inter = np.array([100, 200, 300, 400], dtype=np.int16)
    out = int16_frames_to_stereo([inter], num_channels=2)
    assert out.shape == (2, 2)
    assert np.allclose(out[0], [100 / 32768.0, 200 / 32768.0], atol=1e-4)
    assert np.allclose(out[1], [300 / 32768.0, 400 / 32768.0], atol=1e-4)


def test_int16_frames_to_stereo_empty_is_zero_length_stereo() -> None:
    out = int16_frames_to_stereo([], num_channels=1)
    assert out.shape == (0, 2)
    assert out.dtype == np.float32


def test_synthesize_line_drives_adapter_and_returns_stereo_pcm() -> None:
    frames = [
        _FakeFrame(np.array([8192, -8192], dtype=np.int16), sample_rate=24000, num_channels=1),
        _FakeFrame(np.array([4096, -4096], dtype=np.int16), sample_rate=24000, num_channels=1),
    ]
    adapter = _FakeAdapter(frames)
    audio, sr = asyncio.run(synthesize_line(adapter, "here it comes"))
    assert adapter.last_text == "here it comes"
    assert sr == 24000
    assert audio.shape == (4, 2)
    assert audio.dtype == np.float32
    assert adapter.stream is not None and adapter.stream.closed  # stream drained + closed


def test_synthesize_line_empty_stream_returns_zero_length() -> None:
    adapter = _FakeAdapter([])
    audio, sr = asyncio.run(synthesize_line(adapter, "nothing"))
    assert audio.shape == (0, 2)
    assert sr > 0  # a sane default sample rate, never zero (avoids div-by-zero downstream)
