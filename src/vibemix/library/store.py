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

    @property
    def backend_name(self) -> str:
        return type(self._backend).__name__

    def add_batch(self, items: list[tuple[str, np.ndarray]]) -> None:
        self._backend.add_batch(items)

    def search(
        self, query_vector: np.ndarray, k: int = 10
    ) -> list[tuple[str, float]]:
        """Top-K cosine search. Always uses shared cosine_topk (P55)."""
        ids, vectors = self._backend.load_all()
        return cosine_topk(query_vector, vectors, ids, k)

    def delete(self, track_ids: list[str]) -> None:
        self._backend.delete(track_ids)

    def snapshot_hash(self) -> str:
        return self._backend.snapshot_hash()

    def close(self) -> None:
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
                f"-> library store: backend=SqliteVecStore reason=ok",
                file=sys.stdout,
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
                file=sys.stdout,
                flush=True,
            )

    backend = NumpyStore()
    print(
        f"-> library store: backend=NumpyStore reason=preferred",
        file=sys.stdout,
        flush=True,
    )
    return LibraryStore(backend)


__all__ = [
    "LibraryStore",
    "open_store",
    "snapshot_hash",
    "EMBEDDING_DIM",
]
