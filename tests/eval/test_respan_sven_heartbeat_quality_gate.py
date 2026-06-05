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


def test_describe_bank_census_replay_silence_summary_passes_all_suppressed() -> None:
    kept, report = judge.describe_bank_census(
        [
            {"id": "0001_HEARTBEAT", "event": "HEARTBEAT", "line": "describe-bank"},
            {"id": "0002_PHASE", "event": "PHASE", "line": "more narration"},
            {"id": "0003_KICK_SWAP", "event": "KICK_SWAP", "line": "bare priority"},
        ]
    )
    summary = judge.census_silence_summary(report, min_rows=3)

    assert kept == []
    assert report["silenced_by_describe_bank_census"] == 3
    assert summary["pass"] is True
    assert summary["failures"] == []


def test_describe_bank_census_replay_silence_summary_fails_kept_rows() -> None:
    _kept, report = judge.describe_bank_census(
        [
            {
                "id": "0001_DROP",
                "event": "DROP",
                "line": "this priority event still needs a judge",
            },
        ]
    )
    summary = judge.census_silence_summary(report, min_rows=1)

    assert summary["pass"] is False
    assert "kept_for_judge 1 > 0" in summary["failures"]
