# SPDX-License-Identifier: Apache-2.0
"""ipc.learn.live_grade envelope contract."""
from __future__ import annotations

import json

from vibemix.ui_bus.learn_messages import LearnLiveGrade
from vibemix.ui_bus.messages import _VALIDATOR


def test_live_grade_roundtrips_locked_with_citation() -> None:
    env = LearnLiveGrade.make(
        verdict="locked",
        phase_error_beats=0.0,
        score=1.0,
        citation="[ev:BEATMATCH_GRADED@12.345]",
    )
    wire = json.loads(env.to_json())

    assert wire["type"] == "ipc.learn.live_grade"
    assert wire["payload"] == {
        "verdict": "locked",
        "phase_error_beats": 0.0,
        "score": 1.0,
        "citation": "[ev:BEATMATCH_GRADED@12.345]",
        "save_landed": False,
        "save_from_verdict": None,
        "save_from_phase_error_beats": None,
        "save_recovery_delta_beats": None,
        "save_attempt_active": False,
        "save_floor_seconds_total": None,
        "save_floor_seconds_remaining": None,
        "save_floor_expired": False,
        "save_difficulty_level": 1,
        "save_streak": 0,
    }
    _VALIDATOR.validate(wire)


def test_live_grade_roundtrips_uncited_drift() -> None:
    env = LearnLiveGrade.make(
        verdict="drifting",
        phase_error_beats=0.125,
        score=0.375,
        citation=None,
    )
    wire = json.loads(env.to_json())

    assert wire["payload"]["citation"] is None
    assert wire["payload"]["save_landed"] is False
    assert wire["payload"]["save_attempt_active"] is False
    _VALIDATOR.validate(wire)


def test_live_grade_roundtrips_save_landed_edge() -> None:
    env = LearnLiveGrade.make(
        verdict="locked",
        phase_error_beats=0.0,
        score=1.0,
        citation="[ev:BEATMATCH_GRADED@19.000]",
        save_landed=True,
        save_from_verdict="drifting",
        save_from_phase_error_beats=0.06,
        save_recovery_delta_beats=0.06,
        save_attempt_active=False,
        save_floor_seconds_total=14.0,
        save_floor_seconds_remaining=9.25,
        save_difficulty_level=1,
        save_streak=1,
    )
    wire = json.loads(env.to_json())

    assert wire["payload"]["save_landed"] is True
    assert wire["payload"]["save_from_verdict"] == "drifting"
    assert wire["payload"]["save_from_phase_error_beats"] == 0.06
    assert wire["payload"]["save_recovery_delta_beats"] == 0.06
    assert wire["payload"]["save_floor_seconds_total"] == 14.0
    assert wire["payload"]["save_floor_seconds_remaining"] == 9.25
    assert wire["payload"]["save_difficulty_level"] == 1
    assert wire["payload"]["save_streak"] == 1
    _VALIDATOR.validate(wire)


def test_live_grade_roundtrips_save_floor_expired() -> None:
    env = LearnLiveGrade.make(
        verdict="trainwreck",
        phase_error_beats=-0.28,
        score=0.0,
        citation=None,
        save_floor_expired=True,
        save_floor_seconds_total=8.0,
        save_floor_seconds_remaining=0.0,
        save_difficulty_level=4,
    )
    wire = json.loads(env.to_json())

    assert wire["payload"]["save_floor_expired"] is True
    assert wire["payload"]["save_attempt_active"] is False
    assert wire["payload"]["save_floor_seconds_remaining"] == 0.0
    assert wire["payload"]["save_difficulty_level"] == 4
    _VALIDATOR.validate(wire)
