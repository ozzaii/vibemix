# SPDX-License-Identifier: Apache-2.0
"""Chatterbox-Turbo MLX voice — engine switch + provider plumbing.

The wiring is exercised with a fake engine (no mlx-audio, no model download). The
default engine is Chatterbox; unavailable Chatterbox raises a typed mute reason.
"""
from __future__ import annotations

import asyncio

from livekit.agents import tts as agents_tts

from vibemix.agent.chatterbox_tts import (
    ChatterboxEngine,
    ChatterboxLocalTTS,
    ChatterboxUnavailable,
    configured_temperature,
    engine_selected,
    resolve_ref_path,
)

# ---------------- fake engine seam ----------------

class _FakeEngine(ChatterboxEngine):
    sample_rate = 24000

    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = chunks
        self.calls: list[str] = []

    def synthesize(self, text, on_pcm) -> None:
        self.calls.append(text)
        for c in self._chunks:
            on_pcm(c)


# ---------------- config helpers ----------------

def test_engine_selected_by_default(monkeypatch):
    monkeypatch.delenv("VIBEMIX_TTS_ENGINE", raising=False)
    assert engine_selected() is True


def test_engine_selected_when_env_set(monkeypatch):
    monkeypatch.setenv("VIBEMIX_TTS_ENGINE", "chatterbox")
    assert engine_selected() is True


def test_temperature_defaults_to_0_4(monkeypatch):
    monkeypatch.delenv("VIBEMIX_CHATTERBOX_TEMP", raising=False)
    assert configured_temperature() == 0.4


def test_temperature_override(monkeypatch):
    monkeypatch.setenv("VIBEMIX_CHATTERBOX_TEMP", "0.5")
    assert configured_temperature() == 0.5


def test_ref_path_override_must_exist(monkeypatch, tmp_path):
    ref = tmp_path / "ref.wav"
    ref.write_bytes(b"RIFF....")
    monkeypatch.setenv("VIBEMIX_CHATTERBOX_REF", str(ref))
    assert resolve_ref_path() == ref


def test_ref_path_missing_override_is_none(monkeypatch, tmp_path):
    monkeypatch.setenv("VIBEMIX_CHATTERBOX_REF", str(tmp_path / "nope.wav"))
    assert resolve_ref_path() is None


# ---------------- provider plumbing (fake engine) ----------------

def test_provider_caps_and_identity():
    tts = ChatterboxLocalTTS(engine=_FakeEngine([b"\x00\x00"]))
    assert tts.sample_rate == 24000
    assert tts.num_channels == 1
    assert tts.provider == "chatterbox-mlx"
    assert tts.capabilities.streaming is False


def test_synthesize_pcm_streams_chunks():
    fake = _FakeEngine([b"\x01\x00", b"\x02\x00", b"\x03\x00"])
    tts = ChatterboxLocalTTS(engine=fake)
    out: list[bytes] = []
    tts.synthesize_pcm("here comes the drop [laugh]", out.append)
    assert out == [b"\x01\x00", b"\x02\x00", b"\x03\x00"]
    assert fake.calls == ["here comes the drop [laugh]"]


def test_chunked_stream_pushes_engine_pcm():
    fake = _FakeEngine([b"\x07\x00", b"\x08\x00"])
    tts = ChatterboxLocalTTS(engine=fake)

    pushed: list[bytes] = []

    class _Emitter:
        def initialize(self, **_kw):
            pass

        def push(self, b):
            pushed.append(b)

        def flush(self):
            pass

    async def _drive():
        # ChunkedStream.__init__ schedules a metrics task -> needs a running loop.
        stream = tts.synthesize("[gasp] no way")
        await stream._run(_Emitter())

    asyncio.run(_drive())
    assert pushed == [b"\x07\x00", b"\x08\x00"]


# ---------------- engine switch in build_tts_chain ----------------


def test_default_chain_is_chatterbox(monkeypatch, mocker):
    monkeypatch.delenv("VIBEMIX_TTS_ENGINE", raising=False)
    mocker.patch("vibemix.agent.chatterbox_tts.chatterbox_available", return_value=True)
    fake_chatterbox_cls = mocker.patch("vibemix.agent.chatterbox_tts.ChatterboxLocalTTS")
    mocker.patch.object(agents_tts.FallbackAdapter, "__init__", return_value=None)
    from vibemix.agent.tts_chain import build_tts_chain

    build_tts_chain(mode="direct")
    kwargs = agents_tts.FallbackAdapter.__init__.call_args.kwargs
    assert kwargs["tts"] == [fake_chatterbox_cls.return_value]


def test_chatterbox_selected_and_available_builds_chatterbox(monkeypatch, mocker):
    monkeypatch.setenv("VIBEMIX_TTS_ENGINE", "chatterbox")
    mocker.patch("vibemix.agent.chatterbox_tts.chatterbox_available", return_value=True)
    sentinel = object()
    built = mocker.patch("vibemix.agent.chatterbox_tts.build_chatterbox_adapter", return_value=sentinel)
    from vibemix.agent.tts_chain import build_tts_chain

    assert build_tts_chain(mode="direct") is sentinel
    built.assert_called_once_with(chatterbox=None)


def test_chatterbox_unavailable_raises_without_fallback(monkeypatch, mocker):
    monkeypatch.setenv("VIBEMIX_TTS_ENGINE", "chatterbox")
    mocker.patch("vibemix.agent.chatterbox_tts.chatterbox_available", return_value=False)
    mocker.patch(
        "vibemix.agent.chatterbox_tts.chatterbox_unavailable_reason", return_value="no mlx-audio"
    )
    from vibemix.agent.tts_chain import build_tts_chain

    try:
        build_tts_chain(mode="direct")
    except ChatterboxUnavailable as exc:
        assert "no mlx-audio" in str(exc)
    else:  # pragma: no cover - assertion clarity
        raise AssertionError("unavailable Chatterbox must not fall back")
