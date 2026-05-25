# SPDX-License-Identifier: Apache-2.0
"""next_suggestion — the pill "what's next" engine.

Given the vector of the track playing now, rank the user's OWN library by
mean-centered cosine similarity and return ONE grounded next-track suggestion
("play a similar track, don't jump the vibe A→C"). The pill surfaces it.

This is the embedding-only Phase 1 of the Pill Advancer (design:
``.planning/research/viber-direction-2026-05-25/pill-next-suggestion.md``):

* **Seed is a stored VECTOR, not a track_id.** The now-playing track is already
  identified and its 1536-dim vector already lives in ``library.db`` (folder-
  ingest / Rekordbox import embedded it). We read it back — zero API cost, zero
  latency in steady state — instead of re-embedding like ``similar_to`` does.
* **Grounding (Cardinal Invariant #2).** Only track_ids present in BOTH the
  store and the live library can be suggested; every candidate is resolved via
  ``library.lookup_by_id`` and skipped if absent (store/library skew). The pill
  can never show an invented track — honest silence (``None``) when nothing
  qualifies.
* **Mean-centered ranking is the DEFAULT** (``store.search_centered``, the
  anisotropy fix) — the same path ``similar_to`` uses, so each seed gets a
  distinct neighbour set rather than "everything ~0.92 similar".
* **Harmonic / BPM refine is Phase 2** — a POST-filter on the embedding
  shortlist (embedding similarity stays the primary ranker). Candidates lacking
  key/BPM degrade gracefully (kept, never dropped for missing metadata). When
  no key/BPM is available at all (folder-only library) it is embedding-only and
  ``why = "similar vibe"``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

from vibemix.library._cosine import l2_normalize
from vibemix.library.rekordbox import RekordboxLibrary
from vibemix.library.store import LibraryStore
from vibemix.state import harmonics


@dataclass(frozen=True, slots=True)
class NextSuggestion:
    """One grounded next-track suggestion for the pill."""

    track_id: str
    title: str
    artist: str
    similarity: float  # mean-centered cosine, 4dp
    why: str  # short grounded reason, e.g. "similar vibe" / "similar vibe · 8A · 128"
    camelot: str | None  # None unless Rekordbox-resolved (honest-null)
    bpm: float | None  # None unless Rekordbox-resolved

    def to_dict(self) -> dict:
        return asdict(self)


def seed_vector_for_track_id(
    store: LibraryStore, track_id: str
) -> np.ndarray | None:
    """Read back the stored 1536-dim vector for ``track_id`` (the cached seed).

    Returns ``None`` if the id is not in the store. No embedding, no network —
    this is the steady-state ~free path (the now-playing track is already
    embedded).
    """
    ids, vectors = store._backend.load_all()
    try:
        idx = ids.index(track_id)
    except ValueError:
        return None
    if idx >= len(vectors):
        return None
    return np.asarray(vectors[idx], dtype=np.float32).copy()


def next_suggestion(
    store: LibraryStore,
    library: RekordboxLibrary,
    *,
    seed_vector: np.ndarray,
    seed_track_id: str | None,
    played_ids: set[str],
    seed_camelot: str | None = None,
    seed_bpm: float | None = None,
    k: int = 5,
    bpm_window: float = 15.0,
) -> NextSuggestion | None:
    """Rank the library by similarity to ``seed_vector`` → one next suggestion.

    Returns ``None`` (honest silence) when nothing qualifies — never a
    fabricated track.

    Phase 2 (``seed_camelot``/``seed_bpm`` provided) post-filters the embedding
    shortlist by Camelot compatibility + a BPM window; candidates missing
    key/BPM PASS the filter (degrade gracefully).
    """
    # Match similar_to's query path: normalize the seed before the centered
    # search (search_centered centers + renorms; the input must be L2-normed
    # so the centroid subtraction is meaningful).
    qvec = l2_normalize(np.asarray(seed_vector, dtype=np.float32))

    # Over-fetch so the seed + played + library-skew + harmonic drops still
    # leave at least one survivor.
    over = k + len(played_ids) + 8
    candidates = store.search_centered(qvec, k=over)

    refine = seed_camelot is not None or seed_bpm is not None
    for tid, sim in candidates:
        if tid == seed_track_id or tid in played_ids:
            continue
        entry = library.lookup_by_id(tid)
        if entry is None:  # store/library skew — skip ungrounded ids
            continue

        cand_camelot = harmonics.to_camelot(entry.key) if entry.key else None
        cand_bpm = entry.bpm if (entry.bpm and entry.bpm > 0) else None

        if refine:
            # Camelot: drop only when BOTH keys are known and incompatible.
            if (
                seed_camelot is not None
                and cand_camelot is not None
                and not harmonics.compatible(seed_camelot, cand_camelot)
            ):
                continue
            # BPM: drop only when BOTH are known and outside the window.
            if (
                seed_bpm is not None
                and cand_bpm is not None
                and abs(cand_bpm - seed_bpm) > bpm_window
            ):
                continue

        # Build the "why" honestly from what we actually resolved.
        bits = ["similar vibe"]
        if cand_camelot is not None:
            bits.append(cand_camelot)
        if cand_bpm is not None:
            bits.append(f"{cand_bpm:g}")
        why = " · ".join(bits)

        return NextSuggestion(
            track_id=tid,
            title=entry.title,
            artist=entry.artist,
            similarity=round(float(sim), 4),
            why=why,
            camelot=cand_camelot,
            bpm=cand_bpm,
        )
    return None


__all__ = ["NextSuggestion", "next_suggestion", "seed_vector_for_track_id"]
