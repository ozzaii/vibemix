# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import replace
from pathlib import Path

import pytest

from vibemix.library.cue_landing import (
    ExportTarget,
    cue_set_from_anchors,
    cue_set_from_dict,
    cue_set_to_dict,
    land,
    sections_from_anchors,
)
from vibemix.library.cue_types import CueAnchor
from vibemix.library.rekordbox import CuePoint, TrackEntry
from vibemix.library.smart_cues import SmartCuePolicy


def _track(*, cues=(), filepath: str = "/music/track.mp3") -> TrackEntry:
    return TrackEntry(
        track_id="trk_001",
        title="Landing Track",
        artist="Landing Artist",
        album="",
        bpm=120.0,
        key="8A",
        duration_s=240.0,
        cues=tuple(cues),
        filepath=filepath,
        genre="hardtechno",
        camelot="8A",
    )


def _anchor(label: str, start_s: float, *, source: str = "auto") -> CueAnchor:
    return CueAnchor(
        label=label,  # type: ignore[arg-type]
        start_s=start_s,
        end_s=start_s + 32.0,
        confidence=0.92,
        source=source,  # type: ignore[arg-type]
    )


def _dj_cue(slot: int, start_s: float, name: str) -> CuePoint:
    return CuePoint(
        name=name,
        type="cue",
        start_s=start_s,
        end_s=None,
        number=slot,
        source="dj",
        confidence=0.98,
    )


def _parse_marks(path: Path) -> list[ET.Element]:
    root = ET.parse(path).getroot()
    tracks = root.find("COLLECTION")
    assert tracks is not None
    collection_tracks = tracks.findall("TRACK")
    assert len(collection_tracks) == 1
    return collection_tracks[0].findall("POSITION_MARK")


def test_sections_from_anchors_threads_source_and_beats() -> None:
    track = _track()
    sections = sections_from_anchors(
        track,
        [_anchor("intro", 8.0, source="auto"), _anchor("drop", 64.0, source="fallback")],
    )

    assert [section.role for section in sections] == ["intro", "drop"]
    assert [section.source for section in sections] == ["auto", "fallback"]
    assert [section.cue_source for section in sections] == ["auto", "fallback"]
    assert [section.start_beat for section in sections] == [16, 128]


def test_cue_set_from_anchors_routes_through_smart_cues() -> None:
    cueset = cue_set_from_anchors(
        _track(),
        [
            _anchor("intro", 0.0),
            _anchor("drop", 64.0),
            _anchor("outro", 192.0),
        ],
    )

    by_slot = {cue.slot: cue for cue in cueset.cues}
    assert {"A", "D", "F"} <= set(by_slot)
    assert by_slot["A"].source == "auto"
    assert by_slot["A"].export_label == "VM A IN"
    assert by_slot["D"].review_status == "export_ready"


def test_cue_set_review_packet_carries_policy_target_and_summary() -> None:
    policy = SmartCuePolicy(export_ready_floor=0.9, review_floor=0.55, source_floor=0.45)
    cueset = cue_set_from_anchors(
        _track(cues=(_dj_cue(1, 12.0, "MY B"),)),
        [
            _anchor("intro", 0.0, source="auto"),
            _anchor("drop", 64.0, source="anlz"),
        ],
        policy=policy,
        include_review=True,
        include_preserved=True,
    )

    assert cueset.detected_target == "rekordbox_xml"
    assert cueset.policy_floors.export_ready_floor == pytest.approx(0.9)
    assert cueset.policy_floors.review_floor == pytest.approx(0.55)
    assert cueset.summary.total_count == len(cueset.cues)
    assert cueset.summary.preserved_dj_count == 1
    assert cueset.summary.machine_count == len(cueset.cues) - 1
    assert cueset.summary.auto_count >= 1
    assert cueset.summary.anlz_count >= 1

    by_slot = {cue.slot: cue for cue in cueset.cues}
    assert by_slot["B"].source == "dj"
    assert by_slot["B"].confidence_band == "preserved_dj"
    assert by_slot["A"].source == "auto"
    assert by_slot["A"].confidence_band == "review"
    assert by_slot["D"].source == "anlz"
    assert by_slot["D"].confidence_band == "export_ready"

    round_tripped = cue_set_from_dict(cue_set_to_dict(cueset))
    assert round_tripped == cueset


def test_land_requires_per_call_permission(tmp_path: Path) -> None:
    cueset = cue_set_from_anchors(_track(), [_anchor("intro", 0.0)])

    with pytest.raises(PermissionError, match="permission"):
        land(cueset, ExportTarget.rekordbox_xml(tmp_path / "cues.xml"), granted=False)


def test_land_refuses_unknown_sources(tmp_path: Path) -> None:
    cueset = cue_set_from_anchors(_track(), [_anchor("intro", 0.0)])
    bad = replace(cueset.cues[0], source="ghost")  # type: ignore[arg-type]
    bad_set = replace(cueset, cues=(bad,))

    with pytest.raises(ValueError, match="unknown source"):
        land(bad_set, ExportTarget.rekordbox_xml(tmp_path / "cues.xml"), granted=True)


def test_land_refuses_dj_cue_spoofing_machine_prefix(tmp_path: Path) -> None:
    cueset = cue_set_from_anchors(
        _track(cues=(_dj_cue(1, 12.0, "VM SPOOF"),)),
        [],
        include_preserved=True,
    )

    with pytest.raises(ValueError, match="reserved VM prefix"):
        land(cueset, ExportTarget.rekordbox_xml(tmp_path / "cues.xml"), granted=True)


def test_land_rekordbox_xml_stamps_machine_cues_and_preserves_dj(tmp_path: Path) -> None:
    pytest.importorskip("pyrekordbox")
    track = _track(cues=(_dj_cue(1, 12.0, "MY B"),))
    cueset = cue_set_from_anchors(
        track,
        [_anchor("intro", 0.0), _anchor("drop", 64.0)],
        include_preserved=True,
    )

    receipt = land(
        cueset,
        ExportTarget.rekordbox_xml(tmp_path / "landed.xml", name="Landed"),
        granted=True,
    )

    assert receipt.written_count == len(cueset.cues)
    assert receipt.kept_dj_count == 1
    assert receipt.skipped_count == 0
    marks = _parse_marks(Path(receipt.path))
    names = [mark.attrib["Name"] for mark in marks]
    assert "MY B" in names
    assert any(name.startswith("VM ") for name in names)
    assert "VM MY B" not in names


def test_land_m3u8_uses_order_only_carrier(tmp_path: Path) -> None:
    cueset = cue_set_from_anchors(_track(filepath="/music/new.mp3"), [_anchor("intro", 0.0)])

    receipt = land(cueset, ExportTarget.m3u8(tmp_path / "crate.m3u8"), granted=True)

    assert receipt.path.endswith("crate.m3u8")
    assert receipt.written_count == 0
    assert Path(receipt.path).read_text(encoding="utf-8").splitlines()[-1] == "/music/new.mp3"
