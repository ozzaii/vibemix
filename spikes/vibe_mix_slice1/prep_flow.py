# SPDX-License-Identifier: Apache-2.0
"""End-to-end prep flow — stitches the brief's steps into one pipeline.

    NL query
      -> cheap vibe filter        (search_fn; the shipped vibe_search)
      -> 3-track calibration       (calibrate; Slice 1)
      -> DJ picks the closest      (pick_fn)
      -> focused re-extraction     (rank the pool by similarity to the pick —
                                    the "expensive pass on the curated subset")
      -> narrative arc ordering    (arc_order; Slice 2)
      -> ordered set

Every external capability is injected, so the whole flow is exercisable offline
without the Gemini proxy or a real library. In production, ``search_fn`` is
``vibemix.library.search.vibe_search``, ``vector_of`` reads ``embeddings.db``,
and ``meta_of`` reads ``TrackEntry`` energy/key — but the orchestration shape
is proven here independent of those.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence

import numpy as np

from vibemix.library._cosine import l2_normalize

from spikes.vibe_mix_slice1.calibration import calibrate
from spikes.vibe_mix_slice2.arc import Track, arc_order


def prep_set(
    query: str,
    *,
    search_fn: Callable[[str], Sequence[str]],
    vector_of: Callable[[str], np.ndarray],
    meta_of: Callable[[str], tuple[float, str | None]],
    pick_fn: Callable[[list[str]], str],
    set_size: int = 8,
) -> list[Track]:
    """Run the prep pipeline; return the arc-ordered set (<= ``set_size``)."""
    candidates = list(search_fn(query))
    if not candidates:
        return []

    pool = [(tid, vector_of(tid)) for tid in candidates]

    # Calibration: surface 3 distinct anchors; the DJ picks the closest.
    anchors = calibrate(pool, k=3)
    chosen = pick_fn(anchors)

    # Focused re-extraction: rank the curated pool by similarity to the pick
    # (the expensive pass, run only on the subset) and keep the strongest.
    anchor_vec = l2_normalize(np.asarray(vector_of(chosen), dtype=np.float32))
    scored = sorted(
        candidates,
        key=lambda tid: (
            -float(l2_normalize(np.asarray(vector_of(tid), dtype=np.float32)) @ anchor_vec),
            tid,
        ),
    )
    subset = scored[:set_size]
    if chosen not in subset:                 # the pick is always kept
        subset = [chosen] + subset[: set_size - 1]

    # Narrative arc ordering over the curated subset.
    tracks = []
    for tid in subset:
        energy, camelot = meta_of(tid)
        tracks.append(Track(id=tid, energy=energy, camelot=camelot))
    return arc_order(tracks)
