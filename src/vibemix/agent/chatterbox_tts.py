# SPDX-License-Identifier: Apache-2.0
"""Local Chatterbox-Turbo voice for the live co-host — MLX / Apple-GPU zero-shot clone.

This is the product co-host voice, selected by default with
``VIBEMIX_TTS_ENGINE=chatterbox``. It is built as a LiveKit ``TTS`` provider
with an injectable engine seam (:class:`ChatterboxEngine`) so the wiring is
unit-testable without the heavy ``mlx-audio`` dependency or any model download.

The real engine (:class:`_MlxChatterboxEngine`) renders speech through
``mlx-audio``'s ``chatterbox-turbo-8bit`` on Apple GPU: zero-shot voice clone from a
reference clip, paralinguistic tags (``[laugh]``/``[gasp]``/``[sigh]``) at temperature
0.4, emitted as one contiguous PCM segment so the speaker buffer never underflows.
``mlx-audio`` is Apple-only and is **never** a base dependency — it is imported lazily.
When the engine or reference clip is unavailable, callers start voiceless with an
honest reason instead of falling back to another voice.
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
MAX_TOKENS_ENV = "VIBEMIX_CHATTERBOX_MAX_TOKENS"

_DEFAULT_MODEL = CHATTERBOX_MODEL_REPO
_DEFAULT_TEMP = 0.4  # Kaan-locked: tags fire as SOUND (not read literally), quality holds
_DEFAULT_STREAM_INTERVAL = 0.5  # seconds of audio per streamed chunk (low TTFT)
_DEFAULT_MAX_TOKENS = 96
_PCM_CACHE_LIMIT = 8
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


def configured_max_tokens() -> int:
    raw = os.environ.get(MAX_TOKENS_ENV, "").strip()
    if raw:
        try:
            return max(32, min(256, int(raw)))
        except ValueError:
            pass
    return _DEFAULT_MAX_TOKENS


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
    buffer_before_playback: bool = False

    def synthesize(self, text: str, on_pcm: Callable[[bytes], None]) -> None:  # pragma: no cover - interface
        raise NotImplementedError


class _ChatterboxWorkerJob:
    def __init__(
        self,
        kind: str,
        *,
        text: str | None = None,
        on_pcm: Callable[[bytes], None] | None = None,
        cache_key: str | None = None,
        cache_chunks: list[bytes] | None = None,
    ) -> None:
        self.kind = kind
        self.text = text
        self.on_pcm = on_pcm
        self.cache_key = cache_key
        self.cache_chunks = cache_chunks
        self.done = threading.Event()
        self.error: BaseException | None = None


class _MlxChatterboxEngine(ChatterboxEngine):
    """Real engine: ``mlx-audio`` Chatterbox-Turbo, ref-conditioned once."""

    buffer_before_playback = True

    def __init__(
        self,
        model,
        ref_path: str,
        temperature: float,
        stream_interval: float,
        max_tokens: int,
    ) -> None:
        self._m = model
        self._ref = ref_path
        self._temperature = temperature
        self._stream_interval = stream_interval
        self._max_tokens = max_tokens
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
        return cls(model, ref_path, temperature, _DEFAULT_STREAM_INTERVAL, configured_max_tokens())

    def synthesize(self, text: str, on_pcm: Callable[[bytes], None]) -> None:
        import numpy as np

        # ref_audio=None reuses the primed conditional. Use the one-shot path:
        # Turbo's stream path repeatedly runs S3Gen over partial token windows,
        # which is slower than real time on some Macs and causes audible buffer
        # starvation when forwarded live.
        for seg in self._m.generate(
            text,
            temperature=self._temperature,
            stream=False,
            max_tokens=self._max_tokens,
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
        self._cache_lock = threading.Lock()
        self._pcm_cache: dict[str, tuple[bytes, ...]] = {}
        self._prefetch_jobs: dict[str, _ChatterboxWorkerJob] = {}
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
                    if job.text is None:
                        raise APIError("Chatterbox synthesis job missing text")
                    if job.on_pcm is None and job.cache_key is None:
                        raise APIError("Chatterbox synthesis job missing callback or cache target")
                    on_pcm_callback = job.on_pcm
                    cache_chunks = job.cache_chunks

                    def _on_pcm(
                        pcm: bytes,
                        *,
                        cache_chunks: list[bytes] | None = cache_chunks,
                        on_pcm_callback: Callable[[bytes], None] | None = on_pcm_callback,
                    ) -> None:
                        if cache_chunks is not None:
                            cache_chunks.append(pcm)
                        if on_pcm_callback is not None:
                            on_pcm_callback(pcm)

                    self._get_engine().synthesize(job.text, _on_pcm)
                    if job.cache_key is not None and cache_chunks:
                        self._store_pcm_cache(job.cache_key, tuple(cache_chunks))
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
                if job.cache_key is not None:
                    self._clear_prefetch_job(job.cache_key, job)
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

    def _speech_cache_key(self, text: str) -> str:
        return " ".join((text or "").split())

    def _cached_pcm(self, cache_key: str) -> tuple[bytes, ...] | None:
        with self._cache_lock:
            cached = self._pcm_cache.get(cache_key)
            return tuple(cached) if cached is not None else None

    def _store_pcm_cache(self, cache_key: str, chunks: tuple[bytes, ...]) -> None:
        if not cache_key or not chunks:
            return
        with self._cache_lock:
            self._pcm_cache[cache_key] = chunks
            while len(self._pcm_cache) > _PCM_CACHE_LIMIT:
                oldest = next(iter(self._pcm_cache))
                self._pcm_cache.pop(oldest, None)

    def _prefetch_job(self, cache_key: str) -> _ChatterboxWorkerJob | None:
        with self._cache_lock:
            return self._prefetch_jobs.get(cache_key)

    def _clear_prefetch_job(self, cache_key: str, job: _ChatterboxWorkerJob) -> None:
        with self._cache_lock:
            if self._prefetch_jobs.get(cache_key) is job:
                self._prefetch_jobs.pop(cache_key, None)

    def prefetch_text(self, text: str) -> bool:
        """Start synthesizing ``text`` into the short PCM cache.

        Returns True only when a new background synth was queued. The method is
        best-effort and does not wait; callers still pass through the normal
        linter/LiveKit path before any cached audio can reach speakers.
        """
        cache_key = self._speech_cache_key(text)
        if not cache_key:
            return False
        with self._cache_lock:
            if cache_key in self._pcm_cache or cache_key in self._prefetch_jobs:
                return False
            job = _ChatterboxWorkerJob(
                "synth",
                text=cache_key,
                cache_key=cache_key,
                cache_chunks=[],
            )
            self._prefetch_jobs[cache_key] = job
        self._ensure_worker().put(job)
        return True

    def has_cached_text(self, text: str) -> bool:
        """True only when ``text`` can be spoken without a fresh synth job."""
        cache_key = self._speech_cache_key(text)
        return bool(cache_key and self._cached_pcm(cache_key) is not None)

    def synthesize_pcm(self, text: str, on_pcm: Callable[[bytes], None]) -> None:
        """Synthesize mono PCM bytes for non-LiveKit sinks."""
        with self._synth_lock:
            cache_key = self._speech_cache_key(text)
            if cache_key:
                cached = self._cached_pcm(cache_key)
                if cached is not None:
                    for pcm in cached:
                        on_pcm(pcm)
                    return
                prefetch_job = self._prefetch_job(cache_key)
                if prefetch_job is not None:
                    prefetch_job.done.wait()
                    if prefetch_job.error is not None:
                        raise prefetch_job.error
                    cached = self._cached_pcm(cache_key)
                    if cached is not None:
                        for pcm in cached:
                            on_pcm(pcm)
                        return

            cache_chunks: list[bytes] | None = [] if cache_key else None
            job = _ChatterboxWorkerJob(
                "synth",
                text=text,
                on_pcm=on_pcm,
                cache_key=cache_key or None,
                cache_chunks=cache_chunks,
            )
            self._ensure_worker().put(job)
            job.done.wait()
            if job.error is not None:
                raise job.error

    def synthesize(
        self, text: str, *, conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS
    ) -> agents_tts.ChunkedStream:
        return _ChatterboxChunkedStream(tts=self, input_text=text, conn_options=conn_options)


class _ChatterboxChunkedStream(agents_tts.ChunkedStream):
    """Runs blocking Chatterbox synthesis on the worker and emits PCM safely.

    The real MLX generator may produce partial PCM much slower than real time on
    a busy machine. Forwarding those partial chunks immediately makes the
    sounddevice output underflow, which sounds like repeated consonant ticks.
    For that engine we coalesce the synthesized PCM and hand LiveKit one
    contiguous segment; fake/unit-test engines can still stream chunk-by-chunk.
    """

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
        q: asyncio.Queue[object] = asyncio.Queue()
        engine = getattr(tts, "_engine", None)
        buffer_before_playback = bool(
            engine is None or getattr(engine, "buffer_before_playback", False)
        )
        pending_pcm = bytearray()

        def _on_pcm(pcm: bytes) -> None:
            loop.call_soon_threadsafe(q.put_nowait, pcm)

        def _produce() -> None:
            try:
                tts.synthesize_pcm(self._input_text, _on_pcm)
            except BaseException as exc:
                loop.call_soon_threadsafe(q.put_nowait, exc)
            finally:
                loop.call_soon_threadsafe(q.put_nowait, self._DONE)

        fut = loop.run_in_executor(None, _produce)
        try:
            while True:
                item = await q.get()
                if item is self._DONE:
                    break
                if isinstance(item, BaseException):
                    raise item
                if buffer_before_playback:
                    pending_pcm.extend(item)
                else:
                    output_emitter.push(item)
        except asyncio.CancelledError:
            raise
        except BaseException as exc:
            raise APIError(f"Chatterbox local TTS synthesis failed: {exc}") from exc
        finally:
            await fut

        if pending_pcm:
            output_emitter.push(bytes(pending_pcm))
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
