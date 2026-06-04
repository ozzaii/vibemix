# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import numpy as np

from vibemix.intel.transition_scorer import SectionRecord
from vibemix.library.rekordbox import CuePoint, TrackEntry
from vibemix.library.section_vectors import (
    get_cached_section_vector,
    open_section_vector_db,
    persist_section_vectors_for_track,
    put_section_vector,
    resolve_section_vector,
    section_source_hash,
    section_vector_cached,
    section_window_for_record,
    semantic_basis_for_pair,
)


class _Provider:
    def __init__(self) -> None:
        self.section_vectors = {"vec8:t1#s000": [1.0, 0.0]}


class _Backend:
    def section_vector_for_id(self, section_id: str):
        if section_id == "t2#s000":
            return [0.0, 1.0]
        return None


class _Store:
    def __init__(self) -> None:
        self._backend = _Backend()


def test_resolve_section_vector_reads_mapping_keys() -> None:
    result = resolve_section_vector(_Provider(), "t1#s000")

    assert result.basis == "section_vector"
    assert result.vector is not None
    assert np.allclose(result.vector, [1.0, 0.0])


def test_resolve_section_vector_reads_backend_method() -> None:
    result = resolve_section_vector(_Store(), "t2#s000")

    assert result.basis == "section_vector"
    assert result.vector is not None
    assert np.allclose(result.vector, [0.0, 1.0])


def test_resolve_section_vector_uses_explicit_track_fallback() -> None:
    result = resolve_section_vector(object(), "missing#s000", fallback_vector=np.array([0.2, 0.8]))

    assert result.basis == "track_vector_fallback"
    assert result.vector is not None
    assert np.allclose(result.vector, [0.2, 0.8])


def test_section_vector_cache_roundtrip(tmp_path) -> None:
    conn = open_section_vector_db(tmp_path / "sections.db")
    vector = np.array([0.2, 0.8], dtype=np.float32)

    put_section_vector(
        conn,
        section_id="t9#s000",
        source_hash="hash-1",
        vector=vector,
        model_tag="fake-clap",
        start_s=4.0,
        end_s=20.0,
    )

    assert section_vector_cached(conn, "t9#s000", source_hash="hash-1") is True
    assert section_vector_cached(conn, "t9#s000", source_hash="other") is False
    out = get_cached_section_vector(conn, "t9#s000")
    assert out is not None
    assert np.allclose(out, vector)


def test_semantic_basis_for_pair_is_honest() -> None:
    assert semantic_basis_for_pair("section_vector", "section_vector") == "section_vector"
    assert (
        semantic_basis_for_pair("section_vector", "track_vector_fallback") == "mixed_section_track"
    )
    assert (
        semantic_basis_for_pair("track_vector_fallback", "track_vector_fallback")
        == "track_vector_fallback"
    )
    assert semantic_basis_for_pair("section_vector", "semantic_unknown") == "semantic_unknown"


def test_section_window_clamps_to_duration_and_80s() -> None:
    section = SectionRecord(
        section_id="t1#s000",
        track_id="t1",
        role="intro",
        start_s=10.0,
        end_s=140.0,
    )

    assert section_window_for_record(section, duration_s=70.0) == (10.0, 70.0)
    assert section_window_for_record(section, duration_s=200.0) == (10.0, 90.0)


def test_section_source_hash_changes_with_bounds() -> None:
    a = section_source_hash("track-key", "t1#s000", 0.0, 80.0)
    b = section_source_hash("track-key", "t1#s000", 0.0, 64.0)

    assert a != b
    assert section_source_hash("track-key", "t1#s000", 0.0, 80.0) == a


class _FakeSectionEmbedder:
    backend = "fake-clap"

    def __init__(self) -> None:
        self.byte_calls: list[bytes] = []

    def embed_audio_bytes(self, data: bytes, mime: str) -> np.ndarray:
        self.byte_calls.append(data)
        if data.endswith(b"0-80"):
            return np.array([1.0, 0.0], dtype=np.float32)
        return np.array([0.0, 1.0], dtype=np.float32)


def _track_with_intro_outro(tmp_path) -> tuple[TrackEntry, object]:
    audio = tmp_path / "track.mp3"
    audio.write_bytes(b"fake")
    track = TrackEntry(
        track_id="t1",
        title="Track",
        artist="",
        album="",
        bpm=120.0,
        key="",
        duration_s=180.0,
        cues=(
            CuePoint(name="intro", type="cue", start_s=0.0, end_s=80.0, number=0),
            CuePoint(name="outro", type="cue", start_s=120.0, end_s=180.0, number=5),
        ),
        filepath=str(audio),
    )
    return track, audio


def test_persist_section_vectors_for_track_writes_and_skips_cached(tmp_path) -> None:
    track, audio = _track_with_intro_outro(tmp_path)
    conn = open_section_vector_db(tmp_path / "sections.db")
    embedder = _FakeSectionEmbedder()
    sliced: list[tuple[float, float]] = []

    def slicer(path: str, start_s: float, length_s: float) -> bytes:
        sliced.append((start_s, length_s))
        return f"{start_s:.0f}-{length_s:.0f}".encode()

    written = persist_section_vectors_for_track(
        track,
        audio,
        embedder,
        conn,
        track_cache_key="track-key",
        backend_tag="fake-clap",
        slicer=slicer,
    )
    written_again = persist_section_vectors_for_track(
        track,
        audio,
        embedder,
        conn,
        track_cache_key="track-key",
        backend_tag="fake-clap",
        slicer=slicer,
    )

    assert written == 2
    assert written_again == 0
    assert sliced == [(0.0, 80.0), (120.0, 60.0)]
    assert len(embedder.byte_calls) == 2
    assert np.allclose(get_cached_section_vector(conn, "t1#s000"), [1.0, 0.0])
    assert np.allclose(get_cached_section_vector(conn, "t1#s001"), [0.0, 1.0])
