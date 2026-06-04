# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
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
    assert report["label_set"]["enough_complete_eval_rows"] is False
    assert report["claim_gate"] == {
        "final_precision_recall_claim_allowed": False,
        "evaluation_complete_rows": 1,
        "min_required_rows": 50,
        "reason": "needs_50_complete_holdout_rows_for_final_claim",
    }
    assert report["notes"]["no_final_accuracy_claim_without_min_labels"] is True
    assert report["label_set"]["calibration_strategy"] == "explicit_holdout_default_thresholds"
    assert report["modes"]["template"]["metrics"]["micro"]["precision"] >= 0.0
    assert report["comparison"]["primary_metric"] == "micro_f1"


def test_build_report_does_not_calibrate_on_explicit_holdout(
    tmp_path: Path, monkeypatch
) -> None:
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

    def fail_if_called(*args, **kwargs):
        raise AssertionError("holdout labels must not tune thresholds")

    monkeypatch.setattr(lat, "calibrate_thresholds", fail_if_called)

    report = lat.build_report(labels_path=labels, max_examples=2)

    assert report["label_set"]["calibration_rows"] == 0
    assert report["label_set"]["evaluation_rows"] == 1
    assert report["modes"]["template"]["thresholds"] == {
        "instrument": 0.18,
        "mood": 0.18,
        "texture": 0.18,
    }


def test_rows_without_explicit_split_get_deterministic_calibration_holdout() -> None:
    rows = [
        lat.HandLabelRow(f"t{i}", "eval", {"mood": {"dark"}})
        for i in range(10)
    ]

    calibration, holdout, strategy = lat._rows_by_split(rows)

    assert strategy == "deterministic_calibration_holdout"
    assert [row.track_id for row in calibration] == ["t0", "t5"]
    assert len(holdout) == 8
    assert not ({row.track_id for row in calibration} & {row.track_id for row in holdout})


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


def test_enough_complete_rows_allow_final_claim_gate(
    tmp_path: Path, monkeypatch
) -> None:
    labels = tmp_path / "labels.jsonl"
    labels.write_text(
        "".join(
            json.dumps(
                {
                    "track_id": f"t{i}",
                    "split": "holdout",
                    "mood": ["dark"],
                    "texture": ["raw"],
                    "instrument": [],
                }
            )
            + "\n"
            for i in range(2)
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        lat,
        "_load_store",
        lambda: (
            ["t0", "t1"],
            np.asarray([[1.0, 0.0, 0.0], [1.0, 0.0, 0.0]], dtype=np.float32),
            "FakeStore",
            "snap",
        ),
    )
    monkeypatch.setattr(lat, "ClapEngine", lambda: _FakeEngine())

    report = lat.build_report(labels_path=labels, min_hand_labels=2)

    assert report["status"] == "ok"
    assert report["label_set"]["enough_complete_eval_rows"] is True
    assert report["claim_gate"] == {
        "final_precision_recall_claim_allowed": True,
        "evaluation_complete_rows": 2,
        "min_required_rows": 2,
        "reason": "ok_minimum_complete_holdout_met",
    }
    assert report["notes"]["no_final_accuracy_claim_without_min_labels"] is False


def test_label_audit_reports_missing_partial_and_complete_rows(tmp_path: Path) -> None:
    labels = tmp_path / "labels.jsonl"
    labels.write_text(
        json.dumps({"track_id": "todo", "label_status": "todo", "tags": {}})
        + "\n"
        + json.dumps({"track_id": "partial", "split": "holdout", "mood": ["dark"]})
        + "\n"
        + json.dumps(
            {
                "track_id": "complete",
                "split": "holdout",
                "mood": ["dark"],
                "texture": ["raw"],
                "instrument": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    audit = lat.build_label_audit(labels_path=labels, min_hand_labels=2)

    assert audit["label_status"] == "ok"
    assert audit["pending_rows"] == 1
    assert audit["usable_rows"] == 2
    assert audit["complete_rows"] == 1
    assert audit["calibration_strategy"] == "explicit_holdout_default_thresholds"
    assert audit["evaluation_rows"] == 2
    assert audit["evaluation_complete_rows"] == 1
    assert audit["enough_complete_eval_rows"] is False
    assert audit["missing_category_counts"] == {
        "mood": 0,
        "texture": 1,
        "instrument": 1,
    }
    assert audit["known_tags"]["mood"] == sorted(audit["known_tags"]["mood"])
    assert "dark" in audit["known_tags"]["mood"]
    assert "raw" in audit["known_tags"]["texture"]
    assert "vocal" in audit["known_tags"]["instrument"]
    assert audit["label_row_example"]["split"] == "holdout"
    assert set(audit["label_row_example"]["tags"]) == {"mood", "texture", "instrument"}


def test_label_audit_can_pass_when_enough_complete_eval_rows(tmp_path: Path) -> None:
    labels = tmp_path / "labels.jsonl"
    labels.write_text(
        json.dumps(
            {
                "track_id": "complete",
                "split": "holdout",
                "mood": ["dark"],
                "texture": ["raw"],
                "instrument": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    audit = lat.build_label_audit(labels_path=labels, min_hand_labels=1)

    assert audit["evaluation_complete_rows"] == 1
    assert audit["enough_complete_eval_rows"] is True
    assert audit["next_action"] == "run the full auto-tag bench with --require-labels"


def test_audit_labels_cli_exits_nonzero_until_enough_complete_rows(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    labels = tmp_path / "labels.jsonl"
    labels.write_text(
        json.dumps({"track_id": "partial", "split": "holdout", "mood": ["dark"]}) + "\n",
        encoding="utf-8",
    )

    rc = lat.main(["--audit-labels", "--labels", str(labels), "--min-hand-labels", "1"])

    assert rc == 2
    assert "complete_eval=0/1" in capsys.readouterr().out


def test_audit_labels_cli_writes_json_artifact_even_when_incomplete(
    tmp_path: Path,
) -> None:
    labels = tmp_path / "labels.jsonl"
    out = tmp_path / "audit" / "report.json"
    labels.write_text(
        json.dumps(
            {
                "track_id": "complete",
                "split": "holdout",
                "mood": ["dark"],
                "texture": ["raw"],
                "instrument": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    rc = lat.main(
        [
            "--audit-labels",
            "--labels",
            str(labels),
            "--out",
            str(out),
            "--min-hand-labels",
            "2",
        ]
    )

    assert rc == 2
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["schema"] == "library_auto_tags_bench_v1_label_audit_v1"
    assert payload["evaluation_complete_rows"] == 1
    assert payload["enough_complete_eval_rows"] is False
    assert payload["known_tags"]["mood"]
    assert payload["label_row_example"]["label_status"] == "complete"
    assert payload["next_action"] == (
        "complete eval/private/library/auto_tag_labels.jsonl rows for "
        "mood, texture, and instrument"
    )


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


def test_private_label_template_out_refuses_to_overwrite_without_force(
    tmp_path: Path, monkeypatch, capsys: pytest.CaptureFixture[str]
) -> None:
    private_out = tmp_path / "auto_tag_labels.jsonl"
    private_out.write_text("keep me\n", encoding="utf-8")
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
    monkeypatch.setattr(lat, "_load_track_contexts", lambda ids: {})

    rc = lat.main(
        [
            "--out",
            str(tmp_path / "report.json"),
            "--private-label-template-out",
            str(private_out),
        ]
    )

    assert rc == 3
    assert private_out.read_text(encoding="utf-8") == "keep me\n"
    assert "--force-private-label-template" in capsys.readouterr().err

    rc = lat.main(
        [
            "--out",
            str(tmp_path / "report-force.json"),
            "--private-label-template-out",
            str(private_out),
            "--force-private-label-template",
        ]
    )

    assert rc == 0
    assert "keep me" not in private_out.read_text(encoding="utf-8")
