# SPDX-License-Identifier: Apache-2.0
"""Shared cosine top-K primitives for the Phase 28 library subsystem.

This module is the SINGLE source of math used by BOTH storage backends in
Plan 28-02 (``index_sqlite_vec.py`` and ``index_numpy.py``). Centralising
the math here is the Pitfall P55 (Mac/Win parity) mitigation — Mac runs
sqlite-vec, Windows falls back to numpy, but both backends call the
identical ``cosine_topk()`` to produce bit-identical top-K rank orders
across platforms.

References:
    RESEARCH Pattern 2 — "Storage-only sqlite-vec, math in Python".
    Pitfall P55 — "vec_distance_cosine + np.argpartition produce different
    rank orders for tied similarity values".

We INTENTIONALLY do NOT use sqlite-vec's internal ``vec_distance_cosine``
in v1 — vec0 is treated as a storage-only layer. All ranking happens here
on int16-quantised-back-to-float32 vectors loaded from the backend.

Determinism rules locked here:
    1. Inputs MUST be ``np.float32``; assertion-fails otherwise.
    2. Top-K selection via ``np.argpartition`` (O(N), unstable order).
    3. Final sort: primary DESC by similarity, secondary ASC by track_id.
       Python's Timsort is deterministic + cross-platform stable.
    4. Returned similarities are converted to ``float`` (Python builtin)
       so JSON-serialisation is exact-byte-stable on both platforms.
"""

from __future__ import annotations

import numpy as np

# Locked at 768 per CONTEXT D-cost-balanced and RESEARCH Open Q9.
# Gemini Embedding 2 supports MRL truncation to 768/1536/3072; we ship 768.
# Bumping this constant requires a cache invalidation (EXCERPT_STRATEGY_VERSION).
#
# Plan 41-05 rollback note (LAT-06):
#     If production telemetry surfaces top-K parity drift between v1
#     (full-precision 3072) and v2 (768-truncated) — e.g. citation
#     quality regresses or "what's playing" grounding hallucinates more
#     than the v2.1 baseline — the documented rollback path is:
#         1. Bump EMBEDDING_DIM 768 → 1024.
#         2. Bump embed.EXCERPT_STRATEGY_VERSION (so cache invalidates).
#         3. Re-run tests/library/test_embeddings_parity.py with the
#            new dim — recall threshold of >=9/10 positions identical
#            for >=8/10 queries must still pass.
#         4. Run scripts/library/migrate_embeddings_2.py --re-embed-all
#            against affected user libraries (or rely on lazy first-launch
#            re-embed once the version bump ships).
#     Storage impact: ~33% larger index per row (768 → 1024 = +33%).
EMBEDDING_DIM = 768


def l2_normalize(vec: np.ndarray) -> np.ndarray:
    """L2-normalize a float32 vector. Returns float32.

    Inputs:
        vec: shape (D,), dtype float32.

    Output:
        Unit-length float32 vector. If input norm is < 1e-12, returns input
        unchanged (avoids divide-by-zero on accidental zero vectors).
    """
    assert vec.dtype == np.float32, (
        f"l2_normalize requires float32 input, got {vec.dtype} "
        "(Mac/Win parity contract — see Pitfall P55)"
    )
    norm = float(np.linalg.norm(vec))
    if norm < 1e-12:
        return vec.astype(np.float32, copy=False)
    return (vec / norm).astype(np.float32, copy=False)


def cosine_topk(
    query: np.ndarray,
    vectors: np.ndarray,
    track_ids: list[str],
    k: int = 10,
) -> list[tuple[str, float]]:
    """Top-K cosine similarity over pre-L2-normalized vectors.

    Both ``query`` and ``vectors`` MUST already be L2-normalized — this
    function is hot-path and skips re-normalization. Use ``l2_normalize``
    upstream when persisting embeddings.

    Inputs:
        query: shape (D,), float32, L2-normalized.
        vectors: shape (N, D), float32, each row L2-normalized.
        track_ids: list of N track id strings, matched row-wise with
            ``vectors``.
        k: number of top results to return. Clamped to N if k > N.

    Output:
        List of ``(track_id, similarity)`` tuples, length ``min(k, N)``,
        sorted primary DESC by similarity, secondary ASC by track_id.

    Determinism contract:
        - Two identical similarities resolve by track_id ASC (Timsort,
          stable across CPython 3.11+, Mac arm64 and Win x86_64).
        - Similarities are cast to Python ``float`` so JSON serialisation
          is bit-stable.

    Empty / small N:
        - N == 0 returns ``[]``.
        - N <= k returns all rows in the determinism-locked order.
    """
    assert query.dtype == np.float32, (
        f"cosine_topk query must be float32, got {query.dtype}"
    )
    assert vectors.dtype == np.float32, (
        f"cosine_topk vectors must be float32, got {vectors.dtype}"
    )

    n = vectors.shape[0]
    if n == 0:
        return []

    assert query.shape == (EMBEDDING_DIM,), (
        f"cosine_topk query must be shape ({EMBEDDING_DIM},), "
        f"got {query.shape}"
    )
    assert vectors.shape[1] == EMBEDDING_DIM, (
        f"cosine_topk vectors must be shape (N, {EMBEDDING_DIM}), "
        f"got {vectors.shape}"
    )
    assert len(track_ids) == n, (
        f"cosine_topk track_ids length ({len(track_ids)}) must equal "
        f"vectors row count ({n})"
    )

    # Pre-normalized vectors → dot product == cosine similarity.
    sims = vectors @ query  # shape (N,), float32

    if n <= k:
        top_idx = np.arange(n)
    else:
        # argpartition is O(N) but the top-K block is in unspecified order;
        # final sort below restores determinism.
        top_idx = np.argpartition(-sims, k)[:k]

    pairs = [(track_ids[int(i)], float(sims[int(i)])) for i in top_idx]
    # Primary DESC by similarity, secondary ASC by track_id.
    pairs.sort(key=lambda p: (-p[1], p[0]))
    return pairs[:k]
