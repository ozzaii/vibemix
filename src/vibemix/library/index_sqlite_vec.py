# SPDX-License-Identifier: Apache-2.0
"""SqliteVecStore — sqlite-vec vec0 virtual table backend (Mac primary).

Per RESEARCH §Summary + Pitfall P55: sqlite-vec is **storage-only** in v1.
We do NOT use the extension's built-in KNN-style index lookup — that path
can produce platform-divergent rank orders for tied similarities. Instead
we ``SELECT track_id, embedding ORDER BY track_id ASC``, deserialize blobs
to numpy, and run the shared ``cosine_topk`` from ``_cosine.py``.

Wave 0 sqlite-vec ARM64 Win probe (Assumption A2): if ``sqlite_vec.load(db)``
raises (no extension wheel for the host), constructor re-raises so
``store.open_store()`` can fall through to the numpy backend.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import numpy as np
import sqlite_vec

from vibemix.library._cosine import EMBEDDING_DIM

DB_PATH = Path.home() / ".cache" / "vibemix" / "library.db"


class SqliteVecStore:
    """vec0-virtual-table backed library store.

    Public interface (must match ``NumpyStore``):
        - ``add_batch(items)``
        - ``load_all() -> (list[str], np.ndarray)`` — ORDER BY track_id ASC
        - ``delete(track_ids)``
        - ``snapshot_hash() -> str``
        - ``close()``
    """

    def __init__(self, db_path: Path = DB_PATH) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(self._db_path))
        self.db.enable_load_extension(True)
        # If the host has no sqlite-vec extension wheel, this raises and the
        # caller (open_store) catches → numpy fallback. Assumption A2.
        sqlite_vec.load(self.db)
        self.db.enable_load_extension(False)
        self.db.execute(
            f"CREATE VIRTUAL TABLE IF NOT EXISTS vec_library USING vec0("
            f"track_id TEXT PRIMARY KEY, "
            f"embedding FLOAT[{EMBEDDING_DIM}] distance_metric=cosine"
            f")"
        )
        self.db.commit()

    def add_batch(self, items: list[tuple[str, np.ndarray]]) -> None:
        if not items:
            return
        rows: list[tuple[str, bytes]] = []
        for tid, vec in items:
            assert vec.dtype == np.float32, (
                f"SqliteVecStore.add_batch: {tid!r} vector must be float32, "
                f"got {vec.dtype}"
            )
            assert vec.shape == (EMBEDDING_DIM,), (
                f"SqliteVecStore.add_batch: {tid!r} vector must be "
                f"({EMBEDDING_DIM},), got {vec.shape}"
            )
            rows.append((tid, vec.tobytes()))
        # vec0 doesn't support INSERT OR REPLACE on the virtual-table layer
        # uniformly; do delete-then-insert to make replace deterministic.
        ids_to_replace = [tid for tid, _ in rows]
        placeholders = ",".join("?" for _ in ids_to_replace)
        self.db.execute(
            f"DELETE FROM vec_library WHERE track_id IN ({placeholders})",
            ids_to_replace,
        )
        self.db.executemany(
            "INSERT INTO vec_library(track_id, embedding) VALUES (?, ?)",
            rows,
        )
        self.db.commit()

    def load_all(self) -> tuple[list[str], np.ndarray]:
        """Return (ids, vectors). ORDER BY track_id ASC for stable iteration."""
        rows = self.db.execute(
            "SELECT track_id, embedding FROM vec_library ORDER BY track_id ASC"
        ).fetchall()
        if not rows:
            return [], np.zeros((0, EMBEDDING_DIM), dtype=np.float32)
        ids = [r[0] for r in rows]
        vectors = np.stack(
            [np.frombuffer(r[1], dtype=np.float32) for r in rows]
        )
        return ids, vectors

    def delete(self, track_ids: list[str]) -> None:
        if not track_ids:
            return
        placeholders = ",".join("?" for _ in track_ids)
        self.db.execute(
            f"DELETE FROM vec_library WHERE track_id IN ({placeholders})",
            list(track_ids),
        )
        self.db.commit()

    def snapshot_hash(self) -> str:
        rows = self.db.execute(
            "SELECT track_id FROM vec_library ORDER BY track_id ASC"
        ).fetchall()
        ids = [r[0] for r in rows]
        return hashlib.sha256(json.dumps(ids).encode("utf-8")).hexdigest()

    def close(self) -> None:
        try:
            self.db.close()
        except Exception:
            pass
