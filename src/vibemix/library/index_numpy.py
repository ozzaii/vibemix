# SPDX-License-Identifier: Apache-2.0
"""NumpyStore — pure-numpy vector backend (Windows fallback / any-host fallback).

Used when:
    - sqlite-vec extension fails to load on the host (Win-ARM64 Assumption A2)
    - the user / tests force ``prefer_sqlite_vec=False``

Storage format:
    - Vectors: ``~/.cache/vibemix/library_vectors.npy`` (numpy .npy, no pickle).
    - IDs: ``~/.cache/vibemix/library_ids.json`` (UTF-8 JSON list[str]).

Row alignment between the two files is the integrity contract. Writes are
atomic (``os.replace``) — a crashed process never leaves the pair half-updated.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import numpy as np

from vibemix.library._cosine import EMBEDDING_DIM, l2_normalize

VECTORS_PATH = Path.home() / ".cache" / "vibemix" / "library_vectors.npy"
IDS_PATH = Path.home() / ".cache" / "vibemix" / "library_ids.json"


class NumpyStore:
    """Pickle-free numpy + JSON sidecar backend.

    Public interface (must match ``SqliteVecStore``):
        - ``add_batch(items)``
        - ``load_all() -> (list[str], np.ndarray)``
        - ``delete(track_ids)``
        - ``snapshot_hash() -> str``
        - ``close()``
    """

    def __init__(
        self,
        vectors_path: Path = VECTORS_PATH,
        ids_path: Path = IDS_PATH,
    ) -> None:
        self._vectors_path = Path(vectors_path)
        self._ids_path = Path(ids_path)
        self._vectors_path.parent.mkdir(parents=True, exist_ok=True)
        self._ids: list[str] = []
        self._vectors: np.ndarray = np.zeros((0, EMBEDDING_DIM), dtype=np.float32)
        self._load()

    def _load(self) -> None:
        try:
            with self._ids_path.open("r", encoding="utf-8") as f:
                self._ids = list(json.load(f))
            arr = np.load(self._vectors_path, allow_pickle=False)
            assert arr.dtype == np.float32, (
                f"library_vectors.npy must be float32, got {arr.dtype}"
            )
            if arr.shape[0] != len(self._ids):
                raise ValueError(
                    f"row mismatch: {arr.shape[0]} vectors vs {len(self._ids)} ids"
                )
            if arr.shape[0] > 0 and arr.shape[1] != EMBEDDING_DIM:
                raise ValueError(
                    f"vector dim mismatch: got {arr.shape[1]}, expected {EMBEDDING_DIM}"
                )
            self._vectors = arr
        except FileNotFoundError:
            self._ids = []
            self._vectors = np.zeros((0, EMBEDDING_DIM), dtype=np.float32)

    def _save(self) -> None:
        # np.save appends .npy if not present — pass an explicit name without
        # the .tmp suffix being treated as a "real" suffix.
        tmp_vec = self._vectors_path.parent / (
            self._vectors_path.name + ".tmp"
        )
        tmp_ids = self._ids_path.parent / (self._ids_path.name + ".tmp")
        # allow_pickle=False is the security bar; np.save adds .npy if absent
        # — pass the file handle explicitly to bypass that magic.
        with tmp_vec.open("wb") as f:
            np.save(f, self._vectors, allow_pickle=False)
        with tmp_ids.open("w", encoding="utf-8") as f:
            json.dump(self._ids, f)
        os.replace(tmp_vec, self._vectors_path)
        os.replace(tmp_ids, self._ids_path)

    def add_batch(self, items: list[tuple[str, np.ndarray]]) -> None:
        """Add or replace (track_id, vector) rows. Vectors must be float32 (768,)."""
        if not items:
            return
        for tid, vec in items:
            assert vec.dtype == np.float32, (
                f"NumpyStore.add_batch: vector for {tid!r} must be float32, "
                f"got {vec.dtype}"
            )
            assert vec.shape == (EMBEDDING_DIM,), (
                f"NumpyStore.add_batch: vector for {tid!r} must be shape "
                f"({EMBEDDING_DIM},), got {vec.shape}"
            )

        id_to_idx = {tid: i for i, tid in enumerate(self._ids)}
        new_rows: list[np.ndarray] = []
        new_ids: list[str] = []
        # Trust caller — vectors arrive already L2-normalized from
        # LibraryEmbedder. Re-normalizing here would introduce float-error
        # drift and break the P55 parity contract (the fixture and the
        # backend MUST persist byte-identical bytes). The float32 +
        # shape assertion above is the defense-in-depth.
        for tid, vec in items:
            row = vec.astype(np.float32, copy=False)
            if tid in id_to_idx:
                self._vectors[id_to_idx[tid]] = row
            else:
                new_ids.append(tid)
                new_rows.append(row)

        if new_rows:
            self._ids.extend(new_ids)
            self._vectors = np.vstack([self._vectors, np.stack(new_rows)])
        self._save()

    def load_all(self) -> tuple[list[str], np.ndarray]:
        """Return (ids, vectors). Caller may mutate copies safely."""
        return list(self._ids), self._vectors.copy()

    def delete(self, track_ids: list[str]) -> None:
        if not track_ids:
            return
        drop = set(track_ids)
        keep_idx = [i for i, tid in enumerate(self._ids) if tid not in drop]
        self._ids = [self._ids[i] for i in keep_idx]
        if keep_idx:
            self._vectors = self._vectors[keep_idx]
        else:
            self._vectors = np.zeros((0, EMBEDDING_DIM), dtype=np.float32)
        self._save()

    def snapshot_hash(self) -> str:
        """sha256(json.dumps(sorted(ids))) — stable across reloads."""
        payload = json.dumps(sorted(self._ids))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def close(self) -> None:
        # numpy backend has no file handles to close — _save is sync.
        return
