# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json

import numpy as np
from scripts.eval.library_similarity_tagging import (
    evaluate_triplets,
    evaluate_vectors,
    label_for_track,
    precision_at_k,
    prepare_labeled_subset,
    prototype_cluster_metrics,
)

from vibemix.library.rekordbox import TrackEntry


def _unit_rows(rows: list[list[float]]) -> np.ndarray:
    arr = np.asarray(rows, dtype=np.float32)
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms = np.where(norms < 1e-12, 1.0, norms)
    return (arr / norms).astype(np.float32)


def _track(
    track_id: str,
    *,
    filepath: str = "",
    genre: str = "",
) -> TrackEntry:
    return TrackEntry(
        track_id=track_id,
        title=track_id,
        artist="",
        album="",
        bpm=128.0,
        key="",
        duration_s=300.0,
        cues=(),
        filepath=filepath,
        genre=genre,
    )


def test_precision_at_k_scores_same_label_retrieval() -> None:
    vectors = _unit_rows(
        [
            [1.0, 0.0],
            [0.9, 0.1],
            [-1.0, 0.0],
            [-0.9, -0.1],
        ]
    )
    ids = ["a1", "a2", "b1", "b2"]
    labels = ["a", "a", "b", "b"]

    assert precision_at_k(vectors, ids, labels, k_values=(1,), centered=False) == {1: 1.0}


def test_cluster_purity_and_leave_one_out_accuracy_are_measured() -> None:
    vectors = _unit_rows(
        [
            [1.0, 0.0],
            [0.8, 0.2],
            [0.0, 1.0],
            [0.2, 0.8],
        ]
    )
    labels = ["kick", "kick", "pad", "pad"]

    out = prototype_cluster_metrics(vectors, labels, centered=False)

    assert out["prototype_cluster_purity"] == 1.0
    assert out["prototype_accuracy"] == 1.0
    assert out["prototype_accuracy_leave_one_out"] == 1.0
    assert out["clusters"] == {"kick": {"kick": 2}, "pad": {"pad": 2}}


def test_label_proxy_prefers_parent_folder_then_rekordbox_genre() -> None:
    folder_track = _track(
        "t1",
        filepath="file://localhost/Users/test/Music/Hard%20Techno/Track%201.mp3",
        genre="Techno",
    )
    genre_track = _track("t2", filepath="", genre="Deep House")

    assert label_for_track(folder_track) == ("Hard Techno", "folder_parent")
    assert label_for_track(genre_track) == ("Deep House", "rekordbox_genre")
    assert label_for_track(None) == ("unknown", "missing_entry")


def test_prepare_labeled_subset_filters_unknown_and_tiny_labels() -> None:
    ids = ["a1", "a2", "lonely", "missing"]
    vectors = _unit_rows([[1, 0], [0.9, 0.1], [0, 1], [-1, 0]])
    tracks = {
        "a1": _track("a1", filepath="/Music/A/a1.mp3"),
        "a2": _track("a2", filepath="/Music/A/a2.mp3"),
        "lonely": _track("lonely", filepath="/Music/B/lonely.mp3"),
    }

    subset = prepare_labeled_subset(ids, vectors, tracks, min_label_size=2)

    assert subset["ids"] == ["a1", "a2"]
    assert subset["labels"] == ["A", "A"]
    assert subset["label_counts_raw"] == {"A": 2, "B": 1}
    assert subset["dropped_unknown"] == 1
    assert subset["dropped_too_small"] == 1


def test_triplet_hook_scores_anchor_positive_negative_jsonl(tmp_path) -> None:
    vectors = _unit_rows([[1, 0], [0.9, 0.1], [-1, 0]])
    ids = ["anchor", "positive", "negative"]
    path = tmp_path / "triplets.jsonl"
    path.write_text(
        json.dumps({"anchor": "anchor", "positive": "positive", "negative": "negative"})
        + "\n"
        + json.dumps({"anchor": "anchor", "positive": "missing", "negative": "negative"})
        + "\n",
        encoding="utf-8",
    )

    out = evaluate_triplets(vectors, ids, path, centered=False)

    assert out == {
        "path": str(path),
        "count": 2,
        "scored": 1,
        "missing": 1,
        "agreement": 1.0,
    }


def test_evaluate_vectors_returns_raw_and_centered_metric_bundles() -> None:
    vectors = _unit_rows([[1, 0], [0.9, 0.1], [-1, 0], [-0.9, -0.1]])
    ids = ["a1", "a2", "b1", "b2"]
    labels = ["a", "a", "b", "b"]

    out = evaluate_vectors(ids, vectors, labels, k_values=(1,))

    assert out["status"] == "ok"
    assert out["track_count"] == 4
    assert out["label_count"] == 2
    assert out["metrics"]["raw"]["precision_at_k"] == {1: 1.0}
    assert out["metrics"]["centered"]["triplets"]["agreement"] is None
