# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import numpy as np
from scripts.eval.library_section_retrieval import _balanced_ids, _rank_same_label


def _unit_rows(rows: list[list[float]]) -> dict[str, np.ndarray]:
    ids = ["a1", "a2", "b1", "b2"]
    arr = np.asarray(rows, dtype=np.float32)
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms = np.where(norms < 1e-12, 1.0, norms)
    unit = (arr / norms).astype(np.float32)
    return {tid: unit[i] for i, tid in enumerate(ids)}


def test_rank_same_label_scores_precision_hit_and_mrr() -> None:
    labels = {"a1": "a", "a2": "a", "b1": "b", "b2": "b"}
    queries = _unit_rows([[1, 0], [0.9, 0.1], [-1, 0], [-0.9, -0.1]])
    candidates = _unit_rows([[0.9, 0.1], [1, 0], [-0.9, -0.1], [-1, 0]])

    out = _rank_same_label(queries, candidates, labels, k_values=(1, 3))

    assert out["queries"] == 4
    assert out["precision_at_k"] == {"1": 1.0, "3": 0.333333}
    assert out["hit_at_k"] == {"1": 1.0, "3": 1.0}
    assert out["mrr"] == 1.0


def test_section_vectors_can_beat_whole_track_baseline_on_outro_intro_proxy() -> None:
    labels = {"a1": "a", "a2": "a", "b1": "b", "b2": "b"}
    section_outros = _unit_rows([[1, 0], [0.9, 0.1], [-1, 0], [-0.9, -0.1]])
    section_intros = _unit_rows([[0.9, 0.1], [1, 0], [-0.9, -0.1], [-1, 0]])
    # Whole-track vectors are deliberately collapsed into one cone: a proxy for
    # the mean-pooling failure this bench is supposed to catch.
    whole = _unit_rows([[1, 0], [0.99, 0.01], [0.98, 0.02], [0.97, 0.03]])

    section = _rank_same_label(section_outros, section_intros, labels, k_values=(1,))
    baseline = _rank_same_label(whole, whole, labels, k_values=(1,))

    assert section["precision_at_k"]["1"] == 1.0
    assert baseline["precision_at_k"]["1"] < section["precision_at_k"]["1"]


def test_balanced_ids_caps_large_labels() -> None:
    ids = ["a1", "a2", "a3", "b1", "b2", "c1"]
    labels = ["a", "a", "a", "b", "b", "c"]

    out = _balanced_ids(ids, labels, max_tracks=5, max_per_label=2)

    assert out == ["a1", "b1", "c1", "a2", "b2"]
