# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import numpy as np

from vibemix.library.section_vectors import (
    get_cached_section_vector,
    open_section_vector_db,
    put_section_vector,
    resolve_section_vector,
    section_vector_cached,
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
