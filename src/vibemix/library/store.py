# SPDX-License-Identifier: Apache-2.0
"""LibraryStore — backend-agnostic facade for the Phase 28 library.

The single API surface for downstream plans:

    store = open_store()
    store.add_batch([(track_id, vector), ...])
    matches = store.search(query_vector, k=10)

The two backends (``SqliteVecStore`` Mac/Win-x64, ``NumpyStore`` fallback)
implement an identical add_batch/load_all/delete/snapshot_hash interface.
``open_store()`` probes sqlite-vec and falls through to numpy if the
extension is unavailable (Wave 0 sqlite-vec ARM64 Win probe; Assumption A2).

**Pitfall P55 mitigation — single chokepoint:** ``LibraryStore.search()``
is the ONLY place top-K math runs. Both backends are storage-only. The
shared ``cosine_topk`` from ``_cosine.py`` produces bit-identical rank
orders across Mac and Win. Any future backend MUST NOT do its own KNN.
"""

from __future__ import annotations

import logging
import sys
from typing import Protocol

import numpy as np

from vibemix.library._cosine import EMBEDDING_DIM, cosine_topk
from vibemix.library.index_numpy import NumpyStore

logger = logging.getLogger(__name__)


class _Backend(Protocol):  # pragma: no cover - protocol
    def add_batch(self, items: list[tuple[str, np.ndarray]]) -> None: ...
    def load_all(self) -> tuple[list[str], np.ndarray]: ...
    def delete(self, track_ids: list[str]) -> None: ...
    def snapshot_hash(self) -> str: ...
    def close(self) -> None: ...


class LibraryStore:
    """Storage-agnostic facade. Single chokepoint for top-K math (P55)."""

    def __init__(self, backend: _Backend) -> None:
        self._backend = backend
        self._section_vector_cache = None

    @property
    def backend_name(self) -> str:
        return type(self._backend).__name__

    def add_batch(self, items: list[tuple[str, np.ndarray]]) -> None:
        self._backend.add_batch(items)

    def search(self, query_vector: np.ndarray, k: int = 10) -> list[tuple[str, float]]:
        """Top-K cosine search. Always uses shared cosine_topk (P55)."""
        ids, vectors = self._backend.load_all()
        return cosine_topk(query_vector, vectors, ids, k)

    def search_centered(self, query_vector: np.ndarray, k: int = 10) -> list[tuple[str, float]]:
        """Mean-centered top-K cosine search (the anisotropy fix).

        Loads all vectors once, derives (or reuses) the corpus centroid keyed
        on the store snapshot, centers BOTH the query and every candidate with
        that centroid, then ranks via the same ``cosine_topk`` chokepoint (P55
        parity preserved — only the inputs are centered).

        Degenerate guard: when the corpus has < 2 vectors there is no
        meaningful centroid, so this transparently falls back to the raw
        ``search`` path (byte-identical ranking to pre-fix behaviour).
        """
        from vibemix.library.centering import (
            center_and_renorm,
            load_or_compute_centroid,
        )

        ids, vectors = self._backend.load_all()
        centroid = load_or_compute_centroid(vectors, self._backend.snapshot_hash())
        if centroid is None:
            return cosine_topk(query_vector, vectors, ids, k)
        q_centered = center_and_renorm(query_vector, centroid)
        v_centered = center_and_renorm(vectors, centroid)
        return cosine_topk(q_centered, v_centered, ids, k)

    def delete(self, track_ids: list[str]) -> None:
        self._backend.delete(track_ids)

    def vector_dim(self) -> int | None:
        """On-disk vector dim, or None if the backend can't introspect it.

        Catches a stale-but-empty vec0 schema (768) that the row-data
        cosine path would miss. NumpyStore has no fixed schema (it raises
        at load time on a stale .npy), so it returns None here.
        """
        fn = getattr(self._backend, "vector_dim", None)
        return fn() if callable(fn) else None

    def row_count(self) -> int | None:
        """Stored vector count, or None if the backend can't report it."""
        fn = getattr(self._backend, "row_count", None)
        return fn() if callable(fn) else None

    def recreate_table(self) -> bool:
        """Drop + recreate the backend table at the current EMBEDDING_DIM.

        Returns True if the backend supports it (sqlite-vec). NumpyStore
        returns False — its stale .npy is caught fail-loud at load time.
        """
        fn = getattr(self._backend, "recreate_table", None)
        if callable(fn):
            fn()
            return True
        return False

    def snapshot_hash(self) -> str:
        return self._backend.snapshot_hash()

    def section_vector_for_id(self, section_id: str) -> np.ndarray | None:
        """Optional per-section vector lookup for transition scoring."""
        if self._section_vector_cache is False:
            return None
        try:
            from vibemix.library.section_vectors import (
                get_cached_section_vector,
                open_default_section_vector_db,
            )

            if self._section_vector_cache is None:
                self._section_vector_cache = open_default_section_vector_db(create=False)
                if self._section_vector_cache is None:
                    self._section_vector_cache = False
                    return None
            return get_cached_section_vector(self._section_vector_cache, section_id)
        except Exception:
            return None

    def close(self) -> None:
        cache = self._section_vector_cache
        if cache is not None and cache is not False:
            try:
                cache.close()
            except Exception:
                pass
        self._backend.close()


def snapshot_hash(store: LibraryStore) -> str:
    """Convenience helper used by Plan 03's 24h query cache key."""
    return store.snapshot_hash()


def open_store(prefer_sqlite_vec: bool = True) -> LibraryStore:
    """Probe sqlite-vec on the host; fall through to numpy on failure.

    Wave 0 ARM64 Win probe (Assumption A2). On any failure during
    ``sqlite_vec.load(...)``, log structured diagnostics and return a
    NumpyStore-backed LibraryStore.
    """
    if prefer_sqlite_vec:
        try:
            from vibemix.library.index_sqlite_vec import SqliteVecStore

            backend: _Backend = SqliteVecStore()
            print(
                "-> library store: backend=SqliteVecStore reason=ok",
                file=sys.stderr,
                flush=True,
            )
            return LibraryStore(backend)
        except Exception as e:
            logger.warning(
                "library backend probe failed: backend_probe_failed=sqlite_vec "
                "reason=%s — falling back to NumpyStore",
                e,
            )
            print(
                f"-> library store: backend=NumpyStore reason=sqlite_vec_unavailable ({e})",
                file=sys.stderr,
                flush=True,
            )

    backend = NumpyStore()
    print(
        "-> library store: backend=NumpyStore reason=preferred",
        file=sys.stderr,
        flush=True,
    )
    return LibraryStore(backend)


__all__ = [
    "EMBEDDING_DIM",
    "LibraryStore",
    "open_store",
    "snapshot_hash",
]
