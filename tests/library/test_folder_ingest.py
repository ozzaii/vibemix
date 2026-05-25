# SPDX-License-Identifier: Apache-2.0
"""quick-260525-gz2 — unit tests for folder_ingest.

ZERO network, default pytest selection. A FAKE embedder (object exposing
``embed_track`` + ``has_cached_embedding``) is injected; a REAL NumpyStore
in ``tmp_path`` backs the vectors; ``probe`` is monkeypatched to a constant
so no ffprobe binary / real audio is needed.

Coverage:
    - scan filtering + sort determinism + dotfile/unsupported exclusion
    - track_id stability + title-from-stem
    - resumable skip accounting (has_cached_embedding True → skipped_cached)
    - partial-failure-continues (one embed raises → failed==1, others stored,
      NO faked vector for the failed file)
    - progress callback receives per-track lines
    - library.pkl written so a fresh RekordboxLibrary().try_load_cache()
      repopulates titles
    - dim-mismatch guard fails loud against a stale-dim store
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from vibemix.library import (
    IngestReport,
    folder_to_track_entry,
    ingest_folder,
    scan_folder,
)
from vibemix.library._cosine import EMBEDDING_DIM, l2_normalize
from vibemix.library.index_numpy import NumpyStore
from vibemix.library.rekordbox import RekordboxLibrary
from vibemix.library.store import LibraryStore


# ─── Fixtures ────────────────────────────────────────────────────────────────


def _touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x00" * 16)
    return path


@pytest.fixture
def numpy_store(tmp_path: Path) -> LibraryStore:
    backend = NumpyStore(
        vectors_path=tmp_path / "vectors.npy",
        ids_path=tmp_path / "ids.json",
    )
    return LibraryStore(backend)


class FakeEmbedder:
    """Records calls; returns a fixed L2-normalized vector. No network."""

    def __init__(self, cached: set[str] | None = None) -> None:
        self.cached = cached or set()
        self.embed_calls: list[str] = []
        self._vec = l2_normalize(np.ones(EMBEDDING_DIM, dtype=np.float32))

    def has_cached_embedding(self, track) -> bool:  # noqa: ANN001
        return track.track_id in self.cached

    def embed_track(self, track) -> np.ndarray:  # noqa: ANN001
        self.embed_calls.append(track.track_id)
        return self._vec.copy()


@pytest.fixture(autouse=True)
def _isolate_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Point RekordboxLibrary.CACHE_PATH at tmp so library.pkl never touches
    the real ~/.cache."""
    monkeypatch.setattr(
        RekordboxLibrary, "CACHE_PATH", tmp_path / "library.pkl"
    )


def _const_probe(_dur: float = 120.0):
    return lambda _path: _dur


# ─── scan_folder ─────────────────────────────────────────────────────────────


def test_scan_filters_sorts_and_excludes(tmp_path: Path) -> None:
    _touch(tmp_path / "b.mp3")
    _touch(tmp_path / "a.MP3")  # case-insensitive suffix
    _touch(tmp_path / "sub" / "c.wav")
    _touch(tmp_path / "notes.txt")  # unsupported
    _touch(tmp_path / ".hidden.mp3")  # dotfile excluded

    found = scan_folder(tmp_path)
    names = [p.name for p in found]

    assert "notes.txt" not in names
    assert ".hidden.mp3" not in names
    assert set(names) == {"a.MP3", "b.mp3", "c.wav"}
    # deterministic sorted order
    assert found == sorted(found, key=lambda x: str(x))


def test_scan_nonexistent_dir_returns_empty(tmp_path: Path) -> None:
    assert scan_folder(tmp_path / "nope") == []


# ─── folder_to_track_entry ───────────────────────────────────────────────────


def test_track_id_stable_and_title_from_stem(tmp_path: Path) -> None:
    f = _touch(tmp_path / "Acid Techno 138.mp3")
    e1 = folder_to_track_entry(f, 200.0)
    e2 = folder_to_track_entry(f, 999.0)  # different dur, same path

    assert e1.title == "Acid Techno 138"
    assert e1.track_id.startswith("folder:")
    assert e1.track_id == e2.track_id  # id derives from path only
    assert e1.filepath == str(f.resolve())
    assert e1.duration_s == 200.0


# ─── ingest_folder: happy path + progress ────────────────────────────────────


def test_ingest_embeds_stores_and_reports(
    tmp_path: Path, numpy_store: LibraryStore
) -> None:
    music = tmp_path / "music"
    _touch(music / "one.mp3")
    _touch(music / "two.wav")
    emb = FakeEmbedder()
    lines: list[str] = []

    report = ingest_folder(
        music,
        emb,
        numpy_store,
        progress=lines.append,
        probe=_const_probe(),
    )

    assert isinstance(report, IngestReport)
    assert report.total == 2
    assert report.embedded == 2
    assert report.skipped_cached == 0
    assert report.failed == 0
    # both vectors landed in the store
    ids, vecs = numpy_store._backend.load_all()
    assert len(ids) == 2
    assert vecs.shape == (2, EMBEDDING_DIM)
    # progress emitted one line per file
    assert len(lines) == 2
    assert all("/2]" in ln for ln in lines)


# ─── ingest_folder: resumable skip ───────────────────────────────────────────


def test_resumable_skip_accounting(
    tmp_path: Path, numpy_store: LibraryStore
) -> None:
    music = tmp_path / "music"
    f = _touch(music / "cached.mp3")
    entry = folder_to_track_entry(f, 120.0)
    emb = FakeEmbedder(cached={entry.track_id})

    report = ingest_folder(music, emb, numpy_store, probe=_const_probe())

    assert report.total == 1
    assert report.skipped_cached == 1
    assert report.embedded == 0
    # still re-stored (cheap) so search works after a resume
    ids, _ = numpy_store._backend.load_all()
    assert ids == [entry.track_id]


# ─── ingest_folder: partial failure tolerance ────────────────────────────────


def test_partial_failure_continues_no_faked_embed(
    tmp_path: Path, numpy_store: LibraryStore
) -> None:
    music = tmp_path / "music"
    _touch(music / "a.mp3")
    _touch(music / "bad.mp3")
    _touch(music / "c.mp3")

    class FlakyEmbedder(FakeEmbedder):
        def embed_track(self, track):  # noqa: ANN001
            if "bad" in track.title:
                raise RuntimeError("simulated corrupt audio")
            return super().embed_track(track)

    emb = FlakyEmbedder()
    report = ingest_folder(music, emb, numpy_store, probe=_const_probe())

    assert report.total == 3
    assert report.embedded == 2
    assert report.failed == 1
    assert any("bad.mp3" in fp for fp, _ in report.failures)
    # the failed file produced NO stored vector
    ids, vecs = numpy_store._backend.load_all()
    assert len(ids) == 2
    assert vecs.shape == (2, EMBEDDING_DIM)
    bad_id = folder_to_track_entry(music / "bad.mp3", 120.0).track_id
    assert bad_id not in ids


def test_unprobeable_file_skipped_not_embedded(
    tmp_path: Path, numpy_store: LibraryStore
) -> None:
    music = tmp_path / "music"
    _touch(music / "ok.mp3")
    _touch(music / "weird.mp3")

    def flaky_probe(path: Path) -> float | None:
        return None if "weird" in path.name else 120.0

    emb = FakeEmbedder()
    report = ingest_folder(music, emb, numpy_store, probe=flaky_probe)

    assert report.total == 2
    assert report.embedded == 1
    assert report.failed == 1
    assert emb.embed_calls  # ok.mp3 embedded
    assert all("weird" not in tid for tid in emb.embed_calls)  # never embedded


# ─── ingest_folder: library.pkl round-trip ───────────────────────────────────


def test_library_pkl_written_and_loadable(
    tmp_path: Path, numpy_store: LibraryStore
) -> None:
    music = tmp_path / "music"
    _touch(music / "trackone.mp3")
    emb = FakeEmbedder()

    ingest_folder(music, emb, numpy_store, probe=_const_probe())

    # A fresh RekordboxLibrary can load the cache folder_ingest wrote.
    lib = RekordboxLibrary()
    assert lib.try_load_cache() is True
    titles = {t.title for t in lib.tracks.values()}
    assert "trackone" in titles


# ─── ingest_folder: dim-mismatch guard ───────────────────────────────────────


def test_dim_mismatch_store_fails_loud(tmp_path: Path) -> None:
    music = tmp_path / "music"
    _touch(music / "x.mp3")

    class StaleStore:
        def search(self, q, k=1):  # noqa: ANN001
            raise AssertionError("vectors must be shape (N, 1536), got (N, 768)")

        def add_batch(self, items):  # pragma: no cover
            raise AssertionError("should never be reached")

    with pytest.raises(RuntimeError, match="different dimensionality"):
        ingest_folder(music, FakeEmbedder(), StaleStore(), probe=_const_probe())


def test_empty_stale_dim_table_auto_recreates(
    tmp_path: Path, numpy_store: LibraryStore
) -> None:
    """An EMPTY stale-dim (768) table is auto-recreated at EMBEDDING_DIM —
    no manual file deletion needed (gz2: DB has 0 rows = clean wipe)."""
    music = tmp_path / "music"
    _touch(music / "x.mp3")

    class EmptyStaleStore:
        def __init__(self) -> None:
            self.recreated = False
            self.added: list = []

        def vector_dim(self):
            return 768  # stale

        def row_count(self):
            return 0  # empty → safe to wipe

        def recreate_table(self):
            self.recreated = True

        def search(self, q, k=1):  # noqa: ANN001
            return []

        def add_batch(self, items):  # noqa: ANN001
            self.added.extend(items)

    store = EmptyStaleStore()
    report = ingest_folder(music, FakeEmbedder(), store, probe=_const_probe(),
                           persist_library=False)

    assert store.recreated is True
    assert report.embedded == 1
    assert len(store.added) == 1


def test_populated_stale_dim_table_never_wiped(tmp_path: Path) -> None:
    """A POPULATED stale-dim table fails loud — we never silently destroy
    real embeddings."""
    music = tmp_path / "music"
    _touch(music / "x.mp3")

    class PopulatedStaleStore:
        def vector_dim(self):
            return 768

        def row_count(self):
            return 42  # has real data → must NOT auto-wipe

        def recreate_table(self):  # pragma: no cover
            raise AssertionError("must never wipe a populated table")

        def search(self, q, k=1):  # noqa: ANN001
            return []

        def add_batch(self, items):  # pragma: no cover
            raise AssertionError("should never reach add_batch")

    with pytest.raises(RuntimeError, match="different dimensionality"):
        ingest_folder(
            music, FakeEmbedder(), PopulatedStaleStore(), probe=_const_probe()
        )
