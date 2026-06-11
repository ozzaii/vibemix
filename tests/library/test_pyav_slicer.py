# SPDX-License-Identifier: Apache-2.0
"""PyAV window slicing — the packaged app ships NO ffmpeg binary.

The three audio slicers (section_vectors.default_section_slicer,
ingest._default_slicer, embed.LibraryEmbedder._slice_window) must ride the
bundled PyAV decoder. These tests poison ``subprocess`` so any shell-out on a
decode path fails loudly, and pin the cache-version bumps that keep stale
ffmpeg-era vectors from mixing with the new PyAV-decoded ones.
"""

from __future__ import annotations

import io
import sqlite3
import subprocess
import wave
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest

from vibemix.library.audio_decode import (
    AudioDecodeError,
    load_audio_mono,
    pcm16_wav_bytes,
)
from vibemix.library.clap_engine import CLAP_SR
from vibemix.library.cue_types import CueAnchor
from vibemix.library.rekordbox import CuePoint, TrackEntry

_WAV_SR = 8000


@pytest.fixture(autouse=True)
def _isolated_library_cache(tmp_path, monkeypatch):
    """Repo gotcha: never let a test write the REAL ~/.cache/vibemix/library.pkl."""
    from vibemix.library.rekordbox import RekordboxLibrary

    monkeypatch.setattr(RekordboxLibrary, "CACHE_PATH", tmp_path / "library.pkl")


@pytest.fixture
def no_subprocess(monkeypatch):
    """Poison subprocess — a decode-path shell-out must fail the test loudly."""

    def _boom(*args, **kwargs):
        raise AssertionError("subprocess must never run on an audio decode path")

    monkeypatch.setattr(subprocess, "run", _boom)
    monkeypatch.setattr(subprocess, "Popen", _boom)
    monkeypatch.setattr(subprocess, "check_output", _boom)


def _write_step_wav(path: Path, *, sr: int = _WAV_SR, seconds: float = 6.0) -> None:
    """Mono PCM16 wav where second ``k`` holds constant amplitude (k+1)*0.1.

    The per-second amplitude staircase makes slice positions verifiable: a
    window's mean |amplitude| identifies WHICH seconds were decoded.
    """
    n = int(sr * seconds)
    t = np.arange(n)
    level = ((t // sr) + 1).astype(np.float64) * 0.1
    pcm = np.round(level * 32767.0).astype("<i2")
    with wave.open(str(path), "wb") as fh:
        fh.setnchannels(1)
        fh.setsampwidth(2)
        fh.setframerate(sr)
        fh.writeframes(pcm.tobytes())


class _ArrayEmbedder:
    """Fake CLAP embedder exposing the in-memory array seam."""

    backend = "fake-clap"

    def __init__(self) -> None:
        self.array_calls: list[tuple[int, int]] = []  # (n_samples, sr)
        self.byte_calls: list[bytes] = []
        self.file_calls: list[str] = []

    def embed_audio_array(self, samples: np.ndarray, *, sr: int) -> np.ndarray:
        assert isinstance(samples, np.ndarray)
        self.array_calls.append((int(samples.shape[0]), int(sr)))
        vec = np.zeros(512, dtype=np.float32)
        vec[0] = 1.0
        return vec

    def embed_audio_bytes(self, data: bytes, mime: str) -> np.ndarray:
        raise AssertionError("array clip must use embed_audio_array, not bytes")

    def embed_audio_file(self, path: str) -> np.ndarray:
        self.file_calls.append(str(path))
        vec = np.zeros(512, dtype=np.float32)
        vec[1] = 1.0
        return vec


class _BytesOnlyEmbedder:
    """Duck-typed embedder WITHOUT the array seam — the wav fallback target."""

    backend = "fake-clap"

    def __init__(self) -> None:
        self.byte_calls: list[tuple[bytes, str]] = []

    def embed_audio_bytes(self, data: bytes, mime: str) -> np.ndarray:
        self.byte_calls.append((bytes(data), mime))
        vec = np.zeros(512, dtype=np.float32)
        vec[2] = 1.0
        return vec


def _track(track_id: str, filepath: str, *, duration_s: float, cues: tuple = ()) -> TrackEntry:
    return TrackEntry(
        track_id=track_id,
        title="T",
        artist="A",
        album="",
        bpm=128.0,
        key="8A",
        duration_s=duration_s,
        cues=cues,
        filepath=filepath,
    )


# ─── load_audio_mono offset/duration slicing ────────────────────────────────


def test_load_audio_mono_slices_offset_and_duration(tmp_path, no_subprocess) -> None:
    src = tmp_path / "steps.wav"
    _write_step_wav(src, seconds=6.0)

    sliced = load_audio_mono(src, target_sr=_WAV_SR, offset_s=3.0, duration_s=2.0)

    assert sliced.dtype == np.float32
    assert sliced.shape[0] == 2 * _WAV_SR
    # Second 3 carries amplitude 0.4, second 4 carries 0.5 — position proof.
    first_half = float(np.mean(np.abs(sliced[:_WAV_SR])))
    second_half = float(np.mean(np.abs(sliced[_WAV_SR:])))
    assert abs(first_half - 0.4) < 0.02
    assert abs(second_half - 0.5) < 0.02


def test_load_audio_mono_slice_resamples_to_target_rate(tmp_path, no_subprocess) -> None:
    src = tmp_path / "steps.wav"
    _write_step_wav(src, seconds=6.0)

    sliced = load_audio_mono(src, target_sr=4000, offset_s=1.0, duration_s=2.0)

    assert sliced.shape[0] == 2 * 4000
    assert abs(float(np.mean(np.abs(sliced))) - 0.25) < 0.03  # seconds 1+2 → 0.2/0.3


def test_load_audio_mono_full_decode_unchanged(tmp_path, no_subprocess) -> None:
    src = tmp_path / "steps.wav"
    _write_step_wav(src, seconds=2.0)

    full = load_audio_mono(src, target_sr=_WAV_SR)

    assert full.shape[0] == 2 * _WAV_SR


def test_load_audio_mono_slice_past_eof_raises(tmp_path, no_subprocess) -> None:
    src = tmp_path / "steps.wav"
    _write_step_wav(src, seconds=2.0)

    with pytest.raises(AudioDecodeError):
        load_audio_mono(src, target_sr=_WAV_SR, offset_s=50.0, duration_s=1.0)


def test_pcm16_wav_bytes_roundtrip(no_subprocess) -> None:
    samples = np.linspace(-0.5, 0.5, 800, dtype=np.float32)

    blob = pcm16_wav_bytes(samples, sr=_WAV_SR)

    assert blob.startswith(b"RIFF")
    with wave.open(io.BytesIO(blob), "rb") as fh:
        assert fh.getnchannels() == 1
        assert fh.getframerate() == _WAV_SR
        assert fh.getnframes() == 800


# ─── section_vectors: default slicer + array seam ───────────────────────────


def test_default_section_slicer_decodes_clap_rate_mono(tmp_path, no_subprocess) -> None:
    from vibemix.library.section_vectors import default_section_slicer

    src = tmp_path / "steps.wav"
    _write_step_wav(src, seconds=2.0)

    clip = default_section_slicer(str(src), 0.5, 1.0)

    assert isinstance(clip, np.ndarray)
    assert clip.dtype == np.float32
    assert clip.shape[0] == CLAP_SR  # 1.0s at CLAP's native 48k


def test_persist_section_vectors_uses_array_seam(tmp_path, no_subprocess) -> None:
    from vibemix.library.section_vectors import (
        get_cached_section_vector,
        open_section_vector_db,
        persist_section_vectors_for_track,
    )

    src = tmp_path / "track.wav"
    _write_step_wav(src, seconds=4.0)
    track = _track(
        "t1",
        str(src),
        duration_s=3.0,
        cues=(CuePoint(name="intro", type="cue", start_s=0.0, end_s=2.0, number=0),),
    )
    conn = open_section_vector_db(tmp_path / "sections.db")
    embedder = _ArrayEmbedder()

    written = persist_section_vectors_for_track(
        track,
        src,
        embedder,
        conn,
        track_cache_key="track-key",
        backend_tag="fake-clap",
    )

    assert written >= 1
    assert len(embedder.array_calls) == written
    assert all(sr == CLAP_SR for _n, sr in embedder.array_calls)
    assert get_cached_section_vector(conn, "t1#s000") is not None


def test_persist_section_vectors_bytes_slicer_backcompat(tmp_path, no_subprocess) -> None:
    """An injected byte-returning slicer keeps the embed_audio_bytes contract."""
    from vibemix.library.section_vectors import (
        open_section_vector_db,
        persist_section_vectors_for_track,
    )

    src = tmp_path / "track.wav"
    _write_step_wav(src, seconds=4.0)
    track = _track(
        "t2",
        str(src),
        duration_s=3.0,
        cues=(CuePoint(name="intro", type="cue", start_s=0.0, end_s=2.0, number=0),),
    )
    conn = open_section_vector_db(tmp_path / "sections.db")
    embedder = _BytesOnlyEmbedder()

    written = persist_section_vectors_for_track(
        track,
        src,
        embedder,
        conn,
        track_cache_key="track-key",
        backend_tag="fake-clap",
        slicer=lambda path, start_s, length_s: b"LEGACY-CLIP",
    )

    assert written >= 1
    assert embedder.byte_calls[0] == (b"LEGACY-CLIP", "audio/mpeg")


def test_array_clip_with_bytes_only_embedder_falls_back_to_wav(
    tmp_path, no_subprocess
) -> None:
    """Default array slicer + bytes-only embedder → PCM16 wav bytes, no shell."""
    from vibemix.library.section_vectors import (
        open_section_vector_db,
        persist_section_vectors_for_track,
    )

    src = tmp_path / "track.wav"
    _write_step_wav(src, seconds=4.0)
    track = _track(
        "t3",
        str(src),
        duration_s=3.0,
        cues=(CuePoint(name="intro", type="cue", start_s=0.0, end_s=2.0, number=0),),
    )
    conn = open_section_vector_db(tmp_path / "sections.db")
    embedder = _BytesOnlyEmbedder()

    written = persist_section_vectors_for_track(
        track,
        src,
        embedder,
        conn,
        track_cache_key="track-key",
        backend_tag="fake-clap",
    )

    assert written >= 1
    blob, mime = embedder.byte_calls[0]
    assert blob.startswith(b"RIFF")
    assert mime == "audio/wav"


def test_persist_section_vectors_skips_undecodable_file_honestly(
    tmp_path, no_subprocess, caplog
) -> None:
    from vibemix.library.section_vectors import (
        open_section_vector_db,
        persist_section_vectors_for_track,
    )

    src = tmp_path / "garbage.mp3"
    src.write_bytes(b"NOT-AUDIO" * 16)
    track = _track(
        "t4",
        str(src),
        duration_s=3.0,
        cues=(CuePoint(name="intro", type="cue", start_s=0.0, end_s=2.0, number=0),),
    )
    conn = open_section_vector_db(tmp_path / "sections.db")
    embedder = _ArrayEmbedder()

    with caplog.at_level("WARNING", logger="vibemix.library.section_vectors"):
        written = persist_section_vectors_for_track(
            track,
            src,
            embedder,
            conn,
            track_cache_key="track-key",
            backend_tag="fake-clap",
        )

    assert written == 0  # logged + skipped, never fatal, never a faked vector
    assert embedder.array_calls == []
    assert "skipping section" in caplog.text


# ─── ingest: cue-anchored window path on the array seam ─────────────────────


def test_ingest_cue_windows_use_array_seam(tmp_path, no_subprocess) -> None:
    from vibemix.library.ingest import _embed_track_cue_anchored

    src = tmp_path / "track.wav"
    _write_step_wav(src, seconds=4.0)
    track = _track("t5", str(src), duration_s=3.0)
    anchors = [
        CueAnchor(label="intro", start_s=0.2, end_s=1.2, confidence=1.0, source="dj"),
    ]
    embedder = _ArrayEmbedder()

    vec = _embed_track_cue_anchored(
        track, src, embedder, precomputed_anchors=anchors
    )

    assert len(embedder.array_calls) == 1
    assert embedder.array_calls[0][1] == CLAP_SR
    assert embedder.file_calls == []  # window worked → no whole-track fallback
    assert vec.shape == (512,)
    assert abs(float(np.linalg.norm(vec)) - 1.0) < 1e-5


def test_ingest_undecodable_window_falls_back_to_whole_track(
    tmp_path, no_subprocess
) -> None:
    from vibemix.library.ingest import _embed_track_cue_anchored

    src = tmp_path / "garbage.mp3"
    src.write_bytes(b"NOT-AUDIO" * 16)
    track = _track("t6", str(src), duration_s=3.0)
    anchors = [
        CueAnchor(label="intro", start_s=0.2, end_s=1.2, confidence=1.0, source="dj"),
    ]
    embedder = _ArrayEmbedder()

    vec = _embed_track_cue_anchored(
        track, src, embedder, precomputed_anchors=anchors
    )

    # Slice decode failed honestly → real whole-track re-embed, not a fake.
    assert embedder.array_calls == []
    assert embedder.file_calls == [str(src)]
    assert vec.shape == (512,)


# ─── embed.py: legacy cue_anchored slice rides PyAV → wav bytes ─────────────


def test_legacy_slice_window_emits_wav_without_subprocess(
    tmp_path, no_subprocess
) -> None:
    from vibemix.library.embed import LibraryEmbedder

    src = tmp_path / "steps.wav"
    _write_step_wav(src, seconds=3.0)
    embedder = LibraryEmbedder(
        MagicMock(), cache_db=sqlite3.connect(":memory:"), probe_on_init=False
    )

    blob = embedder._slice_window(src, 0.5, 1.0)

    assert blob.startswith(b"RIFF")
    with wave.open(io.BytesIO(blob), "rb") as fh:
        assert fh.getnchannels() == 1
        assert fh.getnframes() == fh.getframerate()  # exactly 1.0s of audio


def test_legacy_cue_anchored_path_sends_wav_mime(
    tmp_path, no_subprocess, monkeypatch
) -> None:
    from types import SimpleNamespace

    from vibemix.library.embed import LibraryEmbedder

    src = tmp_path / "steps.wav"
    _write_step_wav(src, seconds=3.0)
    embedder = LibraryEmbedder(
        MagicMock(), cache_db=sqlite3.connect(":memory:"), probe_on_init=False
    )
    monkeypatch.setattr(
        "vibemix.library.cue_engine.detect_cues_auto",
        lambda path, max_cues=4: [SimpleNamespace(start_s=0.2, end_s=1.2)],
    )
    captured: list[tuple[bytes, str]] = []

    def _fake_call(clip: bytes, mime_type: str) -> np.ndarray:
        captured.append((clip, mime_type))
        return np.full(512, 0.1, dtype=np.float32)

    monkeypatch.setattr(embedder, "_call_gemini_audio_single", _fake_call)

    vec = embedder._embed_audio_cue_anchored(src, 3.0)

    assert captured, "cue window never reached the embed call"
    clip, mime = captured[0]
    assert clip.startswith(b"RIFF")
    assert mime == "audio/wav"
    assert vec.shape == (512,)


# ─── ClapEngine / ClapEmbedder array entry point ────────────────────────────


def test_clap_engine_embed_audio_array_validates_before_model_load() -> None:
    """Bad inputs fail fast WITHOUT touching the multi-GB model load."""
    from vibemix.library.clap_engine import ClapEngine

    engine = ClapEngine(backend="onnx")

    with pytest.raises(ValueError):
        engine.embed_audio_array(np.zeros(100, dtype=np.float32), sr=44100)
    with pytest.raises(ValueError):
        engine.embed_audio_array(np.zeros(0, dtype=np.float32), sr=CLAP_SR)
    assert engine._model is None  # validation never warmed the engine


def test_clap_embedder_embed_audio_array_delegates_and_l2(monkeypatch) -> None:
    from vibemix.library.embed_clap import ClapEmbedder

    class _FakeEngine:
        def __init__(self) -> None:
            self.calls: list[tuple[int, int]] = []

        def embed_audio_array(self, samples: np.ndarray, *, sr: int) -> np.ndarray:
            self.calls.append((int(samples.shape[0]), int(sr)))
            return np.full(512, 0.5, dtype=np.float32)

    engine = _FakeEngine()
    embedder = ClapEmbedder(engine=engine, cache_db=sqlite3.connect(":memory:"))

    vec = embedder.embed_audio_array(np.zeros(CLAP_SR, dtype=np.float32), sr=CLAP_SR)

    assert engine.calls == [(CLAP_SR, CLAP_SR)]
    assert vec.dtype == np.float32
    assert abs(float(np.linalg.norm(vec)) - 1.0) < 1e-5


# ─── Cache-version bumps: scoped to the paths whose bytes changed ───────────


def test_cache_versions_bumped_for_pyav_and_scoped() -> None:
    from vibemix.library.embed import EXCERPT_STRATEGY_VERSION
    from vibemix.library.embed_config import CUE_ANCHORED_STRATEGY_VERSION
    from vibemix.library.ingest import (
        INGEST_CUE_STRATEGY_VERSION,
        INGEST_STRATEGY_VERSION,
    )
    from vibemix.library.section_vectors import SECTION_VECTOR_CACHE_VERSION

    # The PyAV slice drops the lossy 128k mp3 re-encode → persisted vectors
    # change → these three namespaces MUST diverge from their ffmpeg-era tags.
    assert SECTION_VECTOR_CACHE_VERSION != "v1-clap-section-window"
    assert "pyav" in SECTION_VECTOR_CACHE_VERSION
    assert INGEST_CUE_STRATEGY_VERSION != "v2-clap-cueanchored-anlz"
    assert "pyav" in INGEST_CUE_STRATEGY_VERSION
    assert "cueanchored" in INGEST_CUE_STRATEGY_VERSION  # test-pinned substrings
    assert "anlz" in INGEST_CUE_STRATEGY_VERSION
    assert CUE_ANCHORED_STRATEGY_VERSION != "v1-cueanchored-mean"
    assert "pyav" in CUE_ANCHORED_STRATEGY_VERSION

    # Paths that never shelled out keep their bytes → tags must NOT move.
    assert INGEST_STRATEGY_VERSION == "v1-clap-wholetrack"
    assert EXCERPT_STRATEGY_VERSION == "v1-3excerpt-mean"
