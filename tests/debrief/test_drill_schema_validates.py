# SPDX-License-Identifier: Apache-2.0
"""DEBRIEF-06: Drill / Drills Pydantic schema enforces exactly-3 + 5 fields."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from vibemix.debrief.drills import Drill, Drills


def _ok_drill(idx: int = 0) -> Drill:
    return Drill(
        situation=f"Situation {idx}",
        behavior=f"Behavior [ev:MIX_MOVE@01:0{idx}]",
        impact=f"Impact [ev:PHASE@01:1{idx}]",
        action_recommended=f"Action [track:t{idx}]",
        citation=f"[ev:MIX_MOVE@01:0{idx}]",
    )


def test_three_valid_drills_parses_clean():
    drills = Drills(drills=[_ok_drill(0), _ok_drill(1), _ok_drill(2)])
    assert len(drills.drills) == 3


def test_only_2_drills_raises_validation():
    with pytest.raises(ValidationError):
        Drills(drills=[_ok_drill(0), _ok_drill(1)])


def test_four_drills_raises_validation():
    with pytest.raises(ValidationError):
        Drills(drills=[_ok_drill(i) for i in range(4)])


def test_missing_field_raises_validation():
    with pytest.raises(ValidationError):
        Drill(  # type: ignore[call-arg]
            situation="x",
            behavior="x",
            impact="x",
            # action_recommended missing
            citation="[ev:x@1]",
        )


def test_empty_string_field_raises_validation():
    with pytest.raises(ValidationError):
        Drill(
            situation="",
            behavior="b",
            impact="i",
            action_recommended="a",
            citation="[ev:x@1]",
        )


def test_model_validate_json_roundtrip():
    """Mock-shaped Gemini structured-output payload roundtrips."""
    raw = (
        '{"drills": ['
        + ",".join(
            f'{{"situation":"S{i}","behavior":"B [ev:M@1]","impact":"I [ev:P@2]",'
            f'"action_recommended":"A [track:t{i}]","citation":"[ev:M@1]"}}'
            for i in range(3)
        )
        + "]}"
    )
    drills = Drills.model_validate_json(raw)
    assert len(drills.drills) == 3
    assert drills.drills[0].situation == "S0"
