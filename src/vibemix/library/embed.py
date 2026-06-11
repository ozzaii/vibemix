# SPDX-License-Identifier: Apache-2.0
"""Legacy Gemini Embedding 2 client kept for migration and fallback tests.

# Proxy-only contract
==================

This module is not the product embedding path. Normal library search,
similarity, and curation embeddings use local CLAP ONNX/512 via
``ClapEmbedder``. The legacy Gemini client remains for migrations, compatibility
tests, explicit fallback probes, and historical cache handling.

When this legacy path is used, it NEVER reads any AIza-style env var directly.
All Gemini API traffic flows through the Bravoh proxy via
``build_proxy_genai_client``. Callers build the proxy client once and pass it in.
The privacy + cost-control invariants from LIBRARY-04 + LIBRARY-10 hold because
this module cannot bypass the proxy.

# Strategy
========

1. Tracks with ``duration_s > AUDIO_SINGLE_CALL_MAX_SECONDS`` (80s) are
   split into 3 mp3 excerpts (intro / mid / outro, 60s each via ffmpeg)
   and the mean of their embeddings is used. Mitigates Pitfall P54
   (Gemini Embedding 2's 180s docs cap) AND the observed real-world
   ~80s single-call reliability ceiling on the GA SKU: we proactively
   excerpt 80-180s tracks instead of gambling a full-track upload that
   may fail mid-flight on a slow connection.
2. Tracks <= 80s pass the raw file as a single audio Part (fast path).
3. Streaming-only tracks (no local file) fall back to text-only embed of
   ``"title by artist | bpm BPM | key K"``.
4. Every embed is keyed by SHA256 of
   ``(file_bytes || model_id || strategy_version)`` and persisted to
   ``~/.cache/vibemix/embeddings.db`` so re-imports do 0 API calls.
5. Output dimensionality is single-sourced from
   ``_cosine.EMBEDDING_DIM``. This legacy Gemini embedder is no longer selected
   by the product factory; normal library embeddings are CLAP/512.

# Critical corrections (Phase 28 RESEARCH Open Qs)
===============================================

- Model ID resolved via ``vibemix.llm.model_router.resolve("embedding")``
  (Plan 41-01). Open Q9 verified the legacy text-only embedding-0xx
  series is superseded and CONTEXT was stale; see ``_router_config.py``
  for the live id.
- Cache DB path is ``~/.cache/vibemix/embeddings.db`` — distinct from
  Plan 02's ``library.db`` (vec0 store) and Phase 25's ``library.pkl``
  (Rekordbox parsed cache).
- No legacy task-routing kwarg (Open Q8 — not valid for Embedding 2).
"""

from __future__ import annotations

import hashlib
import logging
import shutil
import sqlite3
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from vibemix.library._cosine import EMBEDDING_DIM, l2_normalize
from vibemix.library.cache_paths import EMBED_CACHE_DB_PATH
from vibemix.library.embed_cache import (
    init_cache_schema as _init_cache_schema,
)
from vibemix.library.embed_cache import (
    open_default_cache_db as _open_default_cache_db,
)
from vibemix.library.embed_config import (
    CUE_ANCHORED_STRATEGY_VERSION,
    CUE_WINDOW_SECONDS,
    DEFAULT_EMBED_STRATEGY,
    EMBED_STRATEGIES,
    MAX_CUES_PER_TRACK,
)
from vibemix.library.embed_factory import build_embedder
from vibemix.library.rekordbox import TrackEntry
from vibemix.llm._router_config import (
    EMBEDDING_GA_CANDIDATES as GEMINI_EMBEDDING_MODEL_GA_CANDIDATES,
)
from vibemix.llm.model_router import resolve_model

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from google import genai


# ─── Locked constants ──────────────────────────────────────────────────────────

# Open Q9 — Gemini Embedding 2 supersedes the legacy text-only embedding series.
# Plan 41-01: resolved via the model router (path: "embedding"). CRITICAL —
# this id flows into the LibraryEmbedder cache-key SHA256. Any model rename
# MUST be coordinated with EXCERPT_STRATEGY_VERSION (Plan 41-05 owns that).
# Plan 41-05: GEMINI_EMBEDDING_MODEL_GA_CANDIDATES below is the probe-time
# override; this constant is the router-resolved default for non-probe paths.
GEMINI_EMBEDDING_MODEL = resolve_model("embedding")

# Plan 41-05 LAT-06 — GA-rename auto-bump probe candidates.
# Sourced from `_router_config.EMBEDDING_GA_CANDIDATES` (the only allowlisted
# location for raw Gemini model literals). Re-exported here for backward
# compatibility with downstream consumers that import from `library.embed`.

# Bump to invalidate ALL cached embeddings. Format: vN-<strategy-name>.
EXCERPT_STRATEGY_VERSION = "v1-3excerpt-mean"

# Plan 41-05 — version bump that runs the moment the GA-rename probe
# resolves to the GA-renamed candidate (first entry of EMBEDDING_GA_CANDIDATES
# in `_router_config.py`). The new cache-key bytes diverge from the legacy
# key, forcing the lazy re-embed migration path.
EXCERPT_STRATEGY_VERSION_GA_RENAME = "v2-3excerpt-mean-emb2-ga"

# Gemini Embedding 2 hard audio cap (Google docs, re-confirmed 2026-05-25).
# P54. Used ONLY by the _is_audio_cap_error heuristic now — the single-call
# routing decision uses AUDIO_SINGLE_CALL_MAX_SECONDS below.
AUDIO_CAP_SECONDS = 180

# Conservative single-call threshold (quick-260525-gz2). Docs say 180s, but
# Kaan's research flagged real-world single-call audio embed failures in the
# 80-180s band on the emb-2 GA SKU. We proactively route 80-180s tracks to
# the proven 3-excerpt path so a slow-connection bring-up never wastes a
# full-track upload + retry on a clip the server will reject anyway. The
# single-call -> cap-error -> force_excerpts fallback stays as defense-in-depth
# for <=80s clips the API still rejects.
AUDIO_SINGLE_CALL_MAX_SECONDS = 80

# Per excerpt length in the 3-excerpt path.
EXCERPT_DURATION = 60

# ffmpeg subprocess timeout per excerpt — guard against malformed audio.
FFMPEG_TIMEOUT_SECONDS = 30

# Cue-window WAV slice rate (PyAV path). 48k mono PCM16 keeps the legacy
# Gemini upload faithful without an external encoder binary.
_SLICE_WAV_SR = 48000

# Re-export so downstream plans don't have to import from _cosine directly.
__all__ = [
    "AUDIO_CAP_SECONDS",
    "AUDIO_SINGLE_CALL_MAX_SECONDS",
    "CUE_ANCHORED_STRATEGY_VERSION",
    "CUE_WINDOW_SECONDS",
    "DEFAULT_EMBED_STRATEGY",
    "EMBEDDING_DIM",
    "EMBED_CACHE_DB_PATH",
    "EMBED_STRATEGIES",
    "EXCERPT_STRATEGY_VERSION",
    "EXCERPT_STRATEGY_VERSION_GA_RENAME",
    "GEMINI_EMBEDDING_MODEL",
    "GEMINI_EMBEDDING_MODEL_GA_CANDIDATES",
    "MAX_CUES_PER_TRACK",
    "LibraryEmbedder",
    "_probe_ga_model_id",
    "build_embedder",
]


# ─── ffmpeg availability check ─────────────────────────────────────────────────


def _require_ffmpeg() -> str:
    """Return the ffmpeg binary path or raise RuntimeError (fail-loud).

    Per RESEARCH "ffmpeg not available" pitfall: ffmpeg is a hard requirement
    for the 3-excerpt path. Surface the missing-binary error at module entry
    rather than mid-embed.
    """
    ff = shutil.which("ffmpeg")
    if ff is None:
        raise RuntimeError(
            "ffmpeg is required for the LibraryEmbedder 3-excerpt path. "
            "Install via `brew install ffmpeg` (mac) or "
            "`winget install Gyan.FFmpeg` (windows)."
        )
    return ff


def _genai_types():
    """Import Gemini SDK types only when the legacy embedder makes a call."""
    from google.genai import types

    return types


# ─── GA-rename probe ──────────────────────────────────────────────────────────


def _probe_ga_model_id(
    client: genai.Client,
    recorder: object | None = None,
) -> tuple[str, str]:
    """Probe Gemini for the canonical Embedding 2 model id (Plan 41-05).

    Tries ``GEMINI_EMBEDDING_MODEL_GA_CANDIDATES`` in order. The first
    candidate that returns a valid embedding for a tiny canary text becomes
    the runtime model id. If the GA-renamed candidate (the first entry of the
    tuple) succeeds, the strategy version bumps to
    ``EXCERPT_STRATEGY_VERSION_GA_RENAME`` so cache keys invalidate. If the
    legacy fallback (second entry) succeeds, the version stays at the v2.1
    default so existing cache rows continue to hit.

    Returns ``(model_id, excerpt_strategy_version)``.

    Raises ``RuntimeError`` if ALL candidates fail — caller decides whether
    to fall back to module defaults or surface the outage to the user.

    The optional ``recorder`` is anything that exposes
    ``log_event(name, **kwargs)`` (matches ``VoiceRecorder``); when present
    we emit an ``embedding_model_probe`` event with the candidate list,
    chosen id, version, and probe duration.
    """
    import time as _time

    started = _time.perf_counter()
    canary = "vibemix probe"
    candidates_tried: list[str] = []
    types = _genai_types()

    for candidate in GEMINI_EMBEDDING_MODEL_GA_CANDIDATES:
        candidates_tried.append(candidate)
        try:
            result = client.models.embed_content(
                model=candidate,
                contents=canary,
                config=types.EmbedContentConfig(
                    output_dimensionality=EMBEDDING_DIM,
                ),
            )
        except Exception as exc:
            logger.info(
                "Embedding GA probe: candidate %r failed (%s); trying next.",
                candidate,
                exc,
            )
            continue

        if result is None or not getattr(result, "embeddings", None):
            logger.info(
                "Embedding GA probe: candidate %r returned no embeddings; "
                "trying next.",
                candidate,
            )
            continue

        # First candidate in the tuple is the GA-renamed id (by contract in
        # `_router_config.EMBEDDING_GA_CANDIDATES`). When the probe lands on
        # it, bump the cache-key version so cached rows invalidate cleanly.
        is_ga_renamed = candidate == GEMINI_EMBEDDING_MODEL_GA_CANDIDATES[0]
        version = (
            EXCERPT_STRATEGY_VERSION_GA_RENAME
            if is_ga_renamed
            else EXCERPT_STRATEGY_VERSION
        )
        duration_ms = int((_time.perf_counter() - started) * 1000)
        if recorder is not None:
            try:
                recorder.log_event(
                    "embedding_model_probe",
                    chosen=candidate,
                    version=version,
                    candidates_tried=list(candidates_tried),
                    duration_ms=duration_ms,
                )
            except Exception as log_exc:  # pragma: no cover - defensive
                logger.warning(
                    "embedding_model_probe event emit failed: %s", log_exc
                )
        return candidate, version

    raise RuntimeError(
        "All GEMINI_EMBEDDING_MODEL_GA_CANDIDATES failed probe "
        f"({list(GEMINI_EMBEDDING_MODEL_GA_CANDIDATES)!r}). "
        "Embeddings unavailable until network / API restored."
    )


# ─── LibraryEmbedder ───────────────────────────────────────────────────────────


class LibraryEmbedder:
    """Legacy Gemini entry point for migration/fallback embedding tests.

    Construction:
        ``LibraryEmbedder(client, cache_db=None)`` where ``client`` is a
        proxy-wired ``genai.Client`` built via
        ``vibemix.agent.proxy_client.build_proxy_genai_client(...)``.
        ``cache_db`` defaults to ``~/.cache/vibemix/embeddings.db``.

    Public API:
        ``embed_track(track)`` → EMBEDDING_DIM float32 L2-normalized vector.
        ``embed_query(query)`` → EMBEDDING_DIM float32 L2-normalized vector (no
            content-hash cache here; Plan 03 owns the 24h query cache).

    Thread safety:
        SQLite connection is not safe across threads by default. Callers in
        async contexts must wrap embed calls in
        ``loop.run_in_executor(None, embedder.embed_track, track)`` (matches
        the existing cohost_v4 pattern).
    """

    def __init__(
        self,
        client: genai.Client,
        cache_db: sqlite3.Connection | None = None,
        *,
        probe_on_init: bool = True,
        recorder: object | None = None,
        embed_strategy: str = DEFAULT_EMBED_STRATEGY,
    ) -> None:
        self._client = client
        self._recorder = recorder
        # Embed strategy selector (Path 2). DEFAULT stays mean_excerpt — the
        # cue_anchored path is opt-in and never changes default behavior.
        if embed_strategy not in EMBED_STRATEGIES:
            raise ValueError(
                f"unknown embed_strategy {embed_strategy!r}; "
                f"expected one of {EMBED_STRATEGIES}"
            )
        self._embed_strategy = embed_strategy
        if cache_db is None:
            self._cache = _open_default_cache_db()
            self._owns_cache = True
        else:
            _init_cache_schema(cache_db)
            self._cache = cache_db
            self._owns_cache = False

        # Plan 41-05 GA-rename probe.
        # Production path: ``probe_on_init=True`` (default). Construction
        # sends one canary embed call against the GA-renamed id first; on
        # 404 falls back to the v2.1 legacy id without invalidating cache.
        # On total probe failure we keep module defaults so the app can
        # still attempt embeds (the real failure will surface on first call).
        # Test path: ``probe_on_init=False`` preserves deterministic call
        # counts for the existing test_embed.py suite.
        self._model = GEMINI_EMBEDDING_MODEL
        self._excerpt_strategy_version = EXCERPT_STRATEGY_VERSION
        if probe_on_init:
            try:
                probed_model, probed_version = _probe_ga_model_id(
                    self._client, recorder=self._recorder
                )
                self._model = probed_model
                self._excerpt_strategy_version = probed_version
            except RuntimeError as exc:
                logger.warning(
                    "Embedding GA probe failed (%s); falling back to module "
                    "defaults model=%s version=%s.",
                    exc,
                    GEMINI_EMBEDDING_MODEL,
                    EXCERPT_STRATEGY_VERSION,
                )

    def __del__(self) -> None:  # pragma: no cover - GC path
        if getattr(self, "_owns_cache", False) and self._cache is not None:
            try:
                self._cache.close()
            except Exception:
                pass

    # ─── Public surface ────────────────────────────────────────────────────

    def embed_track(self, track: TrackEntry) -> np.ndarray:
        """Embed a track, returning an EMBEDDING_DIM float32 L2-normalized vector.

        Decision tree:
            1. content-hash cache hit → return cached
            2. local file exists → audio path (3-excerpt if > 180s else
               single call)
            3. else → text-only embed of "title by artist | BPM | key"
        """
        key = self._track_hash(track)
        cached = self._cache_get(key)
        if cached is not None:
            logger.debug("LibraryEmbedder cache hit: %s", track.track_id)
            # Plan 28-08 — telemetry.
            from vibemix.library.budget import get_telemetry as _gt
            _gt().increment_cache_hit()
            return cached

        local_path: Path | None = None
        if track.filepath:
            p = Path(track.filepath)
            if p.exists():
                local_path = p

        if local_path is not None:
            if self._embed_strategy == "cue_anchored":
                vector = self._embed_audio_cue_anchored(
                    local_path, track.duration_s
                )
            else:
                vector = self._embed_audio(local_path, track.duration_s)
        else:
            text = self._text_signature(track)
            vector = self._call_gemini_text(text)
            vector = l2_normalize(vector)

        self._cache_put(key, vector)
        return vector

    def embed_query(self, query: str) -> np.ndarray:
        """Embed a natural-language vibe-search query (text-only path).

        No content-hash cache here — Plan 28-03's 24h LRU sits on top of
        this, keyed on ``query + library_snapshot_hash``.
        """
        vec = self._call_gemini_text(query)
        return l2_normalize(vec)

    def embed_audio_bytes(self, data: bytes, mime: str) -> np.ndarray:
        """Embed raw audio bytes → EMBEDDING_DIM float32 L2-normalized vector.

        The 'what's playing' grounding path (short ≤30s buffer). Phase 90: this
        is the public seam ``grounding.py`` routes through so a ClapEmbedder
        (no ``_client``) is a drop-in — it no longer reaches into
        ``embedder._client.models.embed_content`` directly.
        """
        from vibemix.library.budget import get_telemetry as _gt
        _gt().increment_audio_embed()
        vec = self._call_gemini_audio_single(data, mime)
        return l2_normalize(vec)

    def has_cached_embedding(self, track: TrackEntry) -> bool:
        """Return True iff a content-hash cache hit would occur.

        Public probe used by ``LibraryImporter`` for accurate cache-hit
        counting in import-progress emissions. Avoids LibraryImporter
        reaching into ``_embedder._cache`` private attribute (REVIEW WR-02).
        """
        try:
            key = self._track_hash(track)
            return self._cache_get(key) is not None
        except sqlite3.Error:
            return False

    # ─── Internal: audio path ──────────────────────────────────────────────

    def _embed_audio(self, audio_path: Path, duration_s: float) -> np.ndarray:
        """Audio embed path. Returns L2-normalized float32 vector."""
        # Short track (<=80s) — try single call first; on cap-error,
        # force-fallback. 80-180s tracks skip this and go straight to the
        # 3-excerpt path (no single-call gamble) per gz2 audio-cap hardening.
        force_excerpts = False
        if duration_s <= AUDIO_SINGLE_CALL_MAX_SECONDS:
            try:
                clip = audio_path.read_bytes()
                mime = self._mime_for_path(audio_path)
                vec = self._call_gemini_audio_single(clip, mime)
                return l2_normalize(vec)
            except Exception as e:
                if not self._is_audio_cap_error(e):
                    raise
                logger.warning(
                    "Single-call audio embed failed with cap error "
                    "(%s); falling back to 3-excerpt path.",
                    e,
                )
                force_excerpts = True

        # 3-excerpt path: intro / mid / outro.
        excerpts = self._extract_excerpts(
            audio_path, duration_s, force=force_excerpts
        )
        vecs: list[np.ndarray] = []
        for clip in excerpts:
            vec = self._call_gemini_audio_single(clip, mime_type="audio/mpeg")
            vecs.append(vec)
        mean = np.mean(np.stack(vecs), axis=0).astype(np.float32)
        return l2_normalize(mean)

    def _embed_audio_cue_anchored(
        self, audio_path: Path, duration_s: float
    ) -> np.ndarray:
        """Cue-anchored audio embed path (Path 2, opt-in).

        Pipeline:
            1. Offline auto-cue detection (``cue_engine.detect_cues_auto``) —
               local DSP/ONNX with heuristic fallback, NO network. Finds the
               mixable structural points.
            2. For each cue, PyAV-slice a <=CUE_WINDOW_SECONDS (80s) window
               anchored AT the cue (cue = window start), embed it as a single
               audio Part, collect the vectors.
            3. MEAN the cue-region vectors → one EMBEDDING_DIM L2-normalized
               vector (single-vector contract preserved).

        Falls back to the mean_excerpt path if cue detection finds nothing
        usable (e.g. an undecodable file, or a track with no detectable
        structure) — never returns a faked vector, never raises on a
        no-structure track.

        # MULTI-VECTOR SEAM
        A future multi-vector mode would store the per-cue ``vecs`` list
        (one row per cue, with the cue's ``start_s`` + hot-cue number) instead
        of meaning them — that's what powers "enter on hot cue 2" retrieval.
        The store + search layers take a single vector today, so we MEAN here
        and leave the per-cue vectors + their CuePoint metadata as the natural
        extension point.
        """
        from vibemix.library.cue_engine import detect_cues_auto

        try:
            cues = detect_cues_auto(audio_path, max_cues=MAX_CUES_PER_TRACK)
        except Exception as e:
            logger.warning(
                "cue detection failed for %s (%s); falling back to "
                "mean_excerpt embed.",
                audio_path,
                e,
            )
            return self._embed_audio(audio_path, duration_s)

        # An EMPTY list means the auto-cue engine found no real structure
        # (silence / too short / failed dance gate with nothing to anchor).
        # Fall back to the proven mean_excerpt path rather than embedding a
        # single 0..80s window that's no better than the intro excerpt.
        usable = list(cues)
        if not usable:
            return self._embed_audio(audio_path, duration_s)

        vecs: list[np.ndarray] = []
        for cue in usable:
            start = max(0.0, float(cue.start_s))
            # Use the phrase-aligned mixable window the engine sized into the
            # anchor (end_s - start_s, already <=80s) instead of a hardcoded
            # CUE_WINDOW_SECONDS — the engine knows how long the mix region is.
            # Clamp so we never request audio past the end-of-track (a slice
            # past EOF just yields a short clip, which embeds fine, but
            # clamping keeps the call honest).
            window = max(1.0, float(cue.end_s) - start)
            if duration_s > 0:
                window = min(window, max(1.0, duration_s - start))
            try:
                clip = self._slice_window(audio_path, start, window)
                vec = self._call_gemini_audio_single(
                    clip, mime_type="audio/wav"
                )
                vecs.append(vec)
            except Exception as e:  # one bad cue must not abort the track
                logger.warning(
                    "cue-region embed failed at %.1fs for %s (%s); skipping "
                    "this cue.",
                    start,
                    audio_path,
                    e,
                )
                continue

        if not vecs:
            # Every cue-region embed failed — fall back rather than fake.
            return self._embed_audio(audio_path, duration_s)

        # MULTI-VECTOR SEAM (see docstring) — single-vector contract: mean.
        mean = np.mean(np.stack(vecs), axis=0).astype(np.float32)
        return l2_normalize(mean)

    def _slice_window(
        self, audio_path: Path, start_s: float, length_s: float
    ) -> bytes:
        """PyAV-slice a single WAV window [start_s, start_s+length_s).

        The packaged app ships NO ffmpeg binary, so the slice rides the
        bundled PyAV decoder; stdlib PCM16 WAV replaces the old lossy 128k mp3
        re-encode (the slice bytes change, which is why
        ``CUE_ANCHORED_STRATEGY_VERSION`` carries the pyav bump).
        """
        from vibemix.library.audio_decode import load_audio_mono, pcm16_wav_bytes

        samples = load_audio_mono(
            audio_path,
            target_sr=_SLICE_WAV_SR,
            offset_s=start_s,
            duration_s=length_s,
        )
        return pcm16_wav_bytes(samples, sr=_SLICE_WAV_SR)

    @staticmethod
    def _mime_for_path(path: Path) -> str:
        """Pick MIME type for the single-call path.

        Per Open Q6: ffmpeg transcodes to MP3 for the 3-excerpt path, so the
        mid path is always audio/mpeg. The single-call path passes the file
        bytes through directly — pick MIME by suffix.
        """
        suffix = path.suffix.lower()
        if suffix == ".wav":
            return "audio/wav"
        if suffix == ".flac":
            return "audio/flac"
        if suffix in (".m4a", ".aac"):
            return "audio/mp4"
        return "audio/mpeg"

    @staticmethod
    def _is_audio_cap_error(err: Exception) -> bool:
        """Heuristic match for Gemini 'audio too long' / 400 cap errors."""
        msg = str(err).lower()
        if "too long" in msg:
            return True
        if "audio cap" in msg or ("duration" in msg and "180" in msg):
            return True
        # google.genai.errors.APIError carries .code on some versions.
        code = getattr(err, "code", None) or getattr(err, "status_code", None)
        if code == 400 and "audio" in msg:
            return True
        return False

    def _extract_excerpts(
        self,
        audio_path: Path,
        duration_s: float,
        force: bool = False,
    ) -> list[bytes]:
        """Use ffmpeg to slice 3 mp3 excerpts (intro / mid / outro).

        Each excerpt is 60s, encoded as MP3 at 128 kbps. Tempfiles are
        cleaned up before return.

        For tracks <= 80s (the single-call threshold), normally we should
        not be here (the single-call path handles them); defensive guard
        returns the whole file as 1 excerpt. Pass ``force=True`` to override
        (used when the single-call path fails with an audio-cap error and we
        want a 3-excerpt fallback even on a short-duration track).
        """
        if duration_s <= AUDIO_SINGLE_CALL_MAX_SECONDS and not force:
            return [audio_path.read_bytes()]

        ffmpeg = _require_ffmpeg()
        starts: list[float] = [
            0.0,
            max(0.0, (duration_s / 2.0) - (EXCERPT_DURATION / 2.0)),
            max(0.0, duration_s - EXCERPT_DURATION),
        ]
        out_clips: list[bytes] = []
        for start in starts:
            with tempfile.NamedTemporaryFile(
                suffix=".mp3", delete=False
            ) as tmp:
                tmp_path = Path(tmp.name)
            try:
                cmd = [
                    ffmpeg,
                    "-y",
                    "-loglevel",
                    "error",
                    "-ss",
                    f"{start:.3f}",
                    "-i",
                    str(audio_path),
                    "-t",
                    str(EXCERPT_DURATION),
                    "-acodec",
                    "libmp3lame",
                    "-b:a",
                    "128k",
                    str(tmp_path),
                ]
                subprocess.run(
                    cmd,
                    check=True,
                    timeout=FFMPEG_TIMEOUT_SECONDS,
                    capture_output=True,
                )
                out_clips.append(tmp_path.read_bytes())
            finally:
                try:
                    tmp_path.unlink()
                except FileNotFoundError:
                    pass
        return out_clips

    # ─── Internal: Gemini calls ───────────────────────────────────────────

    def _call_gemini_audio_single(
        self, clip: bytes, mime_type: str
    ) -> np.ndarray:
        """Single audio-Part embed_content call.

        Uses ``self._model`` (probe-derived runtime id) instead of the
        module constant so a GA rename auto-routes without code change.
        """
        types = _genai_types()
        result = self._client.models.embed_content(
            model=self._model,
            contents=[types.Part.from_bytes(data=clip, mime_type=mime_type)],
            config=types.EmbedContentConfig(
                output_dimensionality=EMBEDDING_DIM
            ),
        )
        values = list(result.embeddings[0].values)
        # Plan 28-08 — runtime cost telemetry.
        from vibemix.library.budget import get_telemetry as _gt
        _gt().increment_audio_embed()
        return np.asarray(values, dtype=np.float32)

    def _call_gemini_text(self, text: str) -> np.ndarray:
        """Text-mode embed_content call.

        Per Gemini SDK 2.0.1: text mode takes a string directly, NOT a
        list. ``contents="..."`` not ``contents=["..."]``.

        Uses ``self._model`` (probe-derived runtime id).
        """
        types = _genai_types()
        result = self._client.models.embed_content(
            model=self._model,
            contents=text,
            config=types.EmbedContentConfig(
                output_dimensionality=EMBEDDING_DIM
            ),
        )
        values = list(result.embeddings[0].values)
        # Plan 28-08 — runtime cost telemetry.
        from vibemix.library.budget import get_telemetry as _gt
        _gt().increment_text_embed()
        return np.asarray(values, dtype=np.float32)

    # ─── Internal: text-only signature & cache key ────────────────────────

    @staticmethod
    def _text_signature(track: TrackEntry) -> str:
        """Build the text-only embed signature for streaming-only tracks.

        Phase 25's TrackEntry coerces missing bpm to 0.0 and missing key
        to empty string, so we just stringify in place.
        """
        bpm = int(track.bpm or 0)
        key = track.key or "unknown"
        return f"{track.title} by {track.artist} | {bpm} BPM | key {key}"

    def _track_hash(self, track: TrackEntry) -> str:
        """SHA256 of (file_bytes_or_marker || model_id || strategy_version).

        For local files: stream in 64KB chunks (avoid loading large mp3s).
        For streaming-only: marker derived from track_id so re-imports of
        the same streaming-only entry still cache-hit.

        Plan 41-05: Uses ``self._model`` + ``self._excerpt_strategy_version``
        (probe-derived runtime values). When the probe falls back to the
        v2.1 legacy id, these resolve to the same bytes the v2.1 code
        wrote, so existing cache rows continue to hit. When the probe
        finds the GA-renamed id, the strategy version bumps and cache
        keys diverge — forcing the lazy re-embed migration path.
        """
        h = hashlib.sha256()
        if track.filepath:
            p = Path(track.filepath)
            if p.exists():
                with p.open("rb") as f:
                    while True:
                        chunk = f.read(64 * 1024)
                        if not chunk:
                            break
                        h.update(chunk)
            else:
                h.update(f"<streaming>{track.track_id}".encode())
        else:
            h.update(f"<streaming>{track.track_id}".encode())
        h.update(b"||")
        h.update(self._model.encode())
        h.update(b"||")
        h.update(self._excerpt_strategy_version.encode())
        # Strategy namespace: cue_anchored vectors must NEVER cache-collide
        # with mean_excerpt vectors for the same file. mean_excerpt keeps the
        # legacy key bytes (no extra component) so existing cache rows still
        # hit; cue_anchored appends its own version string.
        if self._embed_strategy == "cue_anchored":
            h.update(b"||")
            h.update(CUE_ANCHORED_STRATEGY_VERSION.encode())
        return h.hexdigest()

    # ─── Internal: cache get/put ──────────────────────────────────────────

    def _cache_get(self, key: str) -> np.ndarray | None:
        row = self._cache.execute(
            "SELECT vector FROM embed_cache WHERE key = ?", (key,)
        ).fetchone()
        if row is None:
            return None
        blob = row[0]
        vec = np.frombuffer(blob, dtype=np.float32).copy()
        # Dim guard: the content-hash key does not encode EMBEDDING_DIM, so a
        # cache row written at a different dim (e.g. a 768→512 bump without
        # clearing embed_cache) would otherwise be returned and crash the
        # fail-loud dim asserts downstream. Treat a wrong-dim row as a clean
        # MISS → lazy re-embed at the current dim. Correct-dim rows still hit,
        # so an in-progress run stays fully resumable for free.
        if vec.shape[0] != EMBEDDING_DIM:
            return None
        return vec

    def _cache_put(self, key: str, vector: np.ndarray) -> None:
        import time as _time

        assert vector.dtype == np.float32 and vector.shape == (EMBEDDING_DIM,)
        self._cache.execute(
            "INSERT OR REPLACE INTO embed_cache (key, vector, ts) "
            "VALUES (?, ?, ?)",
            (key, vector.tobytes(), _time.time()),
        )
        self._cache.commit()
