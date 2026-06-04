# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import numpy as np
from scripts.eval.library_section_retrieval import (
    _balanced_ids,
    _blend_metrics,
    _compare_modes,
    _query_split,
    _rank_same_label,
)


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


def test_query_split_uses_deterministic_calibration_holdout() -> None:
    split = _query_split([f"t{i}" for i in range(10)])

    assert split["calibration"] == ["t0", "t5"]
    assert split["holdout"] == ["t1", "t2", "t3", "t4", "t6", "t7", "t8", "t9"]


def test_section_aware_blend_can_choose_nonzero_alpha_on_holdout() -> None:
    ids = [f"a{i}" for i in range(5)] + [f"b{i}" for i in range(5)]
    labels = {tid: tid[0] for tid in ids}
    # Whole vectors are mostly right, but the section vectors fix the holdout
    # pair order. The calibration split sees the same pattern and selects a
    # nonzero alpha; holdout then beats alpha=0.
    whole = {
        "a0": np.asarray([1.0, 0.0], dtype=np.float32),
        "a1": np.asarray([0.2, 0.98], dtype=np.float32),
        "a2": np.asarray([0.1, 0.99], dtype=np.float32),
        "a3": np.asarray([0.2, 0.98], dtype=np.float32),
        "a4": np.asarray([0.1, 0.99], dtype=np.float32),
        "b0": np.asarray([0.0, 1.0], dtype=np.float32),
        "b1": np.asarray([1.0, 0.0], dtype=np.float32),
        "b2": np.asarray([0.99, 0.1], dtype=np.float32),
        "b3": np.asarray([1.0, 0.0], dtype=np.float32),
        "b4": np.asarray([0.99, 0.1], dtype=np.float32),
    }
    section = {
        tid: (
            np.asarray([1.0, 0.0], dtype=np.float32)
            if tid.startswith("a")
            else np.asarray([0.0, 1.0], dtype=np.float32)
        )
        for tid in ids
    }

    out = _blend_metrics(
        section_query_vectors=section,
        section_candidate_vectors=section,
        whole_query_vectors=whole,
        whole_candidate_vectors=whole,
        labels=labels,
        k_values=(1,),
        alpha_grid=(0.0, 0.5, 1.0),
    )

    assert out["calibration"]["best_alpha"] > 0.0
    assert (
        out["holdout"]["section_aware_blend"]["precision_at_k"]["1"]
        > out["holdout"]["whole_baseline"]["precision_at_k"]["1"]
    )

    metrics = _compare_modes(
        outro_vectors=section,
        intro_vectors=section,
        whole_vectors=whole,
        labels=labels,
        k_values=(1,),
    )
    assert metrics["primary_delta"] > 0.0
    assert metrics["section_beats_whole"] is False
    assert metrics["interpretation"] == (
        "comparable_to_whole_track_explainability_not_raw_accuracy"
    )
