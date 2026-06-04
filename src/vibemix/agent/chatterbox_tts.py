# SPDX-License-Identifier: Apache-2.0
"""Local Chatterbox-Turbo voice for the live co-host — MLX / Apple-GPU zero-shot clone.

Opt-in alternative to the MOSS voice, selected with ``VIBEMIX_TTS_ENGINE=chatterbox``.
It mirrors :class:`vibemix.agent.local_tts.MossLocalTTS` exactly — a LiveKit ``TTS``
provider with an injectable engine seam (:class:`ChatterboxEngine`) so the wiring is
unit-testable without the heavy ``mlx-audio`` dependency or any model download.

The real engine (:class:`_MlxChatterboxEngine`) renders speech through
``mlx-audio``'s ``chatterbox-turbo-8bit`` on Apple GPU: zero-shot voice clone from a
reference clip, paralinguistic tags (``[laugh]``/``[gasp]``/``[sigh]``) at temperature
0.4, streamed chunk-by-chunk for a ~0.2s time-to-first-audio. ``mlx-audio`` is
Apple-only and is **never** a base dependency — it is imported lazily, and when it is
absent the chain falls back to MOSS so the voice is never muted.
"""

from __future__ import annotations

import asyncio
import importlib.util
import os
import threading
from collections.abc import Callable
from pathlib import Path

from livekit.agents import tts as agents_tts
from livekit.agents._exceptions import APIError
from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS, APIConnectOptions
from livekit.agents.utils import shortuuid

from vibemix.agent.local_tts import pcm16_mono_le  # reuse the proven mono int16 downmix

# Chatterbox-Turbo s3gen output rate; mono to match the live sink + FallbackAdapter.
NATIVE_SR = 24000
ENGINE_ENV = "VIBEMIX_TTS_ENGINE"
REF_ENV = "VIBEMIX_CHATTERBOX_REF"
MODEL_ENV = "VIBEMIX_CHATTERBOX_MODEL"
TEMP_ENV = "VIBEMIX_CHATTERBOX_TEMP"

_DEFAULT_MODEL = "mlx-community/chatterbox-turbo-8bit"
_DEFAULT_TEMP = 0.4  # Kaan-locked: tags fire as SOUND (not read literally), quality holds
_DEFAULT_STREAM_INTERVAL = 0.5  # seconds of audio per streamed chunk (low TTFT)
# Default co-host voice ref = the Kaan-locked "pranker" voice (music-stripped clip,
# rendered at temp 0.4). Lives in the vibemix cache next to the other model assets.
_DEV_REF = Path.home() / ".cache" / "vibemix" / "cohost_voice_ref.wav"


def configured_temperature() -> float:
    raw = os.environ.get(TEMP_ENV, "").strip()
    if not raw:
        return _DEFAULT_TEMP
    try:
        return float(raw)
    except ValueError:
        return _DEFAULT_TEMP


def configured_model() -> str:
    return os.environ.get(MODEL_ENV, "").strip() or _DEFAULT_MODEL


def resolve_ref_path() -> Path | None:
    """The reference clip to clone. ``VIBEMIX_CHATTERBOX_REF`` overrides; else the
    dev Archie ref if it is present; else ``None`` (engine unavailable)."""
    override = os.environ.get(REF_ENV, "").strip()
    if override:
        candidate = Path(override).expanduser()
        return candidate if candidate.is_file() else None
    return _DEV_REF if _DEV_REF.is_file() else None


def engine_selected() -> bool:
    """True when the operator asked for the Chatterbox voice."""
    return os.environ.get(ENGINE_ENV, "moss").strip().lower() == "chatterbox"


def chatterbox_available() -> bool:
    """True when Chatterbox can actually render: ``mlx-audio`` importable + a ref clip."""
    if importlib.util.find_spec("mlx_audio") is None:
        return False
    return resolve_ref_path() is not None


def chatterbox_unavailable_reason() -> str:
    if importlib.util.find_spec("mlx_audio") is None:
        return "mlx-audio not installed (Chatterbox voice is Apple-only)"
    if resolve_ref_path() is None:
        return f"no reference clip (set {REF_ENV} or place {_DEV_REF})"
    return "unknown"


class ChatterboxEngine:
    """Synthesis seam so the LiveKit plumbing is testable without ``mlx-audio``.

    Real impl: :class:`_MlxChatterboxEngine`. ``synthesize`` is BLOCKING and invokes
    ``on_pcm`` once per streamed chunk with mono int16 LE PCM bytes at ``sample_rate``.
    """

    sample_rate: int = NATIVE_SR

    def synthesize(self, text: str, on_pcm: Callable[[bytes], None]) -> None:  # pragma: no cover - interface
        raise NotImplementedError


class _MlxChatterboxEngine(ChatterboxEngine):
    """Real engine: ``mlx-audio`` Chatterbox-Turbo, ref-conditioned once, streamed."""

    def __init__(self, model, ref_path: str, temperature: float, stream_interval: float) -> None:
        self._m = model
        self._ref = ref_path
        self._temperature = temperature
        self._stream_interval = stream_interval
        self.sample_rate = NATIVE_SR

    @classmethod
    def load(cls, model_name: str, ref_path: str, temperature: float) -> _MlxChatterboxEngine:
        import numpy as np  # noqa: F401 - ensure numpy present for the synth path
        from mlx_audio.tts.utils import load_model

        model = load_model(model_name)
        # One-time conditional prime: pay the ref encode once, reuse for every line.
        model.prepare_conditionals(ref_path)
        return cls(model, ref_path, temperature, _DEFAULT_STREAM_INTERVAL)

    def synthesize(self, text: str, on_pcm: Callable[[bytes], None]) -> None:
        import numpy as np

        # ref_audio=None reuses the primed conditional; stream chunks for low TTFT.
        for seg in self._m.generate(
            text,
            temperature=self._temperature,
            stream=True,
            streaming_interval=self._stream_interval,
        ):
            audio = np.asarray(seg.audio, dtype=np.float32).flatten()
            if audio.size:
                on_pcm(pcm16_mono_le(audio))


class ChatterboxLocalTTS(agents_tts.TTS):
    """LiveKit ``TTS`` provider backed by the local Chatterbox-Turbo MLX engine.

    Non-streaming capability (``streaming=False``) mirrors MOSS: the FallbackAdapter
    wraps it in a StreamAdapter for token-streamed text, and we stream PCM out fast
    via the ``synthesize`` ChunkedStream so first audio lands quickly.
    """

    def __init__(
        self,
        *,
        ref_path: str | os.PathLike[str] | None = None,
        model_name: str | None = None,
        temperature: float | None = None,
        engine: ChatterboxEngine | None = None,
    ) -> None:
        resolved_ref = ref_path or resolve_ref_path()
        self._ref_path = str(resolved_ref) if resolved_ref is not None else None
        self._model_name = model_name or configured_model()
        self._temperature = temperature if temperature is not None else configured_temperature()
        self._engine: ChatterboxEngine | None = engine
        self._engine_lock = threading.Lock()
        self._synth_lock = threading.Lock()

        sample_rate = engine.sample_rate if engine is not None else NATIVE_SR
        super().__init__(
            capabilities=agents_tts.TTSCapabilities(streaming=False),
            sample_rate=int(sample_rate),
            num_channels=1,
        )

    @property
    def model(self) -> str:
        return self._model_name

    @property
    def provider(self) -> str:
        return "chatterbox-mlx"

    def _get_engine(self) -> ChatterboxEngine:
        if self._engine is not None:
            return self._engine
        with self._engine_lock:
            if self._engine is None:
                if self._ref_path is None:
                    raise APIError(f"Chatterbox voice unavailable: {chatterbox_unavailable_reason()}")
                self._engine = _MlxChatterboxEngine.load(self._model_name, self._ref_path, self._temperature)
        return self._engine

    def prewarm(self) -> None:
        """Load the model + prime the ref conditional off the loop so reaction #1 is warm."""
        if self._engine is not None:
            return

        def _bg() -> None:
            try:
                self._get_engine()
            except Exception:
                # A failed prewarm must not crash boot; the synth path surfaces the error.
                pass

        threading.Thread(target=_bg, name="chatterbox-tts-prewarm", daemon=True).start()

    def synthesize_pcm(self, text: str, on_pcm: Callable[[bytes], None]) -> None:
        """Synthesize mono PCM bytes for non-LiveKit sinks (parity with MOSS)."""
        with self._synth_lock:
            self._get_engine().synthesize(text, on_pcm)

    def synthesize(
        self, text: str, *, conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS
    ) -> agents_tts.ChunkedStream:
        return _ChatterboxChunkedStream(tts=self, input_text=text, conn_options=conn_options)


class _ChatterboxChunkedStream(agents_tts.ChunkedStream):
    """Runs blocking Chatterbox synthesis in an executor, streaming PCM to the emitter."""

    _DONE = object()

    async def _run(self, output_emitter: agents_tts.AudioEmitter) -> None:
        tts: ChatterboxLocalTTS = self._tts  # type: ignore[assignment]
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
            loop.call_soon_threadsafe(queue.put_nowait, pcm)

        def _produce() -> None:
            try:
                tts.synthesize_pcm(self._input_text, _on_pcm)
            except BaseException as exc:  # noqa: BLE001 - surfaced to the stream
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
                    raise APIError(f"Chatterbox local TTS synthesis failed: {item}") from item
                output_emitter.push(item)
        finally:
            await fut

        output_emitter.flush()


def build_chatterbox_adapter(*, ref_path: str | None = None) -> agents_tts.FallbackAdapter:
    """Build the Chatterbox-only live voice chain (parity with the MOSS-only builder)."""
    cbt = ChatterboxLocalTTS(ref_path=ref_path)
    cbt.prewarm()
    return agents_tts.FallbackAdapter(tts=[cbt], max_retry_per_tts=1)
