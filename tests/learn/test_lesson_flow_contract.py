# SPDX-License-Identifier: Apache-2.0
"""Canonical structured-flow contract for all beginner Learn lessons."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from vibemix.learn.curriculum import CURRICULUM, beginner_lesson_ids
from vibemix.learn.lesson_flow import (
    MAX_FRONTSTAGE_PROMPT_CHARS,
    MAX_FRONTSTAGE_PROMPT_SENTENCES,
    MAX_FRONTSTAGE_PROMPT_WORDS,
    build_all_beginner_flows,
    build_lesson_flow,
    frontstage_prompt_contract_exempt,
    frontstage_prompt_metrics,
    input_surfaces_for_action,
    observable_control_id,
    primary_expected_action,
)
from vibemix.midi import list_profiles, load_profile

BEGINNER_LESSON_IDS = beginner_lesson_ids()
FRONTEND_CURRICULUM_META = (
    Path(__file__).resolve().parent.parent.parent
    / "tauri"
    / "ui"
    / "src"
    / "learn"
    / "lesson"
    / "curriculum-meta.ts"
)


def test_all_36_beginner_lessons_compile_to_structured_flows() -> None:
    flows = build_all_beginner_flows()
    assert len(flows) == 36
    assert tuple(flow.lesson_id for flow in flows) == BEGINNER_LESSON_IDS

    seen_step_ids: set[str] = set()
    for flow in flows:
        assert flow.lesson_id in CURRICULUM
        assert flow.course_id == CURRICULUM[flow.lesson_id].course_id
        assert flow.title == CURRICULUM[flow.lesson_id].title
        assert flow.steps
        assert flow.primary_expected_action == primary_expected_action(flow.lesson_id)
        for step in flow.steps:
            assert step.step_id not in seen_step_ids
            seen_step_ids.add(step.step_id)
            assert step.step_id.startswith(f"{flow.lesson_id}.")
            assert step.prompt
            prompt_metrics = frontstage_prompt_metrics(step.prompt)
            if not frontstage_prompt_contract_exempt(step.step_id):
                assert prompt_metrics["within_contract"] is True
                assert prompt_metrics["chars"] <= MAX_FRONTSTAGE_PROMPT_CHARS
                assert prompt_metrics["words"] <= MAX_FRONTSTAGE_PROMPT_WORDS
                assert prompt_metrics["sentences"] <= MAX_FRONTSTAGE_PROMPT_SENTENCES
            assert step.tts_marker
            assert isinstance(step.citations, tuple)
            assert step.expected_action.get("type") in {"button", "cc"}
            assert step.expected_action.get("control")
            assert step.verification.control == step.expected_action["control"]
            assert step.verification.observable_control_ids
            assert step.verification.observable_control_ids == (
                observable_control_id(step.expected_action),
            )
            assert len(step.hints) >= 3
            assert tuple(hint.strike for hint in step.hints[:3]) == (1, 2, 3)
            for hint in step.hints[:3]:
                assert hint.text
                assert hint.tts_marker


def test_frontend_curriculum_meta_mirrors_python_curriculum() -> None:
    """The chooser's 36-row mirror must stay byte-aligned with Python."""
    source = FRONTEND_CURRICULUM_META.read_text(encoding="utf-8")
    row_re = re.compile(
        r'\{\s*lesson_id:\s*"(?P<lesson_id>L[123]\.\d{2})",\s*'
        r'course_id:\s*"(?P<course_id>[^"]+)",\s*'
        r'title:\s*"(?P<title>[^"]+)"\s*\}'
    )
    rows = {
        match.group("lesson_id"): (
            match.group("course_id"),
            match.group("title"),
        )
        for match in row_re.finditer(source)
    }

    expected = {
        lesson_id: (CURRICULUM[lesson_id].course_id, CURRICULUM[lesson_id].title)
        for lesson_id in BEGINNER_LESSON_IDS
    }
    assert rows == expected


@pytest.mark.parametrize("lesson_id", BEGINNER_LESSON_IDS)
def test_primary_expected_action_stays_fixture_compatible(lesson_id: str) -> None:
    assert primary_expected_action(lesson_id) == CURRICULUM[lesson_id].script[
        "expected_action"
    ]


def test_observer_lessons_expose_real_multi_step_flows() -> None:
    eq_tutor = build_lesson_flow("L1.14")
    assert tuple(step.kind for step in eq_tutor.steps) == (
        "exemplar_band",
        "exemplar_band",
        "exemplar_band",
    )
    assert tuple(step.verification.control for step in eq_tutor.steps) == (
        "eq_low",
        "eq_mid",
        "eq_hi",
    )

    course_1_recital = build_lesson_flow("L1.16")
    course_2_recital = build_lesson_flow("L2.14")
    assert len(course_1_recital.steps) >= 5
    assert len(course_2_recital.steps) >= 5
    assert {step.kind for step in course_1_recital.steps} == {"recital_prompt"}
    assert {step.kind for step in course_2_recital.steps} == {"recital_prompt"}
    assert "library_exemplars" in set(eq_tutor.backstage_lenses)
    assert "recital_observer" in set(course_1_recital.backstage_lenses)
    assert "recital_observer" in set(course_2_recital.backstage_lenses)


def test_continue_lessons_expose_one_step_per_authored_beat() -> None:
    opening = build_lesson_flow("L1.01")
    assert len(opening.steps) == 4
    assert tuple(step.step_id for step in opening.steps) == (
        "L1.01.beat.0",
        "L1.01.beat.1",
        "L1.01.beat.2",
        "L1.01.beat.3",
    )
    assert {step.verification.control for step in opening.steps} == {
        "lesson_continue"
    }
    assert tuple(step.tts_marker for step in opening.steps) == (
        "L101.beat0",
        "L101.beat1",
        "L101.beat2",
        "L101.beat3",
    )


def test_control_lessons_use_the_action_prompt_as_the_practice_step() -> None:
    channel_strip = build_lesson_flow("L1.03")
    assert len(channel_strip.steps) == 1
    assert channel_strip.steps[0].step_id == "L1.03.practice"
    assert channel_strip.steps[0].prompt == (
        "turn the top EQ knob on deck A all the way one direction, then the other."
    )
    assert channel_strip.steps[0].tts_marker == "L103.beat1"


def test_screen_only_controls_are_explicit_in_verification_metadata() -> None:
    """Controls without reliable bundled MIDI mappings are not advertised as hardware."""
    screen_only = {"headphone_cue", "lesson_continue", "master_vol"}
    observed_screen_only: set[str] = set()

    for flow in build_all_beginner_flows():
        for step in flow.steps:
            control = step.expected_action["control"]
            assert step.verification.input_surfaces == input_surfaces_for_action(
                step.expected_action
            )
            if control in screen_only:
                observed_screen_only.add(control)
                assert step.verification.input_surfaces == ("screen",)
            else:
                assert step.verification.input_surfaces == (
                    "hardware",
                    "screen",
                )

    assert screen_only <= observed_screen_only


def test_screen_only_controls_have_no_bundled_physical_profile_mapping() -> None:
    """The screen-only list is grounded in current profile reality."""
    bundled_fields_and_kinds: set[str] = set()
    for profile_id in list_profiles():
        profile = load_profile(profile_id)
        assert profile is not None
        bundled_fields_and_kinds.update(
            binding.field for binding in profile.controls.values()
        )
        bundled_fields_and_kinds.update(
            binding.kind for binding in profile.buttons.values()
        )

    assert "headphone_cue" not in bundled_fields_and_kinds
    assert "lesson_continue" not in bundled_fields_and_kinds
    assert "master_vol" not in bundled_fields_and_kinds


def test_course3_continue_lessons_expose_live_backstage_lenses() -> None:
    """Course 3 is simple frontstage, but not a syllabus-wall backstage."""
    expected: dict[str, set[str]] = {
        "L3.01": {
            "live_audio",
            "cue_section_lookahead",
            "library_suggestions",
            "session_state",
        },
        "L3.02": {
            "live_audio",
            "cue_section_lookahead",
            "prepared_pool",
            "library_suggestions",
            "session_state",
        },
        "L3.03": {
            "live_audio",
            "cue_section_lookahead",
            "library_suggestions",
            "session_state",
        },
        "L3.04": {
            "live_audio",
            "cue_section_lookahead",
            "library_suggestions",
            "session_recording",
            "debrief",
        },
        "L3.05": {
            "live_audio",
            "cue_section_lookahead",
            "library_suggestions",
            "recovery_drill",
        },
        "L3.06": {
            "debrief",
            "dj_profile",
        },
    }

    for lesson_id, required_lenses in expected.items():
        flow = build_lesson_flow(lesson_id)
        lenses = set(flow.backstage_lenses)

        assert flow.primary_expected_action["control"] == "lesson_continue"
        assert "evidence_registry" in lenses
        assert required_lenses <= lenses
        for step in flow.steps:
            assert set(step.backstage_lenses) == lenses

    proactive_ids = {"L3.01", "L3.02", "L3.03", "L3.04", "L3.05"}
    for lesson_id in proactive_ids:
        flow = build_lesson_flow(lesson_id)
        assert flow.proactive_lens_active is True
        assert flow.exemplar_audio_forbidden is True

    graduation = build_lesson_flow("L3.06")
    assert graduation.proactive_lens_active is False
    assert graduation.exemplar_audio_forbidden is False


def test_camelot_lesson_declares_library_suggestion_lens() -> None:
    """L2.11 teaches key compatibility through the user's own library when possible."""
    flow = build_lesson_flow("L2.11")

    assert "library_suggestions" in set(flow.backstage_lenses)
    for step in flow.steps:
        assert "library_suggestions" in set(step.backstage_lenses)
    assert "live_audio" not in set(flow.backstage_lenses)


def test_recovery_drills_keep_authored_shapes_in_structured_flow() -> None:
    flow = build_lesson_flow("L3.05")

    assert tuple(drill.drill for drill in flow.drill_shapes) == (
        "key_clash",
        "misaligned_phrase",
    )
    assert tuple(drill.deck for drill in flow.drill_shapes) == ("B", "B")
    assert "harmonic clash" in flow.drill_shapes[0].shape
    assert "phrase misalignment" in flow.drill_shapes[1].shape
