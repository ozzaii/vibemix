# SPDX-License-Identifier: Apache-2.0
"""Tests for corpus mean-centering (the anisotropy fix) on the query path.

Validates the experimental finding: raw whole-track Gemini embeddings are
anisotropic (avg pairwise cosine ≈ 0.8), and subtracting the corpus centroid
then re-normalizing collapses avg pairwise cosine toward 0 while preserving
exact-duplicate detection (cosine 1.0) — restoring real ranking separation.

All disk I/O is routed to tmp_path; no test touches the real ~/.cache.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from vibemix.library._cosine import EMBEDDING_DIM, l2_normalize
from vibemix.library.centering import (
    center_and_renorm,
    compute_centroid,
    load_or_compute_centroid,
)
from vibemix.library.index_numpy import NumpyStore
from vibemix.library.store import LibraryStore


def _anisotropic_corpus(n: int, seed: int = 0) -> np.ndarray:
    """N L2-normalized vectors sharing a strong common direction (high avg
    pairwise cosine) plus small per-vector noise — mimics real embeddings."""
    rng = np.random.default_rng(seed)
    shared = l2_normalize(rng.standard_normal(EMBEDDING_DIM).astype(np.float32))
    rows = []
    for _ in range(n):
        # Per-vector noise direction, scaled DOWN so the shared component
        # dominates → high avg pairwise cosine (anisotropic, like real
        # whole-track Gemini embeddings).
        noise = l2_normalize(
            rng.standard_normal(EMBEDDING_DIM).astype(np.float32)
        )
        v = l2_normalize((shared + 0.4 * noise).astype(np.float32))
        rows.append(v)
    return np.stack(rows)


def _avg_pairwise_cosine(vectors: np.ndarray) -> float:
    sims = vectors @ vectors.T
    n = vectors.shape[0]
    off_diag = (sims.sum() - np.trace(sims)) / (n * (n - 1))
    return float(off_diag)


def test_compute_centroid_returns_none_below_two() -> None:
    assert compute_centroid(np.zeros((0, EMBEDDING_DIM), np.float32)) is None
    one = l2_normalize(np.ones(EMBEDDING_DIM, np.float32)).reshape(1, -1)
    assert compute_centroid(one) is None


def test_centering_collapses_anisotropy() -> None:
    corpus = _anisotropic_corpus(40)
    raw_avg = _avg_pairwise_cosine(corpus)
    assert raw_avg > 0.5, f"fixture not anisotropic enough: {raw_avg}"

    centroid = compute_centroid(corpus)
    assert centroid is not None
    centered = center_and_renorm(corpus, centroid)
    centered_avg = _avg_pairwise_cosine(centered)

    # Centering must dramatically reduce the average pairwise cosine.
    assert abs(centered_avg) < 0.2
    assert centered_avg < raw_avg - 0.4


def test_centering_preserves_exact_duplicate() -> None:
    corpus = _anisotropic_corpus(20)
    # Inject an exact duplicate of row 0.
    corpus = np.vstack([corpus, corpus[0:1]])
    centroid = compute_centroid(corpus)
    assert centroid is not None
    centered = center_and_renorm(corpus, centroid)
    # Row 0 and its duplicate (last row) must still be cosine ≈ 1.0.
    dup_cos = float(centered[0] @ centered[-1])
    assert dup_cos == pytest.approx(1.0, abs=1e-4)


def test_single_vector_shape_preserved() -> None:
    centroid = l2_normalize(np.ones(EMBEDDING_DIM, np.float32))
    v = l2_normalize(np.arange(EMBEDDING_DIM, dtype=np.float32))
    out = center_and_renorm(v, centroid)
    assert out.shape == (EMBEDDING_DIM,)
    assert out.dtype == np.float32
    assert float(np.linalg.norm(out)) == pytest.approx(1.0, abs=1e-5)


def test_load_or_compute_caches_and_reuses(tmp_path: Path) -> None:
    corpus = _anisotropic_corpus(10)
    cpath = tmp_path / "centroid.npy"
    mpath = tmp_path / "centroid.meta.json"

    c1 = load_or_compute_centroid(
        corpus, "snap-A", centroid_path=cpath, meta_path=mpath
    )
    assert c1 is not None
    assert cpath.exists() and mpath.exists()

    # Same snapshot → cached array returned (identical values).
    c2 = load_or_compute_centroid(
        corpus, "snap-A", centroid_path=cpath, meta_path=mpath
    )
    np.testing.assert_array_equal(c1, c2)

    # Changed snapshot with a different corpus → recompute (different value).
    other = _anisotropic_corpus(10, seed=99)
    c3 = load_or_compute_centroid(
        other, "snap-B", centroid_path=cpath, meta_path=mpath
    )
    assert c3 is not None
    assert not np.array_equal(c1, c3)


def test_search_centered_distinct_neighbours(tmp_path: Path) -> None:
    """End-to-end: search_centered over a NumpyStore yields distinct neighbour
    sets per seed (the raw path would rank everything ~equally similar)."""
    corpus = _anisotropic_corpus(30)
    ids = [f"t{i:03d}" for i in range(corpus.shape[0])]
    store = LibraryStore(
        NumpyStore(
            vectors_path=tmp_path / "v.npy", ids_path=tmp_path / "ids.json"
        )
    )
    store.add_batch(list(zip(ids, corpus, strict=True)))

    # Route centroid cache to tmp.
    import vibemix.library.centering as centering_mod

    centering_mod.CENTROID_PATH = tmp_path / "centroid.npy"
    centering_mod.CENTROID_META_PATH = tmp_path / "centroid.meta.json"

    top_a = store.search_centered(corpus[0], k=5)
    top_b = store.search_centered(corpus[15], k=5)
    # Each seed's own id should top its own centered ranking.
    assert top_a[0][0] == "t000"
    assert top_b[0][0] == "t015"
    # Distinct neighbour sets (anisotropy collapse gives real separation).
    assert [t for t, _ in top_a] != [t for t, _ in top_b]
    store.close()


def test_search_centered_falls_back_below_two(tmp_path: Path) -> None:
    """N < 2 → no centroid → search_centered == raw search (no crash)."""
    store = LibraryStore(
        NumpyStore(
            vectors_path=tmp_path / "v.npy", ids_path=tmp_path / "ids.json"
        )
    )
    v = l2_normalize(np.ones(EMBEDDING_DIM, np.float32))
    store.add_batch([("only", v)])
    import vibemix.library.centering as centering_mod

    centering_mod.CENTROID_PATH = tmp_path / "centroid.npy"
    centering_mod.CENTROID_META_PATH = tmp_path / "centroid.meta.json"
    out = store.search_centered(v, k=3)
    assert out == store.search(v, k=3)
    store.close()
