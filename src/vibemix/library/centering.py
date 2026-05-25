# SPDX-License-Identifier: Apache-2.0
"""Corpus mean-centering for the library query path (search + similar).

THE quality fix (quick-260525, validated experimentally): raw whole-track
Gemini embeddings are strongly anisotropic — average pairwise cosine ≈ 0.81,
so *everything* looks ~0.92 similar to everything else and the ranking has no
discriminative power. Subtracting the corpus centroid (the mean of all stored
vectors) and re-L2-normalizing collapses the average pairwise cosine to ≈ 0,
restoring real separation: exact-dup detection hits cosine 1.000 and each seed
gets a distinct neighbour set.

This is a QUERY-SIDE transform only. We never touch the persisted vectors —
embed-time behaviour is byte-identical. Both the query/seed vector AND every
candidate vector are centered with the SAME centroid, then ranked with the
shared ``cosine_topk`` (P55 parity chokepoint stays intact: the math is the
same dot-product top-K, just on centered inputs).

Centroid lifecycle (the simpler-correct option):
    Computed LAZILY at query time from ``store.load_all()`` and cached to a
    sibling ``library_centroid.npy`` keyed by the store's ``snapshot_hash()``.
    When the track set changes (embed-folder adds/removes vectors), the
    snapshot hash changes and the cache is recomputed on the next query — no
    embed-time hook needed, and robust to a concurrent embed-folder run
    writing the store underneath us. A stale/missing/corrupt cache is simply
    recomputed; we never block on it.

Degenerate guard: an empty library or N < 2 has no meaningful centroid
(centering a single vector to itself yields the zero vector). In that case
``compute_centroid`` returns ``None`` and the query path skips centering,
falling back to the raw-cosine ranking — identical to pre-fix behaviour.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np

from vibemix.library._cosine import EMBEDDING_DIM, l2_normalize

logger = logging.getLogger(__name__)

# Sibling of ~/.cache/vibemix/library.db (the sqlite-vec store) and
# library_vectors.npy (the numpy store). One centroid serves whichever
# backend open_store() selected — they store the same vectors.
CENTROID_PATH = Path.home() / ".cache" / "vibemix" / "library_centroid.npy"
# Tiny sidecar recording the snapshot_hash the cached centroid was computed
# for, so we can cheaply detect a stale cache without re-reading all vectors.
CENTROID_META_PATH = (
    Path.home() / ".cache" / "vibemix" / "library_centroid.meta.json"
)


def compute_centroid(vectors: np.ndarray) -> np.ndarray | None:
    """Return the L2-normalized corpus centroid, or ``None`` for N < 2.

    ``vectors`` is the ``(N, D)`` float32 matrix from ``store.load_all()``.
    The centroid is the per-dimension mean of the (already-unit) vectors;
    we re-L2-normalize it so the subtraction step lives in the same scale.
    N < 2 → ``None`` (no discriminative centroid possible).
    """
    if vectors.ndim != 2 or vectors.shape[0] < 2:
        return None
    mean = vectors.mean(axis=0).astype(np.float32)
    return l2_normalize(mean)


def center_and_renorm(
    vectors: np.ndarray, centroid: np.ndarray
) -> np.ndarray:
    """Subtract ``centroid`` from each row of ``vectors`` then L2-renorm.

    Accepts a single vector ``(D,)`` or a batch ``(N, D)``; returns the same
    shape, float32. A row that becomes (near-)zero after subtraction is left
    as the zero vector by ``l2_normalize``'s small-norm guard (cosine 0 vs
    everything — it simply ranks last, which is the correct degenerate
    behaviour for a track that sits exactly at the corpus mean).
    """
    centered = (vectors - centroid).astype(np.float32, copy=False)
    if centered.ndim == 1:
        return l2_normalize(centered)
    # Row-wise L2 norm; guard zeros to avoid divide-by-zero.
    norms = np.linalg.norm(centered, axis=1, keepdims=True)
    norms = np.where(norms < 1e-12, 1.0, norms)
    return (centered / norms).astype(np.float32, copy=False)


def load_or_compute_centroid(
    vectors: np.ndarray,
    snapshot_hash: str,
    *,
    centroid_path: Path | None = None,
    meta_path: Path | None = None,
) -> np.ndarray | None:
    """Return the cached centroid if it matches ``snapshot_hash``, else
    recompute from ``vectors``, persist, and return it.

    Returns ``None`` when N < 2. All disk I/O is best-effort: a failed read
    recomputes; a failed write just means the next query recomputes again.
    The cache lives as a sibling of the store files.

    Path args default to the module-level ``CENTROID_PATH`` /
    ``CENTROID_META_PATH`` resolved AT CALL TIME (not def time) so tests can
    monkeypatch those globals to a tmp dir.
    """
    if centroid_path is None:
        centroid_path = CENTROID_PATH
    if meta_path is None:
        meta_path = CENTROID_META_PATH
    # Fast path: cached centroid for this exact snapshot.
    try:
        if centroid_path.exists() and meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            if meta.get("snapshot_hash") == snapshot_hash:
                arr = np.load(centroid_path, allow_pickle=False)
                if arr.dtype == np.float32 and arr.shape == (EMBEDDING_DIM,):
                    return arr
    except Exception as e:  # corrupt / partial cache → recompute
        logger.debug("centroid cache read failed (%s) — recomputing", e)

    centroid = compute_centroid(vectors)
    if centroid is None:
        return None

    try:
        centroid_path.parent.mkdir(parents=True, exist_ok=True)
        # Atomic-ish: write tmp then replace so a concurrent reader never
        # sees a half-written .npy.
        # np.save APPENDS .npy unless the name already ends in .npy, so use a
        # tmp name that already does (avoids a doubled ".tmp.npy" suffix that
        # would make the subsequent replace() target the wrong file).
        tmp = centroid_path.with_name(centroid_path.name + ".tmp.npy")
        np.save(tmp, centroid, allow_pickle=False)
        tmp.replace(centroid_path)
        meta_path.write_text(
            json.dumps({"snapshot_hash": snapshot_hash}), encoding="utf-8"
        )
    except Exception as e:  # cache write is optional
        logger.debug("centroid cache write failed (%s) — non-fatal", e)

    return centroid


__all__ = [
    "CENTROID_PATH",
    "CENTROID_META_PATH",
    "compute_centroid",
    "center_and_renorm",
    "load_or_compute_centroid",
]
