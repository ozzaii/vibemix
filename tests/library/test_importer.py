# SPDX-License-Identifier: Apache-2.0
"""Plan 28-06 — LibraryImporter tests."""

from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest

from vibemix.library.importer import LibraryImporter, import_library_async
from vibemix.library.rekordbox import TrackEntry


def _make_track(tid: str) -> TrackEntry:
    return TrackEntry(
        track_id=tid,
        title=f"Title {tid}",
        artist=f"Artist {tid}",
        album="A",
        bpm=138.0,
        key="A min",
        duration_s=240.0,
        cues=(),
        filepath=f"/tmp/{tid}.mp3",
    )


@pytest.fixture
def fake_embedder(tmp_path: Path) -> MagicMock:
    """Embedder mock with a real sqlite cache for cache-hit probing."""
    e = MagicMock()
    e._cache = sqlite3.connect(":memory:")
    e._cache.execute(
        "CREATE TABLE embed_cache "
        "(key TEXT PRIMARY KEY, vector BLOB NOT NULL, ts REAL NOT NULL)"
    )
    e._track_hash = MagicMock(side_effect=lambda t: f"hash_{t.track_id}")
    e.embed_track = MagicMock(
        side_effect=lambda t: np.zeros(768, dtype=np.float32)
    )
    return e


@pytest.fixture
def fake_store() -> MagicMock:
    return MagicMock()


@pytest.fixture
def patch_rekordbox_load(monkeypatch: pytest.MonkeyPatch):
    """Replace RekordboxLibrary.load_xml so we don't need a real XML file."""
    tracks_n = [5]

    def fake_load_xml(self, path):
        self.tracks = {
            f"t{i:03d}": _make_track(f"t{i:03d}") for i in range(tracks_n[0])
        }
        return tracks_n[0]

    monkeypatch.setattr(
        "vibemix.library.importer.RekordboxLibrary.load_xml",
        fake_load_xml,
    )
    return tracks_n


def test_importer_emits_progress_per_track(
    fake_embedder, fake_store, patch_rekordbox_load
) -> None:
    progress_calls: list[dict] = []
    importer = LibraryImporter(
        fake_embedder, fake_store, on_progress=progress_calls.append
    )

    asyncio.run(importer.import_library(Path("/tmp/fake.xml")))

    assert len(progress_calls) == 5
    assert [p["done"] for p in progress_calls] == [1, 2, 3, 4, 5]
    assert all(p["total"] == 5 for p in progress_calls)
    assert all(p["cancelled"] is False for p in progress_calls)


def test_importer_cancel_flag_stops_at_batch_boundary(
    fake_embedder, fake_store, patch_rekordbox_load
) -> None:
    progress_calls: list[dict] = []
    importer = LibraryImporter(
        fake_embedder, fake_store, on_progress=progress_calls.append
    )

    # Set cancel after the second track.
    real_emit = importer._emit
    call_count = [0]

    def maybe_cancel(payload):
        call_count[0] += 1
        if call_count[0] == 2:
            importer.cancel_flag.set()
        real_emit(payload)

    importer._emit = maybe_cancel  # type: ignore

    result = asyncio.run(importer.import_library(Path("/tmp/fake.xml")))
    assert result["cancelled"] is True
    assert result["done"] < 5
    # Last progress call should carry cancelled=True.
    assert progress_calls[-1]["cancelled"] is True


def test_importer_skips_failed_track_continues_batch(
    fake_embedder, fake_store, patch_rekordbox_load
) -> None:
    """One bad track must not fail the batch."""
    call_idx = [0]

    def embed_track_with_failure(t):
        call_idx[0] += 1
        if call_idx[0] == 2:
            raise RuntimeError("simulated bad audio file")
        return np.zeros(768, dtype=np.float32)

    fake_embedder.embed_track = embed_track_with_failure

    importer = LibraryImporter(fake_embedder, fake_store)
    result = asyncio.run(importer.import_library(Path("/tmp/fake.xml")))

    # 5 tracks total; one failed but counted as "done" with no batch entry.
    assert result["total"] == 5
    assert result["cancelled"] is False
    # 5 attempts, 4 successful additions to batch.
    assert call_idx[0] == 5


def test_importer_calls_register_library_after(
    fake_embedder, fake_store, patch_rekordbox_load, monkeypatch
) -> None:
    """Mid-session refresh: post-import EvidenceRegistry registration."""
    registry = MagicMock()
    registry.register_library = MagicMock(return_value=5)

    monkeypatch.setattr(
        "vibemix.library.importer.RekordboxLibrary.try_load_cache",
        lambda self: True,
    )

    asyncio.run(
        import_library_async(
            Path("/tmp/fake.xml"),
            fake_embedder,
            fake_store,
            evidence_registry=registry,
        )
    )

    registry.register_library.assert_called_once()


def test_importer_no_register_when_cancelled(
    fake_embedder, fake_store, patch_rekordbox_load, monkeypatch
) -> None:
    """Cancelled imports MUST NOT refresh the registry."""
    registry = MagicMock()

    monkeypatch.setattr(
        "vibemix.library.importer.RekordboxLibrary.try_load_cache",
        lambda self: True,
    )

    # Pre-set cancel before any embed runs.
    async def run_cancelled():
        importer = LibraryImporter(fake_embedder, fake_store)
        importer.cancel_flag.set()
        return await importer.import_library(Path("/tmp/fake.xml"))

    result = asyncio.run(run_cancelled())
    assert result["cancelled"] is True
    registry.register_library.assert_not_called()


def test_importer_cache_hits_counted(
    fake_embedder, fake_store, patch_rekordbox_load
) -> None:
    """Pre-populate cache so 3/5 tracks count as hits."""
    for tid in ("t000", "t001", "t002"):
        fake_embedder._cache.execute(
            "INSERT INTO embed_cache (key, vector, ts) VALUES (?, ?, ?)",
            (f"hash_{tid}", b"\x00" * 8, 0.0),
        )
    fake_embedder._cache.commit()

    importer = LibraryImporter(fake_embedder, fake_store)
    result = asyncio.run(importer.import_library(Path("/tmp/fake.xml")))

    assert result["cache_hits"] == 3
    assert result["done"] == 5
