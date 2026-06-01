# SPDX-License-Identifier: Apache-2.0
"""Phase 28 Plan 05 — USER-ASKED similar-track lookup.

ANTI-FEATURE GUARD (CONTEXT LIBRARY-14, memory `feedback_no_scope_creep`):
This module NEVER autosurfaces suggestions. Every entrypoint is gated
behind explicit user action — either the ``vibemix library similar
<track_id>`` CLI command or the library window's ``library_similar`` Tauri
command in response to a user click.

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
from vibemix.library.embed_types import TrackEmbedder
from vibemix.library.rekordbox import RekordboxLibrary
from vibemix.library.store import LibraryStore
from vibemix.library.track_relation import compute_relation

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SimilarResult:
    """A single similar-track match.

    One Mind S6 — the ``camelot`` / ``harmonic_compatible`` / ``bpm_delta``
    fields are additive enrichment from the unified ``track_relation`` engine.
    Ranking is UNCHANGED (still centered cosine); these surface the
    harmonic + tempo relation that this module previously ignored. They are
    honest-null: ``harmonic_compatible`` is ``None`` when either key is unknown
    (an unknown key must never read as "incompatible"). Defaults keep every
    existing 5-field construction site byte-compatible.
    """

    track_id: str
    similarity: float
    title: str
    artist: str
    bpm: float | None
    camelot: str | None = None
    harmonic_compatible: bool | None = None
    bpm_delta: float | None = None  # signed dst-src; None when either bpm unknown

    def to_dict(self) -> dict:
        return asdict(self)


def similar_to(
    embedder: TrackEmbedder,
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
    # RekordboxLibrary.tracks is canonically a dict {track_id: TrackEntry};
    # tolerate a bare list too.
    raw = library.tracks
    tracks = list(raw.values()) if isinstance(raw, dict) else list(raw)
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

    # k+1 so we can drop the seed from results. Mean-centered ranking (the
    # anisotropy fix) is the DEFAULT — the store centers the seed + every
    # candidate with the corpus centroid before cosine_topk, and falls back
    # to raw cosine for N < 2 (no centroid). This is what gives each seed a
    # distinct neighbour set instead of "everything ~0.92 similar".
    topk = store.search_centered(qvec, k=k + 1)
    seed_bpm = seed.bpm if (seed.bpm and seed.bpm > 0) else None
    seed_camelot = getattr(seed, "camelot", None)
    out: list[SimilarResult] = []
    for tid, sim in topk:
        if tid == seed_track_id:
            continue
        t = index.get(tid)
        if t is None:
            continue
        cand_bpm = t.bpm if (t.bpm and t.bpm > 0) else None
        cand_camelot = getattr(t, "camelot", None)
        # S6 — enrich with the unified harmonic + tempo relation (ranking
        # stays centered-cosine; this only surfaces dimensions we ignored).
        rel = compute_relation(
            src_track_id=seed_track_id,
            dst_track_id=tid,
            cosine=float(sim),
            src_camelot=seed_camelot,
            dst_camelot=cand_camelot,
            src_bpm=seed_bpm,
            dst_bpm=cand_bpm,
        )
        out.append(
            SimilarResult(
                track_id=tid,
                similarity=round(float(sim), 4),
                title=t.title,
                artist=t.artist,
                bpm=cand_bpm,
                camelot=cand_camelot,
                # Honest-null: only assert (in)compatibility when BOTH keys known.
                harmonic_compatible=(
                    rel.harmonic_compatible
                    if (seed_camelot and cand_camelot)
                    else None
                ),
                bpm_delta=rel.bpm_delta_signed,
            )
        )
        if len(out) >= k:
            break
    return out


__all__ = ["SimilarResult", "similar_to"]
