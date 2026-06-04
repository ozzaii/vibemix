# SPDX-License-Identifier: Apache-2.0
"""Course 3 graduation handoff must be grounded in real app seams."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

from vibemix.coach.citation_linter import CitationLinter
from vibemix.debrief.persistence import write_debrief
from vibemix.learn.graduation import (
    GraduationSummary,
    build_graduation_summary,
    build_graduation_tutor_line,
    graduation_citations,
)
from vibemix.learn.progress import LearnProgress
from vibemix.learn.runtime import LessonRuntime
from vibemix.learn.state import LearnState
from vibemix.state.evidence_registry import EvidenceRegistry


def _completed_progress(count: int) -> LearnProgress:
    progress = LearnProgress()
    for idx in range(1, count + 1):
        progress.mark_completed("course_1_anatomy", f"L1.{idx:02d}")
    return progress


def _tutor_payloads(ipc: MagicMock) -> list[dict]:
    return [
        call.args[0]["payload"]
        for call in ipc.emit.call_args_list
        if call.args and call.args[0].get("type") == "ipc.learn.tutor_speak"
    ]


def test_graduation_summary_is_honest_when_profile_and_debrief_are_missing() -> None:
    summary = build_graduation_summary(
        _completed_progress(3),
        profile_loader=lambda: None,
        consent_loader=lambda: False,
        recordings_root_loader=lambda: Path("/definitely/not/there"),
    )

    assert summary.completed_lessons == 3
    assert summary.total_lessons == 36
    assert summary.profile_consent is False
    assert summary.profile_available is False
    assert summary.debrief_available is False
    assert build_graduation_tutor_line(summary) == (
        "saved: 3/36 lessons. no debrief saved yet. profile consent off."
    )
    assert graduation_citations(summary, registry_available=True) == (
        "[screen:learn-progress]",
    )


def test_graduation_summary_reads_profile_and_latest_debrief(tmp_path: Path) -> None:
    old_session = tmp_path / "20260528-010000"
    new_session = tmp_path / "20260529-010000"
    write_debrief(old_session, {"summary": "old"}, b"old mp3")
    write_debrief(new_session, {"summary": "new"}, b"new mp3")
    profile = {
        "preferred_genre": "techno",
        "avg_session_duration": 42,
        "mix_style_tags": ["long_blends", "phrase_locked"],
        "tempo_preference_bin": "128-138",
        "event_type_response_preferences": {},
    }

    summary = build_graduation_summary(
        _completed_progress(5),
        profile_loader=lambda: profile,
        consent_loader=lambda: True,
        recordings_root_loader=lambda: tmp_path,
    )

    assert summary.profile_available is True
    assert summary.profile_genre == "techno"
    assert summary.profile_tempo_bin == "128-138"
    assert summary.profile_tags == ("long_blends", "phrase_locked")
    assert summary.debrief_available is True
    assert summary.debrief_session_dir == "20260529-010000"
    assert build_graduation_tutor_line(summary) == (
        "saved: 5/36 lessons. latest debrief: 20260529-010000. "
        "profile: techno, 128-138."
    )


def test_graduation_summary_maps_cited_debrief_action_to_next_lesson(
    tmp_path: Path,
) -> None:
    session = tmp_path / "20260529-010000"
    write_debrief(
        session,
        {
            "summary": "new",
            "drills": [
                {
                    "situation": "S",
                    "behavior": "Deck B arrived late [ev:MIX_MOVE@30.000]",
                    "impact": "The phrase landed rough [ev:MIX_MOVE@30.000]",
                    "action_recommended": (
                        "Practice phrase matching before the next transition "
                        "[ev:MIX_MOVE@30.000]"
                    ),
                    "citation": "[ev:MIX_MOVE@30.000]",
                }
            ],
        },
        b"new mp3",
    )

    summary = build_graduation_summary(
        _completed_progress(5),
        profile_loader=lambda: None,
        consent_loader=lambda: False,
        recordings_root_loader=lambda: tmp_path,
    )

    assert summary.debrief_recommended_lesson_id == "L2.12"
    assert summary.debrief_recommended_lesson_title == "phrase matching"
    assert summary.debrief_recommendation_reason == "phrase matching"
    assert build_graduation_tutor_line(summary) == (
        "saved: 5/36 lessons. latest debrief: 20260529-010000. "
        "profile consent off. next lesson from debrief: L2.12 phrase matching."
    )


def test_graduation_summary_refuses_uncited_or_unknown_debrief_advice(
    tmp_path: Path,
) -> None:
    session = tmp_path / "20260529-010000"
    write_debrief(
        session,
        {
            "summary": "new",
            "drills": [
                {
                    "situation": "S",
                    "behavior": "The set felt intense.",
                    "impact": "The room wanted more.",
                    "action_recommended": "Try a darker mood next time.",
                    "citation": "",
                }
            ],
        },
        b"new mp3",
    )

    summary = build_graduation_summary(
        _completed_progress(5),
        profile_loader=lambda: None,
        consent_loader=lambda: False,
        recordings_root_loader=lambda: tmp_path,
    )

    assert summary.debrief_recommended_lesson_id is None
    assert summary.debrief_recommended_lesson_title is None
    assert summary.debrief_recommendation_reason is None
    assert build_graduation_tutor_line(summary) == (
        "saved: 5/36 lessons. latest debrief: 20260529-010000. "
        "profile consent off."
    )


def test_graduation_line_names_practice_surface_without_counts() -> None:
    """The capstone can admire how the learner practiced without a data wall."""
    progress = _completed_progress(5)
    progress.mark_practice_source("course_1_anatomy", "L1.03", "midi")
    progress.mark_practice_source("course_1_anatomy", "L1.03", "midi")
    progress.mark_practice_source("course_1_anatomy", "L1.04", "click")

    summary = build_graduation_summary(
        progress,
        profile_loader=lambda: None,
        consent_loader=lambda: False,
        recordings_root_loader=lambda: Path("/definitely/not/there"),
    )

    assert summary.hardware_practice_actions == 2
    assert summary.screen_practice_actions == 1
    assert summary.last_practice_source == "screen"
    assert build_graduation_tutor_line(summary) == (
        "saved: 5/36 lessons. no debrief saved yet. profile consent off. "
        "practice: mostly hardware deck."
    )


def test_graduation_line_names_mixed_practice_surface() -> None:
    progress = _completed_progress(2)
    progress.mark_practice_source("course_1_anatomy", "L1.01", "midi")
    progress.mark_practice_source("course_1_anatomy", "L1.02", "click")

    summary = build_graduation_summary(
        progress,
        profile_loader=lambda: None,
        consent_loader=lambda: False,
        recordings_root_loader=lambda: Path("/definitely/not/there"),
    )

    assert build_graduation_tutor_line(summary).endswith(
        "practice: hardware + screen."
    )


def test_graduation_line_names_cited_skill_proofs_and_mastered_skills() -> None:
    progress = _completed_progress(2)
    progress.skills["deck_control"] = {
        "live_proof_count": 3,
        "mastered": True,
        "first_mastered_at": "2026-06-04T10:00:00Z",
    }
    progress.skills["eq_mixing"] = {
        "live_proof_count": 1,
        "mastered": False,
        "first_mastered_at": None,
    }

    summary = build_graduation_summary(
        progress,
        profile_loader=lambda: None,
        consent_loader=lambda: False,
        recordings_root_loader=lambda: Path("/definitely/not/there"),
    )

    assert summary.cited_skill_proofs == 4
    assert summary.mastered_skill_labels == ("deck control",)
    assert build_graduation_tutor_line(summary) == (
        "saved: 2/36 lessons. no debrief saved yet. profile consent off. "
        "proofs: 4 cited; mastered deck control."
    )


def test_l3_06_runtime_emits_registry_grounded_graduation_status() -> None:
    summary = GraduationSummary(
        completed_lessons=36,
        total_lessons=36,
        profile_consent=True,
        profile_available=True,
        profile_genre="house",
        profile_tempo_bin="120-128",
        debrief_available=True,
        debrief_session_dir="20260529-010000",
    )
    registry = EvidenceRegistry()
    ipc = MagicMock(name="ipc_router")
    runtime = LessonRuntime(
        learn_state=LearnState(),
        midi_mirror=MagicMock(name="midi_mirror"),
        controller_state=MagicMock(name="controller_state"),
        ipc_router=ipc,
        progress_store=LearnProgress(),
        evidence_registry=registry,
        evidence_clock=lambda: 18.0,
        graduation_summary_loader=lambda _progress: summary,
    )

    runtime.send(
        "load",
        lesson_id="L3.06",
        course_id="course_3_play_mode",
        controller_id="pioneer_ddj_flx4",
    )
    runtime.send("begin")

    status = next(
        payload
        for payload in _tutor_payloads(ipc)
        if payload["tts_marker"] == "L306.graduation_status"
    )
    assert status["text"] == (
        "saved: 36/36 lessons. latest debrief: 20260529-010000. "
        "profile: house, 120-128."
    )
    assert status["citations"] == [
        "[screen:learn-progress]",
        "[screen:learn-debrief]",
        "[screen:learn-profile]",
    ]
    result = CitationLinter().check(
        " ".join(status["citations"]),
        registry.snapshot(),
        mode="live",
    )
    assert result.valid is True


def test_l3_06_fixture_no_longer_claims_debrief_open_without_evidence() -> None:
    fixture = (
        Path(__file__).resolve().parent.parent.parent
        / "src"
        / "vibemix"
        / "learn"
        / "transcripts"
        / "course_3_play_mode"
        / "06_dj_profile_graduation.json"
    )
    data = json.loads(fixture.read_text(encoding="utf-8"))
    text = " ".join(
        [row["text"] for row in data["tutor_speak"]]
        + [row["text"] for row in data["hints"]]
    )

    assert "the debrief is open" not in text
    assert "should have opened automatically" not in text
    assert "only name what is actually saved" in text
