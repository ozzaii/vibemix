# SPDX-License-Identifier: Apache-2.0
"""Phase 25 Plan 25-03 Task 2 — DEBRIEF IPC schema roundtrip + validation tests.

Covers the 3 architectural-slot wrappers reserved for v2.1 implementation:
``DebriefSessionLoaded`` / ``DebriefCitationSummary`` / ``DebriefEventTimeline``.

The wrappers' ``.to_json()`` method runs through ``_serialize`` which in
turn calls ``jsonschema.Draft7Validator.validate`` — so a wrapper produced
with invalid field values raises ``jsonschema.ValidationError`` at JSON
emit time. Each "rejects" test exploits that path.
"""

from __future__ import annotations

import json

import jsonschema
import pytest

from vibemix.ui_bus import (
    DebriefCitationSummary,
    DebriefEventTimeline,
    DebriefSessionLoaded,
)
from vibemix.ui_bus.messages import _SCHEMA


def test_debrief_session_loaded_roundtrip():
    """Wrapper → JSON → parse → schema-validate."""
    msg = DebriefSessionLoaded.make(
        session_id="20260513-210410",
        started_at=1715616250.0,
        duration_s=5040.0,
    )
    raw = msg.to_json()
    parsed = json.loads(raw)
    assert parsed["type"] == "ipc.debrief.session-loaded"
    assert parsed["payload"]["session_id"] == "20260513-210410"
    assert parsed["payload"]["started_at"] == 1715616250.0
    assert parsed["payload"]["duration_s"] == 5040.0
    jsonschema.validate(parsed, _SCHEMA)


def test_debrief_citation_summary_roundtrip():
    """4-int payload roundtrips cleanly."""
    msg = DebriefCitationSummary.make(total=120, valid=95, stripped=20, bypassed=5)
    raw = msg.to_json()
    parsed = json.loads(raw)
    assert parsed["type"] == "ipc.debrief.citation-summary"
    payload = parsed["payload"]
    assert payload["total"] == 120
    assert payload["valid"] == 95
    assert payload["stripped"] == 20
    assert payload["bypassed"] == 5
    jsonschema.validate(parsed, _SCHEMA)


def test_debrief_event_timeline_roundtrip_tuple_becomes_list():
    """Tuple events normalize to a JSON array on emit (schema requires array)."""
    events = (
        {"t": 0.0, "kind": "session_start"},
        {"t": 3.21, "kind": "trigger", "reason": "phase_change"},
    )
    msg = DebriefEventTimeline.make(events=events)
    raw = msg.to_json()
    parsed = json.loads(raw)
    assert parsed["type"] == "ipc.debrief.event-timeline"
    assert isinstance(parsed["payload"]["events"], list)
    assert len(parsed["payload"]["events"]) == 2
    assert parsed["payload"]["events"][1]["reason"] == "phase_change"
    jsonschema.validate(parsed, _SCHEMA)


def test_debrief_event_timeline_accepts_list_input():
    """``.make`` accepts list input for ergonomics; normalizes to tuple internally."""
    msg = DebriefEventTimeline.make(
        events=[{"t": 1.0, "kind": "kick_drop"}],
    )
    assert isinstance(msg.payload.events, tuple)
    parsed = json.loads(msg.to_json())
    assert parsed["payload"]["events"] == [{"t": 1.0, "kind": "kick_drop"}]


def test_debrief_session_loaded_rejects_negative_started_at():
    """Schema enforces ``started_at: number minimum: 0``."""
    msg = DebriefSessionLoaded.make(
        session_id="x", started_at=-1.0, duration_s=10.0
    )
    with pytest.raises(jsonschema.ValidationError):
        msg.to_json()


def test_debrief_session_loaded_rejects_negative_duration():
    """Schema enforces ``duration_s: number minimum: 0``."""
    msg = DebriefSessionLoaded.make(
        session_id="x", started_at=1.0, duration_s=-5.0
    )
    with pytest.raises(jsonschema.ValidationError):
        msg.to_json()


def test_debrief_session_loaded_rejects_empty_session_id():
    """``session_id`` schema has ``minLength: 1``."""
    msg = DebriefSessionLoaded.make(
        session_id="", started_at=1.0, duration_s=10.0
    )
    with pytest.raises(jsonschema.ValidationError):
        msg.to_json()


def test_debrief_citation_summary_rejects_negative_count():
    """All 4 counts are ``minimum: 0`` in the schema."""
    msg = DebriefCitationSummary.make(total=-1, valid=0, stripped=0, bypassed=0)
    with pytest.raises(jsonschema.ValidationError):
        msg.to_json()


def test_debrief_event_timeline_accepts_empty_events():
    """An empty events tuple is valid — the v2.1 UI will render "no events"."""
    msg = DebriefEventTimeline.make(events=())
    raw = msg.to_json()
    parsed = json.loads(raw)
    assert parsed["payload"]["events"] == []
    jsonschema.validate(parsed, _SCHEMA)


def test_debrief_event_timeline_requires_t_per_event():
    """Each event dict must have ``t`` (required by schema)."""
    msg = DebriefEventTimeline.make(events=({"kind": "trigger"},))
    with pytest.raises(jsonschema.ValidationError):
        msg.to_json()


def test_debrief_event_timeline_requires_kind_per_event():
    """Each event dict must have ``kind`` (required by schema)."""
    msg = DebriefEventTimeline.make(events=({"t": 1.0},))
    with pytest.raises(jsonschema.ValidationError):
        msg.to_json()


def test_debrief_event_timeline_allows_additional_event_properties():
    """``additionalProperties: true`` on event rows — v2.1 can grow fields."""
    msg = DebriefEventTimeline.make(
        events=({"t": 1.0, "kind": "trigger", "extra_v2_1_field": "ok"},),
    )
    raw = msg.to_json()
    parsed = json.loads(raw)
    assert parsed["payload"]["events"][0]["extra_v2_1_field"] == "ok"


def test_debrief_wrappers_are_frozen_dataclasses():
    """``frozen=True`` + ``slots=True`` matches the Phase 11 dataclass convention."""
    msg = DebriefSessionLoaded.make(session_id="x", started_at=1.0, duration_s=10.0)
    with pytest.raises((AttributeError, Exception)):
        msg.type = "different"  # type: ignore[misc]
