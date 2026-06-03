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

Wiring: ``tts_chain`` and proxy mode both use this provider as the single source
of TTS. If the model is missing, voice is unavailable; vibemix does not route to
a paid/cloud voice as a fallback.

The heavy ONNX runtime (~728 MB, 9 ORT sessions) loads once per instance, lazily,
off the event loop. ``prewarm()`` kicks the load in the background so the first
reaction of a session isn't the one that pays for it. All blocking synthesis runs
in an executor; decoded PCM is marshalled back to the loop as it is produced, so
first audio still streams out fast.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import threading
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from livekit.agents import tts as agents_tts
from livekit.agents._exceptions import APIError
from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS, APIConnectOptions
from livekit.agents.utils import shortuuid

from vibemix.voice_presets import (
    DEFAULT_MOSS_VOICE,
    normalize_stored_voice,
    select_moss_voice_row,
)

if TYPE_CHECKING:
    import numpy as np

# --- config (plain env, not the Gemini-only model_router) ---
# Native model output rate. The codec emits 48 kHz; we read the real value from
# the model meta at construction and only fall back to this if that read fails.
_DEFAULT_NATIVE_SR = 48000
_DEFAULT_VOICE = os.environ.get(
    "VIBEMIX_MOSS_TTS_VOICE", DEFAULT_MOSS_VOICE
)  # clear EN male preset
_DEFAULT_THREADS = int(os.environ.get("VIBEMIX_MOSS_TTS_THREADS", "4") or "4")
MOSS_MODEL_DIR_ENV = "VIBEMIX_MOSS_TTS_DIR"
_MOSS_MANIFEST = "browser_poc_manifest.json"
_MOSS_MODEL_DIRNAME = "MOSS-TTS-Nano-100M-ONNX"
_BUNDLED_MODEL_ROOT = Path("models") / "moss-tts-onnx"


def default_model_dir() -> Path:
    """The cached MOSS-TTS-Nano ONNX model dir (mirrors the CLAP/CUE model caches)."""
    cache = os.environ.get("VIBEMIX_CACHE_DIR") or os.path.join(Path.home(), ".cache", "vibemix")
    return Path(cache) / "moss-tts-onnx" / _MOSS_MODEL_DIRNAME


def _bundled_model_dir_candidates() -> list[Path]:
    """Return possible PyInstaller/Tauri bundled MOSS model dirs.

    Release builds put the sidecar in a Tauri resource directory with a
    PyInstaller ``_internal`` tree beside it. In that layout ``sys._MEIPASS``
    normally points at ``_internal``; some smoke/frozen contexts are easier to
    reason about from ``sys.executable``. Probe both so a clean packaged app can
    find its bundled MOSS model without relying on Kaan's dev cache or a
    process-env override.
    """
    roots: list[Path] = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        roots.append(Path(meipass))
    if getattr(sys, "frozen", False):
        try:
            exe_dir = Path(sys.executable).resolve().parent
            roots.extend([exe_dir / "_internal", exe_dir])
        except Exception:
            pass

    candidates: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        candidate = root / _BUNDLED_MODEL_ROOT / _MOSS_MODEL_DIRNAME
        try:
            key = candidate.resolve(strict=False)
        except Exception:
            key = candidate
        if key not in seen:
            seen.add(key)
            candidates.append(candidate)
    return candidates


def candidate_model_dir() -> Path:
    """Return the configured MOSS model dir, even when it is not installed."""
    override = os.environ.get(MOSS_MODEL_DIR_ENV)
    if override:
        return Path(override).expanduser()
    for candidate in _bundled_model_dir_candidates():
        if candidate.exists():
            return candidate
    return default_model_dir()


def resolve_model_dir() -> Path | None:
    """Return the usable MOSS model dir, or ``None`` if not present/cached.

    ``VIBEMIX_MOSS_TTS_DIR`` overrides; it must point at the ``*-Nano-100M-ONNX``
    dir (the dir holding ``browser_poc_manifest.json``). Without an override,
    a frozen sidecar first checks its bundled model tree, then the user cache.
    """
    candidate = candidate_model_dir()
    if not model_status()["installed"]:
        return None
    if (candidate / _MOSS_MANIFEST).is_file():
        return candidate
    return None


def _resolve_manifest_path(base: Path, rel_path: str) -> Path:
    path = Path(rel_path)
    return path if path.is_absolute() else (base / path).resolve(strict=False)


def _display_model_path(path: Path, model_dir: Path) -> str:
    for root in (model_dir, model_dir.parent):
        try:
            return str(path.relative_to(root))
        except ValueError:
            continue
    return str(path)


def _read_json_file(path: Path, mismatched: list[str], model_dir: Path) -> dict[str, object] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        mismatched.append(_display_model_path(path, model_dir))
        return None


def _add_meta_files(
    *,
    meta_path: Path,
    required: set[Path],
    missing: list[str],
    mismatched: list[str],
    model_dir: Path,
) -> None:
    """Add ONNX/data files referenced by a MOSS meta file to ``required``."""
    if not meta_path.is_file():
        missing.append(_display_model_path(meta_path, model_dir))
        return
    meta = _read_json_file(meta_path, mismatched, model_dir)
    if not meta:
        return
    base = meta_path.parent
    files = meta.get("files")
    if isinstance(files, dict):
        for rel_path in files.values():
            if isinstance(rel_path, str):
                required.add(_resolve_manifest_path(base, rel_path))
    external = meta.get("external_data_files")
    if isinstance(external, dict):
        for rel_paths in external.values():
            if isinstance(rel_paths, list):
                for rel_path in rel_paths:
                    if isinstance(rel_path, str):
                        required.add(_resolve_manifest_path(base, rel_path))


def model_status() -> dict[str, object]:
    """Return a cheap, no-ORT readiness check for the required MOSS model tree."""
    model_dir = candidate_model_dir()
    manifest_path = model_dir / _MOSS_MANIFEST
    missing: list[str] = []
    mismatched: list[str] = []
    required: set[Path] = {manifest_path}

    if not manifest_path.is_file():
        missing.append(_MOSS_MANIFEST)
    else:
        manifest = _read_json_file(manifest_path, mismatched, model_dir)
        if manifest:
            model_files = manifest.get("model_files")
            if isinstance(model_files, dict):
                for key, rel_path in model_files.items():
                    if not isinstance(rel_path, str):
                        continue
                    path = _resolve_manifest_path(model_dir, rel_path)
                    required.add(path)
                    if key in {"tts_meta", "codec_meta"}:
                        _add_meta_files(
                            meta_path=path,
                            required=required,
                            missing=missing,
                            mismatched=mismatched,
                            model_dir=model_dir,
                        )

    for path in sorted(required, key=lambda p: str(p)):
        if not path.is_file():
            display = _display_model_path(path, model_dir)
            if display not in missing:
                missing.append(display)

    return {
        "installed": not missing and not mismatched,
        "path": str(model_dir),
        "missing": missing,
        "mismatched": mismatched,
    }


_DISABLE_FLAGS = {"0", "false", "no", "off", "disabled"}


class LocalTTSUnavailable(RuntimeError):
    """Raised when the only allowed TTS provider, local MOSS, cannot be built."""


def _local_tts_disabled_by_env() -> bool:
    return (os.environ.get("VIBEMIX_LOCAL_TTS") or "").strip().lower() in _DISABLE_FLAGS


def local_tts_enabled() -> bool:
    """True when local MOSS is allowed and the model is cached.

    MOSS is the single TTS provider. ``VIBEMIX_LOCAL_TTS=0`` disables speech, but
    it never enables a cloud fallback.
    """
    if _local_tts_disabled_by_env():
        return False
    return resolve_model_dir() is not None


def local_tts_unavailable_reason() -> str:
    """Human-actionable reason the MOSS provider cannot be built."""
    if _local_tts_disabled_by_env():
        return "MOSS local TTS is disabled by VIBEMIX_LOCAL_TTS=0"
    return (
        "MOSS local TTS model not found; cache it under "
        "~/.cache/vibemix/moss-tts-onnx/MOSS-TTS-Nano-100M-ONNX or set "
        f"{MOSS_MODEL_DIR_ENV}"
    )


def _read_native_sample_rate(model_dir: Path) -> int:
    """Cheaply read the codec output sample rate from the model meta (no ORT load)."""
    try:
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
        row = select_moss_voice_row(voices, voice, fallback=_DEFAULT_VOICE)
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
        self._voice = normalize_stored_voice(voice)
        self._thread_count = thread_count
        self._engine: MossEngine | None = engine
        self._engine_lock = threading.Lock()
        self._synth_lock = threading.Lock()

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

    def set_voice(self, voice: str) -> None:
        """Switch the live MOSS voice; the next synthesis rebuilds the engine."""
        normalized = normalize_stored_voice(voice)
        with self._synth_lock:
            with self._engine_lock:
                if self._voice == normalized:
                    return
                self._voice = normalized
                self._engine = None

    def prewarm(self) -> None:
        """Kick the (~728 MB) engine load in the background so reaction #1 is warm."""
        if self._engine is not None:
            return

        def _bg() -> None:
            try:
                self._get_engine()
            except Exception:
                # A failed prewarm must not crash boot; the synth path surfaces
                # the error because there is no cloud TTS fallback.
                pass

        threading.Thread(target=_bg, name="moss-tts-prewarm", daemon=True).start()

    def synthesize_pcm(self, text: str, on_pcm: Callable[[bytes], None]) -> None:
        """Synthesize mono PCM bytes for non-LiveKit sinks such as Learn tutor audio."""
        with self._synth_lock:
            self._get_engine().synthesize(text, on_pcm)

    def synthesize(
        self, text: str, *, conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS
    ) -> agents_tts.ChunkedStream:
        return _MossChunkedStream(tts=self, input_text=text, conn_options=conn_options)


def build_local_tts_adapter(
    *, voice: str | None = None, moss: MossLocalTTS | None = None
) -> agents_tts.FallbackAdapter:
    """Build the single allowed live voice chain: one local MOSS provider."""
    if not local_tts_enabled():
        raise LocalTTSUnavailable(local_tts_unavailable_reason())
    moss = moss or MossLocalTTS(voice=voice or _DEFAULT_VOICE)
    moss.prewarm()
    return agents_tts.FallbackAdapter(tts=[moss], max_retry_per_tts=1)


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
                tts.synthesize_pcm(self._input_text, _on_pcm)
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
