# SPDX-License-Identifier: Apache-2.0
"""Phase 89 Plan 89-01 — ingest_source end-to-end / resumability / honest-failure.

Tests A/B/C are spec'd RED here (strict-xfail) and flip green when Task 2 lands
``ingest_source`` + ``RekordboxSource``. Test D's Protocol pin lives in
``test_sources_rekordbox.py``.

Honest-green posture (the hard CLAUDE.md gate):
    * NO GEMINI_API_KEY, NO network, NO real CLAP forward pass.
    * ``FakeClapEmbedder.embed_audio_file`` returns a deterministic (512,)
      float32 L2-normalized vector seeded off the path — never torch.
    * The store is an in-memory ``_DimAgnosticStore`` (no sqlite file, accepts
      CLAP's 512-dim vectors without flipping the global EMBEDDING_DIM=1536).
    * ``RekordboxLibrary.CACHE_PATH`` is monkeypatched so the real library.pkl
      is never written.
"""

from __future__ import annotations

import sqlite3
import urllib.parse
from pathlib import Path

import numpy as np
import pytest

from vibemix.library.rekordbox import RekordboxLibrary

CLAP_DIM = 512


# --------------------------------------------------------------------------- #
# Test doubles                                                                 #
# --------------------------------------------------------------------------- #


class FakeClapEmbedder:
    """Deterministic stand-in for ClapEngine — NEVER a real CLAP forward pass.

    ``embed_audio_file(path)`` returns a (512,) float32 L2-normalized vector
    seeded off the path string, so re-embedding the same file is bit-identical
    (mirrors the real CLAP determinism contract). Optionally raises for one
    track id's filepath to exercise the honest-failure path.
    """

    backend = "fake-clap"

    def __init__(
        self,
        raise_on_substr: str | None = None,
        *,
        bytes_raise_on: str | None = None,
    ) -> None:
        self._raise_on_substr = raise_on_substr
        self._bytes_raise_on = bytes_raise_on
        self.calls: list[str] = []  # embed_audio_file calls (whole-track path)
        self.byte_calls: list[bytes] = []  # embed_audio_bytes calls (window path)

    def embed_audio_file(self, path: str) -> np.ndarray:
        self.calls.append(str(path))
        if self._raise_on_substr and self._raise_on_substr in str(path):
            raise RuntimeError(f"fake decode error for {path}")
        seed = abs(hash(str(path))) % (2**32)
        rng = np.random.default_rng(seed)
        vec = rng.standard_normal(CLAP_DIM).astype(np.float32)
        return (vec / (np.linalg.norm(vec) + 1e-8)).astype(np.float32)

    def embed_audio_bytes(self, data: bytes, mime: str) -> np.ndarray:
        self.byte_calls.append(data)
        if self._bytes_raise_on and self._bytes_raise_on in data:
            raise RuntimeError("fake window decode error")
        seed = abs(hash(bytes(data))) % (2**32)
        rng = np.random.default_rng(seed)
        vec = rng.standard_normal(CLAP_DIM).astype(np.float32)
        return (vec / (np.linalg.norm(vec) + 1e-8)).astype(np.float32)


class _DimAgnosticStore:
    """In-memory store that accepts any vector dim (no sqlite file).

    The real NumpyStore hard-asserts EMBEDDING_DIM=1536; CLAP returns 512.
    Per the plan's dim posture we do NOT flip the global dim — so the test
    store is dim-agnostic, exercising the ingest loop with the real CLAP
    shape. Exposes vector_dim()/row_count()/recreate_table() so the ingest
    dim-reconciliation branch can introspect it.
    """

    def __init__(self) -> None:
        self._rows: dict[str, np.ndarray] = {}

    def add_batch(self, items: list[tuple[str, np.ndarray]]) -> None:
        for tid, vec in items:
            assert vec.dtype == np.float32
            self._rows[tid] = np.asarray(vec, dtype=np.float32)

    def search(self, query_vector: np.ndarray, k: int = 10) -> list[tuple[str, float]]:
        if not self._rows:
            return []
        ids = list(self._rows)
        mat = np.stack([self._rows[i] for i in ids])
        q = np.asarray(query_vector, dtype=np.float32)
        sims = mat @ q
        order = np.argsort(-sims)[:k]
        return [(ids[i], float(sims[i])) for i in order]

    def vector_dim(self) -> int | None:
        if not self._rows:
            return None
        return int(next(iter(self._rows.values())).shape[0])

    def row_count(self) -> int | None:
        return len(self._rows)

    def recreate_table(self) -> bool:
        self._rows.clear()
        return True

    def close(self) -> None:
        return


# --------------------------------------------------------------------------- #
# Fixtures                                                                      #
# --------------------------------------------------------------------------- #


@pytest.fixture
def isolated_cache(tmp_path, monkeypatch):
    cache = tmp_path / "library.pkl"
    monkeypatch.setattr(RekordboxLibrary, "CACHE_PATH", cache)
    return cache


def _make_collection_xml(tmp_path: Path, n: int = 5) -> Path:
    """Write a real collection.xml whose tracks point at real tmp audio files.

    The ingest path content-hashes the file BYTES, so the referenced files
    must exist with readable content. Each file gets distinct bytes so the
    per-track hash differs.
    """
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir(exist_ok=True)
    tracks_xml: list[str] = []
    for i in range(1, n + 1):
        f = audio_dir / f"track-{i}.mp3"
        f.write_bytes(f"FAKE-AUDIO-{i}".encode() * 8)
        loc = "file://localhost" + urllib.parse.quote(str(f.resolve()))
        tracks_xml.append(
            f'    <TRACK Location="{loc}" TrackID="{i}" Name="Track {i}" '
            f'Artist="Artist {i}" Album="Album {i}" AverageBpm="120.0" '
            f'Tonality="Am" TotalTime="200" />'
        )
    xml = (
        "<?xml version='1.0' encoding='utf-8'?>\n"
        '<DJ_PLAYLISTS Version="1.0.0">\n'
        '  <PRODUCT Name="vibemix" Version="1.0.0" Company="vibemix-test" />\n'
        f'  <COLLECTION Entries="{n}">\n'
        + "\n".join(tracks_xml)
        + "\n  </COLLECTION>\n"
        '  <PLAYLISTS>\n    <NODE Name="ROOT" Type="0" Count="0" />\n  </PLAYLISTS>\n'
        "</DJ_PLAYLISTS>\n"
    )
    xml_path = tmp_path / "collection.xml"
    xml_path.write_text(xml, encoding="utf-8")
    return xml_path


def _open_cache(tmp_path: Path) -> sqlite3.Connection:
    """An injectable content-hash cache (in-memory-ish; tmp file is fine)."""
    return sqlite3.connect(str(tmp_path / "clap_embeddings.db"))


# --------------------------------------------------------------------------- #
# Test A — end-to-end                                                          #
# --------------------------------------------------------------------------- #


def test_ingest_source_end_to_end(isolated_cache, tmp_path):
    from vibemix.library.ingest import ingest_source
    from vibemix.library.sources.rekordbox import RekordboxSource

    xml_path = _make_collection_xml(tmp_path, n=5)
    store = _DimAgnosticStore()
    report = ingest_source(
        RekordboxSource(xml_path=str(xml_path)),
        embedder=FakeClapEmbedder(),
        store=store,
        cache=_open_cache(tmp_path),
    )
    assert report.total == 5
    assert report.embedded == 5
    assert report.failed == 0
    assert store.row_count() == 5


# --------------------------------------------------------------------------- #
# Test B — resumability (~0 re-embeds on a second run)                         #
# --------------------------------------------------------------------------- #


def test_ingest_source_resumable(isolated_cache, tmp_path):
    from vibemix.library.ingest import ingest_source
    from vibemix.library.sources.rekordbox import RekordboxSource

    xml_path = _make_collection_xml(tmp_path, n=5)
    cache = _open_cache(tmp_path)

    first = ingest_source(
        RekordboxSource(xml_path=str(xml_path)),
        embedder=FakeClapEmbedder(),
        store=_DimAgnosticStore(),
        cache=cache,
    )
    assert first.embedded == 5

    second_embedder = FakeClapEmbedder()
    second = ingest_source(
        RekordboxSource(xml_path=str(xml_path)),
        embedder=second_embedder,
        store=_DimAgnosticStore(),
        cache=cache,
    )
    assert second.skipped_cached == 5
    assert second.embedded == 0
    assert second_embedder.calls == []  # zero re-embeds


# --------------------------------------------------------------------------- #
# Test C — honest per-file failure                                             #
# --------------------------------------------------------------------------- #


def test_ingest_source_honest_failure(isolated_cache, tmp_path):
    from vibemix.library.ingest import ingest_source
    from vibemix.library.sources.rekordbox import RekordboxSource

    xml_path = _make_collection_xml(tmp_path, n=5)
    store = _DimAgnosticStore()
    # Raise specifically on track-3's file — it must NOT be stored.
    embedder = FakeClapEmbedder(raise_on_substr="track-3.mp3")
    report = ingest_source(
        RekordboxSource(xml_path=str(xml_path)),
        embedder=embedder,
        store=store,
        cache=_open_cache(tmp_path),
    )
    assert report.failed == 1
    assert report.embedded == 4
    assert report.total == 5
    assert any("track-3.mp3" in fp for fp, _err in report.failures)
    assert "3" not in {tid for tid, _ in store.search(np.zeros(CLAP_DIM, np.float32), k=10)}
    assert store.row_count() == 4  # no faked zero vector for track 3


# --------------------------------------------------------------------------- #
# Cue-anchored window path (Plan 03)                                           #
# --------------------------------------------------------------------------- #


class _SyntheticSource:
    """A minimal LibrarySource yielding pre-built TrackEntry objects.

    Lets a test inject DJ cues directly without crafting collection.xml
    position marks. ``resolved_path`` is None so persist_library writes under a
    per-source marker (harmless in tmp).
    """

    name = "synthetic"
    resolved_path = None

    def __init__(self, tracks):
        self._tracks = list(tracks)

    def detect(self) -> bool:
        return True

    def iter_tracks(self):
        return iter(self._tracks)


def _track_entry(track_id, filepath, *, cues=(), duration_s=300.0):
    from vibemix.library.rekordbox import TrackEntry

    return TrackEntry(
        track_id=track_id,
        title=f"Track {track_id}",
        artist="Artist",
        album="Album",
        bpm=128.0,
        key="8A",
        duration_s=duration_s,
        cues=tuple(cues),
        filepath=filepath,
    )


def _dj_cue(start_s, number, *, type="cue"):
    from vibemix.library.rekordbox import CuePoint

    return CuePoint(name="", type=type, start_s=start_s, end_s=None, number=number)


def test_dj_cued_track_uses_window_path_and_mean_pools(isolated_cache, tmp_path, monkeypatch):
    """A track WITH dj cues embeds via embed_audio_bytes (window path), NOT whole-track."""
    from vibemix.library import ingest as ingest_mod
    from vibemix.library.ingest import ingest_source

    f = tmp_path / "cued.mp3"
    f.write_bytes(b"CUED-AUDIO" * 8)
    track = _track_entry(
        "10",
        str(f.resolve()),
        cues=(_dj_cue(0.0, 0), _dj_cue(90.0, 1)),  # hot-0 intro + hot-1 drop
        duration_s=300.0,
    )

    # Stub the ffmpeg slicer so NO real ffmpeg / audio decode runs.
    sliced: list[tuple[float, float]] = []

    def _fake_slicer(path, start_s, length_s):
        sliced.append((start_s, length_s))
        return f"WIN-{start_s:.0f}-{length_s:.0f}".encode()

    monkeypatch.setattr(ingest_mod, "_default_slicer", _fake_slicer)

    embedder = FakeClapEmbedder()
    store = _DimAgnosticStore()
    report = ingest_source(
        _SyntheticSource([track]),
        embedder=embedder,
        store=store,
        cache=_open_cache(tmp_path),
    )

    assert report.embedded == 1
    assert report.failed == 0
    assert store.row_count() == 1
    # Window path used: bytes-embed called per window, whole-track NOT called.
    assert len(embedder.byte_calls) == 2  # two cues -> two windows
    assert embedder.calls == []  # whole-track fallback never hit
    assert len(sliced) == 2
    # Stored vector is L2-normalized (mean-pool then normalize).
    stored = store._rows["10"]
    assert stored.shape == (CLAP_DIM,)
    assert abs(float(np.linalg.norm(stored)) - 1.0) < 1e-4


def test_no_structure_track_falls_back_to_whole_track(isolated_cache, tmp_path, monkeypatch):
    """A track with no cues + empty detect_cues uses embed_audio_file (whole-track)."""
    from vibemix.library import ingest as ingest_mod
    from vibemix.library.ingest import ingest_source
    import vibemix.library.cue_detect as cue_detect

    # No structure anywhere.
    monkeypatch.setattr(cue_detect, "detect_cues", lambda *a, **k: [])

    f = tmp_path / "plain.mp3"
    f.write_bytes(b"PLAIN-AUDIO" * 8)
    track = _track_entry("20", str(f.resolve()), cues=(), duration_s=300.0)

    embedder = FakeClapEmbedder()
    store = _DimAgnosticStore()
    report = ingest_source(
        _SyntheticSource([track]),
        embedder=embedder,
        store=store,
        cache=_open_cache(tmp_path),
    )

    assert report.embedded == 1
    assert store.row_count() == 1
    # Whole-track fallback: embed_audio_file called, no window bytes embeds.
    assert embedder.calls == [str(f.resolve())]
    assert embedder.byte_calls == []


def test_one_bad_window_is_non_fatal(isolated_cache, tmp_path, monkeypatch):
    """One window embed failing skips that window; the track still embeds from the rest."""
    from vibemix.library import ingest as ingest_mod
    from vibemix.library.ingest import ingest_source

    f = tmp_path / "partial.mp3"
    f.write_bytes(b"PARTIAL" * 8)
    track = _track_entry(
        "30",
        str(f.resolve()),
        cues=(_dj_cue(0.0, 0), _dj_cue(90.0, 1)),
        duration_s=300.0,
    )

    # Slicer marks the first window as poison; FakeClapEmbedder raises on it.
    def _fake_slicer(path, start_s, length_s):
        if start_s == 0.0:
            return b"POISON-WINDOW"
        return f"WIN-{start_s:.0f}".encode()

    monkeypatch.setattr(ingest_mod, "_default_slicer", _fake_slicer)

    embedder = FakeClapEmbedder(bytes_raise_on=b"POISON")
    store = _DimAgnosticStore()
    report = ingest_source(
        _SyntheticSource([track]),
        embedder=embedder,
        store=store,
        cache=_open_cache(tmp_path),
    )

    assert report.embedded == 1  # survived: second window embedded
    assert store.row_count() == 1
    assert embedder.calls == []  # did NOT degrade to whole-track (one window worked)


def test_all_windows_failed_falls_back_to_whole_track(isolated_cache, tmp_path, monkeypatch):
    """Every window embed failing degrades to the whole-track embed, never a faked vector."""
    from vibemix.library import ingest as ingest_mod
    from vibemix.library.ingest import ingest_source

    f = tmp_path / "allbad.mp3"
    f.write_bytes(b"ALLBAD" * 8)
    track = _track_entry(
        "40",
        str(f.resolve()),
        cues=(_dj_cue(0.0, 0), _dj_cue(90.0, 1)),
        duration_s=300.0,
    )

    monkeypatch.setattr(
        ingest_mod, "_default_slicer", lambda *a, **k: b"POISON-WINDOW"
    )

    embedder = FakeClapEmbedder(bytes_raise_on=b"POISON")
    store = _DimAgnosticStore()
    report = ingest_source(
        _SyntheticSource([track]),
        embedder=embedder,
        store=store,
        cache=_open_cache(tmp_path),
    )

    assert report.embedded == 1
    assert store.row_count() == 1
    # All windows failed -> whole-track fallback (a real vector, not faked).
    assert embedder.calls == [str(f.resolve())]
    stored = store._rows["40"]
    assert abs(float(np.linalg.norm(stored)) - 1.0) < 1e-4


def test_cue_strategy_version_namespaces_cache(isolated_cache, tmp_path):
    """The cue-anchored cache key must not collide with the whole-track key."""
    from vibemix.library.ingest import (
        INGEST_CUE_STRATEGY_VERSION,
        INGEST_STRATEGY_VERSION,
    )

    assert INGEST_CUE_STRATEGY_VERSION != INGEST_STRATEGY_VERSION
    assert "cueanchored" in INGEST_CUE_STRATEGY_VERSION
