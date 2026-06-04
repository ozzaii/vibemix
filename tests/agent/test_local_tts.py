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
import sys

import numpy as np
import pytest

from vibemix.agent.local_tts import (
    LocalTTSUnavailable,
    MossEngine,
    MossLocalTTS,
    _OrtCpuEngine,
    _read_native_sample_rate,
    build_local_tts_adapter,
    candidate_model_dir,
    local_tts_enabled,
    model_status,
    pcm16_mono_le,
    resolve_model_dir,
)
from vibemix.voice_presets import (
    LEGACY_CLOUD_TTS_VOICES,
    MOSS_UI_VOICE_OPTIONS,
    select_moss_voice_row,
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


def test_enabled_without_flag_when_model_cached(monkeypatch, tmp_path):
    monkeypatch.setenv("VIBEMIX_MOSS_TTS_DIR", str(_fake_model_dir(tmp_path)))
    monkeypatch.delenv("VIBEMIX_LOCAL_TTS", raising=False)
    assert local_tts_enabled() is True


def test_disabled_by_explicit_off(monkeypatch, tmp_path):
    monkeypatch.setenv("VIBEMIX_MOSS_TTS_DIR", str(_fake_model_dir(tmp_path)))
    monkeypatch.setenv("VIBEMIX_LOCAL_TTS", "0")
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


def test_resolves_bundled_pyinstaller_model_before_dev_cache(monkeypatch, tmp_path):
    bundled = (
        tmp_path
        / "_internal"
        / "models"
        / "moss-tts-onnx"
        / "MOSS-TTS-Nano-100M-ONNX"
    )
    bundled.mkdir(parents=True)
    _fake_model_dir(bundled)
    monkeypatch.delenv("VIBEMIX_MOSS_TTS_DIR", raising=False)
    monkeypatch.setenv("VIBEMIX_CACHE_DIR", str(tmp_path / "empty-cache"))
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path / "_internal"), raising=False)

    assert candidate_model_dir() == bundled
    assert resolve_model_dir() == bundled
    assert local_tts_enabled() is True


def test_model_status_reports_missing_manifest(monkeypatch, tmp_path):
    missing = tmp_path / "missing-moss"
    monkeypatch.setenv("VIBEMIX_MOSS_TTS_DIR", str(missing))

    status = model_status()

    assert status == {
        "installed": False,
        "path": str(missing),
        "missing": ["browser_poc_manifest.json"],
        "mismatched": [],
    }


def test_model_status_checks_manifest_referenced_files(monkeypatch, tmp_path):
    model_dir = tmp_path / "MOSS-TTS-Nano-100M-ONNX"
    codec_dir = tmp_path / "MOSS-Audio-Tokenizer-Nano-ONNX"
    model_dir.mkdir()
    codec_dir.mkdir()
    (model_dir / "browser_poc_manifest.json").write_text(
        json.dumps(
            {
                "model_files": {
                    "tts_meta": "tts_browser_onnx_meta.json",
                    "codec_meta": "../MOSS-Audio-Tokenizer-Nano-ONNX/codec_browser_onnx_meta.json",
                    "tokenizer_model": "tokenizer.model",
                }
            }
        ),
        encoding="utf-8",
    )
    (model_dir / "tts_browser_onnx_meta.json").write_text(
        json.dumps(
            {
                "files": {"prefill": "moss_tts_prefill.onnx"},
                "external_data_files": {"moss_tts_prefill.onnx": ["moss_tts_global_shared.data"]},
            }
        ),
        encoding="utf-8",
    )
    (codec_dir / "codec_browser_onnx_meta.json").write_text(
        json.dumps(
            {
                "files": {"decode_step": "moss_audio_tokenizer_decode_step.onnx"},
                "external_data_files": {
                    "moss_audio_tokenizer_decode_step.onnx": [
                        "moss_audio_tokenizer_decode_shared.data"
                    ]
                },
            }
        ),
        encoding="utf-8",
    )
    for path in (
        model_dir / "tokenizer.model",
        model_dir / "moss_tts_prefill.onnx",
        model_dir / "moss_tts_global_shared.data",
        codec_dir / "moss_audio_tokenizer_decode_step.onnx",
        codec_dir / "moss_audio_tokenizer_decode_shared.data",
    ):
        path.write_bytes(b"x")
    monkeypatch.setenv("VIBEMIX_MOSS_TTS_DIR", str(model_dir))

    assert model_status()["installed"] is True

    (codec_dir / "moss_audio_tokenizer_decode_shared.data").unlink()
    status = model_status()
    assert status["installed"] is False
    assert status["missing"] == [
        "MOSS-Audio-Tokenizer-Nano-ONNX/moss_audio_tokenizer_decode_shared.data"
    ]


def test_read_native_sample_rate(monkeypatch, tmp_path):
    _fake_model_dir(tmp_path, sample_rate=48000)
    assert _read_native_sample_rate(tmp_path) == 48000


def test_read_native_sample_rate_defaults_on_broken_meta(tmp_path):
    # no manifest at all -> safe default (the model genuinely emits 48k)
    assert _read_native_sample_rate(tmp_path) == 48000


def test_select_moss_voice_row_uses_requested_voice():
    voices = [{"voice": "Junhao"}, {"voice": "Adam"}, {"voice": "Bella"}]

    row = select_moss_voice_row(voices, "Bella")

    assert row["voice"] == "Bella"


def test_moss_ui_voice_options_are_real_product_subset():
    """Settings must expose real MOSS names, never retired cloud voice ids."""
    expected = (
        "Adam",
        "Nathan",
        "Ava",
        "Bella",
        "Xiaoyu",
        "Yuewen",
        "Lingyu",
        "Soyo",
        "Mei",
        "Arisa",
        "Saki",
        "Mortis",
        "Umiri",
        "Anon",
    )

    assert MOSS_UI_VOICE_OPTIONS == expected
    assert not (set(MOSS_UI_VOICE_OPTIONS) & LEGACY_CLOUD_TTS_VOICES)


def test_select_moss_voice_row_falls_back_to_default_not_first_voice():
    voices = [{"voice": "Junhao"}, {"voice": "Adam"}, {"voice": "Bella"}]

    row = select_moss_voice_row(voices, "kore")

    assert row["voice"] == "Adam"


# ---------------- FallbackAdapter wiring ----------------

def test_moss_leads_chain_when_enabled(mocker, monkeypatch):
    monkeypatch.delenv("CARTESIA_API_KEY", raising=False)
    from livekit.agents import tts as agents_tts

    mocker.patch("vibemix.agent.local_tts.local_tts_enabled", return_value=True)
    fake_moss_cls = mocker.patch("vibemix.agent.local_tts.MossLocalTTS")  # avoid real construct/prewarm
    mocker.patch.object(agents_tts.FallbackAdapter, "__init__", return_value=None)

    from vibemix.agent.tts_chain import build_tts_chain

    build_tts_chain(mode="direct")

    chain = agents_tts.FallbackAdapter.__init__.call_args.kwargs["tts"]
    assert chain[0] is fake_moss_cls.return_value  # MOSS leads
    fake_moss_cls.return_value.prewarm.assert_called_once()  # background load kicked
    assert len(chain) == 1  # MOSS is the only voice — zero paid fallback (cost + no key)


def test_moss_absent_fails_loud(mocker):
    mocker.patch("vibemix.agent.local_tts.local_tts_enabled", return_value=False)
    mocker.patch(
        "vibemix.agent.local_tts.local_tts_unavailable_reason",
        return_value="MOSS model missing",
    )

    with pytest.raises(LocalTTSUnavailable, match="MOSS model missing"):
        build_local_tts_adapter()


# ---------------- ChunkedStream plumbing (fake engine, no model) ----------------

class _FakeEngine(MossEngine):
    def __init__(self, sample_rate=24000, chunks=4, samples_per_chunk=2400):
        self.sample_rate = sample_rate
        self._chunks = chunks
        self._spc = samples_per_chunk

    def synthesize(self, text, on_pcm):
        for _ in range(self._chunks):
            on_pcm(pcm16_mono_le(np.full(self._spc, 0.1, dtype=np.float32)))


class _RetargetableEngine(_FakeEngine):
    def __init__(self, sample_rate=24000, chunks=1, samples_per_chunk=10):
        super().__init__(sample_rate=sample_rate, chunks=chunks, samples_per_chunk=samples_per_chunk)
        self.voice_prompts: list[str] = []

    def set_voice_prompt(self, voice: str) -> str:
        self.voice_prompts.append(voice)
        return voice


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


def test_synthesize_pcm_uses_engine_directly():
    fake = _FakeEngine(sample_rate=24000, chunks=2, samples_per_chunk=10)
    tts = MossLocalTTS(engine=fake, sample_rate=24000)
    chunks: list[bytes] = []

    tts.synthesize_pcm("coach this line", chunks.append)

    assert len(chunks) == 2


def test_set_voice_rebuilds_engine_on_next_synthesis(monkeypatch, tmp_path):
    first = _FakeEngine(sample_rate=24000, chunks=1, samples_per_chunk=10)
    loaded: list[str] = []

    def load(_model_dir, voice, _thread_count):
        loaded.append(voice)
        return _FakeEngine(sample_rate=24000, chunks=1, samples_per_chunk=10)

    monkeypatch.setattr("vibemix.agent.local_tts._OrtCpuEngine.load", load)
    tts = MossLocalTTS(model_dir=tmp_path, voice="Adam", engine=first, sample_rate=24000)

    tts.synthesize_pcm("first", lambda _pcm: None)
    tts.set_voice("Bella")
    tts.synthesize_pcm("second", lambda _pcm: None)

    assert loaded == ["Bella"]


def test_set_voice_retargets_warm_engine_without_reload(monkeypatch, tmp_path):
    warm = _RetargetableEngine(sample_rate=24000)

    def load(_model_dir, voice, _thread_count):
        raise AssertionError(f"warm voice swap reloaded engine for {voice}")

    monkeypatch.setattr("vibemix.agent.local_tts._OrtCpuEngine.load", load)
    tts = MossLocalTTS(model_dir=tmp_path, voice="Adam", engine=warm, sample_rate=24000)

    tts.synthesize_pcm("first", lambda _pcm: None)
    tts.set_voice("Bella")
    tts.synthesize_pcm("second", lambda _pcm: None)

    assert tts._engine is warm
    assert warm.voice_prompts == ["Bella"]


def test_set_voice_normalizes_retired_cloud_voice_ids(monkeypatch, tmp_path):
    loaded: list[str] = []

    def load(_model_dir, voice, _thread_count):
        loaded.append(voice)
        return _FakeEngine(sample_rate=24000, chunks=1, samples_per_chunk=10)

    monkeypatch.setattr("vibemix.agent.local_tts._OrtCpuEngine.load", load)
    tts = MossLocalTTS(
        model_dir=tmp_path,
        voice="Bella",
        engine=_FakeEngine(sample_rate=24000, chunks=1, samples_per_chunk=10),
        sample_rate=24000,
    )

    tts.set_voice("kore")
    tts.synthesize_pcm("legacy", lambda _pcm: None)

    assert loaded == ["Adam"]


def test_set_voice_retargets_warm_engine_with_normalized_cloud_voice(monkeypatch, tmp_path):
    warm = _RetargetableEngine(sample_rate=24000)

    def load(_model_dir, voice, _thread_count):
        raise AssertionError(f"warm voice swap reloaded engine for {voice}")

    monkeypatch.setattr("vibemix.agent.local_tts._OrtCpuEngine.load", load)
    tts = MossLocalTTS(model_dir=tmp_path, voice="Bella", engine=warm, sample_rate=24000)

    tts.set_voice("kore")
    tts.synthesize_pcm("legacy", lambda _pcm: None)

    assert tts._engine is warm
    assert warm.voice_prompts == ["Adam"]


def test_ort_cpu_engine_set_voice_prompt_swaps_prompt_codes():
    class _Runtime:
        def list_builtin_voices(self):
            return [
                {"voice": "Adam", "prompt_audio_codes": [[1, 2], [3, 4]]},
                {"voice": "Bella", "prompt_audio_codes": [[5, 6], [7, 8]]},
            ]

    engine = _OrtCpuEngine(
        _Runtime(),
        sp=object(),
        sample_rate=48000,
        prompt_audio_codes=[[1, 2], [3, 4]],
        voice_name="Adam",
    )

    resolved = engine.set_voice_prompt("Bella")

    assert resolved == "Bella"
    assert engine.voice_name == "Bella"
    assert engine._prompt_audio_codes == [[5, 6], [7, 8]]


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
