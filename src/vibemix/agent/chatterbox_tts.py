# SPDX-License-Identifier: Apache-2.0
"""Local Chatterbox-Turbo voice for the live co-host — MLX / Apple-GPU zero-shot clone.

This is the product co-host voice, selected by default with
``VIBEMIX_TTS_ENGINE=chatterbox``. It is built as a LiveKit ``TTS`` provider
with an injectable engine seam (:class:`ChatterboxEngine`) so the wiring is
unit-testable without the heavy ``mlx-audio`` dependency or any model download.

The real engine (:class:`_MlxChatterboxEngine`) renders speech through
``mlx-audio``'s ``chatterbox-turbo-8bit`` on Apple GPU: zero-shot voice clone from a
reference clip, paralinguistic tags (``[laugh]``/``[gasp]``/``[sigh]``) at temperature
0.4, streamed chunk-by-chunk for a ~0.2s time-to-first-audio. ``mlx-audio`` is
Apple-only and is **never** a base dependency — it is imported lazily. When the
engine or reference clip is unavailable, callers start voiceless with an honest
reason instead of falling back to another voice.
"""

from __future__ import annotations

import asyncio
import importlib.util
import os
import queue
import sys
import threading
from collections.abc import Callable
from pathlib import Path

from livekit.agents import tts as agents_tts
from livekit.agents._exceptions import APIError
from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS, APIConnectOptions
from livekit.agents.utils import shortuuid

from vibemix.library.model_assets import (
    CHATTERBOX_ALLOW_PATTERNS,
    CHATTERBOX_MODEL_REPO,
    CHATTERBOX_MODEL_REVISION,
    chatterbox_model_cached,
    chatterbox_model_revision,
)

# Chatterbox-Turbo s3gen output rate; mono to match the live sink + FallbackAdapter.
NATIVE_SR = 24000
ENGINE_ENV = "VIBEMIX_TTS_ENGINE"
REF_ENV = "VIBEMIX_CHATTERBOX_REF"
MODEL_ENV = "VIBEMIX_CHATTERBOX_MODEL"
TEMP_ENV = "VIBEMIX_CHATTERBOX_TEMP"

_DEFAULT_MODEL = CHATTERBOX_MODEL_REPO
_DEFAULT_TEMP = 0.4  # Kaan-locked: tags fire as SOUND (not read literally), quality holds
_DEFAULT_STREAM_INTERVAL = 0.5  # seconds of audio per streamed chunk (low TTFT)
# Default co-host voice ref = the Kaan-locked "pranker" voice (music-stripped clip,
# rendered at temp 0.4). Lives in the vibemix cache next to the other model assets.
_DEV_REF = Path.home() / ".cache" / "vibemix" / "cohost_voice_ref.wav"
_BUNDLED_REF_REL = Path("models") / "chatterbox" / "cohost_voice_ref.wav"


class ChatterboxUnavailable(RuntimeError):
    """Raised when the product voice cannot be built on this machine."""


def pcm16_mono_le(audio_2d) -> bytes:
    """Downmix float audio in [-1, 1] to mono little-endian int16 PCM bytes."""
    import numpy as np

    a = np.asarray(audio_2d, dtype=np.float32)
    mono = a if a.ndim == 1 else (a.mean(axis=0) if a.shape[0] > 1 else a[0])
    pcm = np.round(np.clip(mono, -1.0, 1.0) * 32767.0).astype("<i2")
    return pcm.tobytes()


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


def configured_model_revision(model_name: str | None = None) -> str | None:
    return chatterbox_model_revision(model_name or configured_model())


def default_ref_path() -> Path:
    return _DEV_REF


def bundled_ref_candidates() -> tuple[Path, ...]:
    roots: list[Path] = []
    frozen_root = getattr(sys, "_MEIPASS", None)
    if frozen_root:
        roots.append(Path(frozen_root))
    try:
        exe_parent = Path(sys.executable).resolve().parent
        roots.extend([exe_parent, exe_parent / "_internal"])
    except Exception:
        pass
    return tuple(root / _BUNDLED_REF_REL for root in roots)


def resolve_ref_path() -> Path | None:
    """The reference clip to clone. ``VIBEMIX_CHATTERBOX_REF`` overrides; else the
    bundled/cache pranker ref if present; else ``None`` (engine unavailable)."""
    override = os.environ.get(REF_ENV, "").strip()
    if override:
        candidate = Path(override).expanduser()
        return candidate if candidate.is_file() else None
    bundled = next((candidate for candidate in bundled_ref_candidates() if candidate.is_file()), None)
    if bundled is not None:
        return bundled
    return _DEV_REF if _DEV_REF.is_file() else None


def engine_selected() -> bool:
    """True when the configured product voice engine is Chatterbox."""
    return os.environ.get(ENGINE_ENV, "chatterbox").strip().lower() == "chatterbox"


def chatterbox_available() -> bool:
    """True when Chatterbox can render without first-line network downloads."""
    if importlib.util.find_spec("mlx_audio") is None:
        return False
    if resolve_ref_path() is None:
        return False
    return chatterbox_model_cached(configured_model(), configured_model_revision())


def chatterbox_unavailable_reason() -> str:
    if importlib.util.find_spec("mlx_audio") is None:
        return "mlx-audio not installed (Chatterbox voice is Apple-only)"
    if resolve_ref_path() is None:
        return f"no reference clip (set {REF_ENV} or place {_DEV_REF})"
    if not chatterbox_model_cached(configured_model(), configured_model_revision()):
        return (
            "Chatterbox model not downloaded. Complete the first-run voice download "
            f"for {CHATTERBOX_MODEL_REPO}@{CHATTERBOX_MODEL_REVISION} before starting a set."
        )
    return "unknown"


class ChatterboxEngine:
    """Synthesis seam so the LiveKit plumbing is testable without ``mlx-audio``.

    Real impl: :class:`_MlxChatterboxEngine`. ``synthesize`` is BLOCKING and invokes
    ``on_pcm`` once per streamed chunk with mono int16 LE PCM bytes at ``sample_rate``.
    """

    sample_rate: int = NATIVE_SR

    def synthesize(self, text: str, on_pcm: Callable[[bytes], None]) -> None:  # pragma: no cover - interface
        raise NotImplementedError


class _ChatterboxWorkerJob:
    def __init__(
        self,
        kind: str,
        *,
        text: str | None = None,
        on_pcm: Callable[[bytes], None] | None = None,
    ) -> None:
        self.kind = kind
        self.text = text
        self.on_pcm = on_pcm
        self.done = threading.Event()
        self.error: BaseException | None = None


class _MlxChatterboxEngine(ChatterboxEngine):
    """Real engine: ``mlx-audio`` Chatterbox-Turbo, ref-conditioned once, streamed."""

    def __init__(self, model, ref_path: str, temperature: float, stream_interval: float) -> None:
        self._m = model
        self._ref = ref_path
        self._temperature = temperature
        self._stream_interval = stream_interval
        self.sample_rate = NATIVE_SR

    @classmethod
    def load(
        cls,
        model_name: str,
        ref_path: str,
        temperature: float,
        revision: str | None = None,
    ) -> _MlxChatterboxEngine:
        import numpy as np  # noqa: F401 - ensure numpy present for the synth path
        from mlx_audio.tts.utils import load_model

        kwargs = {"allow_patterns": list(CHATTERBOX_ALLOW_PATTERNS)}
        if revision:
            kwargs["revision"] = revision
        model = load_model(model_name, **kwargs)
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

    Non-streaming capability (``streaming=False``) matches the live sink: the FallbackAdapter
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
        self._model_revision = configured_model_revision(self._model_name)
        self._temperature = temperature if temperature is not None else configured_temperature()
        self._engine: ChatterboxEngine | None = engine
        self._engine_lock = threading.Lock()
        self._synth_lock = threading.Lock()
        self._prewarm_start_lock = threading.Lock()
        self._prewarm_done = threading.Event()
        self._prewarm_error: BaseException | None = None
        self._prewarm_inflight = False
        self._worker_lock = threading.Lock()
        self._worker_queue: queue.Queue[_ChatterboxWorkerJob] | None = None
        self._worker_thread: threading.Thread | None = None
        if engine is not None:
            self._prewarm_done.set()

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
            self._prewarm_done.set()
            return self._engine
        with self._engine_lock:
            if self._engine is None:
                if self._ref_path is None:
                    exc = APIError(
                        f"Chatterbox voice unavailable: {chatterbox_unavailable_reason()}"
                    )
                    self._prewarm_error = exc
                    self._prewarm_done.set()
                    raise exc
                try:
                    self._engine = _MlxChatterboxEngine.load(
                        self._model_name,
                        self._ref_path,
                        self._temperature,
                        revision=self._model_revision,
                    )
                except BaseException as exc:
                    self._prewarm_error = exc
                    self._prewarm_done.set()
                    raise
                self._prewarm_error = None
                self._prewarm_done.set()
        return self._engine

    def _ensure_worker(self) -> queue.Queue[_ChatterboxWorkerJob]:
        with self._worker_lock:
            if self._worker_queue is None:
                self._worker_queue = queue.Queue()
            if self._worker_thread is None or not self._worker_thread.is_alive():
                self._worker_thread = threading.Thread(
                    target=self._worker_loop,
                    name="chatterbox-tts-worker",
                    daemon=True,
                )
                self._worker_thread.start()
            return self._worker_queue

    def _worker_loop(self) -> None:
        q = self._worker_queue
        if q is None:
            return
        while True:
            job = q.get()
            try:
                if job.kind == "prewarm":
                    self._get_engine()
                elif job.kind == "synth":
                    if job.text is None or job.on_pcm is None:
                        raise APIError("Chatterbox synthesis job missing text or callback")
                    self._get_engine().synthesize(job.text, job.on_pcm)
                else:
                    raise APIError(f"unknown Chatterbox worker job: {job.kind}")
            except BaseException as exc:
                job.error = exc
                if job.kind == "prewarm":
                    self._prewarm_error = exc
            finally:
                if job.kind == "prewarm":
                    with self._prewarm_start_lock:
                        self._prewarm_inflight = False
                    self._prewarm_done.set()
                job.done.set()

    def prewarm(self) -> None:
        """Load the model + prime the ref conditional off the loop so reaction #1 is warm."""
        if self._engine is not None:
            self._prewarm_done.set()
            return

        with self._prewarm_start_lock:
            if self._prewarm_inflight:
                return
            self._prewarm_done.clear()
            self._prewarm_error = None
            self._prewarm_inflight = True
            self._ensure_worker().put(_ChatterboxWorkerJob("prewarm"))

    @property
    def prewarm_error(self) -> BaseException | None:
        return self._prewarm_error

    def wait_until_warm(self, timeout_s: float | None = None) -> bool:
        """Wait for the prewarm thread to finish loading the engine.

        Returns True only when the local voice is ready to synthesize. Failures
        stay fail-soft here; the actual synth path still raises the provider
        error if a caller tries to speak while unavailable.
        """
        if self._engine is not None:
            self._prewarm_done.set()
            return True
        self.prewarm()
        if not self._prewarm_done.wait(timeout_s):
            return False
        return self._engine is not None and self._prewarm_error is None

    def synthesize_pcm(self, text: str, on_pcm: Callable[[bytes], None]) -> None:
        """Synthesize mono PCM bytes for non-LiveKit sinks."""
        with self._synth_lock:
            job = _ChatterboxWorkerJob("synth", text=text, on_pcm=on_pcm)
            self._ensure_worker().put(job)
            job.done.wait()
            if job.error is not None:
                raise job.error

    def synthesize(
        self, text: str, *, conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS
    ) -> agents_tts.ChunkedStream:
        return _ChatterboxChunkedStream(tts=self, input_text=text, conn_options=conn_options)


class _ChatterboxChunkedStream(agents_tts.ChunkedStream):
    """Runs blocking Chatterbox synthesis in an executor, then emits finished PCM."""

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
        chunks: list[bytes] = []

        def _produce() -> None:
            tts.synthesize_pcm(self._input_text, chunks.append)

        try:
            await loop.run_in_executor(None, _produce)
        except asyncio.CancelledError:
            raise
        except BaseException as exc:
            raise APIError(f"Chatterbox local TTS synthesis failed: {exc}") from exc

        for pcm in chunks:
            output_emitter.push(pcm)

        output_emitter.flush()


def build_chatterbox_adapter(
    *, ref_path: str | None = None, chatterbox: ChatterboxLocalTTS | None = None
) -> agents_tts.FallbackAdapter:
    """Build the Chatterbox-only live voice chain."""
    if chatterbox is None and not chatterbox_available():
        raise ChatterboxUnavailable(chatterbox_unavailable_reason())
    cbt = chatterbox or ChatterboxLocalTTS(ref_path=ref_path)
    cbt.prewarm()
    return agents_tts.FallbackAdapter(tts=[cbt], max_retry_per_tts=1)
