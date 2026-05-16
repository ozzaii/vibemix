# SPDX-License-Identifier: Apache-2.0
"""Plan 28-03 — vibe_search() unit tests with mocked embedder + store."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest

from vibemix.library.rekordbox import TrackEntry
from vibemix.library.search import (
    QUERY_CACHE_TTL,
    VibeSearchResult,
    vibe_search,
)


def _make_track(tid: str, bpm: float = 138.0) -> TrackEntry:
    return TrackEntry(
        track_id=tid,
        title=f"Title {tid}",
        artist=f"Artist {tid}",
        album="A",
        bpm=bpm,
        key="A min",
        duration_s=240.0,
        cues=(),
        filepath=f"/tmp/{tid}.mp3",
    )


@pytest.fixture
def fake_library() -> MagicMock:
    lib = MagicMock()
    lib.tracks = [_make_track(f"t{i:03d}") for i in range(10)]
    return lib


@pytest.fixture
def fake_embedder() -> MagicMock:
    e = MagicMock()
    e.embed_query.return_value = np.zeros(768, dtype=np.float32)
    return e


@pytest.fixture
def fake_store() -> MagicMock:
    s = MagicMock()
    s.snapshot_hash.return_value = "snapshot_hash_v1"
    s.search.return_value = [
        ("t000", 0.9123),
        ("t001", 0.7456),
        ("t002", 0.6789),
    ]
    return s


@pytest.fixture
def cache_db(tmp_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(tmp_path / "embeddings.db"))
    conn.execute(
        "CREATE TABLE IF NOT EXISTS query_cache "
        "(key TEXT PRIMARY KEY, query_text TEXT NOT NULL, "
        "result_json TEXT NOT NULL, ts REAL NOT NULL)"
    )
    conn.commit()
    return conn


def test_vibe_search_returns_top_k(
    fake_embedder, fake_store, fake_library, cache_db
) -> None:
    results, cache_hit = vibe_search(
        fake_embedder, fake_store, fake_library, "techno", cache_db=cache_db
    )
    assert len(results) == 3
    assert cache_hit is False
    assert all(isinstance(r, VibeSearchResult) for r in results)
    assert results[0].track_id == "t000"
    assert results[0].confidence == round(0.9123, 4)


def test_query_cache_24h_ttl(
    fake_embedder, fake_store, fake_library, cache_db, monkeypatch
) -> None:
    base = 1715000000.0

    monkeypatch.setattr("vibemix.library.search.time.time", lambda: base)
    r1, hit1 = vibe_search(
        fake_embedder, fake_store, fake_library, "test query", cache_db=cache_db
    )
    assert hit1 is False
    assert fake_embedder.embed_query.call_count == 1

    # Second call within 24h → cache hit, no embed.
    monkeypatch.setattr(
        "vibemix.library.search.time.time", lambda: base + 1000
    )
    r2, hit2 = vibe_search(
        fake_embedder, fake_store, fake_library, "test query", cache_db=cache_db
    )
    assert hit2 is True
    assert fake_embedder.embed_query.call_count == 1
    assert r2 == r1

    # Move past TTL → cache miss.
    monkeypatch.setattr(
        "vibemix.library.search.time.time", lambda: base + QUERY_CACHE_TTL + 1
    )
    _, hit3 = vibe_search(
        fake_embedder, fake_store, fake_library, "test query", cache_db=cache_db
    )
    assert hit3 is False
    assert fake_embedder.embed_query.call_count == 2


def test_cache_key_includes_snapshot_hash(
    fake_embedder, fake_store, fake_library, cache_db
) -> None:
    fake_store.snapshot_hash.return_value = "snapshot_a"
    _, hit1 = vibe_search(
        fake_embedder, fake_store, fake_library, "x", cache_db=cache_db
    )
    assert hit1 is False
    assert fake_embedder.embed_query.call_count == 1

    # Snapshot changes (re-import simulated) → cache miss.
    fake_store.snapshot_hash.return_value = "snapshot_b"
    _, hit2 = vibe_search(
        fake_embedder, fake_store, fake_library, "x", cache_db=cache_db
    )
    assert hit2 is False
    assert fake_embedder.embed_query.call_count == 2


def test_empty_library_returns_empty_no_embed(
    fake_embedder, fake_store, cache_db
) -> None:
    lib = MagicMock()
    lib.tracks = []
    results, hit = vibe_search(
        fake_embedder, fake_store, lib, "anything", cache_db=cache_db
    )
    assert results == []
    assert hit is False
    assert fake_embedder.embed_query.call_count == 0


def test_vibe_search_result_to_dict() -> None:
    r = VibeSearchResult(
        track_id="t1",
        title="X",
        artist="Y",
        bpm=128.0,
        confidence=0.87,
        snippet="X — Y @ 128 BPM",
    )
    d = r.to_dict()
    assert d == {
        "track_id": "t1",
        "title": "X",
        "artist": "Y",
        "bpm": 128.0,
        "confidence": 0.87,
        "snippet": "X — Y @ 128 BPM",
    }


def test_confidence_clamped_above_one(
    fake_embedder, fake_library, cache_db
) -> None:
    """Float quirks can return cosine 1.0001 — must clamp + round to 1.0."""
    s = MagicMock()
    s.snapshot_hash.return_value = "snap"
    s.search.return_value = [("t000", 1.00009)]
    results, _ = vibe_search(
        fake_embedder, s, fake_library, "x", cache_db=cache_db
    )
    assert results[0].confidence == 1.0


def test_confidence_clamped_below_zero(
    fake_embedder, fake_library, cache_db
) -> None:
    s = MagicMock()
    s.snapshot_hash.return_value = "snap"
    s.search.return_value = [("t000", -0.0001)]
    results, _ = vibe_search(
        fake_embedder, s, fake_library, "x", cache_db=cache_db
    )
    assert results[0].confidence == 0.0


def test_skips_unknown_track_ids(
    fake_embedder, fake_library, cache_db
) -> None:
    """Track in store but not in library — defensive skip."""
    s = MagicMock()
    s.snapshot_hash.return_value = "snap"
    s.search.return_value = [
        ("t000", 0.9),
        ("t-unknown", 0.8),
        ("t001", 0.7),
    ]
    results, _ = vibe_search(
        fake_embedder, s, fake_library, "x", cache_db=cache_db
    )
    ids = [r.track_id for r in results]
    assert "t-unknown" not in ids
    assert ids == ["t000", "t001"]
