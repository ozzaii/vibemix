# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scripts.eval import library_auto_tags as lat

from vibemix.library.auto_tags import AutoTagDecision
from vibemix.library.rekordbox import TrackEntry


def test_load_hand_labels_accepts_nested_tags_and_reports_unknown(tmp_path: Path) -> None:
    path = tmp_path / "labels.jsonl"
    path.write_text(
        json.dumps(
            {
                "track_id": "t1",
                "split": "holdout",
                "tags": {
                    "mood": ["Dark"],
                    "texture": ["raw"],
                    "instrument": ["laser-harp"],
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    loaded = lat.load_hand_labels(path)
    row = loaded["rows"][0]

    assert loaded["status"] == "ok"
    assert row.track_id == "t1"
    assert row.split == "holdout"
    assert row.labels["mood"] == {"dark"}
    assert row.labels["texture"] == {"raw"}
    assert row.labels["instrument"] == set()
    assert loaded["unknown_tags"] == {"instrument": ["laser_harp"]}


def test_load_hand_labels_skips_todo_template_rows(tmp_path: Path) -> None:
    path = tmp_path / "labels.jsonl"
    path.write_text(
        json.dumps(
            {
                "track_id": "t1",
                "split": "holdout",
                "label_status": "todo",
                "tags": {"mood": [], "texture": [], "instrument": []},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    loaded = lat.load_hand_labels(path)

    assert loaded["status"] == "empty"
    assert loaded["pending_rows"] == 1
    assert loaded["usable_rows"] == 0
    assert loaded["rows"] == []


def test_evaluate_labeled_predictions_measures_precision_recall_and_abstain() -> None:
    rows = [
        lat.HandLabelRow("t1", "eval", {"mood": {"dark"}, "texture": {"raw"}}),
        lat.HandLabelRow("t2", "eval", {"mood": {"euphoric"}, "texture": {"airy"}}),
    ]
    predictions = {
        "t1": (
            AutoTagDecision("mood", "dark", 0.8, None, -1.0, 1.8, 0.2, True, "accepted"),
            AutoTagDecision("texture", None, 0.1, "raw", 0.09, 0.01, 0.2, False, "below_threshold"),
        ),
        "t2": (
            AutoTagDecision("mood", "dark", 0.7, None, -1.0, 1.7, 0.2, True, "accepted"),
            AutoTagDecision("texture", "airy", 0.7, None, -1.0, 1.7, 0.2, True, "accepted"),
        ),
    }

    metrics = lat.evaluate_labeled_predictions(rows, predictions)

    assert metrics["micro"]["tp"] == 2
    assert metrics["micro"]["fp"] == 1
    assert metrics["micro"]["fn"] == 2
    assert metrics["micro"]["precision"] == 0.666667
    assert metrics["micro"]["recall"] == 0.5
    assert metrics["micro"]["abstentions"] == 1


class _FakeEngine:
    def embed_query(self, text: str) -> np.ndarray:
        text = text.lower()
        if "dark" in text or "raw" in text or "vocal" in text:
            return np.asarray([1.0, 0.0, 0.0], dtype=np.float32)
        if "euphoric" in text or "airy" in text:
            return np.asarray([0.0, 1.0, 0.0], dtype=np.float32)
        return np.asarray([0.0, 0.0, 1.0], dtype=np.float32)


def test_build_report_missing_labels_is_honest_null(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        lat,
        "_load_store",
        lambda: (
            ["t1"],
            np.asarray([[1.0, 0.0, 0.0]], dtype=np.float32),
            "FakeStore",
            "snap",
        ),
    )
    monkeypatch.setattr(lat, "ClapEngine", lambda: _FakeEngine())

    report = lat.build_report(
        labels_path=tmp_path / "missing.jsonl",
        label_template_size=1,
        max_examples=2,
    )

    assert report["status"] == "unproven_no_hand_labels"
    assert report["label_set"]["usable_rows"] == 0
    assert report["comparison"] is None
    assert report["modes"]["template"]["metrics"] is None
    assert report["modes"]["template"]["prediction_summary"]["track_count"] == 1
    assert report["label_template"]["status"] == "needed"
    assert report["label_template"]["row_count"] == 1
    assert report["label_template"]["rows"][0]["label_status"] == "todo"
    assert report["label_template"]["rows"][0]["split"] == "calibration"


def test_build_report_with_labels_scores_template_and_bare(tmp_path: Path, monkeypatch) -> None:
    labels = tmp_path / "labels.jsonl"
    labels.write_text(
        json.dumps(
            {
                "track_id": "t1",
                "split": "holdout",
                "mood": ["dark"],
                "texture": ["raw"],
                "instrument": ["vocal"],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        lat,
        "_load_store",
        lambda: (
            ["t1"],
            np.asarray([[1.0, 0.0, 0.0]], dtype=np.float32),
            "FakeStore",
            "snap",
        ),
    )
    monkeypatch.setattr(lat, "ClapEngine", lambda: _FakeEngine())

    report = lat.build_report(labels_path=labels, max_examples=2)

    assert report["status"] == "measured_small_hand_label_subset"
    assert report["label_set"]["usable_rows"] == 1
    assert report["label_set"]["complete_rows"] == 1
    assert report["label_set"]["evaluation_complete_rows"] == 1
    assert report["label_set"]["min_required_rows"] == 50
    assert report["modes"]["template"]["metrics"]["micro"]["precision"] >= 0.0
    assert report["comparison"]["primary_metric"] == "micro_f1"


def test_partial_label_rows_do_not_satisfy_complete_row_gate(
    tmp_path: Path, monkeypatch
) -> None:
    labels = tmp_path / "labels.jsonl"
    labels.write_text(
        json.dumps({"track_id": "t1", "split": "holdout", "mood": ["dark"]})
        + "\n"
        + json.dumps(
            {
                "track_id": "t2",
                "split": "holdout",
                "mood": ["dark"],
                "texture": ["raw"],
                "instrument": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        lat,
        "_load_store",
        lambda: (
            ["t1", "t2"],
            np.asarray([[1.0, 0.0, 0.0], [1.0, 0.0, 0.0]], dtype=np.float32),
            "FakeStore",
            "snap",
        ),
    )
    monkeypatch.setattr(lat, "ClapEngine", lambda: _FakeEngine())

    report = lat.build_report(labels_path=labels, min_hand_labels=2)

    assert report["label_set"]["usable_rows"] == 2
    assert report["label_set"]["evaluation_rows"] == 2
    assert report["label_set"]["evaluation_complete_rows"] == 1
    assert report["status"] == "measured_small_hand_label_subset"


def test_build_label_template_rows_balances_buckets_and_excludes_labeled_ids() -> None:
    predictions = {
        "a1": (
            AutoTagDecision("mood", "dark", 0.8, None, -1.0, 1.8, 0.2, True, "accepted"),
            AutoTagDecision("texture", "raw", 0.7, None, -1.0, 1.7, 0.2, True, "accepted"),
        ),
        "a2": (
            AutoTagDecision("mood", "dark", 0.8, None, -1.0, 1.8, 0.2, True, "accepted"),
            AutoTagDecision("texture", "raw", 0.7, None, -1.0, 1.7, 0.2, True, "accepted"),
        ),
        "b1": (
            AutoTagDecision("mood", "euphoric", 0.8, None, -1.0, 1.8, 0.2, True, "accepted"),
            AutoTagDecision("texture", "airy", 0.7, None, -1.0, 1.7, 0.2, True, "accepted"),
        ),
    }

    rows = lat.build_label_template_rows(predictions, max_rows=3, exclude_track_ids={"a1"})

    assert [row["track_id"] for row in rows] == ["a2", "b1"]
    assert all(row["label_status"] == "todo" for row in rows)


def test_private_label_template_rows_add_review_context_without_changing_labels(
    monkeypatch,
) -> None:
    track = TrackEntry(
        track_id="t1",
        title="Track One",
        artist="Artist",
        album="Album",
        bpm=145.0,
        key="5A",
        duration_s=360.0,
        cues=(),
        filepath="file:///Users/test/Music/Hard%20Techno/track-one.mp3",
        genre="Techno",
    )
    monkeypatch.setattr(lat, "_load_track_contexts", lambda ids: {"t1": track})
    rows = [
        {
            "track_id": "t1",
            "split": "holdout",
            "label_status": "todo",
            "tags": {"mood": [], "texture": [], "instrument": []},
        }
    ]

    out = lat.build_private_label_template_rows(rows)

    assert out[0]["label_status"] == "todo"
    assert out[0]["tags"] == {"mood": [], "texture": [], "instrument": []}
    assert out[0]["track_context"] == {
        "found": True,
        "title": "Track One",
        "artist": "Artist",
        "album": "Album",
        "genre": "Techno",
        "bpm": 145.0,
        "key": "5A",
        "duration_s": 360.0,
        "folder": "Hard Techno",
        "filename": "track-one.mp3",
    }
