# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import xml.etree.ElementTree as ET

from vibemix.intel.transition_scorer import SectionRecord
from vibemix.library.export_rekordbox import export_set
from vibemix.library.rekordbox import CuePoint, TrackEntry
from vibemix.library.smart_cues import (
    proposal_to_export_marks,
    propose_smart_cues,
    slot_priority_for_genre,
    smart_cue_to_anchor,
)


def _track(*, cues=(), genre: str = "hardtechno", duration_s: float = 240.0) -> TrackEntry:
    return TrackEntry(
        track_id="trk_001",
        title="Fixture Track",
        artist="Fixture Artist",
        album="",
        bpm=120.0,
        key="8A",
        duration_s=duration_s,
        cues=tuple(cues),
        filepath="fixture://tracks/trk_001.wav",
        genre=genre,
        camelot="8A",
    )


def _section(
    section_id: str,
    role: str,
    start_s: float,
    end_s: float,
    *,
    source: str = "anlz",
    confidence: float = 0.86,
) -> SectionRecord:
    return SectionRecord(
        section_id=section_id,
        track_id="trk_001",
        role=role,
        source=source,
        source_detail="pssi" if source == "anlz" else source,
        confidence=confidence,
        start_s=start_s,
        end_s=end_s,
        start_beat=round(start_s * 2),
        end_beat=round(end_s * 2),
        bar_count=(end_s - start_s) * 120.0 / 60.0 / 4.0,
        bpm=120.0,
        camelot="8A",
    )


def _cue(
    slot_num: int,
    start_s: float,
    *,
    name: str = "",
    source: str = "dj",
    confidence: float | None = None,
) -> CuePoint:
    return CuePoint(
        name=name,
        type="cue",
        start_s=start_s,
        end_s=None,
        number=slot_num,
        source=source,
        confidence=confidence,
    )


def _by_slot(proposal):
    return {cue.slot: cue for cue in proposal.cues}


def test_fills_a_d_f_from_high_confidence_anlz_sections() -> None:
    proposal = propose_smart_cues(
        _track(),
        [
            _section("trk_001#s000", "intro", 0.0, 32.0),
            _section("trk_001#s001", "drop", 64.0, 128.0, confidence=0.91),
            _section("trk_001#s002", "outro", 192.0, 240.0, confidence=0.88),
        ],
    )

    cues = _by_slot(proposal)
    assert cues["A"].role == "mix_in"
    assert cues["D"].role == "main_drop"
    assert cues["F"].role == "mix_out"
    assert cues["A"].source == "anlz"
    assert cues["D"].review_status == "export_ready"
    assert proposal.missing_slots == ()


def test_preserves_existing_human_hot_cue_slot_and_suppresses_shadow() -> None:
    proposal = propose_smart_cues(
        _track(cues=(_cue(1, 12.0, name="MY B"),)),
        [_section("trk_001#s001", "groove", 16.0, 96.0, confidence=0.91)],
    )

    cues = _by_slot(proposal)
    assert cues["B"].source == "dj"
    assert cues["B"].export_label == "MY B"
    assert cues["B"].reason_codes == ("preserve_human_hot_cue",)
    assert any(
        item.slot == "B" and "human_slot_occupied" in item.reason_codes
        for item in proposal.suppressed_candidates
    )


def test_materialized_auto_cues_are_proposals_not_preserved_human_slots() -> None:
    proposal = propose_smart_cues(
        _track(
            cues=(
                _cue(0, 0.0, name="INTRO", source="auto", confidence=0.88),
                _cue(3, 64.0, name="DROP", source="auto", confidence=0.91),
            )
        ),
        [
            _section("trk_001#s000", "intro", 0.0, 32.0, source="auto", confidence=0.88),
            _section("trk_001#s001", "drop", 64.0, 128.0, source="auto", confidence=0.91),
        ],
    )

    cues = _by_slot(proposal)
    assert cues["A"].source == "auto"
    assert cues["D"].source == "auto"
    assert cues["A"].export_label == "VM A IN"
    assert cues["A"].reason_codes == ("high_confidence",)
    assert cues["A"].review_status == "export_ready"


def test_missing_required_slot_is_reported_not_fabricated() -> None:
    proposal = propose_smart_cues(
        _track(),
        [_section("trk_001#s000", "intro", 0.0, 32.0)],
    )

    assert proposal.missing_slots == ("D", "F")
    assert "D" not in _by_slot(proposal)
    assert "F" not in _by_slot(proposal)
    assert proposal.summary.missing_required_count == 2


def test_mid_confidence_breakdown_is_review_not_export_ready() -> None:
    proposal = propose_smart_cues(
        _track(),
        [_section("trk_001#s010", "breakdown", 96.0, 128.0, confidence=0.64)],
    )

    cue = _by_slot(proposal)["C"]
    assert cue.review_status == "review"
    assert cue.reason_codes == ("needs_review",)


def test_low_confidence_candidate_is_suppressed() -> None:
    proposal = propose_smart_cues(
        _track(),
        [_section("trk_001#s000", "intro", 0.0, 32.0, confidence=0.40)],
    )

    assert "A" not in _by_slot(proposal)
    assert any(
        "low_source_confidence" in item.reason_codes for item in proposal.suppressed_candidates
    )


def test_no_candidate_without_grounded_source() -> None:
    proposal = propose_smart_cues(
        _track(),
        [_section("trk_001#s000", "intro", 0.0, 32.0, source="llm", confidence=0.99)],
    )

    assert "A" not in _by_slot(proposal)
    assert any("no_grounded_source" in item.reason_codes for item in proposal.suppressed_candidates)


def test_genre_policy_prioritizes_b_and_f_for_techno() -> None:
    assert slot_priority_for_genre("industrial hardtechno")[:4] == ("A", "B", "F", "D")
    proposal = propose_smart_cues(_track(genre="hardtechno"), [])
    assert proposal.summary.slot_priority[:4] == ("A", "B", "F", "D")


def test_proposal_ids_and_cue_ids_are_stable() -> None:
    sections = [
        _section("trk_001#s000", "intro", 0.0, 32.0),
        _section("trk_001#s001", "drop", 64.0, 128.0),
    ]
    first = propose_smart_cues(_track(), sections)
    second = propose_smart_cues(_track(), sections)

    assert first.proposal_id == second.proposal_id
    assert [cue.cue_id for cue in first.cues] == [cue.cue_id for cue in second.cues]
    assert all(cue.cue_id.startswith(first.proposal_id + ":") for cue in first.cues)


def test_export_marks_preserve_slot_numbers_and_skip_preserved_by_default() -> None:
    proposal = propose_smart_cues(
        _track(cues=(_cue(1, 12.0, name="MY B"),)),
        [
            _section("trk_001#s000", "intro", 0.0, 32.0),
            _section("trk_001#s001", "drop", 64.0, 128.0),
            _section("trk_001#s002", "outro", 192.0, 240.0),
        ],
    )

    marks = proposal_to_export_marks(proposal)

    assert {mark["num"] for mark in marks} == {0, 3, 5}
    assert all(mark["source"] != "dj" for mark in marks)
    assert {mark["name"] for mark in marks} == {"VM A IN", "VM D DROP", "VM F OUT"}


def test_smart_cue_marks_round_trip_through_rekordbox_export(tmp_path) -> None:
    proposal = propose_smart_cues(
        _track(),
        [
            _section("trk_001#s000", "intro", 0.0, 32.0),
            _section("trk_001#s001", "drop", 64.0, 128.0),
            _section("trk_001#s002", "outro", 192.0, 240.0),
        ],
    )
    out = tmp_path / "smart-cues.xml"

    export_set(
        [
            {
                "track_id": "trk_001",
                "filepath": "/Music/fixture.wav",
                "title": "Fixture Track",
                "artist": "Fixture Artist",
                "bpm": 120.0,
                "camelot": "8A",
                "duration_s": 240.0,
                "cues": proposal_to_export_marks(proposal),
            }
        ],
        name="Smart Cues",
        out_path=out,
    )

    marks = ET.parse(out).getroot().findall(".//POSITION_MARK")
    by_name = {mark.attrib["Name"]: mark for mark in marks}
    assert by_name["VM A IN"].attrib["Num"] == "0"
    assert by_name["VM D DROP"].attrib["Num"] == "3"
    assert by_name["VM F OUT"].attrib["Num"] == "5"


def test_export_marks_can_include_review_when_selected() -> None:
    proposal = propose_smart_cues(
        _track(),
        [_section("trk_001#s010", "breakdown", 96.0, 128.0, confidence=0.64)],
    )

    assert proposal_to_export_marks(proposal) == []
    marks = proposal_to_export_marks(proposal, include_review=True)
    assert marks[0]["num"] == 2
    assert marks[0]["review_status"] == "review"


def test_smart_cue_to_anchor_keeps_legacy_contract() -> None:
    proposal = propose_smart_cues(
        _track(),
        [_section("trk_001#s001", "drop", 64.0, 128.0)],
    )
    anchor = smart_cue_to_anchor(_by_slot(proposal)["D"])

    assert anchor.label == "drop"
    assert anchor.source == "anlz"
    assert anchor.start_s == 64.0
