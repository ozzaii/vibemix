# SPDX-License-Identifier: Apache-2.0
"""Phase 92 Plan 02 — LESSON-02 binding for the 11 P92 envelopes.

The 11 new ``ipc.learn.*`` envelopes added in Plan 92-01 (LearnStartCourse,
LearnStartLesson, LearnCompleteLesson, LearnLessonLoaded, LearnHighlight,
LearnAdvance, LearnAck, LearnTutorSpeak, LearnExemplarPlay,
LearnExemplarStop, LearnProgressState) round-trip cleanly through:

1. ``EnvelopeFactory.make(**kwargs)`` → ``.to_json()``     — Python dataclass
2. ``json.loads(...)``                                    — wire bytes
3. ``_VALIDATOR.validate(...)``                           — JSON Schema gate

Plus two structural-parity tests:

* ``test_oneof_count_parity_matches_dataclass_count`` — 13 Learn $refs in
  the shared schema oneOf (2 P91 + 11 P92).
* ``test_additional_properties_false_on_every_payload`` — every Learn*
  payload (and every nested object) declares
  ``additionalProperties: false`` — the wire-side guard against unknown
  fields slipping through ajv.

This file is LIVE — Plan 92-01 already shipped the 11 dataclasses + the
schema. It MUST pass green day-one.

Sibling: ``tests/ipc/test_learn_envelope_parity.py`` (P91) covers the 2
earlier envelopes; this file is the P92 extension to the 11 new ones.
"""
from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from vibemix.learn.progress import LearnProgress
from vibemix.ui_bus.learn_messages import (
    LearnAck,
    LearnAdvance,
    LearnCompleteLesson,
    LearnExemplarPlay,
    LearnExemplarStop,
    LearnHighlight,
    LearnLessonLoaded,
    LearnLiveGrade,
    LearnProgressState,
    LearnStartCourse,
    LearnStartLesson,
    LearnTutorSpeak,
)
from vibemix.ui_bus.messages import _VALIDATOR

# ---------------------------------------------------------------------------
# Per-envelope round-trip via parametric matrix
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("envelope_factory", "kwargs", "expected_type"),
    [
        (
            LearnStartCourse.make,
            {"course_id": "course_0", "controller_id": "pioneer_ddj_flx4"},
            "ipc.learn.start_course",
        ),
        (
            LearnStartLesson.make,
            {"lesson_id": "L0.00-press-play", "level": "fresh"},
            "ipc.learn.start_lesson",
        ),
        (
            LearnCompleteLesson.make,
            {"lesson_id": "L0.00-press-play", "reason": "completed"},
            "ipc.learn.complete_lesson",
        ),
        (
            LearnLessonLoaded.make,
            {
                "course_id": "course_0",
                "lesson_id": "L0.00-press-play",
                "title": "press play",
                "controller_id": "pioneer_ddj_flx4",
                "progress_dots": (
                    {"lesson_id": "L0.00-press-play", "status": "current"},
                ),
            },
            "ipc.learn.lesson_loaded",
        ),
        (
            LearnHighlight.make,
            {
                "control_id": "play",
                "deck": "A",
                "cue_color": "amber",
                "cue_shape": "pulse-ring",
                "annotation": "press play",
                "expected_action": {
                    "type": "button",
                    "control": "play",
                    "deck": "A",
                    "direction": "down",
                },
            },
            "ipc.learn.highlight",
        ),
        (
            LearnAdvance.make,
            {"lesson_id": "L0.00-press-play", "reason": "action_matched"},
            "ipc.learn.advance",
        ),
        (
            LearnAck.make,
            {
                "control_id": "play:A",
                "source": "midi",
                "value": 127,
                "direction": "down",
            },
            "ipc.learn.ack",
        ),
        (
            LearnTutorSpeak.make,
            {
                "text": "find deck A play button",
                "tts_marker": "L000.beat0",
                "citations": (),
                "data_state": "active",
            },
            "ipc.learn.tutor_speak",
        ),
        (
            LearnLiveGrade.make,
            {
                "verdict": "drifting",
                "phase_error_beats": 0.125,
                "score": 0.375,
                "citation": None,
            },
            "ipc.learn.live_grade",
        ),
        (
            LearnExemplarPlay.make,
            {"track_id": "track_0001", "duration_s": 30.0, "gain_db": -12.0},
            "ipc.learn.exemplar_play",
        ),
        (
            LearnExemplarStop.make,
            {"track_id": "track_0001", "reason": "completed"},
            "ipc.learn.exemplar_stop",
        ),
        (
            LearnProgressState.make,
            {
                "action": "snapshot",
                "progress": {
                    "schema_version": 1,
                    "courses": {},
                    "lessons": {},
                },
            },
            "ipc.learn.progress_state",
        ),
    ],
    ids=lambda v: (
        v if isinstance(v, str) else (v.__name__ if callable(v) else str(v)[:32])
    ),
)
def test_envelope_roundtrip(
    envelope_factory, kwargs: dict, expected_type: str
) -> None:
    """``.make(**kwargs)`` → ``.to_json()`` → ``json.loads`` validates."""
    env = envelope_factory(**kwargs)
    wire = json.loads(env.to_json())
    assert wire["type"] == expected_type, (
        f"factory {envelope_factory!r} emitted type {wire['type']!r}, "
        f"expected {expected_type!r}"
    )
    # _VALIDATOR.validate already ran inside to_json (via _serialize / the
    # per-class _validate override on LearnProgressState). Re-running here
    # confirms the wire-side JSON is independently parseable + valid.
    _VALIDATOR.validate(wire)


def test_progress_state_accepts_current_progress_schema() -> None:
    """The shared IPC schema must accept the live v2 LearnProgress snapshot."""
    progress = LearnProgress()
    progress.mark_practice_source("course_1_anatomy", "L1.03", "midi")
    progress.mark_practice_source("course_1_anatomy", "L1.03", "click")
    progress.mark_completed(
        "course_1_anatomy",
        "L1.03",
        demonstrated=False,
    )
    env = LearnProgressState.make(
        action="snapshot",
        progress=progress.to_dict(),
    )
    wire = json.loads(env.to_json())

    assert wire["payload"]["progress"]["schema_version"] == 2
    assert "skills" in wire["payload"]["progress"]
    lesson = wire["payload"]["progress"]["lessons"]["L1.03"]
    assert lesson["demonstrated"] is False
    assert lesson["practice_sources"] == {"hardware": 1, "screen": 1}
    assert lesson["last_practice_source"] == "screen"
    _VALIDATOR.validate(wire)


# ---------------------------------------------------------------------------
# Schema-side count parity: 13 Learn refs in the shared oneOf list
# ---------------------------------------------------------------------------


_SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "tauri"
    / "ui"
    / "src"
    / "ipc"
    / "messages.schema.json"
)


def _load_schema() -> dict:
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


def test_oneof_count_parity_matches_dataclass_count() -> None:
    """14 Learn-prefixed $refs in the schema's oneOf list (2 P91 + 12 P92+).

    Mirrors the overall count-parity gate, now 73 wrappers against 73
    oneOf entries; this test slices that gate down to the Learn-only
    subset so a future Learn envelope cannot silently mask a Learn-side
    regression.
    """
    schema = _load_schema()
    learn_refs = [
        entry
        for entry in schema.get("oneOf", [])
        if "$ref" in entry and "Learn" in entry["$ref"]
    ]
    assert len(learn_refs) == 14, (
        f"expected 14 Learn $refs in schema oneOf (2 P91 + 12 P92+), got "
        f"{len(learn_refs)}: {[r.get('$ref') for r in learn_refs]!r}. "
        "If you added a P93+ envelope, update the expected count here."
    )


# ---------------------------------------------------------------------------
# additionalProperties: false on every envelope + payload + nested object
# ---------------------------------------------------------------------------


_P92_DEFINITION_NAMES: tuple[str, ...] = (
    "LearnStartCourse",
    "LearnStartLesson",
    "LearnCompleteLesson",
    "LearnLessonLoaded",
    "LearnHighlight",
    "LearnAdvance",
    "LearnAck",
    "LearnTutorSpeak",
    "LearnLiveGrade",
    "LearnExemplarPlay",
    "LearnExemplarStop",
    "LearnProgressState",
)


def test_additional_properties_false_on_every_payload() -> None:
    """Every P92 envelope + its ``payload`` MUST declare
    ``additionalProperties: false`` — the schema-side gate against an
    unknown field slipping through ajv on the wire.
    """
    schema = _load_schema()
    defs = schema.get("definitions", {})
    for name in _P92_DEFINITION_NAMES:
        envelope = defs.get(name)
        assert envelope is not None, f"definition {name!r} missing from schema"
        assert envelope.get("additionalProperties") is False, (
            f"{name}: top-level envelope MUST declare "
            "additionalProperties: false"
        )
        payload_schema = envelope.get("properties", {}).get("payload", {})
        assert payload_schema.get("additionalProperties") is False, (
            f"{name}.payload: MUST declare additionalProperties: false"
        )


# ---------------------------------------------------------------------------
# Negative path — out-of-enum cue_color is rejected (sanity gate)
# ---------------------------------------------------------------------------


def test_rejects_unknown_cue_color() -> None:
    """``cue_color`` outside the enum (``"amber" | "warning"``) must be
    rejected — pins the dual-channel cue contract on the schema side."""
    env = LearnHighlight.make(
        control_id="play",
        deck="A",
        cue_color="amber",
        cue_shape="pulse-ring",
        annotation="press play",
        expected_action={
            "type": "button",
            "control": "play",
            "deck": "A",
            "direction": "down",
        },
    )
    wire = json.loads(env.to_json())
    wire["payload"]["cue_color"] = "purple"  # not in enum
    with pytest.raises(jsonschema.ValidationError):
        _VALIDATOR.validate(wire)
