# SPDX-License-Identifier: Apache-2.0
"""Local MOSS-TTS-Nano voice — the free, key-free, never-mute co-host voice.

Covers: the mono int16 downmix, opt-in gating (VIBEMIX_LOCAL_TTS + cached model),
the native-sample-rate probe, the FallbackAdapter wiring (MOSS-only when enabled),
and the LiveKit ChunkedStream plumbing via a fake engine (no 728MB model needed).
A guarded integration test exercises the real ONNX engine when it's cached.
"""
from __future__ import annotations

import asyncio
import json

import numpy as np
import pytest

from vibemix.agent.local_tts import (
    MossEngine,
    MossLocalTTS,
    _read_native_sample_rate,
    local_tts_enabled,
    pcm16_mono_le,
    resolve_model_dir,
)

# ---------------- pure helpers ----------------

def test_pcm16_mono_le_downmixes_stereo():
    # (channels, samples) float32 -> mono int16 LE; length is samples*2 bytes.
    stereo = np.array([[0.5, 0.5, 0.5], [-0.5, -0.5, -0.5]], dtype=np.float32)  # avg -> 0.0
    out = pcm16_mono_le(stereo)
    assert len(out) == 3 * 2  # 3 samples, int16
    samples = np.frombuffer(out, dtype="<i2")
    assert samples.shape == (3,)
    assert np.all(np.abs(samples) <= 1)  # 0.0 average -> ~0


def test_pcm16_mono_le_accepts_mono_and_clips():
    mono = np.array([2.0, -2.0, 0.0], dtype=np.float32)  # out of [-1,1] -> clip
    samples = np.frombuffer(pcm16_mono_le(mono), dtype="<i2")
    assert samples[0] == 32767  # +clip
    assert samples[1] == -32767  # -clip (round(-1*32767))
    assert samples[2] == 0


# ---------------- gating ----------------

def _fake_model_dir(tmp_path, sample_rate=44100):
    (tmp_path / "browser_poc_manifest.json").write_text(
        json.dumps({"model_files": {"codec_meta": "codec.json"}}), encoding="utf-8"
    )
    (tmp_path / "codec.json").write_text(
        json.dumps({"codec_config": {"sample_rate": sample_rate, "channels": 2}}), encoding="utf-8"
    )
    return tmp_path


def test_disabled_without_flag(monkeypatch, tmp_path):
    monkeypatch.setenv("VIBEMIX_MOSS_TTS_DIR", str(_fake_model_dir(tmp_path)))
    monkeypatch.delenv("VIBEMIX_LOCAL_TTS", raising=False)
    assert local_tts_enabled() is False


def test_disabled_when_model_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("VIBEMIX_LOCAL_TTS", "1")
    monkeypatch.setenv("VIBEMIX_MOSS_TTS_DIR", str(tmp_path / "nope"))  # no manifest
    assert resolve_model_dir() is None
    assert local_tts_enabled() is False


def test_enabled_with_flag_and_cached_model(monkeypatch, tmp_path):
    monkeypatch.setenv("VIBEMIX_LOCAL_TTS", "true")
    monkeypatch.setenv("VIBEMIX_MOSS_TTS_DIR", str(_fake_model_dir(tmp_path)))
    assert resolve_model_dir() == tmp_path
    assert local_tts_enabled() is True


def test_read_native_sample_rate(monkeypatch, tmp_path):
    _fake_model_dir(tmp_path, sample_rate=48000)
    assert _read_native_sample_rate(tmp_path) == 48000


def test_read_native_sample_rate_defaults_on_broken_meta(tmp_path):
    # no manifest at all -> safe default (the model genuinely emits 48k)
    assert _read_native_sample_rate(tmp_path) == 48000


# ---------------- FallbackAdapter wiring ----------------

def test_moss_leads_chain_when_enabled(mocker, monkeypatch):
    monkeypatch.delenv("CARTESIA_API_KEY", raising=False)  # keep Cartesia out of the chain
    from livekit.agents import tts as agents_tts

    mocker.patch("vibemix.agent.local_tts.local_tts_enabled", return_value=True)
    fake_moss_cls = mocker.patch("vibemix.agent.local_tts.MossLocalTTS")  # avoid real construct/prewarm
    mocker.patch.object(agents_tts.FallbackAdapter, "__init__", return_value=None)

    from vibemix.agent.tts_chain import build_tts_chain

    build_tts_chain(gemini_api_key="g", mode="direct")

    chain = agents_tts.FallbackAdapter.__init__.call_args.kwargs["tts"]
    assert chain[0] is fake_moss_cls.return_value  # MOSS leads
    fake_moss_cls.return_value.prewarm.assert_called_once()  # background load kicked
    assert len(chain) == 1  # MOSS is the only voice — zero paid fallback (cost + no key)


def test_moss_absent_when_disabled(mocker, monkeypatch):
    monkeypatch.delenv("CARTESIA_API_KEY", raising=False)
    monkeypatch.delenv("VIBEMIX_LOCAL_TTS", raising=False)
    from livekit.agents import tts as agents_tts

    mocker.patch.object(agents_tts.FallbackAdapter, "__init__", return_value=None)
    from vibemix.agent.tts_chain import build_tts_chain

    build_tts_chain(gemini_api_key="g", mode="direct")

    chain = agents_tts.FallbackAdapter.__init__.call_args.kwargs["tts"]
    # first entry is a Gemini native, not a MossLocalTTS
    assert type(chain[0]).__name__ != "MossLocalTTS"


# ---------------- ChunkedStream plumbing (fake engine, no model) ----------------

class _FakeEngine(MossEngine):
    def __init__(self, sample_rate=24000, chunks=4, samples_per_chunk=2400):
        self.sample_rate = sample_rate
        self._chunks = chunks
        self._spc = samples_per_chunk

    def synthesize(self, text, on_pcm):
        for _ in range(self._chunks):
            on_pcm(pcm16_mono_le(np.full(self._spc, 0.1, dtype=np.float32)))


class _BoomEngine(MossEngine):
    sample_rate = 24000

    def synthesize(self, text, on_pcm):
        raise RuntimeError("engine exploded")


def test_synthesize_streams_all_pushed_pcm():
    fake = _FakeEngine(sample_rate=24000, chunks=4, samples_per_chunk=2400)
    tts = MossLocalTTS(engine=fake, sample_rate=24000)

    async def _run():
        total_samples = 0
        async with tts.synthesize("yo, that drop is filthy") as stream:
            async for ev in stream:
                assert ev.frame.sample_rate == 24000
                assert ev.frame.num_channels == 1
                total_samples += ev.frame.samples_per_channel
        return total_samples

    total = asyncio.run(_run())
    pushed = 4 * 2400
    # every pushed sample reaches the emitter; LiveKit may append one tiny
    # end-of-segment marker (sr//100 samples), so allow that single margin.
    assert pushed <= total <= pushed + tts.sample_rate // 100


def test_synthesize_surfaces_engine_error():
    from livekit.agents._exceptions import APIError
    from livekit.agents.types import APIConnectOptions

    tts = MossLocalTTS(engine=_BoomEngine(), sample_rate=24000)

    async def _run():
        with pytest.raises(APIError):
            async with tts.synthesize("x", conn_options=APIConnectOptions(max_retry=0)) as stream:
                async for _ev in stream:
                    pass

    asyncio.run(_run())


# ---------------- guarded real-model integration ----------------

@pytest.mark.slow
def test_real_engine_synthesizes_when_cached():
    """End-to-end with the real vendored ONNX engine — only when the model is cached."""
    model_dir = resolve_model_dir()
    if model_dir is None:
        pytest.skip("MOSS ONNX model not cached (~/.cache/vibemix/moss-tts-onnx)")
    pytest.importorskip("onnxruntime")
    pytest.importorskip("sentencepiece")

    tts = MossLocalTTS(model_dir=model_dir)
    assert tts.sample_rate == 48000
    assert tts.num_channels == 1

    async def _run():
        total = 0
        async with tts.synthesize("Yo, that drop on deck B is filthy.") as stream:
            async for ev in stream:
                total += ev.frame.samples_per_channel
        return total

    total = asyncio.run(_run())
    assert total > 48000 * 0.5  # at least ~0.5s of real audio
