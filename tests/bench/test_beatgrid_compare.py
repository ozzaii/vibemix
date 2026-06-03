# SPDX-License-Identifier: Apache-2.0
"""Offline tests for the beat-this BPM comparison harness."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from scripts.eval import beatgrid_compare as bgc


def _write_manifest(tmp_path: Path, tracks: list[dict[str, Any]]) -> Path:
    manifest = tmp_path / "bpm_truth_manifest.json"
    manifest.write_text(json.dumps({"tracks": tracks}), encoding="utf-8")
    for track in tracks:
        (tmp_path / track["file"]).write_bytes(b"not decoded by this test")
    return manifest


def test_octave_error_flags_half_double_and_triplet_aliases() -> None:
    assert bgc.octave_error(65.0, 130.0)
    assert bgc.octave_error(260.0, 130.0)
    assert bgc.octave_error(195.0, 130.0)
    assert bgc.octave_error(97.5, 130.0)
    assert not bgc.octave_error(130.8, 130.0)
    assert not bgc.octave_error(None, 130.0)


def test_report_schema_and_ok_gate_pass_with_stubbed_beat_this(tmp_path: Path) -> None:
    tracks = [
        {"file": "a.mp3", "truth_bpm": 130.0, "genre": "techno"},
        {"file": "b.mp3", "truth_bpm": 140.0, "genre": "techno"},
    ]
    manifest = _write_manifest(tmp_path, tracks)

    live_by_file = {
        "a.mp3": bgc.LiveBpmEstimate(65.0, 65.0, False, [65.0] * 5, "techno", True),
        "b.mp3": bgc.LiveBpmEstimate(70.0, 70.0, False, [70.0] * 5, "techno", True),
    }

    def live_estimator(track: dict[str, Any], _audio_path: Path) -> bgc.LiveBpmEstimate:
        return live_by_file[str(track["file"])]

    def beat_this_runner(audio_path: Path) -> dict[str, float]:
        return {"bpm": 130.0 if audio_path.name == "a.mp3" else 140.0}

    report = bgc.evaluate_beatgrid(
        audio_dir=tmp_path,
        manifest_path=manifest,
        beat_this_runner=beat_this_runner,
        live_estimator=live_estimator,
    )

    assert report["schema"] == "beatgrid_compare_v1"
    assert report["ok"] is True
    assert report["n_tracks"] == 2
    assert report["live_octave_error_rate"] == 1.0
    assert report["beat_this_octave_error_rate"] == 0.0
    assert report["beat_this_median_abs_delta"] == 0.0
    assert report["rows"][0]["live_post_guard_bpm"] == 65.0
    assert report["rows"][0]["beat_this_bpm"] == 130.0
    assert any("torchaudio" in site for site in report["torch_free_contract"]["lazy_only_sites"])


def test_ok_gate_fails_on_new_beat_this_octave_error(tmp_path: Path) -> None:
    tracks = [{"file": "a.mp3", "truth_bpm": 130.0, "genre": "techno"}]
    manifest = _write_manifest(tmp_path, tracks)

    def live_estimator(_track: dict[str, Any], _audio_path: Path) -> bgc.LiveBpmEstimate:
        return bgc.LiveBpmEstimate(130.0, 130.0, False, [130.0] * 5, "techno", True)

    report = bgc.evaluate_beatgrid(
        audio_dir=tmp_path,
        manifest_path=manifest,
        beat_this_runner=lambda _path: {"bpm": 65.0},
        live_estimator=live_estimator,
    )

    assert report["ok"] is False
    assert report["new_beat_this_octave_failures"] == ["a.mp3"]
    assert report["rows"][0]["live_octave_error"] is False
    assert report["rows"][0]["beat_this_octave_error"] is True


def test_cli_runner_reads_json_file_written_by_beat_this(
    tmp_path: Path,
    monkeypatch,
) -> None:
    audio_path = tmp_path / "track.mp3"
    audio_path.write_bytes(b"fake")

    def fake_run(argv: list[str], **_kwargs: Any) -> SimpleNamespace:
        json_arg = next(arg for arg in argv if str(arg).startswith("--json="))
        Path(json_arg.split("=", 1)[1]).write_text(json.dumps({"tempo": 128.0}))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(bgc.subprocess, "run", fake_run)

    payload = bgc._run_beat_this_cli(audio_path, beat_this_bin="beat-this")
    assert bgc.parse_beat_this_bpm(payload) == 128.0
