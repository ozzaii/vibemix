# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from scripts.eval import respan_sven_heartbeat_judge as judge


def _row(
    *,
    friend: int = 3,
    grounded: int = 3,
    earned: int = 3,
    move: int = 3,
    voice: int = 3,
    should_speak: bool = True,
) -> dict:
    return {
        "id": "fixture",
        "event": "MANUAL",
        "line": "Hold this for four bars, then move on the phrase.",
        "scores": {
            "friend_not_narrator": friend,
            "grounded_not_fabricated": grounded,
            "earned_not_constant": earned,
            "move_specific_not_spectrum": move,
            "voice_no_slop": voice,
            "should_speak": should_speak,
            "why": "fixture",
        },
    }


def test_quality_summary_passes_real_line_floor() -> None:
    summary = judge.quality_summary([_row()], min_judged=1, errors=0)

    assert summary["judged"] == 1
    assert summary["dim_means"]["grounded_not_fabricated"] == 3
    assert summary["failures"] == []


def test_quality_summary_fails_low_dimensions() -> None:
    summary = judge.quality_summary(
        [_row(friend=1, grounded=2, earned=1, voice=1)],
        min_judged=1,
        errors=0,
    )

    assert "mean friend_not_narrator 1.0 below 2" in summary["failures"]
    assert "mean grounded_not_fabricated 2.0 below 2.4" in summary["failures"]
    assert "mean earned_not_constant 1.0 below 2" in summary["failures"]
    assert "mean voice_no_slop 1.0 below 2" in summary["failures"]


def test_quality_summary_fails_should_not_have_spoken() -> None:
    summary = judge.quality_summary([_row(should_speak=False)], min_judged=1, errors=0)

    assert "should_NOT_have_spoken 1 > 0" in summary["failures"]


def test_quality_summary_fails_minimum_rows_and_errors() -> None:
    summary = judge.quality_summary([], min_judged=2, errors=1)

    assert "judged rows 0 below minimum 2" in summary["failures"]
    assert "judge errors 1 > 0" in summary["failures"]
    assert "no judged dim means" in summary["failures"]
