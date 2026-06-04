# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
from pathlib import Path

from scripts.eval.key_estimator_bench import (
    KeyLabel,
    evaluate_dataset,
    main,
    mirex_relation,
    mirex_score,
    parse_key_label,
)

from vibemix.library.key_estimator import KeyEstimate


def test_parse_key_label_supports_giantsteps_and_vibemix_forms() -> None:
    assert parse_key_label("key 0 C minor") == KeyLabel(pc=0, mode="minor")
    assert parse_key_label("F# major") == KeyLabel(pc=6, mode="major")
    assert parse_key_label("Bb") == KeyLabel(pc=10, mode="major")
    assert parse_key_label("Am") == KeyLabel(pc=9, mode="minor")


def test_mirex_relation_weights_exact_fifth_relative_parallel() -> None:
    c_major = KeyLabel(pc=0, mode="major")
    a_minor = KeyLabel(pc=9, mode="minor")

    assert mirex_relation(c_major, KeyLabel(pc=0, mode="major")) == "exact"
    assert mirex_score(c_major, KeyLabel(pc=0, mode="major")) == 1.0
    assert mirex_relation(c_major, KeyLabel(pc=7, mode="major")) == "fifth"
    assert mirex_score(c_major, KeyLabel(pc=7, mode="major")) == 0.5
    assert mirex_relation(c_major, a_minor) == "relative"
    assert mirex_score(c_major, a_minor) == 0.3
    assert mirex_relation(c_major, KeyLabel(pc=0, mode="minor")) == "parallel"
    assert mirex_score(c_major, KeyLabel(pc=0, mode="minor")) == 0.2
    assert mirex_relation(c_major, None) == "abstained"
    assert mirex_score(c_major, None) == 0.0


def _write_annotation(path: Path, label: str) -> None:
    path.write_text(f"#@format: key\ttimestamp(float)\tkey(string)\nkey 0 {label}\n")


def test_evaluate_dataset_scores_redacted_fixture(tmp_path: Path) -> None:
    annotations = tmp_path / "annotations"
    audio = tmp_path / "audio"
    annotations.mkdir()
    audio.mkdir()
    labels = {
        "exact.LOFI": "C major",
        "fifth.LOFI": "A minor",
        "parallel.LOFI": "F minor",
        "abstain.LOFI": "D major",
        "missing.LOFI": "E major",
    }
    for stem, label in labels.items():
        _write_annotation(annotations / f"{stem}.key", label)
    for stem in ("exact.LOFI", "fifth.LOFI", "parallel.LOFI", "abstain.LOFI"):
        (audio / f"{stem}.mp3").write_bytes(b"fixture")

    predictions = {
        "exact.LOFI": KeyEstimate(camelot="8B", musical="C", confidence=0.9),
        "fifth.LOFI": KeyEstimate(camelot="9A", musical="Em", confidence=0.8),
        "parallel.LOFI": KeyEstimate(camelot="7B", musical="F", confidence=0.7),
        "abstain.LOFI": None,
    }

    def fake_estimator(path: Path) -> KeyEstimate | None:
        return predictions[path.stem]

    result = evaluate_dataset(
        annotations_dir=annotations,
        audio_dir=audio,
        estimator=fake_estimator,
        include_tracks=True,
    )

    assert result["schema"] == "key_estimator_bench_v1"
    assert result["status"] == "ok"
    assert result["annotations_total"] == 5
    assert result["attempted"] == 4
    assert result["audio_missing"] == 1
    assert result["emitted"] == 3
    assert result["counts"] == {
        "exact": 1,
        "fifth": 1,
        "relative": 0,
        "parallel": 1,
        "other": 0,
        "abstained": 1,
    }
    assert result["mirex_weighted"] == 0.425
    assert result["exact_accuracy"] == 0.25
    assert result["notes"]["source_path_redacted"] is True
    assert "tmp_path" not in json.dumps(result)


def test_cli_no_audio_is_nonzero_unless_allowed(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    annotations = tmp_path / "annotations"
    audio = tmp_path / "audio"
    annotations.mkdir()
    _write_annotation(annotations / "one.LOFI.key", "C major")

    assert main(["--annotations-dir", str(annotations), "--audio-dir", str(audio), "--json"]) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "no_audio"
    assert payload["attempted"] == 0

    assert (
        main(
            [
                "--annotations-dir",
                str(annotations),
                "--audio-dir",
                str(audio),
                "--json",
                "--allow-empty",
            ]
        )
        == 0
    )
