# SPDX-License-Identifier: Apache-2.0
"""Unit tests for the real-CLAP retrieval evaluator's pure metric functions.

These tests exercise the metric math (recall@k, MRR, anisotropy gap) on
SYNTHETIC vectors where the correct answer is known by construction - no model,
no audio. The companion ``test_clap_real_retrieval.py`` runs these same
functions over REAL committed CLAP embeddings as the regression guard.

The evaluator deliberately rides the PRODUCTION ranking primitives
(``_cosine.cosine_topk`` + ``centering.compute_centroid`` /
``center_and_renorm``) so a metric here can only move if the shipped ranking
math moves.
"""

from __future__ import annotations

import numpy as np
from scripts.eval.clap_retrieval import (
    anisotropy_gap,
    evaluate_retrieval,
    mean_pairwise_cosine,
)

from vibemix.library._cosine import EMBEDDING_DIM


def _unit_rows(arr: np.ndarray) -> np.ndarray:
    arr = arr.astype(np.float32, copy=False)
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms = np.where(norms < 1e-12, 1.0, norms)
    return (arr / norms).astype(np.float32)


def test_evaluate_retrieval_perfect_recall_when_query_matches_its_track() -> None:
    """Query i = corpus i + tiny noise -> nearest neighbour is corpus i."""
    rng = np.random.default_rng(7)
    n = 6
    corpus = _unit_rows(rng.standard_normal((n, EMBEDDING_DIM)))
    # Each query is its own track nudged by a tiny perturbation.
    noise = (rng.standard_normal((n, EMBEDDING_DIM)) * 0.01).astype(np.float32)
    queries = _unit_rows(corpus + noise)
    ids = [f"track-{i}" for i in range(n)]

    out = evaluate_retrieval(corpus, ids, queries, ids, centered=False)

    assert out["recall"][1] == 1.0
    assert out["mrr"] == 1.0
    assert out["n_queries"] == n


def test_evaluate_retrieval_recall_at_k_counts_rank_within_k() -> None:
    """A query whose true match sits at rank 2 misses recall@1, hits recall@3."""
    # Build a corpus where query0's true match (id 'b') is the 2nd-nearest,
    # not the 1st. Use 3 near-orthogonal anchors.
    e = np.eye(EMBEDDING_DIM, dtype=np.float32)
    a, b, c = e[0], e[1], e[2]
    corpus = np.stack([a, b, c]).astype(np.float32)
    ids = ["a", "b", "c"]
    # Query leans mostly toward 'a' but its declared ground truth is 'b'
    # (e.g. 0.9*a + 0.4*b) -> top1 = a, top2 = b.
    q = _unit_rows((0.9 * a + 0.4 * b)[None, :])
    out = evaluate_retrieval(corpus, ids, q, ["b"], centered=False, k_values=(1, 2, 3))

    assert out["recall"][1] == 0.0  # 'a' wins rank 1
    assert out["recall"][2] == 1.0  # 'b' is within top 2
    assert out["mrr"] == 0.5  # true match at rank 2


def test_anisotropy_gap_collapses_pairwise_cosine_on_biased_corpus() -> None:
    """A corpus sharing a strong common direction is anisotropic; centering
    must REDUCE the mean pairwise cosine (the shipped quality fix)."""
    rng = np.random.default_rng(11)
    n = 20
    base = rng.standard_normal((n, EMBEDDING_DIM)).astype(np.float32)
    bias = rng.standard_normal(EMBEDDING_DIM).astype(np.float32)
    bias /= np.linalg.norm(bias)
    # Inject a shared component that DOMINATES the random base so the corpus
    # genuinely crowds one cone. In D=512 the base has norm ~sqrt(512) ~= 22.6, so
    # the bias magnitude must be on that order to lift the mean pairwise cosine
    # (raw ~= a^2/(a^2+D) ~= 0.55 at a=25).
    biased = _unit_rows(base + 25.0 * bias)

    gap = anisotropy_gap(biased)

    assert gap["raw"] > 0.3  # genuinely anisotropic before the fix
    assert gap["centered"] < gap["raw"]  # centering collapses the cone
    assert gap["gap"] > 0.0


def test_mean_pairwise_cosine_of_orthonormal_basis_is_zero() -> None:
    """Orthonormal rows have zero pairwise cosine - the metric's ground truth."""
    rows = np.eye(EMBEDDING_DIM, dtype=np.float32)[:5]
    assert abs(mean_pairwise_cosine(rows)) < 1e-6


def test_evaluate_retrieval_centered_not_worse_than_raw_on_biased_corpus() -> None:
    """On an anisotropic corpus, centered recall must be >= raw recall -
    centering may help and must never hurt retrieval (the shipped guard)."""
    rng = np.random.default_rng(13)
    n = 8
    base = rng.standard_normal((n, EMBEDDING_DIM)).astype(np.float32)
    bias = rng.standard_normal(EMBEDDING_DIM).astype(np.float32)
    bias /= np.linalg.norm(bias)
    corpus = _unit_rows(base + 25.0 * bias)
    queries = _unit_rows(corpus + (rng.standard_normal((n, EMBEDDING_DIM)) * 0.05).astype(np.float32))
    ids = [f"t{i}" for i in range(n)]

    raw = evaluate_retrieval(corpus, ids, queries, ids, centered=False)
    centered = evaluate_retrieval(corpus, ids, queries, ids, centered=True)

    assert centered["recall"][1] >= raw["recall"][1]
