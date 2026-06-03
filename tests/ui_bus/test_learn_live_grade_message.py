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
    _VALIDATOR.validate(wire)
