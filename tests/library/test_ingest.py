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
      CLAP's 512-dim vectors without depending on the active global
      ``EMBEDDING_DIM``).
    * ``RekordboxLibrary.CACHE_PATH`` is monkeypatched so the real library.pkl
      is never written.
"""

from __future__ import annotations

import pickle
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

    Real stores hard-assert the active ``EMBEDDING_DIM``. This fake stays
    dim-agnostic so ingest tests exercise CLAP-shaped vectors without coupling
    the fixture to the current global dimension. Exposes
    vector_dim()/row_count()/recreate_table() so the ingest dim-reconciliation
    branch can introspect it.
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
    from vibemix.library import section_vectors

    monkeypatch.setattr(
        section_vectors,
        "SECTION_VECTOR_CACHE_DB_PATH",
        tmp_path / "section_vectors.db",
    )
    return cache


@pytest.fixture(autouse=True)
def _stub_detect_cues(monkeypatch):
    """Default: the auto-cue engine finds no structure (honest-green, no ffmpeg).

    The Plan-01 e2e/resumability/failure tracks carry no DJ cues, so
    ``anchors_for_track`` would otherwise run ``detect_cues_auto`` on fake bytes.
    Stubbing it to ``[]`` keeps the suite offline + ffmpeg-free and drives the
    whole-track fallback path the Plan-01 tests assert. Tests that need a
    specific auto result override this with their own monkeypatch.
    """
    import vibemix.library.cue_engine as cue_engine

    monkeypatch.setattr(cue_engine, "detect_cues_auto", lambda *a, **k: [])


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
        f'  <COLLECTION Entries="{n}">\n' + "\n".join(tracks_xml) + "\n  </COLLECTION>\n"
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


def _anlz_index_for_track(track, *, ppth_path: str | None = None):
    from vibemix.library.anlz_ingest import (
        AnlzBeatGrid,
        AnlzIndex,
        AnlzTrackMeta,
        phrases_from_pssi_entries,
    )

    bpm = 120.0
    grid = AnlzBeatGrid(
        times_s=tuple(i * 60.0 / bpm for i in range(160)),
        bpms=tuple(bpm for _ in range(160)),
        beat_in_bar=tuple((i % 4) + 1 for i in range(160)),
    )
    phrases = phrases_from_pssi_entries(
        mood=1,
        end_beat=129,
        entries=[
            {"beat": 1, "kind": 1},
            {"beat": 65, "kind": 5},
        ],
        beatgrid=grid,
    )
    path = ppth_path or str(track.filepath)
    meta = AnlzTrackMeta(
        ext_path=Path("/fixture/ANLZ0000.EXT"),
        dat_path=Path("/fixture/ANLZ0000.DAT"),
        ppth_path=path,
        basename_key=Path(path).name.lower(),
        beatgrid=grid,
        phrases=phrases,
    )
    return AnlzIndex(by_basename={meta.basename_key: (meta,)})


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
    assert len(embedder.byte_calls) == 4  # two track windows + two section windows
    assert embedder.calls == []  # whole-track fallback never hit
    assert len(sliced) == 4
    # Stored vector is L2-normalized (mean-pool then normalize).
    stored = store._rows["10"]
    assert stored.shape == (CLAP_DIM,)
    assert abs(float(np.linalg.norm(stored)) - 1.0) < 1e-4
    from vibemix.library.section_vectors import (
        get_cached_section_vector,
        open_default_section_vector_db,
    )

    section_cache = open_default_section_vector_db(create=False)
    assert section_cache is not None
    assert get_cached_section_vector(section_cache, "10#s000") is not None
    assert get_cached_section_vector(section_cache, "10#s001") is not None
    section_cache.close()


def test_no_structure_track_falls_back_to_whole_track(isolated_cache, tmp_path, monkeypatch):
    """A track with no cues + empty detect_cues_auto uses embed_audio_file."""
    import vibemix.library.cue_engine as cue_engine
    from vibemix.library.ingest import ingest_source

    # No structure anywhere.
    monkeypatch.setattr(cue_engine, "detect_cues_auto", lambda *a, **k: [])

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
    # Whole-track vector fallback stays true. The default section-vector slicer
    # may honestly skip these fake bytes; a dedicated stubbed-slicer test pins
    # the section-cache path below.
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

    monkeypatch.setattr(ingest_mod, "_default_slicer", lambda *a, **k: b"POISON-WINDOW")

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


def test_anlz_index_drives_windows_and_has_separate_cache(isolated_cache, tmp_path, monkeypatch):
    """A later ANLZ match must not reuse an earlier no-structure whole-track vector."""
    from vibemix.library import ingest as ingest_mod
    from vibemix.library.ingest import ingest_source
    from vibemix.library.section_builder import sections_for_entry

    f = tmp_path / "anlz.mp3"
    f.write_bytes(b"ANLZ-AUDIO" * 8)
    track = _track_entry("50", str(f.resolve()), cues=(), duration_s=180.0)
    cache = _open_cache(tmp_path)

    no_anlz_embedder = FakeClapEmbedder()
    no_anlz = ingest_source(
        _SyntheticSource([track]),
        embedder=no_anlz_embedder,
        store=_DimAgnosticStore(),
        cache=cache,
    )
    assert no_anlz.embedded == 1
    assert no_anlz.skipped_cached == 0
    assert no_anlz_embedder.calls == [str(f.resolve())]
    assert no_anlz_embedder.byte_calls == []

    sliced: list[tuple[float, float]] = []

    def _fake_slicer(path, start_s, length_s):
        sliced.append((start_s, length_s))
        return f"ANLZ-WIN-{start_s:.0f}-{length_s:.0f}".encode()

    monkeypatch.setattr(ingest_mod, "_default_slicer", _fake_slicer)

    anlz_index = _anlz_index_for_track(track)
    anlz_embedder = FakeClapEmbedder()
    with_anlz = ingest_source(
        _SyntheticSource([track]),
        embedder=anlz_embedder,
        store=_DimAgnosticStore(),
        cache=cache,
        anlz_index=anlz_index,
    )

    assert with_anlz.embedded == 1
    assert with_anlz.skipped_cached == 0
    assert anlz_embedder.calls == []
    assert len(anlz_embedder.byte_calls) == 4
    assert sliced[:2] == [(0.0, 32.0), (32.0, 32.0)]
    with isolated_cache.open("rb") as fh:
        blob = pickle.load(fh)
    cached_track = blob.tracks["50"]
    assert [cue.source for cue in cached_track.cues] == ["anlz", "anlz"]
    assert [cue.name for cue in cached_track.cues] == ["INTRO", "DROP"]
    assert [cue.number for cue in cached_track.cues] == [0, 3]
    assert cached_track.cues[0].confidence == pytest.approx(0.84)
    sections = sections_for_entry(cached_track)
    assert sections[0].source == "anlz"
    assert sections[0].source_detail == "pssi"
    assert sections[0].cue_source == "anlz"
    assert sections[0].cue_confidence == pytest.approx(0.84)
    assert [section.cue_slot for section in sections] == ["A", "D"]
    assert sections[0].role == "intro"

    resumed_embedder = FakeClapEmbedder()
    resumed = ingest_source(
        _SyntheticSource([track]),
        embedder=resumed_embedder,
        store=_DimAgnosticStore(),
        cache=cache,
        anlz_index=anlz_index,
    )
    assert resumed.skipped_cached == 1
    assert resumed.embedded == 0
    assert resumed_embedder.calls == []
    assert resumed_embedder.byte_calls == []


def test_auto_cues_materialize_to_cached_library_and_sections(
    isolated_cache, tmp_path, monkeypatch
):
    """Auto cues must survive ingest so pill/Viber see grounded sections after restart."""
    import vibemix.library.cue_engine as cue_engine
    from vibemix.library import ingest as ingest_mod
    from vibemix.library.cue_types import CueAnchor
    from vibemix.library.ingest import (
        INGEST_CUE_STRATEGY_VERSION,
        _cue_strategy_tag_for_auto,
        ingest_source,
    )
    from vibemix.library.section_builder import sections_for_entry

    anchors = [
        CueAnchor(label="intro", start_s=0.0, end_s=32.0, confidence=0.82, source="auto"),
        CueAnchor(label="drop", start_s=96.0, end_s=156.0, confidence=0.74, source="auto"),
    ]
    monkeypatch.setattr(cue_engine, "detect_cues_auto", lambda *a, **k: anchors)

    f = tmp_path / "auto.mp3"
    f.write_bytes(b"AUTO-AUDIO" * 8)
    track = _track_entry("55", str(f.resolve()), cues=(), duration_s=180.0)

    sliced: list[tuple[float, float]] = []

    def _fake_slicer(path, start_s, length_s):
        sliced.append((start_s, length_s))
        return f"AUTO-WIN-{start_s:.0f}-{length_s:.0f}".encode()

    monkeypatch.setattr(ingest_mod, "_default_slicer", _fake_slicer)

    embedder = FakeClapEmbedder()
    report = ingest_source(
        _SyntheticSource([track]),
        embedder=embedder,
        store=_DimAgnosticStore(),
        cache=_open_cache(tmp_path),
    )

    assert report.embedded == 1
    assert report.failed == 0
    assert embedder.calls == []
    assert len(embedder.byte_calls) == 4  # two track windows + two section windows
    assert sliced[:2] == [(0.0, 32.0), (96.0, 60.0)]
    with isolated_cache.open("rb") as fh:
        blob = pickle.load(fh)
    cached_track = blob.tracks["55"]
    assert [cue.source for cue in cached_track.cues] == ["auto", "auto"]
    assert [cue.name for cue in cached_track.cues] == ["INTRO", "DROP"]
    assert [cue.number for cue in cached_track.cues] == [0, 3]
    assert cached_track.cues[0].confidence == pytest.approx(0.82)

    sections = sections_for_entry(cached_track)
    assert sections[0].source == "auto"
    assert sections[0].source_detail == "auto_cue"
    assert sections[0].cue_source == "auto"
    assert sections[0].cue_confidence == pytest.approx(0.82)
    assert [section.cue_slot for section in sections] == ["A", "D"]
    assert sections[0].role == "intro"
    assert sections[1].role == "drop"

    auto_tag = _cue_strategy_tag_for_auto(anchors)
    assert auto_tag != INGEST_CUE_STRATEGY_VERSION
    assert ":auto:" in auto_tag


def test_cue_agreement_calibration_compares_dj_cues_without_replacing_them(
    isolated_cache, tmp_path, monkeypatch
):
    """Calibration runs auto-cues against DJ cues, but keeps human cues authoritative."""
    import vibemix.library.cue_engine as cue_engine
    from vibemix.library.cue_types import CueAnchor
    from vibemix.library.ingest import ingest_source

    auto_anchors = [
        CueAnchor(label="intro", start_s=0.4, end_s=32.0, confidence=0.8, source="auto"),
        CueAnchor(label="drop", start_s=96.6, end_s=156.0, confidence=0.8, source="auto"),
        CueAnchor(label="outro", start_s=210.0, end_s=250.0, confidence=0.7, source="auto"),
    ]
    monkeypatch.setattr(cue_engine, "detect_cues_auto", lambda *a, **k: list(auto_anchors))

    f = tmp_path / "dj-cued.mp3"
    f.write_bytes(b"DJ-CUED-AUDIO" * 8)
    track = _track_entry(
        "dj-cued",
        str(f.resolve()),
        cues=(_dj_cue(0.0, 0), _dj_cue(96.0, 3)),
        duration_s=240.0,
    )

    report = ingest_source(
        _SyntheticSource([track]),
        embedder=FakeClapEmbedder(),
        store=_DimAgnosticStore(),
        cache=_open_cache(tmp_path),
        cue_agreement_calibration=True,
    )

    assert report.embedded == 1
    assert report.cue_agreement_tracks == 1
    assert report.cue_agreement_scored == 1
    assert report.cue_agreement_weak_labels == 1
    assert report.as_dict()["cue_agreement"] == {
        "tracks": 1,
        "scored": 1,
        "weak_labels": 1,
        "mean_score": pytest.approx(2 / 3),
        "mean_abs_offset_s": 0.5,
    }
    with isolated_cache.open("rb") as fh:
        blob = pickle.load(fh)
    cached_track = blob.tracks["dj-cued"]
    assert [cue.source for cue in cached_track.cues] == ["dj", "dj"]


def test_materialized_auto_cues_use_semantic_hot_cue_slots() -> None:
    """Semantic cue labels should land on stable Rekordbox A-H slots."""
    from vibemix.library.cue_types import CueAnchor
    from vibemix.library.ingest import _materialize_anchor_cues

    anchors = [
        CueAnchor(label="intro", start_s=0.0, end_s=32.0, confidence=0.82, source="auto"),
        CueAnchor(label="build", start_s=32.0, end_s=64.0, confidence=0.8, source="auto"),
        CueAnchor(label="breakdown", start_s=64.0, end_s=96.0, confidence=0.79, source="auto"),
        CueAnchor(label="drop", start_s=96.0, end_s=156.0, confidence=0.84, source="auto"),
        CueAnchor(label="drop", start_s=180.0, end_s=220.0, confidence=0.76, source="auto"),
        CueAnchor(label="outro", start_s=240.0, end_s=300.0, confidence=0.81, source="auto"),
        CueAnchor(label="bridge", start_s=220.0, end_s=240.0, confidence=0.7, source="auto"),
    ]

    materialized, usable = _materialize_anchor_cues(
        _track_entry("semantic", "/tmp/semantic.mp3", cues=()),
        anchors,
        "auto",
    )

    assert [cue.name for cue in materialized.cues] == [
        "INTRO",
        "BUILD",
        "BREAKDOWN",
        "DROP",
        "DROP",
        "BRIDGE",
        "OUTRO",
    ]
    assert [cue.number for cue in materialized.cues] == [0, 1, 2, 3, 4, 6, 5]
    assert {cue.source for cue in materialized.cues} == {"auto"}
    assert [anchor.label for anchor in usable] == [
        "intro",
        "build",
        "breakdown",
        "drop",
        "drop",
        "bridge",
        "outro",
    ]


def test_ingest_keeps_dj_cues_ahead_of_anlz(isolated_cache, tmp_path, monkeypatch):
    """Even with an ANLZ index, human DJ cues remain the highest-trust source."""
    from vibemix.library import ingest as ingest_mod
    from vibemix.library.ingest import ingest_source

    f = tmp_path / "dj-wins.mp3"
    f.write_bytes(b"DJ-WINS" * 8)
    track = _track_entry(
        "60",
        str(f.resolve()),
        cues=(_dj_cue(10.0, 0),),
        duration_s=180.0,
    )

    sliced: list[tuple[float, float]] = []

    def _fake_slicer(path, start_s, length_s):
        sliced.append((start_s, length_s))
        return f"DJ-WIN-{start_s:.0f}-{length_s:.0f}".encode()

    monkeypatch.setattr(ingest_mod, "_default_slicer", _fake_slicer)

    embedder = FakeClapEmbedder()
    report = ingest_source(
        _SyntheticSource([track]),
        embedder=embedder,
        store=_DimAgnosticStore(),
        cache=_open_cache(tmp_path),
        anlz_index=_anlz_index_for_track(track),
    )

    assert report.embedded == 1
    assert embedder.calls == []
    assert len(embedder.byte_calls) == 2
    assert sliced[0] == (10.0, 80.0)
    with isolated_cache.open("rb") as fh:
        blob = pickle.load(fh)
    cached_track = blob.tracks["60"]
    assert len(cached_track.cues) == 1
    assert cached_track.cues[0].source == "dj"


def test_cue_strategy_version_namespaces_cache(isolated_cache, tmp_path):
    """The cue-anchored cache key must not collide with the whole-track key."""
    from vibemix.library.ingest import (
        INGEST_CUE_STRATEGY_VERSION,
        INGEST_STRATEGY_VERSION,
    )

    assert INGEST_CUE_STRATEGY_VERSION != INGEST_STRATEGY_VERSION
    assert "cueanchored" in INGEST_CUE_STRATEGY_VERSION
    assert "anlz" in INGEST_CUE_STRATEGY_VERSION
