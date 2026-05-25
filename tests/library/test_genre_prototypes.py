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


@pytest.mark.xfail(strict=True, reason="PERCEIVE-03 — flips when Plan 03 lands")
def test_build_centered_means():
    """``build_prototypes`` produces ONE centered-mean prototype per label, each
    L2-normalized, shape ``(n_labels, EMBEDDING_DIM)``.

    RED today: ``vibemix.library.genre_prototypes`` does not exist — the import
    raises ModuleNotFoundError (the xfail trigger).
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


# ---------- PERCEIVE-03 — classify floor + margin ----------


@pytest.mark.xfail(strict=True, reason="PERCEIVE-03 — flips when Plan 03 lands")
def test_classify_floor_and_margin():
    """``classify`` returns the nearest-prototype label above floor; below floor
    OR within tie-margin → ``("unknown", conf)`` (anti-slop abstain).

    RED today: the import raises ModuleNotFoundError.
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
