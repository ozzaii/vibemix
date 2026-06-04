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


def test_quality_summary_can_target_optional_kick_density_scenario() -> None:
    rows = _passing_results()
    rows.append(
        {
            "name": "kick_density_shift_sparser",
            "event": "KICK_DENSITY_SHIFT",
            "gate": "speak",
            "gate_reason": "event_priority",
            "expect": "speak",
            "gate_ok": True,
            "line": "Use the added space for the next layer.",
            "model_line": "Use the added space for the next layer.",
            "raw_line": "Use the added space for the next layer.",
            "scores": _scores(friend=2, voice=2),
        }
    )

    summary = sim._quality_summary(
        rows,
        target_scenarios=sim.QUALITY_TARGET_SCENARIOS + sim.KICK_DENSITY_TARGET_SCENARIOS,
        expected_total=len(sim.SCENARIOS) + 1,
    )

    assert summary["gate_ok"] == 10
    assert summary["gate_total"] == 10
    assert summary["target_scenarios"]["kick_density_shift_sparser"]["scores"][
        "friend_not_narrator"
    ] == 2
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


def test_quality_summary_fails_when_earned_mean_stays_below_floor() -> None:
    rows = _passing_results()
    for row in rows:
        if isinstance(row.get("scores"), dict):
            row["scores"] = _scores(earned=1)

    failures = sim._quality_summary(rows)["failures"]

    assert "mean earned_not_constant 1.0 below 2" in failures


def test_quality_summary_fails_target_cue_row_marked_should_not_speak() -> None:
    rows = _passing_results()
    for row in rows:
        if row["name"] == "phase_with_cue_lookahead":
            row["scores"] = {
                **_scores(friend=2, voice=2),
                "should_speak": False,
            }

    failures = sim._quality_summary(rows)["failures"]

    assert "phase_with_cue_lookahead judge marked should_speak=false" in failures


def test_quality_summary_fails_partial_or_misrouted_runs() -> None:
    rows = _passing_results()[:-1]
    rows[0]["gate"] = "speak"
    rows[0]["gate_ok"] = False

    failures = sim._quality_summary(rows)["failures"]

    assert "expected 9 scenarios, got 8" in failures
    assert "gate routing mismatch: idle_heartbeat expected silent got speak" in failures


def test_line_or_grounded_fallback_uses_cue_receipt_when_model_is_empty() -> None:
    ev_extra = {
        "next_suggestion_voice_line": (
            "Forward cue receipt: the next citable phrase boundary is about 4 bars ahead. "
            "Use it as one forward timing nudge for what comes next if the live sound "
            "supports it. Copy this citation exactly: [cue:phrase_boundary@108.0]."
        )
    }

    line, model_line, fallback_line = sim._line_or_grounded_fallback(
        "",
        gate_reason="grounded_voice_payload",
        ev_extra=ev_extra,
    )

    assert fallback_line == (
        "Hold this for about 4 bars; make the move on the next phrase. "
        "[cue:phrase_boundary@108.0]"
    )
    assert model_line == fallback_line
    assert line == "Hold this for about 4 bars; make the move on the next phrase."


def test_line_or_grounded_fallback_replaces_broken_model_fragment() -> None:
    ev_extra = {
        "next_suggestion_voice_line": (
            "Forward cue receipt: the next citable phrase boundary is about 4 bars ahead. "
            "Use it as one forward timing nudge for what comes next if the live sound "
            "supports it. Copy this citation exactly: [cue:phrase_boundary@108.0]."
        )
    }

    line, model_line, fallback_line = sim._line_or_grounded_fallback(
        ':* "This sub is heavy--hold this groove until the phrase breaks at 10',
        gate_reason="grounded_voice_payload",
        ev_extra=ev_extra,
    )

    assert fallback_line is not None
    assert model_line == fallback_line
    assert line == "Hold this for about 4 bars; make the move on the next phrase."


def test_line_or_grounded_fallback_replaces_unclosed_citation_tail() -> None:
    ev_extra = {
        "next_suggestion_voice_line": (
            "Forward cue receipt: the next citable phrase boundary is about 4 bars ahead. "
            "Use it as one forward timing nudge for what comes next if the live sound "
            "supports it. Copy this citation exactly: [cue:phrase_boundary@108.0]."
        )
    }

    line, model_line, fallback_line = sim._line_or_grounded_fallback(
        "Hold this heavy sub until the next phrase boundary [cue:phrase_boundary@10",
        gate_reason="grounded_voice_payload",
        ev_extra=ev_extra,
    )

    assert fallback_line is not None
    assert model_line == fallback_line
    assert line == "Hold this for about 4 bars; make the move on the next phrase."


def test_line_or_grounded_fallback_replaces_incomplete_next_track_tail() -> None:
    line, model_line, fallback_line = sim._line_or_grounded_fallback(
        "Let the sub ride, then pull back before you bring in that 1",
        gate_reason="grounded_voice_payload",
        ev_extra={
            "next_suggestion_voice_line": (
                "Forward read: a darker rolling 9A track pairs next - keeps the build. "
                "Copy these citations exactly: [track:track-42] [mix:next_suggestion=track-42]."
            )
        },
    )

    assert fallback_line is not None
    assert model_line == fallback_line
    assert line == "Line up a darker rolling 9A track next to keep this build moving."


def test_run_heartbeat_judge_propagates_required_quality_gate(monkeypatch) -> None:
    calls: list[list[str]] = []

    def fake_call(cmd: list[str]) -> int:
        calls.append(cmd)
        return 0

    monkeypatch.setattr(sim.subprocess, "call", fake_call)

    rc = sim._run_heartbeat_judge(
        session="/tmp/session",
        out="/tmp/out.json",
        dry_run=False,
        no_log=True,
        require_quality=True,
    )

    assert rc == 0
    assert len(calls) == 1
    cmd = calls[0]
    assert "--describe-bank-census" in cmd
    assert "--require-quality" in cmd
    assert cmd[cmd.index("--min-judged") + 1] == "1"
    assert "--no-log" in cmd
    assert cmd[cmd.index("--out") + 1] == "/tmp/out.json"
