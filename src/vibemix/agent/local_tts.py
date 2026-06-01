# SPDX-License-Identifier: Apache-2.0
"""Local, on-device TTS for the live co-host — MOSS-TTS-Nano over torch-free ONNX.

This is the "free voice" path: a LiveKit ``TTS`` provider that synthesizes speech
entirely on the user's CPU (no API, no key, never 503/mute), wrapping the vendored
MOSS-TTS-Nano ONNX engine (``vibemix.agent.moss_tts.ort_cpu_runtime``). Benched on
an M4 Max at 71 ms TTFT / 0.18 RTF (CPU, torch-free) — well inside the live in-ear
latency budget.

Data flow: full reaction text -> SentencePiece encode -> autoregressive frame
generation -> streaming codec decode -> mono int16 PCM pushed chunk-by-chunk into
LiveKit's ``AudioEmitter``. The model emits 48 kHz stereo; we downmix to mono and
declare the native rate, letting the FallbackAdapter / playback sink resample to
the 24 kHz output contract (``OUTPUT_SR``).

Wiring: when ``VIBEMIX_LOCAL_TTS`` is enabled and the model is cached,
``tts_chain._build_direct_chain`` uses this as the only voice. Off by default -
flipping it to the default free-tier voice is a product decision, not a code one.

The heavy ONNX runtime (~728 MB, 9 ORT sessions) loads once per instance, lazily,
off the event loop. ``prewarm()`` kicks the load in the background so the first
reaction of a session isn't the one that pays for it. All blocking synthesis runs
in an executor; decoded PCM is marshalled back to the loop as it is produced, so
first audio still streams out fast.
"""

from __future__ import annotations

import asyncio
import os
import threading
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from livekit.agents import tts as agents_tts
from livekit.agents._exceptions import APIError
from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS, APIConnectOptions
from livekit.agents.utils import shortuuid

from vibemix.agent.config import (
    VOICE as _GEMINI_VOICE,  # noqa: F401  (kept for parity of voice config home)
)

if TYPE_CHECKING:
    import numpy as np

# --- config (plain env, NOT the Gemini-only model_router — see config.py/Cartesia) ---
# Native model output rate. The codec emits 48 kHz; we read the real value from
# the model meta at construction and only fall back to this if that read fails.
_DEFAULT_NATIVE_SR = 48000
_DEFAULT_VOICE = os.environ.get("VIBEMIX_MOSS_TTS_VOICE", "Adam")  # clear EN male preset
_DEFAULT_THREADS = int(os.environ.get("VIBEMIX_MOSS_TTS_THREADS", "4") or "4")


def default_model_dir() -> Path:
    """The cached MOSS-TTS-Nano ONNX model dir (mirrors the CLAP/CUE model caches)."""
    cache = os.environ.get("VIBEMIX_CACHE_DIR") or os.path.join(Path.home(), ".cache", "vibemix")
    return Path(cache) / "moss-tts-onnx" / "MOSS-TTS-Nano-100M-ONNX"


def resolve_model_dir() -> Path | None:
    """Return the usable MOSS model dir, or ``None`` if not present/cached.

    ``VIBEMIX_MOSS_TTS_DIR`` overrides; it must point at the ``*-Nano-100M-ONNX``
    dir (the dir holding ``browser_poc_manifest.json``).
    """
    override = os.environ.get("VIBEMIX_MOSS_TTS_DIR")
    candidate = Path(override).expanduser() if override else default_model_dir()
    if (candidate / "browser_poc_manifest.json").is_file():
        return candidate
    return None


def local_tts_enabled() -> bool:
    """True when the operator opted in AND the model is cached.

    Opt-in is explicit (``VIBEMIX_LOCAL_TTS`` truthy) so existing Cartesia/Gemini
    behavior is unchanged until a user chooses the local voice. Flipping this to a
    default-on free-tier voice is a separate product decision.
    """
    flag = (os.environ.get("VIBEMIX_LOCAL_TTS") or "").strip().lower()
    if flag not in {"1", "true", "yes", "on"}:
        return False
    return resolve_model_dir() is not None


def _read_native_sample_rate(model_dir: Path) -> int:
    """Cheaply read the codec output sample rate from the model meta (no ORT load)."""
    try:
        import json

        manifest = json.loads((model_dir / "browser_poc_manifest.json").read_text(encoding="utf-8"))
        codec_meta_rel = manifest["model_files"]["codec_meta"]
        codec_meta_path = (model_dir / codec_meta_rel).resolve()
        codec_meta = json.loads(codec_meta_path.read_text(encoding="utf-8"))
        return int(codec_meta["codec_config"]["sample_rate"])
    except Exception:
        return _DEFAULT_NATIVE_SR


def pcm16_mono_le(audio_2d: np.ndarray) -> bytes:
    """Downmix (channels, samples) | (samples,) float32 in [-1, 1] -> mono int16 LE bytes.

    The live sink is mono int16 (``playback_sink`` / sounddevice ``channels=1``);
    the model emits stereo, so we average channels. Little-endian is pinned so the
    bytes are correct regardless of host endianness.
    """
    import numpy as np

    a = np.asarray(audio_2d, dtype=np.float32)
    mono = a if a.ndim == 1 else (a.mean(axis=0) if a.shape[0] > 1 else a[0])
    pcm = np.round(np.clip(mono, -1.0, 1.0) * 32767.0).astype("<i2")
    return pcm.tobytes()


class MossEngine:
    """Minimal synthesis seam so the LiveKit plumbing is testable without the model.

    Real impl: :class:`_OrtCpuEngine`. ``synthesize`` is BLOCKING and invokes
    ``on_pcm`` once per decoded chunk with mono int16 LE PCM bytes at ``sample_rate``.
    """

    sample_rate: int = _DEFAULT_NATIVE_SR

    def synthesize(self, text: str, on_pcm: Callable[[bytes], None]) -> None:  # pragma: no cover - interface
        raise NotImplementedError


class _OrtCpuEngine(MossEngine):
    """Real engine: vendored torch-free MOSS ONNX runtime + SentencePiece + a builtin voice."""

    def __init__(self, runtime, sp, sample_rate: int, prompt_audio_codes, voice_name: str) -> None:
        self._rt = runtime
        self._sp = sp
        self.sample_rate = int(sample_rate)
        self._prompt_audio_codes = prompt_audio_codes
        self.voice_name = voice_name

    @classmethod
    def load(cls, model_dir: Path, voice: str, thread_count: int) -> _OrtCpuEngine:
        import sentencepiece as spm

        from vibemix.agent.moss_tts.ort_cpu_runtime import OrtCpuRuntime

        rt = OrtCpuRuntime(
            model_dir=str(model_dir),
            thread_count=thread_count,
            sample_mode="fixed",  # repo default fast path (matches the bench)
            do_sample=True,
        )
        tok_rel = str(rt.manifest["model_files"].get("tokenizer_model", "tokenizer.model"))
        tok_path = rt.resolve_manifest_relative_path(tok_rel)
        sp = spm.SentencePieceProcessor(model_file=str(tok_path))
        sample_rate = int(rt.codec_meta["codec_config"]["sample_rate"])
        voices = rt.list_builtin_voices()
        row = next((v for v in voices if v.get("voice") == voice), voices[0])
        prompt_codes = list(row["prompt_audio_codes"])
        rt.warmup()  # build/JIT the ORT graphs so the first real synth is warm
        return cls(rt, sp, sample_rate, prompt_codes, row.get("voice", voice))

    def synthesize(self, text: str, on_pcm: Callable[[bytes], None]) -> None:
        # Mirrors the proven bench streaming decode (ort_cpu_runtime path): generate
        # audio frames autoregressively, decode them through the streaming codec
        # session in budgeted chunks, and emit each decoded chunk as mono int16 PCM.
        import time

        from vibemix.agent.moss_tts.ort_cpu_runtime import _resolve_stream_decode_frame_budget

        rt = self._rt
        text_token_ids = [int(t) for t in self._sp.encode(text, out_type=int)]
        request_rows = rt.build_voice_clone_request_rows(self._prompt_audio_codes, text_token_ids)

        pending: list[list[int]] = []
        state = {"emitted_samples": 0, "first_audio_at": None}
        rt.codec_streaming_session.reset()

        def decode_pending(force: bool) -> None:
            n = len(pending)
            if n <= 0:
                return
            budget = _resolve_stream_decode_frame_budget(
                state["emitted_samples"], self.sample_rate, state["first_audio_at"]
            )
            if not force and n < max(1, budget):
                return
            fb = n if force else min(n, max(1, budget))
            chunk = pending[:fb]
            del pending[:fb]
            decoded = rt.codec_streaming_session.run_frames(chunk)
            if decoded is None:
                return
            audio, audio_len = decoded
            if audio_len <= 0:
                return
            if state["first_audio_at"] is None:
                state["first_audio_at"] = time.perf_counter()
            state["emitted_samples"] += audio_len
            on_pcm(pcm16_mono_le(audio[0, :, :audio_len]))

        def on_frame(_gen, _step, frame) -> None:
            pending.append(list(frame))
            decode_pending(False)

        try:
            rt.generate_audio_frames(request_rows, on_frame=on_frame)
            decode_pending(True)  # flush the tail
        finally:
            rt.codec_streaming_session.reset()


class MossLocalTTS(agents_tts.TTS):
    """LiveKit ``TTS`` provider backed by the local MOSS-TTS-Nano ONNX engine.

    Non-streaming (``streaming=False``): the FallbackAdapter auto-wraps it in a
    StreamAdapter for the agent's token-streamed text, and we stream PCM out fast
    via the ``synthesize`` ChunkedStream so first audio still lands quickly.
    """

    def __init__(
        self,
        *,
        model_dir: Path | None = None,
        voice: str = _DEFAULT_VOICE,
        thread_count: int = _DEFAULT_THREADS,
        sample_rate: int | None = None,
        engine: MossEngine | None = None,
    ) -> None:
        self._model_dir = model_dir or resolve_model_dir()
        self._voice = voice
        self._thread_count = thread_count
        self._engine: MossEngine | None = engine
        self._engine_lock = threading.Lock()

        if sample_rate is None:
            sample_rate = (
                engine.sample_rate
                if engine is not None
                else (_read_native_sample_rate(self._model_dir) if self._model_dir else _DEFAULT_NATIVE_SR)
            )
        super().__init__(
            capabilities=agents_tts.TTSCapabilities(streaming=False),
            sample_rate=int(sample_rate),
            num_channels=1,  # mono — matches the live sink + FallbackAdapter uniformity
        )

    @property
    def model(self) -> str:
        return "moss-tts-nano-100m-onnx"

    @property
    def provider(self) -> str:
        return "moss-local"

    def _get_engine(self) -> MossEngine:
        """Load the (heavy) engine once. Thread-safe; intended to run off the loop."""
        if self._engine is not None:
            return self._engine
        with self._engine_lock:
            if self._engine is None:
                if self._model_dir is None:
                    raise APIError("MOSS local TTS model not found (set VIBEMIX_MOSS_TTS_DIR or cache it)")
                self._engine = _OrtCpuEngine.load(self._model_dir, self._voice, self._thread_count)
        return self._engine

    def prewarm(self) -> None:
        """Kick the (~728 MB) engine load in the background so reaction #1 is warm."""
        if self._engine is not None:
            return

        def _bg() -> None:
            try:
                self._get_engine()
            except Exception:
                # A failed prewarm must not crash boot; the synth path surfaces the
                # error into the FallbackAdapter (Cartesia/Gemini take over).
                pass

        threading.Thread(target=_bg, name="moss-tts-prewarm", daemon=True).start()

    def synthesize(
        self, text: str, *, conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS
    ) -> agents_tts.ChunkedStream:
        return _MossChunkedStream(tts=self, input_text=text, conn_options=conn_options)


class _MossChunkedStream(agents_tts.ChunkedStream):
    """Runs blocking MOSS synthesis in an executor, streaming PCM into the emitter."""

    _DONE = object()

    async def _run(self, output_emitter: agents_tts.AudioEmitter) -> None:
        tts: MossLocalTTS = self._tts  # type: ignore[assignment]
        output_emitter.initialize(
            request_id=shortuuid(),
            sample_rate=tts.sample_rate,
            num_channels=tts.num_channels,
            mime_type="audio/pcm",
            stream=False,
        )

        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()

        def _on_pcm(pcm: bytes) -> None:
            # called from the executor thread — marshal to the loop
            loop.call_soon_threadsafe(queue.put_nowait, pcm)

        def _produce() -> None:
            try:
                engine = tts._get_engine()  # may lazy-load here (off the loop)
                engine.synthesize(self._input_text, _on_pcm)
            except BaseException as exc:
                loop.call_soon_threadsafe(queue.put_nowait, exc)
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, self._DONE)

        fut = loop.run_in_executor(None, _produce)
        try:
            while True:
                item = await queue.get()
                if item is self._DONE:
                    break
                if isinstance(item, BaseException):
                    raise APIError(f"MOSS local TTS synthesis failed: {item}") from item
                output_emitter.push(item)
        finally:
            await fut  # join the worker / surface a late failure

        output_emitter.flush()
