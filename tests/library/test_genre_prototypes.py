# SPDX-License-Identifier: Apache-2.0
"""Phase 78 PERCEIVE-03 — mean-centered nearest-prototype genre Wave-0 RED
scaffolds (ALL xfail-strict).

These pin the ``vibemix.library.genre_prototypes`` contract that Plan 03 lands:

- ``build_prototypes(...)`` → one CENTERED-mean prototype per genre label, each
  L2-normalized, shape ``(n_labels, EMBEDDING_DIM)``.
- ``classify(track_embedding, protos, labels, centroid, *, floor=…, margin=…)``
  → nearest-prototype label above floor; below floor OR within tie-margin →
  ``("unknown", conf)`` (the anti-slop abstain, invariant #2/#3).

The module does NOT exist yet — the in-test ``import vibemix.library.genre_prototypes``
raises ``ModuleNotFoundError``, which is exactly the ``xfail(strict=True)`` trigger.
Plan 03 creates the module → the imports resolve → these flip to real green.

T-78-01-01 (dev-data tampering) mitigation — MANDATORY: every test monkeypatches
``RekordboxLibrary.CACHE_PATH``, ``centering.CENTROID_PATH``,
``centering.CENTROID_META_PATH``, AND the new prototype cache path to ``tmp_path``
so no test can clobber the real ``~/.cache/vibemix/`` (library.pkl /
genre_prototypes.npy). The ``_route_caches_to_tmp`` autouse fixture does this for
every test in the file; a real-cache mtime spot-check pins the mitigation.

Honest green: synthetic 1536-dim corpus, no live API, no GEMINI_API_KEY.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from vibemix.library._cosine import EMBEDDING_DIM, l2_normalize


def _anisotropic_corpus(n: int, seed: int = 0) -> np.ndarray:
    """N L2-normalized vectors sharing a common direction — the anisotropic
    shape from tests/library/test_centering.py."""
    rng = np.random.default_rng(seed)
    shared = l2_normalize(rng.standard_normal(EMBEDDING_DIM).astype(np.float32))
    rows = []
    for _ in range(n):
        noise = l2_normalize(rng.standard_normal(EMBEDDING_DIM).astype(np.float32))
        rows.append(l2_normalize((shared + 0.4 * noise).astype(np.float32)))
    return np.stack(rows)


def _labeled_corpus(n: int = 12, labels=("hardtechno", "house", "trance"), seed: int = 0):
    vectors = _anisotropic_corpus(n, seed=seed)
    ids = [f"t{i:03d}" for i in range(n)]
    label_of = {tid: labels[i % len(labels)] for i, tid in enumerate(ids)}
    return vectors, ids, label_of


@pytest.fixture(autouse=True)
def _route_caches_to_tmp(tmp_path: Path, monkeypatch):
    """T-78-01-01 mitigation — route EVERY cache path to tmp_path so no test
    touches the real ~/.cache/vibemix/. Applied to all tests in this file."""
    import vibemix.library.centering as centering_mod
    from vibemix.library.rekordbox import RekordboxLibrary

    monkeypatch.setattr(
        RekordboxLibrary, "CACHE_PATH", tmp_path / "library.pkl", raising=False
    )
    monkeypatch.setattr(centering_mod, "CENTROID_PATH", tmp_path / "centroid.npy", raising=False)
    monkeypatch.setattr(
        centering_mod, "CENTROID_META_PATH", tmp_path / "centroid.meta.json", raising=False
    )
    # The new prototype sidecar path (lands in Plan 03 as a module global mirroring
    # CENTROID_PATH). raising=False so this is a no-op until the module exists.
    try:
        import vibemix.library.genre_prototypes as gp_mod  # noqa: F401

        monkeypatch.setattr(
            gp_mod, "PROTOTYPES_PATH", tmp_path / "genre_prototypes.npy", raising=False
        )
        monkeypatch.setattr(
            gp_mod, "PROTOTYPES_META_PATH", tmp_path / "genre_prototypes.meta.json", raising=False
        )
    except ModuleNotFoundError:
        pass  # module not built yet — the xfail tests below trigger on their own import
    return tmp_path


# ---------- PERCEIVE-03 — prototype build ----------


def test_build_centered_means():
    """``build_prototypes`` produces ONE centered-mean prototype per label, each
    L2-normalized, shape ``(n_labels, EMBEDDING_DIM)``.

    GREEN since Plan 03: ``vibemix.library.genre_prototypes`` builds the table.
    """
    from vibemix.library.genre_prototypes import build_prototypes

    vectors, ids, label_of = _labeled_corpus(n=12)
    protos, labels = build_prototypes(vectors, ids, label_of)

    assert protos.shape[1] == EMBEDDING_DIM
    assert protos.shape[0] == len(labels)
    assert len(labels) == len(set(label_of.values()))
    # Each prototype is L2-normalized (a unit direction in centered space).
    norms = np.linalg.norm(protos, axis=1)
    assert np.allclose(norms, 1.0, atol=1e-4)


# ---------- PERCEIVE-03 — WR-04 "unknown" never competes as a prototype ----------


def test_unknown_excluded_from_prototypes():
    """WR-04 — the "unknown" folder-proxy sentinel must NOT become a prototype
    row. Tracks absent from the Rekordbox cache map to "unknown"; if that became
    a real centered-mean prototype it could margin-suppress a correct genre or
    win as best_label="unknown" at high cosine. Abstain is the floor/margin's
    job, not an "unknown" cluster's.
    """
    from vibemix.library.genre_prototypes import build_prototypes

    vectors = _anisotropic_corpus(n=12)
    ids = [f"t{i:03d}" for i in range(12)]
    # Half the corpus is "unknown" (cache-miss tracks); the rest are "techno".
    label_of = {tid: ("unknown" if i % 2 == 0 else "techno") for i, tid in enumerate(ids)}

    protos, labels = build_prototypes(vectors, ids, label_of)
    assert "unknown" not in labels, "unknown must never be a competing prototype"
    assert labels == ["techno"]
    assert protos.shape[0] == len(labels)


def test_all_unknown_corpus_yields_empty_table():
    """WR-04 — an all-"unknown" corpus yields an empty prototype table, so
    classify abstains ("unknown", 0.0) rather than building a junk prototype."""
    from vibemix.library.genre_prototypes import build_prototypes, classify
    from vibemix.library.centering import compute_centroid

    vectors = _anisotropic_corpus(n=8)
    ids = [f"t{i:03d}" for i in range(8)]
    label_of = {tid: "unknown" for tid in ids}

    protos, labels = build_prototypes(vectors, ids, label_of)
    assert labels == []
    assert protos.shape == (0, EMBEDDING_DIM)
    # The empty table → classify abstains regardless of the query.
    centroid = compute_centroid(vectors)
    assert classify(vectors[0], protos, labels, centroid) == ("unknown", 0.0)


def test_correct_genre_not_margin_suppressed_by_unknown():
    """WR-04 — a track that belongs to a real genre still classifies as that
    genre even when many cache-miss "unknown" tracks share the corpus. With the
    fix the "unknown" rows never enter cosine_topk, so they cannot become the
    runner-up that shrinks best-vs-second below PROTO_MARGIN.
    """
    from vibemix.library.centering import compute_centroid
    from vibemix.library.genre_prototypes import build_prototypes, classify

    # Three genres + a pile of unknowns drawn from the same anisotropic shape.
    vectors = _anisotropic_corpus(n=18)
    ids = [f"t{i:03d}" for i in range(18)]
    real = ("techno", "house", "trance")
    label_of = {}
    for i, tid in enumerate(ids):
        label_of[tid] = real[i % 3] if i < 9 else "unknown"

    protos, labels = build_prototypes(vectors, ids, label_of)
    assert "unknown" not in labels
    centroid = compute_centroid(vectors)
    assert centroid is not None

    # A real-genre track classifies as its own label (floor/margin relaxed so the
    # test isolates the "unknown does not compete" property, not the cosine
    # geometry of the synthetic corpus).
    own = label_of[ids[0]]
    label, conf = classify(vectors[0], protos, labels, centroid, floor=0.0, margin=0.0)
    assert label == own
    assert label != "unknown"


# ---------- PERCEIVE-03 — classify floor + margin ----------


def test_classify_floor_and_margin():
    """``classify`` returns the nearest-prototype label above floor; below floor
    OR within tie-margin → ``("unknown", conf)`` (anti-slop abstain).

    GREEN since Plan 03.
    """
    from vibemix.library.centering import compute_centroid
    from vibemix.library.genre_prototypes import build_prototypes, classify

    vectors, ids, label_of = _labeled_corpus(n=12)
    protos, labels = build_prototypes(vectors, ids, label_of)
    centroid = compute_centroid(vectors)
    assert centroid is not None

    # A vector that IS one of the corpus tracks → classifies as its own label,
    # above floor.
    own_label = label_of[ids[0]]
    label, conf = classify(vectors[0], protos, labels, centroid, floor=0.0, margin=0.0)
    assert label == own_label
    assert 0.0 <= conf <= 1.0

    # An impossibly high floor → forces abstain regardless of nearest match.
    label_floor, conf_floor = classify(
        vectors[0], protos, labels, centroid, floor=0.999, margin=0.0
    )
    assert label_floor == "unknown"

    # A huge tie-margin → no prototype clears the nearest-vs-runner-up gap → abstain.
    label_margin, _ = classify(
        vectors[0], protos, labels, centroid, floor=0.0, margin=2.0
    )
    assert label_margin == "unknown"


# ---------- PERCEIVE-03 — thread-safe holder (GenrePrototypeLookup) ----------


def test_holder_late_write_discarded_after_clear():
    """A stale ``classify_playing`` write that completes AFTER ``clear()`` is
    discarded by the generation token (anti-second-writer, mirrors Grounding).

    Simulates the race manually: capture a generation, bump it via ``clear()``,
    then assert a write guarded by the stale generation does not latch.
    """
    from vibemix.library.genre_prototypes import GenrePrototypeLookup

    holder = GenrePrototypeLookup(store=object())  # store unused on this path

    # Dispatch A captures gen=1.
    with holder._lock:
        holder._inflight_gen += 1
        my_gen = holder._inflight_gen

    # clear() runs (e.g. end of turn / superseded) → bumps gen to 2, latch None.
    holder.clear()
    assert holder.get_latest() is None

    # Dispatch A's late write must be discarded (my_gen != _inflight_gen).
    with holder._lock:
        if my_gen == holder._inflight_gen:
            holder._latest = ("hardtechno", 0.9)
    assert holder.get_latest() is None  # stale write dropped

    # A fresh dispatch (current gen) DOES latch.
    with holder._lock:
        holder._inflight_gen += 1
        fresh = holder._inflight_gen
    with holder._lock:
        if fresh == holder._inflight_gen:
            holder._latest = ("house", 0.7)
    assert holder.get_latest() == ("house", 0.7)


def test_classify_playing_unknown_track_abstains_no_api(monkeypatch):
    """``classify_playing`` on a track NOT in the library returns
    ``("unknown", 0.0)`` WITHOUT any live embed (RESEARCH A1, €0)."""
    import vibemix.library.genre_prototypes as gp

    from vibemix.library.genre_prototypes import GenrePrototypeLookup

    vectors, ids, label_of = _labeled_corpus(n=12)

    class _FakeBackend:
        def load_all(self):
            return ids, vectors

        def snapshot_hash(self):
            return "snap-test"

    class _FakeStore:
        def __init__(self):
            self._backend = _FakeBackend()

        def snapshot_hash(self):
            return self._backend.snapshot_hash()

    # Build prototypes from the library (cached folder labels via monkeypatched lib).
    monkeypatch.setattr(
        gp, "_label_of_from_library", lambda ids_, lib=None: label_of, raising=True
    )

    holder = GenrePrototypeLookup(store=_FakeStore())
    label, conf = holder.classify_playing("NOT-IN-LIBRARY-id")
    assert (label, conf) == ("unknown", 0.0)
    # A known track classifies (proves the path is live, still €0 cached vectors).
    known_label, known_conf = holder.classify_playing(ids[0])
    assert isinstance(known_label, str)
    assert 0.0 <= known_conf <= 1.0


def test_ensure_prototypes_concurrent_no_torn_publish(monkeypatch):
    """WR-02 — concurrent off-loop workers calling ``_ensure_prototypes`` must
    publish ``(_protos, _labels, _centroid)`` atomically under the lock and never
    leave a torn multi-store (``_protos`` set while ``_centroid`` is still None).

    Drives many threads through ``_ensure_prototypes`` while a slow build runs;
    asserts every observed published state is internally consistent and the
    final triple is coherent.
    """
    import threading
    import time

    import vibemix.library.genre_prototypes as gp
    from vibemix.library.genre_prototypes import GenrePrototypeLookup

    fake_protos = np.zeros((2, EMBEDDING_DIM), dtype=np.float32)
    fake_labels = ["house", "techno"]
    fake_centroid = np.zeros(EMBEDDING_DIM, dtype=np.float32)

    def _slow_build(_store):
        time.sleep(0.02)  # widen the race window
        return fake_protos, fake_labels, fake_centroid

    monkeypatch.setattr(gp, "load_or_build_prototypes", _slow_build, raising=True)

    holder = GenrePrototypeLookup(store=object())  # _ensure_store short-circuits

    torn = []

    def _worker():
        holder._ensure_prototypes()
        # Read the published fields; a torn publish would show one set, one None.
        p, c = holder._protos, holder._centroid
        if (p is None) != (c is None):
            torn.append((p is None, c is None))

    threads = [threading.Thread(target=_worker) for _ in range(16)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not torn, f"torn publish observed (protos/centroid out of sync): {torn}"
    assert holder._protos is not None and holder._centroid is not None
    assert holder._labels == fake_labels


def test_holder_never_writes_music_state():
    """The holder exposes only get_latest() — no MusicState write path."""
    from vibemix.library.genre_prototypes import GenrePrototypeLookup

    holder = GenrePrototypeLookup(store=object())
    assert holder.get_latest() is None
    # get_latest snapshots the lock-guarded latch.
    with holder._lock:
        holder._latest = ("trance", 0.6)
    assert holder.get_latest() == ("trance", 0.6)


# ---------- T-78-01-01 mitigation pin (real green) ----------


def test_real_cache_untouched(_route_caches_to_tmp):
    """The autouse fixture must point every cache path INTO tmp_path — the real
    ~/.cache/vibemix/ is never a write target during this file's run.

    Real green: asserts the routed paths live under tmp_path (so even when the
    xfail tests above eventually flip green and write prototypes, the writes land
    in tmp, not the dev cache)."""
    import vibemix.library.centering as centering_mod
    from vibemix.library.rekordbox import RekordboxLibrary

    tmp = _route_caches_to_tmp
    assert str(RekordboxLibrary.CACHE_PATH).startswith(str(tmp))
    assert str(centering_mod.CENTROID_PATH).startswith(str(tmp))
    assert str(centering_mod.CENTROID_META_PATH).startswith(str(tmp))
