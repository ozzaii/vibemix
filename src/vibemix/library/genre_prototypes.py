# SPDX-License-Identifier: Apache-2.0
"""PERCEIVE-03 — mean-centered nearest-prototype genre lookup (MECHANISM only).

Replaces the coarse 3-band DSP genre proxy with the embedding-driven genre the
Phase-78 research validated (86.5% folder-proxy agreement), at **€0**: it ranks
a track's ALREADY-CACHED library embedding against one centered-mean prototype
vector per folder-label. No live embed, no Gemini client, no API key on any
path here.

This module is the pure mechanism + a thread-safe holder. It NEVER writes the
live state dataclass (invariant #1, single-writer). It returns values / fills a
``GenrePrototypeLookup`` holder that the single-writer refresh loop reads — the
refresh wiring is Plan 04's job, not this module's.

Composition contract (RESEARCH Pitfall 2 — centroid divergence = garbage
cosine): all centroid / normalize / cosine math is DELEGATED, never re-rolled:

    - corpus centroid + centering  → ``library.centering`` (the anisotropy fix)
    - nearest-prototype top-K      → ``library._cosine.cosine_topk`` (P55 parity)
    - genre proxy = parent folder  → ``library.rekordbox`` (TrackEntry.filepath)

BOTH prototype-build and classify center with the SAME corpus centroid, so the
cosine lives in one consistent space.

Anti-slop abstain (invariant #2/#3): ``classify`` returns ``("unknown", conf)``
below a cosine floor OR within a tie-margin — it never asserts a low-confidence
genre. The floor/margin here are CENTERED-cosine-scale params (separation in
centered space sits far below the DSP 0.55 scale); reconciling this raw centered
cosine into coach.py's ``>= 0.5`` render band is Plan 04's job, not this module's.

Persistence mirrors ``centering.CENTROID_PATH``: a snapshot-hash-keyed
``genre_prototypes.npy`` + ``.meta.json`` sidecar, atomic tmp→replace,
best-effort. It auto-rebuilds when ``library.db`` changes. All paths resolve AT
CALL TIME so tests can monkeypatch them to a tmp dir (the ``library.pkl`` gotcha).
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
from pathlib import Path

import numpy as np

from vibemix.library._cosine import EMBEDDING_DIM, cosine_topk, l2_normalize
from vibemix.library.centering import center_and_renorm, load_or_compute_centroid
from vibemix.library.rekordbox import RekordboxLibrary
from vibemix.library.store import open_store

logger = logging.getLogger(__name__)

# Centered-cosine-scale floor + tie-margin (NOT the DSP 0.55 scale — separation
# in centered space is far tighter). Below floor OR within margin → abstain.
# RESEARCH Pattern 3: floor≈0.25, margin≈0.05. NOTE: the >=0.5 render-gate
# reconciliation (coach.py:334) is Plan 04's concern; this module returns the
# RAW centered cosine.
PROTO_FLOOR: float = 0.25
PROTO_MARGIN: float = 0.05

# Snapshot-hash-keyed sidecar, sibling of library_centroid.npy. Resolved at call
# time (module global) so tests monkeypatch these to tmp_path.
PROTOTYPES_PATH = Path.home() / ".cache" / "vibemix" / "genre_prototypes.npy"
PROTOTYPES_META_PATH = (
    Path.home() / ".cache" / "vibemix" / "genre_prototypes.meta.json"
)


def _label_of_from_library(
    ids: list[str], lib: RekordboxLibrary | None = None
) -> dict[str, str]:
    """Genre proxy: ``label = Path(TrackEntry.filepath).parent.name`` per id.

    Loads the Rekordbox cache once and looks up each id; an id absent from the
    library (or a missing entry) maps to ``"unknown"``. Best-effort: a failed
    cache load just yields all-``"unknown"`` labels.
    """
    if lib is None:
        lib = RekordboxLibrary()
        try:
            lib.try_load_cache()
        except Exception as e:  # cache load is best-effort
            logger.debug("rekordbox cache load failed (%s) — labels unknown", e)
    out: dict[str, str] = {}
    for tid in ids:
        te = lib.lookup_by_id(tid)
        out[tid] = Path(te.filepath).parent.name if te else "unknown"
    return out


def build_prototypes(
    vectors: np.ndarray,
    ids: list[str],
    label_of: dict[str, str],
    *,
    snapshot_hash: str | None = None,
) -> tuple[np.ndarray, list[str]]:
    """Build one CENTERED-mean prototype vector per distinct label.

    ``vectors`` is the ``(N, EMBEDDING_DIM)`` float32 corpus (cached library
    vectors); ``ids`` matches it row-wise; ``label_of`` maps each id to its
    folder-proxy genre. The centroid is derived via
    ``load_or_compute_centroid`` (the SAME chokepoint the ranking path uses —
    Pitfall 2), vectors are centered with it, then rows are grouped by label
    and each group's mean is L2-normalized into a prototype.

    Returns ``(protos, labels)`` with ``protos`` shape ``(n_labels,
    EMBEDDING_DIM)`` float32 (one row per distinct label, sorted) and
    ``labels`` the matching label list. Degenerate corpus (N<2 → centroid
    ``None``) returns ``(np.empty((0, EMBEDDING_DIM), float32), [])`` — no crash.

    Injectable corpus + label_of so the synthetic test drives it disk-free.
    """
    vectors = np.asarray(vectors, dtype=np.float32)
    if snapshot_hash is None:
        # Content-derived key when the caller has no store snapshot (tests):
        # stable across identical corpora, changes when vectors change.
        snapshot_hash = hashlib.sha256(vectors.tobytes()).hexdigest()[:16]

    centroid = load_or_compute_centroid(vectors, snapshot_hash)
    if centroid is None:  # N<2 — no discriminative centroid
        return (np.empty((0, EMBEDDING_DIM), dtype=np.float32), [])

    centered = center_and_renorm(vectors, centroid)  # (N, D)

    # WR-04 — EXCLUDE the "unknown" folder-proxy sentinel from the prototype
    # table. Any track absent from the Rekordbox cache maps to "unknown"; if it
    # became a real centered-mean prototype row it would compete in classify's
    # cosine_topk(k=2): it could be the runner-up and shrink the
    # `best_sim - second_sim` gap below PROTO_MARGIN, forcing a correct genre into
    # abstain — or itself win as best_label="unknown" at high cosine. Abstain is
    # decided by the floor / tie-margin, NOT by a junk "unknown" cluster winning.
    labels = sorted({label_of.get(tid, "unknown") for tid in ids} - {"unknown"})
    if not labels:  # all-"unknown" corpus → empty table → ("unknown", 0.0) abstain
        return (np.empty((0, EMBEDDING_DIM), dtype=np.float32), [])
    protos: list[np.ndarray] = []
    for label in labels:
        rows = centered[[i for i, tid in enumerate(ids) if label_of.get(tid, "unknown") == label]]
        # l2_normalize the group mean = the prototype direction in centered space.
        protos.append(l2_normalize(rows.mean(axis=0).astype(np.float32)))
    return (np.stack(protos).astype(np.float32), labels)


def classify(
    track_embedding: np.ndarray,
    protos: np.ndarray,
    labels: list[str],
    centroid: np.ndarray,
    *,
    floor: float = PROTO_FLOOR,
    margin: float = PROTO_MARGIN,
) -> tuple[str, float]:
    """Nearest-prototype genre for a track embedding, with anti-slop abstain.

    Centers ``track_embedding`` with the SAME ``centroid`` the prototypes were
    built with (Pitfall 2), ranks against ``protos`` via ``cosine_topk``, and
    returns ``(best_label, best_sim)`` only when ``best_sim >= floor`` AND the
    nearest-vs-runner-up gap ``>= margin``. Otherwise → ``("unknown", conf)``
    (below floor OR within tie-margin — the abstain). Empty prototype table →
    ``("unknown", 0.0)``.
    """
    if protos.shape[0] == 0:
        return ("unknown", 0.0)

    q = center_and_renorm(np.asarray(track_embedding, dtype=np.float32), centroid)
    ranked = cosine_topk(q, protos.astype(np.float32), labels, k=2)
    if not ranked:
        return ("unknown", 0.0)

    best_label, best_sim = ranked[0]
    second_sim = ranked[1][1] if len(ranked) >= 2 else -1.0

    if best_sim < floor or (best_sim - second_sim) < margin:
        return ("unknown", float(max(0.0, best_sim)))
    return (best_label, float(best_sim))


def _persist_prototypes(
    protos: np.ndarray, labels: list[str], snapshot_hash: str
) -> None:
    """Best-effort snapshot-hash-keyed sidecar write (mirrors centering)."""
    path = PROTOTYPES_PATH
    meta = PROTOTYPES_META_PATH
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp.npy")
        np.save(tmp, protos, allow_pickle=False)
        tmp.replace(path)
        meta.write_text(
            json.dumps({"snapshot_hash": snapshot_hash, "labels": labels}),
            encoding="utf-8",
        )
    except Exception as e:  # cache write is optional
        logger.debug("prototype cache write failed (%s) — non-fatal", e)


def _load_cached_prototypes(
    snapshot_hash: str,
) -> tuple[np.ndarray, list[str]] | None:
    """Return cached ``(protos, labels)`` if the sidecar matches ``snapshot_hash``."""
    path = PROTOTYPES_PATH
    meta = PROTOTYPES_META_PATH
    try:
        if path.exists() and meta.exists():
            m = json.loads(meta.read_text(encoding="utf-8"))
            if m.get("snapshot_hash") == snapshot_hash:
                arr = np.load(path, allow_pickle=False)
                if arr.dtype == np.float32 and arr.ndim == 2 and arr.shape[1] == EMBEDDING_DIM:
                    return (arr, list(m.get("labels", [])))
    except Exception as e:  # corrupt / partial cache → rebuild
        logger.debug("prototype cache read failed (%s) — rebuilding", e)
    return None


def load_or_build_prototypes(store) -> tuple[np.ndarray, list[str], np.ndarray | None]:
    """Lazy snapshot-hash-keyed prototype table from the cached library vectors.

    Returns ``(protos, labels, centroid)``. When the snapshot-hash sidecar
    matches, returns the cached prototypes (recomputing only the centroid, which
    is cheap and itself cached by ``centering``); otherwise rebuilds from
    ``store._backend.load_all()`` and persists. €0 — uses only cached vectors.
    A degenerate corpus yields an empty table + ``None`` centroid.
    """
    ids, vectors = store._backend.load_all()
    vectors = np.asarray(vectors, dtype=np.float32)
    snap = store.snapshot_hash()
    centroid = load_or_compute_centroid(vectors, snap)

    cached = _load_cached_prototypes(snap)
    if cached is not None:
        protos, labels = cached
        return (protos, labels, centroid)

    label_of = _label_of_from_library(ids)
    protos, labels = build_prototypes(vectors, ids, label_of, snapshot_hash=snap)
    _persist_prototypes(protos, labels, snap)
    return (protos, labels, centroid)


class GenrePrototypeLookup:
    """Thread-safe holder for the off-loop genre lookup (mirrors ``Grounding``).

    The off-loop worker (``classify_playing`` on TRACK_CHANGE) classifies the
    PLAYING track's CACHED library embedding and stores the result under a lock.
    A per-dispatch generation token (``_inflight_gen``, bumped in ``clear()``)
    discards a stale write if the dispatch was superseded — the same
    anti-second-writer seam as ``Grounding`` (Phase 77 CR-01).

    **Anti-second-writer (Pitfall 1):** this holder is the ONLY place the genre
    result lives off-loop. ``refresh._tick_once`` READS ``get_latest()`` and is
    the single writer of the live state dataclass — this class NEVER touches it.
    Wiring that read is Plan 04.
    """

    def __init__(self, store=None) -> None:
        self._store = store  # lazily opened on first use if None
        self._lock = threading.Lock()
        self._latest: tuple[str, float] | None = None
        self._inflight_gen: int = 0
        # Lazy-built prototype table + matching centroid (snapshot-hash-keyed).
        self._protos: np.ndarray | None = None
        self._labels: list[str] = []
        self._centroid: np.ndarray | None = None
        # WR-02 — memoized corpus for the per-track embedding lookup. The whole
        # (N, EMBEDDING_DIM) vector array + an id->row-index map, loaded ONCE per
        # instance. Without this, `_cached_embedding` called `load_all()` (the
        # full ~9 MB corpus) on EVERY `get_track_features` call — so curating N
        # tracks re-loaded + re-scanned the corpus N times. The prototype-table
        # memoization only covers the prototypes, not this lookup.
        self._corpus_vectors: np.ndarray | None = None
        self._corpus_index: dict[str, int] | None = None

    def _ensure_store(self):
        # WR-02 — double-checked lock. Each TRACK_CHANGE spawns a fresh daemon
        # worker with no in-flight guard, so two workers can race here; an
        # unguarded `self._store = open_store()` could open the store twice (and
        # a future reader could observe a half-published handle). The cheap
        # outside-lock fast path keeps the steady-state hot path lock-free.
        if self._store is not None:
            return self._store
        store = open_store()
        with self._lock:
            if self._store is None:
                self._store = store
        return self._store

    def _ensure_prototypes(self) -> None:
        """Lazy-build the prototype table on first use (cached, snapshot-keyed).

        WR-02 — the tuple assign `self._protos, self._labels, self._centroid =
        ...` is THREE separate attribute stores; two concurrent off-loop workers
        could otherwise interleave them so a reader observes `_protos` set while
        `_centroid` is still None (or a `_protos`/`_centroid` pair from different
        builds). Build outside the lock (the expensive part), then publish the
        three fields atomically under the holder's existing lock with a
        double-check so only one build wins and no torn multi-store is visible.
        """
        if self._protos is not None:
            return
        store = self._ensure_store()
        protos, labels, centroid = load_or_build_prototypes(store)
        with self._lock:
            if self._protos is None:
                self._protos, self._labels, self._centroid = protos, labels, centroid

    def _ensure_corpus(self) -> None:
        """Load the cached corpus ONCE per instance (WR-02).

        Materializes ``(ids, vectors)`` from ``load_all()`` a single time and
        builds an ``id -> row index`` dict so per-track lookups are O(1) instead
        of a fresh full-corpus load + linear ``ids.index`` scan per call. Mirrors
        ``_ensure_prototypes``: build outside the lock (the expensive ~9 MB load),
        then publish the two fields atomically under the holder's lock with a
        double-check so concurrent off-loop workers do at most one load that
        wins and a reader never sees a torn vectors/index pair. Serialized
        dispatch (the curator path) hits this lock-free after the first call.
        """
        if self._corpus_index is not None:
            return
        store = self._ensure_store()
        ids, vectors = store._backend.load_all()
        vectors = np.asarray(vectors, dtype=np.float32)
        index = {tid: i for i, tid in enumerate(ids)}
        with self._lock:
            if self._corpus_index is None:
                self._corpus_vectors, self._corpus_index = vectors, index

    def _cached_embedding(self, track_id: str) -> np.ndarray | None:
        """Fetch the track's CACHED library embedding by id (€0 — no live embed).

        WR-02 — reads from the per-instance memoized corpus (loaded once via
        ``_ensure_corpus``), so this is an O(1) dict lookup, not a per-call
        ``load_all()`` of the whole ~9 MB vector array.
        """
        self._ensure_corpus()
        assert self._corpus_index is not None and self._corpus_vectors is not None
        idx = self._corpus_index.get(track_id)
        if idx is None:
            return None
        return np.asarray(self._corpus_vectors[idx], dtype=np.float32)

    def classify_playing(self, track_id: str) -> tuple[str, float]:
        """Off-loop worker entry: classify the playing track from cached vectors.

        Returns ``("unknown", 0.0)`` WITHOUT any live embed when the track is
        not in the library (the abstain-safe path, RESEARCH A1) or the prototype
        table is degenerate. Latches the result into the holder only if this
        dispatch was not superseded by a ``clear()`` (generation token).
        """
        with self._lock:
            self._inflight_gen += 1
            my_gen = self._inflight_gen

        self._ensure_prototypes()
        if self._protos is None or self._protos.shape[0] == 0 or self._centroid is None:
            return ("unknown", 0.0)

        emb = self._cached_embedding(track_id)
        if emb is None:  # unknown-to-library track → abstain, NO live embed (A1)
            return ("unknown", 0.0)

        result = classify(emb, self._protos, self._labels, self._centroid)

        with self._lock:
            # Discard a stale write if clear() ran during the (off-loop) work.
            if my_gen == self._inflight_gen:
                self._latest = result
        return result

    def get_latest(self) -> tuple[str, float] | None:
        """Lock-guarded snapshot — the single-writer refresh loop reads THIS."""
        with self._lock:
            return self._latest

    def clear(self) -> None:
        """Drop the latest result + bump the generation token (discards an
        in-flight write that has now been superseded)."""
        with self._lock:
            self._inflight_gen += 1
            self._latest = None


__all__ = [
    "build_prototypes",
    "classify",
    "load_or_build_prototypes",
    "GenrePrototypeLookup",
    "PROTO_FLOOR",
    "PROTO_MARGIN",
    "PROTOTYPES_PATH",
    "PROTOTYPES_META_PATH",
]
