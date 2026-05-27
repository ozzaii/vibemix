# SPDX-License-Identifier: Apache-2.0
"""discovery — Mode A library-local candidate-pool builder.

Pure-compute, library-local pool building over the existing local vector
store. Given reference tracks (and/or a text vibe), produce a diverse,
hard-filtered candidate pool of the user's OWN library — never a fabricated
track.

Three composable primitives + one orchestrator:

* ``intent_centroid`` — fold reference vectors (+ optional text vector) into a
  single L2-normalized intent direction. Weighted mean of refs (front-loaded
  default weights), then an ``alpha`` blend toward the text vector. Honest
  failure (``ValueError``) when there is nothing to build from.
* ``hard_filter`` — drop candidates failing BPM / Camelot / duration / exclude
  gates. The Camelot gate mirrors ``next_suggestion``'s BOTH-KNOWN degrade
  (``state/harmonics.compatible``): a track is dropped ONLY when both its key
  and a ref key resolve AND no ref is harmonically compatible. Missing
  key/bpm/duration always PASS — we never punish absent metadata.
* ``mmr_rerank`` — Maximal Marginal Relevance: greedily pick the candidate that
  maximizes ``lambda_ * sim_to_intent - (1 - lambda_) * max_sim_to_selected``.
  Spreads near-duplicate clusters instead of returning k clones of the top hit.

Grounding (Cardinal Invariant #2 / #3): every surviving id must resolve in BOTH
the store and the live library; store/library skew ids are silently dropped, so
the pool can never surface an invented track.

Dim-agnostic: vectors flow through as-is (current product D is 512 CLAP; future
stores may choose another D). Historical Gemini stores remain backend-namespaced
and are not the active product path. Similarities use a dot product on
L2-normalized vectors (== cosine).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

from vibemix.library.rekordbox import RekordboxLibrary
from vibemix.library.store import LibraryStore
from vibemix.state import harmonics


@dataclass(frozen=True, slots=True)
class PoolItem:
    """One grounded candidate in a discovery pool. Honest-null metadata."""

    track_id: str
    title: str
    artist: str
    bpm: float | None  # None unless library-resolved (>0)
    camelot: str | None  # None unless library key normalized
    similarity: float  # store similarity to the intent centroid, 4dp

    def to_dict(self) -> dict:
        return asdict(self)


def _l2(vec: np.ndarray) -> np.ndarray:
    """L2-normalize, dim-agnostic. Returns float32. Zero-norm passthrough."""
    v = np.asarray(vec, dtype=np.float32)
    norm = float(np.linalg.norm(v))
    if norm < 1e-12:
        return v
    return (v / norm).astype(np.float32, copy=False)


def _default_weights(n: int) -> list[float]:
    """Front-loaded reference weights, e.g. [0.5, 0.3, 0.2, ...] normalized.

    The most recent / strongest reference dominates. We geometrically decay
    (each ref ~0.6x the prior) and normalize — robust for any ``n >= 1`` rather
    than a fixed-length literal list.
    """
    raw = [0.6**i for i in range(n)]
    total = sum(raw)
    return [w / total for w in raw]


def intent_centroid(
    ref_vectors: list[np.ndarray],
    weights: list[float] | None = None,
    text_vector: np.ndarray | None = None,
    alpha: float = 0.7,
) -> np.ndarray:
    """Fold reference vectors (+ optional text) into one L2-normalized intent.

    * ``ref_vectors`` empty + ``text_vector`` given → return normalized text.
    * ``ref_vectors`` empty + no text → ``ValueError`` (nothing to build from).
    * Otherwise: weighted mean of refs (default front-loaded weights), then if a
      text vector is given blend ``alpha * centroid + (1 - alpha) * text``.

    The result is always L2-normalized so downstream dot-products are cosine.
    """
    if not ref_vectors:
        if text_vector is None:
            raise ValueError(
                "intent_centroid needs at least one reference vector or a "
                "text vector — nothing to build an intent from."
            )
        out = _l2(text_vector)
        # WR-04: a zero / degenerate text vector cannot ground a direction.
        if float(np.linalg.norm(out)) < 1e-12:
            raise ValueError(
                "cannot build a grounded intent from a zero embedding"
            )
        return out

    refs = [np.asarray(v, dtype=np.float32) for v in ref_vectors]
    if weights is None:
        weights = _default_weights(len(refs))
    if len(weights) != len(refs):
        raise ValueError(
            f"weights length ({len(weights)}) must match ref_vectors "
            f"({len(refs)})"
        )
    w = np.asarray(weights, dtype=np.float32)
    w_sum = float(w.sum())
    if w_sum <= 0.0:
        raise ValueError("intent_centroid weights must sum to > 0")
    w = w / w_sum

    centroid = np.zeros_like(refs[0], dtype=np.float32)
    for vec, wt in zip(refs, w, strict=True):
        centroid = centroid + wt * vec
    centroid = _l2(centroid)

    if text_vector is not None:
        text = _l2(text_vector)
        centroid = _l2(alpha * centroid + (1.0 - alpha) * text)

    # WR-04: refuse a degenerate centroid (e.g. all-zero refs, or a blend that
    # exactly cancels) — an un-normalized/zero intent grounds nothing.
    if float(np.linalg.norm(centroid)) < 1e-12:
        raise ValueError("cannot build a grounded intent from a zero embedding")

    return centroid


def hard_filter(
    candidates: list[tuple[str, float]],
    *,
    library: RekordboxLibrary,
    bpm_min: float | None = None,
    bpm_max: float | None = None,
    ref_camelots: list[str] | None = None,
    min_duration_s: float | None = None,
    max_duration_s: float | None = None,
    exclude_ids: set[str] | None = None,
) -> list[tuple[str, float]]:
    """Drop candidates failing the discovery gates, preserving input order.

    Gates (a candidate must pass ALL to survive):

    * **Grounding** — must resolve in ``library`` (store/library skew dropped).
    * **Exclude** — not in ``exclude_ids``.
    * **BPM** — if the track's bpm is known (> 0) it must lie in
      ``[bpm_min, bpm_max]`` (either bound may be ``None`` = open). A missing
      bpm PASSES.
    * **Camelot** — BOTH-KNOWN degrade (mirrors ``next_suggestion``): dropped
      ONLY when the track's key resolves AND ``ref_camelots`` is non-empty with
      at least one resolvable ref AND the track is incompatible with EVERY
      resolvable ref. Missing track key, or no resolvable ref key, PASSES.
    * **Duration** — if known (> 0) must lie in
      ``[min_duration_s, max_duration_s]``; missing duration PASSES.
    """
    exclude = exclude_ids or set()
    # Pre-normalize ref keys once (drop any that don't resolve to Camelot).
    ref_cams: list[str] = []
    if ref_camelots:
        for raw in ref_camelots:
            c = harmonics.to_camelot(raw)
            if c is not None:
                ref_cams.append(c)

    out: list[tuple[str, float]] = []
    for tid, sim in candidates:
        if tid in exclude:
            continue
        entry = library.lookup_by_id(tid)
        if entry is None:  # store/library skew — ungrounded, skip
            continue

        cand_bpm = entry.bpm if (entry.bpm and entry.bpm > 0) else None
        if cand_bpm is not None:
            if bpm_min is not None and cand_bpm < bpm_min:
                continue
            if bpm_max is not None and cand_bpm > bpm_max:
                continue

        cand_dur = (
            entry.duration_s if (entry.duration_s and entry.duration_s > 0) else None
        )
        if cand_dur is not None:
            if min_duration_s is not None and cand_dur < min_duration_s:
                continue
            if max_duration_s is not None and cand_dur > max_duration_s:
                continue

        # Camelot both-known gate: only drop when both keys are known and NO ref
        # is compatible. Missing key (either side) → keep.
        cand_cam = harmonics.to_camelot(entry.key) if entry.key else None
        if cand_cam is not None and ref_cams:
            if not any(harmonics.compatible(rc, cand_cam) for rc in ref_cams):
                continue

        out.append((tid, sim))
    return out


def mmr_rerank(
    scored_candidates: list[tuple[str, float]],
    vectors_by_id: dict[str, np.ndarray],
    k: int = 50,
    lambda_: float = 0.7,
) -> list[str]:
    """Maximal Marginal Relevance rerank → up to ``k`` diverse track ids.

    Greedily selects the candidate maximizing
    ``lambda_ * sim_to_intent - (1 - lambda_) * max_sim_to_selected``.

    ``sim_to_intent`` is the provided score (store cosine to the centroid).
    Pairwise similarity uses a dot product on L2-normalized vectors (cosine).
    ``lambda_ = 1`` → pure relevance (score order); ``lambda_ = 0`` → pure
    diversity after the first pick. Candidates without a vector in
    ``vectors_by_id`` are treated as maximally distinct (0 sim to selected).
    """
    if not scored_candidates:
        return []

    # Pre-normalize candidate vectors once.
    norm_vecs: dict[str, np.ndarray] = {}
    for tid, _ in scored_candidates:
        v = vectors_by_id.get(tid)
        if v is not None:
            norm_vecs[tid] = _l2(v)

    score = {tid: float(s) for tid, s in scored_candidates}
    remaining = [tid for tid, _ in scored_candidates]
    selected: list[str] = []

    limit = min(k, len(remaining))
    while remaining and len(selected) < limit:
        best_tid: str | None = None
        best_val = float("-inf")
        for tid in remaining:
            if not selected:
                mmr = score[tid]
            else:
                cand_v = norm_vecs.get(tid)
                if cand_v is None:
                    max_sim = 0.0  # no vector → treat as maximally distinct
                else:
                    sims = [
                        float(cand_v @ norm_vecs[s])
                        for s in selected
                        if s in norm_vecs
                    ]
                    max_sim = max(sims) if sims else 0.0
                mmr = lambda_ * score[tid] - (1.0 - lambda_) * max_sim
            # Tie-break deterministically by id ASC to mirror cosine_topk.
            if mmr > best_val or (mmr == best_val and (best_tid is None or tid < best_tid)):
                best_val = mmr
                best_tid = tid
        assert best_tid is not None  # remaining non-empty
        selected.append(best_tid)
        remaining.remove(best_tid)

    return selected


def _seed_vector(store: LibraryStore, track_id: str) -> np.ndarray | None:
    """Read back a stored vector by id (dim-agnostic). None if absent."""
    ids, vectors = store._backend.load_all()
    try:
        idx = ids.index(track_id)
    except ValueError:
        return None
    if idx >= len(vectors):
        return None
    return np.asarray(vectors[idx], dtype=np.float32).copy()


def discover_pool(
    store: LibraryStore,
    library: RekordboxLibrary,
    embedder=None,
    *,
    ref_track_ids: list[str] | None = None,
    text_query: str | None = None,
    k: int = 50,
    bpm_min: float | None = None,
    bpm_max: float | None = None,
    min_duration_s: float | None = None,
    max_duration_s: float | None = None,
    exclude_ids: set[str] | None = None,
    lambda_: float = 0.7,
) -> list[PoolItem]:
    """Build a grounded, diverse candidate pool (Mode A — library-local).

    Pipeline: load ref vectors from the store → ``intent_centroid`` (text via
    ``embedder.embed_query`` when ``text_query`` is given) → over-fetch KNN via
    ``store.search_centered`` → ``hard_filter`` (BPM / Camelot vs ref keys /
    duration / exclude / grounding) → ``mmr_rerank`` for diversity → resolve
    metadata into ``PoolItem``s.

    ``embedder`` is OPTIONAL and only touched when ``text_query`` is set — so
    the ref-ids-only path runs offline with no API. Raises ``ValueError`` when
    neither refs nor a text query are supplied, or when a named ref id has no
    stored vector (cannot ground an intent on a missing seed).
    """
    ref_track_ids = ref_track_ids or []
    exclude = exclude_ids or set()

    # WR-05: load the whole store ONCE and index it id→vector. Previously
    # ``_seed_vector`` ran ``load_all()`` per ref AND per filtered candidate — on
    # a large library that is hundreds of full-store loads per discovery call and
    # a 30s dispatch-timeout risk. One load + a dict lookup is O(1) per id.
    all_ids, all_vectors = store._backend.load_all()
    vec_index: dict[str, np.ndarray] = {}
    for idx, tid in enumerate(all_ids):
        if idx < len(all_vectors):
            vec_index[tid] = np.asarray(all_vectors[idx], dtype=np.float32)

    # 1. Load reference vectors from the store (grounding: must exist on disk).
    ref_vectors: list[np.ndarray] = []
    for tid in ref_track_ids:
        v = vec_index.get(tid)
        if v is None:
            raise ValueError(
                f"ref_track_id {tid!r} has no stored vector — cannot build a "
                "grounded intent from a missing seed."
            )
        ref_vectors.append(v.copy())

    # 2. Optional text vector (lazy — only embeds when a query is given).
    text_vector: np.ndarray | None = None
    if text_query:
        if embedder is None:
            raise ValueError(
                "text_query supplied but no embedder — cannot embed text "
                "offline."
            )
        text_vector = np.asarray(
            embedder.embed_query(text_query), dtype=np.float32
        )

    if not ref_vectors and text_vector is None:
        raise ValueError(
            "discover_pool needs ref_track_ids and/or a text_query."
        )

    # 3. Intent centroid.
    centroid = intent_centroid(ref_vectors, text_vector=text_vector)

    # 4. Over-fetch KNN (filters + dedupe + diversity prune need slack).
    over = max(k * 4, k + len(exclude) + 16)
    knn = store.search_centered(centroid, k=over)

    # 5. Reference Camelot keys for the harmonic gate (from library metadata).
    ref_cams: list[str] = []
    for tid in ref_track_ids:
        entry = library.lookup_by_id(tid)
        if entry is not None and entry.key:
            ref_cams.append(entry.key)

    # Always exclude the reference tracks themselves from their own pool.
    exclude_all = set(exclude) | set(ref_track_ids)

    # 6. Hard filter (grounding + BPM/Camelot/duration/exclude).
    filtered = hard_filter(
        knn,
        library=library,
        bpm_min=bpm_min,
        bpm_max=bpm_max,
        ref_camelots=ref_cams or None,
        min_duration_s=min_duration_s,
        max_duration_s=max_duration_s,
        exclude_ids=exclude_all,
    )

    # 7. MMR diversity rerank. Reuse the single store load (WR-05) for the
    # per-candidate vectors instead of re-reading the store per candidate.
    vectors_by_id: dict[str, np.ndarray] = {}
    for tid, _ in filtered:
        v = vec_index.get(tid)
        if v is not None:
            vectors_by_id[tid] = v
    sim_by_id = {tid: sim for tid, sim in filtered}
    ranked_ids = mmr_rerank(filtered, vectors_by_id, k=k, lambda_=lambda_)

    # 8. Resolve metadata into grounded PoolItems (skip any late skew).
    pool: list[PoolItem] = []
    for tid in ranked_ids:
        entry = library.lookup_by_id(tid)
        if entry is None:
            continue
        cam = harmonics.to_camelot(entry.key) if entry.key else None
        bpm = entry.bpm if (entry.bpm and entry.bpm > 0) else None
        pool.append(
            PoolItem(
                track_id=tid,
                title=entry.title,
                artist=entry.artist,
                bpm=bpm,
                camelot=cam,
                similarity=round(float(sim_by_id.get(tid, 0.0)), 4),
            )
        )
    return pool


__all__ = [
    "PoolItem",
    "discover_pool",
    "hard_filter",
    "intent_centroid",
    "mmr_rerank",
]
