# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from vibemix.debrief.main import _build_cited_critique, _near_miss_receipt_text
from vibemix.debrief.near_miss_detector import NearMissResult
from vibemix.debrief.stripper import assert_all_cited, strip_uncited_sentences


def test_debrief_critique_emits_cited_line_for_judged_transition() -> None:
    critique = _build_cited_critique(
        [
            {
                "t": 128.4,
                "kind": "transition_judged",
                "verdict_state": "judged",
                "score": 0.71,
                "components": {"harmonic": 0.75, "bass_collision": 1.0},
                "citation_id": "judge:transition@128.4",
                "track_a": "a",
                "track_b": "b",
            }
        ],
        [],
    )

    assert "[judge:transition@128.4]" in critique
    assert "compatible keys" in critique
    assert "clean low end, one bass ducked" in critique
    assert "blend score 0.71/1" in critique
    cleaned, dropped = strip_uncited_sentences(critique)
    assert cleaned == critique
    assert dropped == 0
    assert_all_cited(critique)


def test_debrief_critique_skips_abstain_transition() -> None:
    critique = _build_cited_critique(
        [
            {
                "kind": "transition_judged",
                "verdict_state": "abstained",
                "score": None,
                "abstain_reason": "routing_disabled",
            }
        ],
        [],
    )

    assert critique == ""
    assert "routing_disabled" not in critique


def test_debrief_critique_judged_clash() -> None:
    critique = _build_cited_critique(
        [
            {
                "kind": "transition_judged",
                "verdict_state": "judged",
                "score": 0.2,
                "components": {"harmonic": 0.0, "bass_collision": 0.0},
                "citation_id": "judge:transition@64.0",
            }
        ],
        [],
    )

    assert "key clash" in critique
    assert "both basslines up, low-end mud" in critique
    assert_all_cited(critique)


def test_debrief_critique_includes_learn_grade_receipts() -> None:
    critique = _build_cited_critique(
        [
            {
                "kind": "learn_control_practice_graded",
                "lesson_id": "L1.03",
                "step_id": "eq",
                "evidence_time": 12.5,
                "control": "eq_hi",
                "deck": "A",
                "skill_id": "eq_mixing",
                "credited": ["eq_mixing"],
            },
            {
                "kind": "learn_beatmatch_practice_graded",
                "lesson_id": "L2.01",
                "step_id": "lock",
                "evidence_time": 42.4,
                "verdict": "locked",
                "credited": ["beatmatching"],
            },
            {
                "kind": "learn_cue_placement_practice_graded",
                "lesson_id": "L3.06",
                "step_id": "drop",
                "evidence_time": 64.0,
                "verdict": "drop_locked",
                "credited": ["phrasing_performance"],
            },
            {
                "kind": "learn_harmonic_practice_graded",
                "lesson_id": "L2.11",
                "step_id": "pair",
                "evidence_time": 91.25,
                "source_track_id": "track:source",
                "target_track_id": "track:target",
                "relation": "compatible neighbors",
                "credited": ["harmonic_mixing"],
            },
        ],
        [],
    )

    assert "control practice graded eq_hi:A for eq_mixing" in critique
    assert "[ev:CONTROL_PRACTICE_GRADED@12.500]" in critique
    assert "beatmatch practice graded locked" in critique
    assert "[ev:BEATMATCH_GRADED@42.400]" in critique
    assert "cue placement practice graded drop_locked" in critique
    assert "[ev:CUE_PLACEMENT_GRADED@64.000]" in critique
    assert "harmonic practice graded compatible neighbors" in critique
    assert "[ev:HARMONIC_PRACTICE_GRADED@91.250]" in critique
    assert_all_cited(critique)


def test_near_miss_receipt_adds_wall_clock_and_matching_judge_context() -> None:
    near_miss = NearMissResult(
        t_center_s=42.0,
        window_start_s=36.0,
        window_end_s=46.0,
        depth_beats=0.16,
        recovery_bars=2.0,
        confidence=0.82,
        bpm=120.0,
        phase_error_beats_peak=0.16,
        citation="[mix:near_miss@42.000]",
        event_type="MIX_MOVE",
        event_t_s=40.0,
    )
    events = [
        {
            "t": 0.0,
            "kind": "session_start",
            "wall_clock_iso": "2026-05-15T11:21:39+00:00",
        },
        {
            "t": 40.0,
            "kind": "transition_judged",
            "verdict_state": "judged",
            "score": 0.71,
            "components": {"harmonic": 0.75, "bass_collision": 1.0},
            "citation_id": "judge:transition@40.0",
        },
    ]

    receipt = _near_miss_receipt_text(
        near_miss,
        "the mix recovered by ear at 0:42 [mix:near_miss@42.000]",
        events,
    )

    assert "wall clock 11:22:21 last night" in receipt
    assert "[judge:transition@40.0]" in receipt
    assert "compatible keys" in receipt
    assert "clean low end" in receipt
    assert_all_cited(receipt)
