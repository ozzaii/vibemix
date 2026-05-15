# SPDX-License-Identifier: Apache-2.0
"""DEBRIEF-04: synthesized TLDR audio is MP3 (libmp3lame via PyAV).

Real Gemini TTS calls are out of scope for offline tests — we verify
the PyAV encode pipeline produces valid MP3 magic bytes when fed a
synthetic PCM buffer.

PyAV libmp3lame availability was verified at Plan 29-00 Wave 0 (A3).
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from vibemix.debrief.tldr import (
    DebriefGenerationError,
    _encode_pcm_to_mp3,
    synthesize_achird_mp3,
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


def test_synthesize_achird_mp3_happy_path():
    """End-to-end: mocked TTS response → PCM → MP3 bytes."""
    pcm = _make_silent_pcm(seconds=1.0)
    inline_part = SimpleNamespace(
        inline_data=SimpleNamespace(data=pcm),
    )
    candidate = SimpleNamespace(
        content=SimpleNamespace(parts=[inline_part])
    )
    response = SimpleNamespace(candidates=[candidate])

    client = MagicMock()
    client.models.generate_content.return_value = response
    mp3 = synthesize_achird_mp3(client, "Hello world")
    assert isinstance(mp3, bytes)
    assert len(mp3) > 0


def test_synthesize_achird_mp3_raises_on_empty_pcm():
    """TTS returns no audio → typed error."""
    inline_part = SimpleNamespace(inline_data=SimpleNamespace(data=b""))
    candidate = SimpleNamespace(content=SimpleNamespace(parts=[inline_part]))
    response = SimpleNamespace(candidates=[candidate])
    client = MagicMock()
    client.models.generate_content.return_value = response
    with pytest.raises(DebriefGenerationError) as ei:
        synthesize_achird_mp3(client, "x")
    assert ei.value.reason == "tldr_generation_failed"


def test_synthesize_achird_mp3_raises_on_gemini_exception():
    client = MagicMock()
    client.models.generate_content.side_effect = RuntimeError("rate limited")
    with pytest.raises(DebriefGenerationError) as ei:
        synthesize_achird_mp3(client, "x")
    assert ei.value.reason == "tldr_generation_failed"


def test_uses_achird_voice_in_tts_call():
    """The voice name is passed in speech_config."""
    pcm = _make_silent_pcm(seconds=0.5)
    inline_part = SimpleNamespace(inline_data=SimpleNamespace(data=pcm))
    candidate = SimpleNamespace(content=SimpleNamespace(parts=[inline_part]))
    response = SimpleNamespace(candidates=[candidate])
    client = MagicMock()
    client.models.generate_content.return_value = response
    synthesize_achird_mp3(client, "x")
    call_kwargs = client.models.generate_content.call_args.kwargs
    voice_cfg = (
        call_kwargs["config"]["speech_config"]["voice_config"]
        ["prebuilt_voice_config"]["voice_name"]
    )
    assert voice_cfg == "Achird"
