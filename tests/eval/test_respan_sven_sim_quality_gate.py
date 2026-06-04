# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from scripts.eval import respan_sven_sim as sim


def _scores(
    *,
    friend: int = 3,
    grounded: int = 3,
    earned: int = 3,
    move: int = 3,
    voice: int = 3,
) -> dict[str, int | bool | str]:
    return {
        "friend_not_narrator": friend,
        "grounded_not_fabricated": grounded,
        "earned_not_constant": earned,
        "move_specific_not_spectrum": move,
        "voice_no_slop": voice,
        "should_speak": True,
        "why": "fixture",
    }


def _passing_results() -> list[dict]:
    rows: list[dict] = []
    for scenario in sim.SCENARIOS:
        gate = scenario["expect"]
        row = {
            "name": scenario["name"],
            "event": scenario["event"],
            "gate": gate,
            "gate_reason": "fixture",
            "expect": scenario["expect"],
            "gate_ok": True,
        }
        if gate == "speak":
            row.update(
                {
                    "line": "Hold the phrase and make the next move clean.",
                    "model_line": "Hold the phrase and make the next move clean.",
                    "raw_line": "Hold the phrase and make the next move clean.",
                    "scores": _scores(),
                }
            )
        rows.append(row)
    return rows


def test_quality_summary_passes_gate_and_cue_lookahead_targets() -> None:
    summary = sim._quality_summary(_passing_results())

    assert summary["gate_ok"] == 9
    assert summary["gate_total"] == 9
    assert summary["means"]["friend_not_narrator"] == 3
    assert summary["failures"] == []


def test_quality_summary_fails_gate_only_no_score_runs() -> None:
    rows = _passing_results()
    for row in rows:
        row.pop("scores", None)

    failures = sim._quality_summary(rows)["failures"]

    assert "no judged lines were scored" in failures
    assert "phase_with_cue_lookahead has no judged scores" in failures
    assert "track_change_with_cue_lookahead has no judged scores" in failures


def test_quality_summary_fails_target_cue_rows_below_friend_or_voice_floor() -> None:
    rows = _passing_results()
    for row in rows:
        if row["name"] == "phase_with_cue_lookahead":
            row["scores"] = _scores(friend=1, voice=1)

    failures = sim._quality_summary(rows)["failures"]

    assert "phase_with_cue_lookahead friend_not_narrator 1.0 below 2" in failures
    assert "phase_with_cue_lookahead voice_no_slop 1.0 below 2" in failures


def test_quality_summary_fails_partial_or_misrouted_runs() -> None:
    rows = _passing_results()[:-1]
    rows[0]["gate"] = "speak"
    rows[0]["gate_ok"] = False

    failures = sim._quality_summary(rows)["failures"]

    assert "expected 9 scenarios, got 8" in failures
    assert "gate routing mismatch: idle_heartbeat expected silent got speak" in failures
