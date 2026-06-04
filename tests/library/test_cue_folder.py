# SPDX-License-Identifier: Apache-2.0
"""Tests for the folder->auto-cue->Rekordbox bridge (`library cue <folder>`).

Task 1 of the cue+export plan. `cue_folder` walks a folder, runs the auto-cue
engine per file, and emits the exact track-dict shape `export_rekordbox.export_set`
consumes - so a DJ can point at a folder and get a cued, importable collection.xml.

The auto-cue engine is dependency-injected (`detect=`) so these tests need no
audio and no ONNX model; one test exercises the REAL `export_set` round-trip to
prove the bridge dict actually produces POSITION_MARK pads.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from vibemix.library.cue_folder import (
    CueExportReport,
    anchors_to_marks,
    cue_folder,
    export_cued_folder,
    write_m3u8,
)
from vibemix.library.cue_types import CueAnchor

_REAL_MP3 = (
    Path(__file__).resolve().parents[1] / "bench" / "data" / "t1_pyrez_darkside.mp3"
)


def _anchor(label: str, start_s: float, *, end_s: float | None = None, conf: float = 0.9) -> CueAnchor:
    return CueAnchor(
        label=label,  # type: ignore[arg-type]
        start_s=start_s,
        end_s=end_s if end_s is not None else start_s + 8.0,
        confidence=conf,
        source="auto",
    )


def test_anchors_to_marks_assigns_ascending_num_and_label_names() -> None:
    """Out-of-order anchors -> marks sorted by start_s, hot-cue Num 0,1,2,
    label NAMEs, all point cues."""
    anchors = [_anchor("outro", 200.0), _anchor("intro", 5.0), _anchor("drop", 64.0)]
    marks = anchors_to_marks(anchors)
    assert [m["num"] for m in marks] == [0, 1, 2]
    assert [m["name"] for m in marks] == ["INTRO", "DROP", "OUTRO"]
    assert [m["start_s"] for m in marks] == [5.0, 64.0, 200.0]
    assert [m["source"] for m in marks] == ["auto", "auto", "auto"]
    assert all(m["type"] == "cue" for m in marks)


def test_anchors_to_marks_caps_at_eight_hot_cue_slots() -> None:
    """Rekordbox has 8 hot-cue pads (A-H); a track with more anchors keeps the
    8 earliest, numbered 0-7."""
    anchors = [_anchor("build", float(i)) for i in range(12)]
    marks = anchors_to_marks(anchors)
    assert len(marks) == 8
    assert [m["num"] for m in marks] == list(range(8))


def test_cue_folder_walks_audio_and_bridges_each_track(tmp_path: Path) -> None:
    for name in ("a.mp3", "b.wav", "c.flac"):
        (tmp_path / name).write_bytes(b"x")
    (tmp_path / "notes.txt").write_text("not audio")

    def fake_detect(path: str, *, max_cues: int = 8) -> list[CueAnchor]:
        return [_anchor("intro", 5.0), _anchor("drop", 64.0)]

    result = cue_folder(tmp_path, detect=fake_detect)

    assert len(result.tracks) == 3  # the .txt is ignored
    assert not result.skipped
    for track in result.tracks:
        assert Path(track["filepath"]).suffix.lower() in {".mp3", ".wav", ".flac"}
        assert track["title"]  # filename stem as the title
        assert [c["num"] for c in track["cues"]] == [0, 1]
        assert [c["name"] for c in track["cues"]] == ["INTRO", "DROP"]


def test_cue_folder_skips_decode_errors_non_fatal(tmp_path: Path) -> None:
    (tmp_path / "good.mp3").write_bytes(b"x")
    (tmp_path / "bad.mp3").write_bytes(b"x")

    def flaky_detect(path: str, *, max_cues: int = 8) -> list[CueAnchor]:
        if Path(path).name == "bad.mp3":
            raise RuntimeError("decode failed")
        return [_anchor("intro", 5.0)]

    result = cue_folder(tmp_path, detect=flaky_detect)

    assert len(result.tracks) == 1
    assert len(result.skipped) == 1
    assert result.skipped[0]["filepath"].endswith("bad.mp3")
    assert "decode failed" in result.skipped[0]["reason"]


def test_cue_folder_emits_no_track_for_anchorless_file(tmp_path: Path) -> None:
    """A file the engine finds no cues in is skipped (no empty cue track)."""
    (tmp_path / "silent.mp3").write_bytes(b"x")

    def empty_detect(path: str, *, max_cues: int = 8) -> list[CueAnchor]:
        return []

    result = cue_folder(tmp_path, detect=empty_detect)
    assert result.tracks == []
    assert len(result.skipped) == 1
    assert "no cues" in result.skipped[0]["reason"].lower()


def test_cue_folder_output_feeds_export_set(tmp_path: Path) -> None:
    """The bridge dict carries exactly the keys export_set._add_cues consumes
    (type/start_s/num/name), and export_set accepts the shape and writes a
    collection without raising. (The deep POSITION_MARK XML assertions live in
    test_export_rekordbox.py - export_set's own suite.)"""
    pytest.importorskip("pyrekordbox")
    from vibemix.library.export_rekordbox import export_set

    (tmp_path / "track.mp3").write_bytes(b"x")

    def fake_detect(path: str, *, max_cues: int = 8) -> list[CueAnchor]:
        return [_anchor("intro", 5.0), _anchor("breakdown", 48.0), _anchor("drop", 64.0)]

    result = cue_folder(tmp_path, detect=fake_detect)

    cues = result.tracks[0]["cues"]
    assert [c["name"] for c in cues] == ["INTRO", "BREAKDOWN", "DROP"]
    assert [c["num"] for c in cues] == [0, 1, 2]
    assert all(set(c) >= {"type", "start_s", "num", "name", "source"} for c in cues)

    out = tmp_path / "collection.xml"
    res = export_set(result.tracks, "vibemix cues", out)
    assert res.written == 1
    assert out.exists() and out.stat().st_size > 0


def test_export_cued_folder_writes_rekordbox_and_reports_counts(tmp_path: Path) -> None:
    """The orchestration: walk -> cue -> export_set, returning honest counts."""
    pytest.importorskip("pyrekordbox")
    for name in ("one.mp3", "two.mp3"):
        (tmp_path / name).write_bytes(b"x")

    def fake_detect(path: str, *, max_cues: int = 8) -> list[CueAnchor]:
        if Path(path).name == "one.mp3":
            return [_anchor("intro", 5.0), _anchor("drop", 64.0)]
        return [_anchor("intro", 4.0)]

    out = tmp_path / "vibemix.xml"
    report = export_cued_folder(tmp_path, out, name="vibemix cues", detect=fake_detect)

    assert isinstance(report, CueExportReport)
    assert report.tracks_cued == 2
    assert report.cues_total == 3
    assert report.skipped == 0
    assert report.outputs["rekordbox"] == str(out)
    assert out.exists() and out.stat().st_size > 0


def test_export_cued_folder_counts_skips_and_still_writes(tmp_path: Path) -> None:
    """Decode-error and anchorless files land in the skip count, not the export."""
    pytest.importorskip("pyrekordbox")
    for name in ("good.mp3", "bad.mp3", "silent.mp3"):
        (tmp_path / name).write_bytes(b"x")

    def fake_detect(path: str, *, max_cues: int = 8) -> list[CueAnchor]:
        stem = Path(path).name
        if stem == "bad.mp3":
            raise RuntimeError("decode failed")
        if stem == "silent.mp3":
            return []
        return [_anchor("intro", 5.0)]

    out = tmp_path / "vibemix.xml"
    report = export_cued_folder(tmp_path, out, detect=fake_detect)

    assert report.tracks_cued == 1
    assert report.cues_total == 1
    assert report.skipped == 2
    assert out.exists()


def test_write_m3u8_emits_extm3u_header_and_filepaths(tmp_path: Path) -> None:
    """The neutral playlist sink: #EXTM3U + #EXTINF + raw filepaths, in order.
    (Mixxx imports an .m3u8 as an additive crate - order only, no DB touch.)"""
    tracks = [
        {"filepath": "/music/one.mp3", "title": "One", "cues": []},
        {"filepath": "/music/two.mp3", "title": "Two", "cues": []},
    ]
    out = tmp_path / "set.m3u8"
    written = write_m3u8(tracks, out)

    assert written == out
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "#EXTM3U"
    assert lines[1] == "#EXTINF:-1,One"
    assert lines[2] == "/music/one.mp3"
    assert lines[3] == "#EXTINF:-1,Two"
    assert lines[4] == "/music/two.mp3"


def test_export_cued_folder_m3u8_only(tmp_path: Path) -> None:
    (tmp_path / "t.mp3").write_bytes(b"x")

    def fake_detect(path: str, *, max_cues: int = 8) -> list[CueAnchor]:
        return [_anchor("intro", 5.0)]

    out = tmp_path / "set.m3u8"
    report = export_cued_folder(tmp_path, out, export="m3u8", detect=fake_detect)

    assert report.outputs == {"m3u8": str(out)}
    assert "rekordbox" not in report.outputs
    assert out.exists() and out.read_text(encoding="utf-8").startswith("#EXTM3U")


def test_export_cued_folder_both_writes_xml_and_m3u8(tmp_path: Path) -> None:
    pytest.importorskip("pyrekordbox")
    (tmp_path / "t.mp3").write_bytes(b"x")

    def fake_detect(path: str, *, max_cues: int = 8) -> list[CueAnchor]:
        return [_anchor("intro", 5.0), _anchor("drop", 64.0)]

    out = tmp_path / "vibemix.xml"
    report = export_cued_folder(tmp_path, out, export="both", detect=fake_detect)

    assert set(report.outputs) == {"rekordbox", "m3u8"}
    assert report.outputs["rekordbox"].endswith(".xml")
    assert report.outputs["m3u8"].endswith(".m3u8")
    assert Path(report.outputs["rekordbox"]).exists()
    assert Path(report.outputs["m3u8"]).exists()


def test_export_cued_folder_rejects_unknown_export_format(tmp_path: Path) -> None:
    (tmp_path / "t.mp3").write_bytes(b"x")
    with pytest.raises(ValueError, match="export"):
        export_cued_folder(tmp_path, tmp_path / "o.xml", export="serato", detect=lambda p, *, max_cues=8: [])


@pytest.mark.skipif(not _REAL_MP3.exists(), reason="needs the in-repo test mp3")
def test_tag_folder_serato_writes_cues_into_each_file(tmp_path: Path) -> None:
    """The file-tag sink: walk -> cue -> write Serato Markers2 tags."""
    pytest.importorskip("mutagen")
    from vibemix.library.cue_folder import tag_folder_serato
    from vibemix.library.export_serato import read_serato_cues

    for name in ("a.mp3", "b.mp3"):
        shutil.copy(_REAL_MP3, tmp_path / name)

    def fake_detect(path: str, *, max_cues: int = 8) -> list[CueAnchor]:
        return [_anchor("intro", 5.0), _anchor("drop", 64.0)]

    report = tag_folder_serato(tmp_path, allow_write=True, detect=fake_detect)

    assert report["tagged"] == 2
    assert report["cues_total"] == 4
    assert report["skipped"] == 0
    for name in ("a.mp3", "b.mp3"):
        back = read_serato_cues(tmp_path / name)
        assert [c.name for c in back] == ["VM INTRO", "VM DROP"]


def test_tag_folder_serato_requires_opt_in(tmp_path: Path) -> None:
    """Without allow_write nothing is tagged (the files are never mutated)."""
    from vibemix.library.cue_folder import tag_folder_serato

    (tmp_path / "a.mp3").write_bytes(b"x")

    def fake_detect(path: str, *, max_cues: int = 8) -> list[CueAnchor]:
        return [_anchor("intro", 5.0)]

    report = tag_folder_serato(tmp_path, allow_write=False, detect=fake_detect)
    assert report["tagged"] == 0
    assert report["skipped"] >= 1
