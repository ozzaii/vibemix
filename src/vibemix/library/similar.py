# SPDX-License-Identifier: Apache-2.0
"""Phase 28 Plan 05 — USER-ASKED similar-track lookup.

ANTI-FEATURE GUARD (CONTEXT LIBRARY-14, memory `feedback_no_scope_creep`):
This module NEVER autosurfaces suggestions. Every entrypoint is gated
behind explicit user action — either the ``vibemix library similar
<track_id>`` CLI command or the ``ipc.library.similar_request`` IPC
message dispatched by the renderer in response to a user click.

The agent path MUST NOT call ``similar_to`` from any background loop or
event handler. The Phase 20 prompt linter rejects unsolicited "you might
also like..." style emissions; this module is the technical enforcement
of that product contract.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass

import numpy as np

from vibemix.library._cosine import EMBEDDING_DIM, l2_normalize
from vibemix.library.embed import LibraryEmbedder
from vibemix.library.rekordbox import RekordboxLibrary
from vibemix.library.store import LibraryStore

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SimilarResult:
    """A single similar-track match."""

    track_id: str
    similarity: float
    title: str
    artist: str
    bpm: float | None

    def to_dict(self) -> dict:
        return asdict(self)


def similar_to(
    embedder: LibraryEmbedder,
    store: LibraryStore,
    library: RekordboxLibrary,
    seed_track_id: str,
    k: int = 10,
) -> list[SimilarResult]:
    """Find tracks similar to ``seed_track_id``. USER-ASKED ONLY.

    Returns up to ``k`` matches sorted by similarity DESC. The seed track
    is excluded from results (we ask for k+1 matches and drop the seed if
    it appears at top with cosine ≈ 1.0).

    Empty library or unknown seed → returns ``[]``.
    """
    tracks = list(library.tracks)
    if not tracks:
        return []

    index = {t.track_id: t for t in tracks}
    seed = index.get(seed_track_id)
    if seed is None:
        logger.warning(
            "similar_to: seed track %r not in library", seed_track_id
        )
        return []

    # Embed the seed track via the existing pipeline.
    seed_vec = embedder.embed_track(seed)
    if seed_vec.shape != (EMBEDDING_DIM,):
        logger.error("similar_to: embedder returned bad shape %s", seed_vec.shape)
        return []
    qvec = l2_normalize(seed_vec.astype(np.float32, copy=False))

    # k+1 so we can drop the seed from results.
    topk = store.search(qvec, k=k + 1)
    out: list[SimilarResult] = []
    for tid, sim in topk:
        if tid == seed_track_id:
            continue
        t = index.get(tid)
        if t is None:
            continue
        out.append(
            SimilarResult(
                track_id=tid,
                similarity=round(float(sim), 4),
                title=t.title,
                artist=t.artist,
                bpm=t.bpm if (t.bpm and t.bpm > 0) else None,
            )
        )
        if len(out) >= k:
            break
    return out


__all__ = ["SimilarResult", "similar_to"]
