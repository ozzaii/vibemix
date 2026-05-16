# SPDX-License-Identifier: Apache-2.0
"""Plan 29-03 Task 1 — Roundtrip tests for the 6 new debrief wrappers.

Mirrors the Phase 25 ``test_debrief_schemas.py`` style. Each wrapper:
- has ``frozen=True, slots=True``
- has a ``.make()`` factory + ``.to_json()`` method
- validates against the schema at JSON emit time
"""

from __future__ import annotations

import json

import jsonschema
import pytest

from vibemix.ui_bus import (
    ChapterRegionPayload,
    DebriefChapterList,
    DebriefCitationTooltip,
    DebriefCitationTooltipReq,
    DebriefDrills,
    DebriefError,
    DebriefTldrAudio,
    DrillPayload,
)
from vibemix.ui_bus.messages import _SCHEMA


# ---------------------------------------------------------------------------
# DebriefChapterList
# ---------------------------------------------------------------------------


def _sample_chapter(idx: int = 0) -> ChapterRegionPayload:
    return ChapterRegionPayload(
        id=f"track-{idx:02d}",
        start=float(idx * 300),
        end=float((idx + 1) * 300),
        label=f"Track {idx + 1}: Opening",
        kind="track",
        citation_event_id=f"ev:TRACK_CHANGE@{idx * 5:02d}:00",
    )


def test_debrief_chapter_list_roundtrip():
    msg = DebriefChapterList.make(
        chapters=(_sample_chapter(0), _sample_chapter(1)),
        derived_at="2026-05-15T11:21:39.656+00:00",
    )
    parsed = json.loads(msg.to_json())
    assert parsed["type"] == "ipc.debrief.chapter-list"
    assert len(parsed["payload"]["chapters"]) == 2
    assert parsed["payload"]["chapters"][0]["kind"] == "track"
    jsonschema.validate(parsed, _SCHEMA)


def test_debrief_chapter_list_accepts_empty_chapters():
    msg = DebriefChapterList.make(
        chapters=(),
        derived_at="2026-05-15T11:21:39.656+00:00",
    )
    parsed = json.loads(msg.to_json())
    assert parsed["payload"]["chapters"] == []


def test_debrief_chapter_list_rejects_invalid_kind():
    msg = DebriefChapterList.make(
        chapters=(
            ChapterRegionPayload(
                id="x",
                start=0.0,
                end=1.0,
                label="x",
                kind="bogus",
                citation_event_id="ev:x@0",
            ),
        ),
        derived_at="2026-05-15T11:21:39.656+00:00",
    )
    with pytest.raises(jsonschema.ValidationError):
        msg.to_json()


# ---------------------------------------------------------------------------
# DebriefTldrAudio
# ---------------------------------------------------------------------------


def test_debrief_tldr_audio_roundtrip():
    msg = DebriefTldrAudio.make(
        audio_relative_path="debrief_tldr.mp3",
        duration_s=75.0,
        tldr_sha256="a" * 64,
        mime_type="audio/mpeg",
    )
    parsed = json.loads(msg.to_json())
    assert parsed["type"] == "ipc.debrief.tldr-audio"
    assert parsed["payload"]["mime_type"] == "audio/mpeg"
    jsonschema.validate(parsed, _SCHEMA)


def test_debrief_tldr_audio_rejects_wrong_mime():
    msg = DebriefTldrAudio.make(
        audio_relative_path="debrief_tldr.wav",
        duration_s=75.0,
        tldr_sha256="a" * 64,
        mime_type="audio/wav",
    )
    with pytest.raises(jsonschema.ValidationError):
        msg.to_json()


# ---------------------------------------------------------------------------
# DebriefDrills (DEBRIEF-06: exactly 3)
# ---------------------------------------------------------------------------


def _sample_drill(idx: int = 0) -> DrillPayload:
    return DrillPayload(
        situation=f"Drill {idx} situation",
        behavior=f"Behavior [ev:MIX_MOVE@01:0{idx}]",
        impact=f"Impact [ev:PHASE@01:1{idx}]",
        action_recommended=f"Action [track:t{idx}]",
        citation=f"[ev:MIX_MOVE@01:0{idx}]",
    )


def test_debrief_drills_roundtrip_exactly_3():
    msg = DebriefDrills.make(
        drills=tuple(_sample_drill(i) for i in range(3)),
    )
    parsed = json.loads(msg.to_json())
    assert parsed["type"] == "ipc.debrief.drills"
    assert len(parsed["payload"]["drills"]) == 3
    jsonschema.validate(parsed, _SCHEMA)


def test_debrief_drills_rejects_only_2():
    msg = DebriefDrills.make(drills=tuple(_sample_drill(i) for i in range(2)))
    with pytest.raises(jsonschema.ValidationError):
        msg.to_json()


def test_debrief_drills_rejects_4():
    msg = DebriefDrills.make(drills=tuple(_sample_drill(i) for i in range(4)))
    with pytest.raises(jsonschema.ValidationError):
        msg.to_json()


# ---------------------------------------------------------------------------
# DebriefCitationTooltipReq + DebriefCitationTooltip
# ---------------------------------------------------------------------------


def test_debrief_citation_tooltip_request_roundtrip():
    msg = DebriefCitationTooltipReq.make(event_id="ev:MIX_MOVE@01:23")
    parsed = json.loads(msg.to_json())
    assert parsed["type"] == "ipc.debrief.citation-tooltip-request"
    assert parsed["payload"]["event_id"] == "ev:MIX_MOVE@01:23"
    jsonschema.validate(parsed, _SCHEMA)


def test_debrief_citation_tooltip_response_roundtrip():
    msg = DebriefCitationTooltip.make(
        event_id="ev:MIX_MOVE@01:23",
        evidence_text="A_filter boost at 1:23",
        timestamp=83.0,
        found=True,
    )
    parsed = json.loads(msg.to_json())
    assert parsed["type"] == "ipc.debrief.citation-tooltip"
    assert parsed["payload"]["found"] is True
    jsonschema.validate(parsed, _SCHEMA)


def test_debrief_citation_tooltip_not_found_path():
    msg = DebriefCitationTooltip.make(
        event_id="bogus", evidence_text="", timestamp=0.0, found=False
    )
    parsed = json.loads(msg.to_json())
    assert parsed["payload"]["found"] is False
    jsonschema.validate(parsed, _SCHEMA)


# ---------------------------------------------------------------------------
# DebriefError
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "reason",
    [
        "events_missing",
        "session_too_short",
        "invalid_session_dir",
        "sidecar_crashed",
        "tldr_generation_failed",
        "drills_generation_failed",
        "port_in_use",
        "unknown_kind",
    ],
)
def test_debrief_error_each_reason_allowed(reason: str):
    msg = DebriefError.make(reason=reason, message="detail")
    parsed = json.loads(msg.to_json())
    assert parsed["payload"]["reason"] == reason
    jsonschema.validate(parsed, _SCHEMA)


def test_debrief_error_rejects_unknown_reason():
    msg = DebriefError.make(reason="bogus_reason", message="x")
    with pytest.raises(jsonschema.ValidationError):
        msg.to_json()


# ---------------------------------------------------------------------------
# All new wrappers frozen + slots
# ---------------------------------------------------------------------------


def test_all_new_wrappers_frozen():
    msg = DebriefError.make(reason="port_in_use", message="x")
    with pytest.raises((AttributeError, Exception)):
        msg.type = "different"  # type: ignore[misc]


def test_all_new_payloads_have_slots():
    """frozen=True, slots=True is the Phase 11 convention."""
    for cls in (
        ChapterRegionPayload,
        DrillPayload,
    ):
        assert hasattr(cls, "__slots__"), f"{cls.__name__} missing __slots__"
