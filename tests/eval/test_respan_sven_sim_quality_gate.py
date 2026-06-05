# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse

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


def test_strict_sven_gate_enables_live_parity_quality_flags() -> None:
    args = argparse.Namespace(
        strict_sven_gate=True,
        match_live_persona=False,
        match_live_linter=False,
        include_kick_density_target=False,
        require_quality=False,
        gate_only=False,
    )

    out = sim._apply_strict_sven_gate_flags(args)

    assert out.match_live_persona is True
    assert out.match_live_linter is True
    assert out.include_kick_density_target is True
    assert out.require_quality is True


def test_strict_sven_gate_opt_out_preserves_manual_flags() -> None:
    args = argparse.Namespace(
        strict_sven_gate=False,
        match_live_persona=False,
        match_live_linter=True,
        include_kick_density_target=False,
        require_quality=False,
        gate_only=False,
    )

    out = sim._apply_strict_sven_gate_flags(args)

    assert out.match_live_persona is False
    assert out.match_live_linter is True
    assert out.include_kick_density_target is False
    assert out.require_quality is False


def test_strict_sven_gate_allows_gate_only_routing_smoke() -> None:
    args = argparse.Namespace(
        strict_sven_gate=True,
        match_live_persona=False,
        match_live_linter=False,
        include_kick_density_target=False,
        require_quality=False,
        gate_only=True,
    )

    out = sim._apply_strict_sven_gate_flags(args)

    assert out.match_live_persona is True
    assert out.match_live_linter is True
    assert out.include_kick_density_target is True
    assert out.require_quality is False


def test_kick_density_target_seeds_live_linter_event_ref() -> None:
    registry = sim._registry_for_sim(sim.KICK_DENSITY_TARGET, {})

    lint = sim.CitationLinter().check(
        "Use the added space before the next layer. [ev:KICK_DENSITY_SHIFT@1281.0]",
        registry.snapshot(),
        mode="live",
    )

    assert lint.valid is True


def test_line_or_silence_keeps_empty_model_silent() -> None:
    line, model_line, suppressed = sim._line_or_silence("")

    assert line == ""
    assert model_line == ""
    assert suppressed is False


def test_line_or_silence_strips_broken_model_fragment() -> None:
    line, model_line, suppressed = sim._line_or_silence(
        ':* "This sub is heavy--hold this groove until the phrase breaks at 10'
    )

    assert line == ""
    assert model_line == ""
    assert suppressed is True


def test_line_or_silence_strips_unclosed_citation_tail() -> None:
    line, model_line, suppressed = sim._line_or_silence(
        "Hold this heavy sub until the next phrase boundary [cue:phrase_boundary@10"
    )

    assert line == ""
    assert model_line == ""
    assert suppressed is True


def test_live_linter_mode_strips_uncited_grounded_receipt_instead_of_substituting() -> None:
    ev_extra = {"next_suggestion_voice_line": sim._FORWARD_READ_RECEIPT}
    registry = sim._registry_for_sim({"evidence": ""}, ev_extra)

    line, model_line, live_linter = sim._live_linter_checked_line(
        "That darker 9A roller is ready next.",
        "That darker 9A roller is ready next.",
        registry=registry,
    )

    assert line == ""
    assert model_line == ""
    assert live_linter["action"] == "strip"
    assert live_linter["valid"] is False


def test_live_linter_mode_strips_uncitable_model_citation_without_fallback() -> None:
    registry = sim._registry_for_sim(
        {"evidence": "grounding_refs[[midi:A_filter:_flat_to_cut_big_twist@612.4]]"},
        {},
    )

    line, model_line, live_linter = sim._live_linter_checked_line(
        "Let this roll [track:Raik - Trio d'Acid].",
        "Let this roll [track:Raik - Trio d'Acid].",
        registry=registry,
    )

    assert line == ""
    assert model_line == ""
    assert live_linter["action"] == "strip"
    assert live_linter["valid"] is False
    assert live_linter["reason"] == "no_citations"


def test_live_linter_mode_strips_registered_kick_event_instead_of_substituting() -> None:
    ev_extra = {"prev_density": 6.0, "new_density": 4.5, "delta": -1.5}
    registry = sim._registry_for_sim(sim.KICK_DENSITY_TARGET, ev_extra)

    line, model_line, live_linter = sim._live_linter_checked_line(
        "Bring a bright layer into the space. [",
        "Bring a bright layer into the space. [",
        registry=registry,
    )

    assert line == ""
    assert model_line == ""
    assert live_linter["action"] == "strip"
    assert live_linter["valid"] is False


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
