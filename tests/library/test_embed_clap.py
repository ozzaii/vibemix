# SPDX-License-Identifier: Apache-2.0
"""ClapEmbedder + build_embedder wiring (Phase 90).

CI-safe: a fake ClapEngine stands in for the real onnx engine, so these run
with NO onnxruntime/transformers/librosa installed (mirrors the engine's lazy
contract). Locks the drop-in contract + the backend dispatch seam.
"""

from __future__ import annotations

import numpy as np
import pytest

import vibemix.library._cosine as _cosine
import vibemix.library.embed as embed_mod
import vibemix.library.embed_clap as embed_clap
from vibemix.library.embed_clap import ClapEmbedder
from vibemix.library.rekordbox import TrackEntry

_DIM = 512


def _track(track_id: str, filepath: str | None) -> TrackEntry:
    return TrackEntry(
        track_id=track_id,
        title="T",
        artist="A",
        album="",
        bpm=140.0,
        key="8A",
        duration_s=200.0,
        cues=(),
        filepath=filepath,
    )


class _FakeEngine:
    """Stand-in for ClapEngine — returns fixed unit-ish 512-dim vectors."""

    def __init__(self, *args, **kwargs) -> None:  # accept backend= like ClapEngine
        self.calls: list[str] = []

    def embed_audio_file(self, path: str) -> np.ndarray:
        self.calls.append(f"audio_file:{path}")
        v = np.full(_DIM, 0.04, dtype=np.float32)
        return v

    def embed_audio_bytes(self, data: bytes, mime: str) -> np.ndarray:
        self.calls.append(f"audio_bytes:{mime}")
        return np.full(_DIM, 0.05, dtype=np.float32)

    def embed_query(self, text: str) -> np.ndarray:
        self.calls.append(f"query:{text}")
        return np.full(_DIM, 0.06, dtype=np.float32)


@pytest.fixture
def clap_dim_512(monkeypatch) -> None:
    # ClapEmbedder's cache dim-guard reads the module-level EMBEDDING_DIM, which
    # is 1536 by default (gemini). Pin it to 512 so the clap contract is tested.
    monkeypatch.setattr(embed_clap, "EMBEDDING_DIM", _DIM, raising=True)


@pytest.fixture
def embedder(tmp_path, clap_dim_512) -> ClapEmbedder:
    import sqlite3

    db = sqlite3.connect(":memory:")
    return ClapEmbedder(engine=_FakeEngine(), cache_db=db)


def test_embed_query_delegates_and_l2(embedder) -> None:
    v = embedder.embed_query("dark rolling techno")
    assert v.shape == (_DIM,) and v.dtype == np.float32
    assert abs(float(np.linalg.norm(v)) - 1.0) < 1e-5  # L2-normalized


def test_embed_audio_bytes_delegates(embedder) -> None:
    v = embedder.embed_audio_bytes(b"xxxx", "audio/mpeg")
    assert v.shape == (_DIM,)
    assert "audio_bytes:audio/mpeg" in embedder._engine.calls


def test_embed_track_local_file_uses_audio_path(embedder, tmp_path) -> None:
    f = tmp_path / "t.mp3"
    f.write_bytes(b"ID3fakeaudio")
    track = _track("t1", str(f))
    v = embedder.embed_track(track)
    assert v.shape == (_DIM,)
    assert any(c.startswith("audio_file:") for c in embedder._engine.calls)


def test_embed_track_caches(embedder, tmp_path) -> None:
    f = tmp_path / "t.mp3"
    f.write_bytes(b"ID3fakeaudio")
    track = _track("t1", str(f))
    assert embedder.has_cached_embedding(track) is False
    embedder.embed_track(track)
    assert embedder.has_cached_embedding(track) is True
    n = len(embedder._engine.calls)
    embedder.embed_track(track)  # 2nd call → cache hit, no new engine call
    assert len(embedder._engine.calls) == n


def test_embed_track_no_file_uses_text_signature(embedder) -> None:
    track = _track("t2", None)
    v = embedder.embed_track(track)
    assert v.shape == (_DIM,)
    assert any(c.startswith("query:") for c in embedder._engine.calls)


def test_build_embedder_dispatch_clap(monkeypatch) -> None:
    monkeypatch.setattr(_cosine, "EMBED_BACKEND", "clap", raising=True)
    monkeypatch.setattr(embed_clap, "ClapEngine", _FakeEngine, raising=True)
    e = embed_mod.build_embedder(client=None)
    assert isinstance(e, ClapEmbedder)


def test_build_embedder_dispatch_gemini_default(monkeypatch) -> None:
    monkeypatch.setattr(_cosine, "EMBED_BACKEND", "gemini", raising=True)
    e = embed_mod.build_embedder(client=object(), probe_on_init=False)
    assert e.__class__.__name__ == "LibraryEmbedder"
