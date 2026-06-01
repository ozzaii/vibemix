# SPDX-License-Identifier: Apache-2.0
"""DEBRIEF-04: synthesized MOSS TLDR audio is MP3 (libmp3lame via PyAV).

Real MOSS model calls are out of scope for offline tests — we verify the PyAV
encode pipeline produces valid MP3 magic bytes when fed synthetic line audio.

PyAV libmp3lame availability was verified at Plan 29-00 Wave 0 (A3).
"""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pytest

from vibemix.agent.local_tts import LocalTTSUnavailable
from vibemix.debrief.tldr import (
    DebriefGenerationError,
    _encode_pcm_to_mp3,
    synthesize_moss_mp3,
)


def _make_silent_pcm(seconds: float, sample_rate: int = 24000) -> bytes:
    """24kHz mono int16 silence — sufficient to drive a real encode."""
    n_samples = int(seconds * sample_rate)
    return b"\x00\x00" * n_samples


def test_pcm_to_mp3_produces_mp3_magic_bytes():
    """The encoded output starts with an MP3 frame sync.

    MP3 frame sync is 0xFF followed by 0xE0-0xFF on the second byte.
    Some encoders prepend an ID3 tag (b"ID3") instead — we accept both.
    """
    pcm = _make_silent_pcm(seconds=2.0)
    mp3 = _encode_pcm_to_mp3(pcm, sample_rate=24000)
    assert len(mp3) > 0
    # MP3 frame sync OR ID3 tag.
    assert mp3.startswith(b"ID3") or (mp3[0] == 0xFF and (mp3[1] & 0xE0) == 0xE0)


def test_synthesize_moss_mp3_happy_path():
    """End-to-end: mocked MOSS line audio → PCM → MP3 bytes."""
    adapter = object()
    adapter_factory = MagicMock(return_value=adapter)
    seen: list[str] = []

    async def fake_line_synthesizer(adapter_arg, text):
        assert adapter_arg is adapter
        seen.append(text)
        return np.zeros((24000, 2), dtype=np.float32), 24000

    mp3 = synthesize_moss_mp3(
        "Hello world",
        adapter_factory=adapter_factory,
        line_synthesizer=fake_line_synthesizer,
    )
    assert isinstance(mp3, bytes)
    assert len(mp3) > 0
    assert seen == ["Hello world"]
    adapter_factory.assert_called_once_with()


def test_synthesize_moss_mp3_raises_on_empty_audio():
    """MOSS returns no audio → typed error."""
    async def empty_line_synthesizer(_adapter, _text):
        return np.zeros((0, 2), dtype=np.float32), 24000

    with pytest.raises(DebriefGenerationError) as ei:
        synthesize_moss_mp3(
            "x",
            adapter_factory=lambda: object(),
            line_synthesizer=empty_line_synthesizer,
        )
    assert ei.value.reason == "tldr_generation_failed"


def test_synthesize_moss_mp3_raises_on_line_synth_exception():
    async def failing_line_synthesizer(_adapter, _text):
        raise RuntimeError("model crashed")

    with pytest.raises(DebriefGenerationError) as ei:
        synthesize_moss_mp3(
            "x",
            adapter_factory=lambda: object(),
            line_synthesizer=failing_line_synthesizer,
        )
    assert ei.value.reason == "tldr_generation_failed"
    assert "model crashed" in ei.value.message


def test_synthesize_moss_mp3_raises_on_unavailable_model():
    def missing_model_factory():
        raise LocalTTSUnavailable("missing MOSS model")

    with pytest.raises(DebriefGenerationError) as ei:
        synthesize_moss_mp3("x", adapter_factory=missing_model_factory)
    assert ei.value.reason == "tldr_generation_failed"
    assert "MOSS TTS unavailable" in ei.value.message
