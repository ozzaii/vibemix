# SPDX-License-Identifier: Apache-2.0
"""3-track calibration: surface distinct anchors across a vibe-filtered pool.

The prep flow's calibration step. Given the embedding pool returned by the
cheap vibe-search pass (each track = one embedding vector), pick a small set of
candidates the DJ chooses between to pin their exact intent.

Algorithm — centroid-anchored farthest-first traversal (deterministic):

1. The first candidate is the pool *medoid* — the real track closest to the
   pool centroid. This is the "most typical" reading of the requested vibe.
2. Each subsequent candidate is the track whose similarity to its NEAREST
   already-chosen candidate is the LOWEST — i.e. the track that pulls hardest
   in a direction not yet represented.

This yields "one prototypical + the most contrasting alternatives", which is
exactly what a calibration question wants: a center to anchor on and distinct
poles to disambiguate intent. Deterministic given the input order (ties break
to the lowest pool index), so the same pool always offers the same choices.

Reuses ``vibemix.library._cosine.l2_normalize`` so the geometry matches the
shipping search/similar code exactly (Mac/Win parity, Pitfall P55).
"""
from __future__ import annotations

import numpy as np

from vibemix.library._cosine import l2_normalize


def calibrate(pool: list[tuple[str, np.ndarray]], k: int = 3) -> list[str]:
    """Return up to ``k`` track ids spread across the pool's vibe space.

    ``pool`` is ``[(track_id, vector), ...]``. Vectors may be any dimension
    (need not be 768) and need not be pre-normalized. If the pool has ``k`` or
    fewer tracks, every id is returned in input order.
    """
    if k <= 0:
        return []
    if len(pool) <= k:
        return [tid for tid, _ in pool]

    ids = [tid for tid, _ in pool]
    # The shipping l2_normalize enforces float32 (Mac/Win parity, Pitfall P55).
    mat = np.stack([l2_normalize(np.asarray(v, dtype=np.float32)) for _, v in pool])

    # Step 1: medoid — the real track closest to the (normalized) centroid.
    centroid = l2_normalize(mat.mean(axis=0).astype(np.float32))
    sims_to_centroid = mat @ centroid
    first = int(np.argmax(sims_to_centroid))
    chosen = [first]

    # Step 2..k: farthest-first. Track each candidate's similarity to its
    # nearest already-chosen anchor; pick the one with the lowest such value.
    nearest_sim = mat @ mat[first]  # sim of every track to the first anchor
    while len(chosen) < k:
        masked = nearest_sim.copy()
        masked[chosen] = np.inf  # never re-pick an anchor
        nxt = int(np.argmin(masked))
        chosen.append(nxt)
        # Update each track's nearest-anchor similarity with the new anchor.
        nearest_sim = np.maximum(nearest_sim, mat @ mat[nxt])

    return [ids[i] for i in chosen]
