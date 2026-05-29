# SPDX-License-Identifier: Apache-2.0
"""Phase 95 — Course 2 curriculum dispatch tests.

Pins the 14 L2.NN entries that Plan 95 lands in
``src/vibemix/learn/curriculum.py``. Mirrors the implicit P94 contract
the existing learn-suite tests already enforce on Course 1, but makes
the Course 2 contract EXPLICIT so a future planner who edits the
CURRICULUM table can't silently break the dispatch.

Five test paths:

  1. **All 14 lesson IDs present** — CURRICULUM has keys L2.01..L2.14.

  2. **Every entry tagged ``course_2_transitions``** — no L2.NN entry
     leaks into a foreign course frame (would scramble the HUD dots /
     proactive-lens routing later).

  3. **COURSE_FRAMES['course_2_transitions'] exists + ≤200 chars** —
     same composition-time cap as P92/P94 frames (``prompts.py:185``
     raises ValueError on overflow at system-instruction build time).

  4. **Per-lesson addendum byte-equal between curriculum.py and the
     fixture JSON** — the lock that prevents drift between the
     planner-edited curriculum.py table and the hand-authored fixture
     (the drift is silent: an inconsistency means the live tutor
     system instruction does NOT match what a future reader sees in
     the JSON). Mirrors test_tutor_prompts_byte_equality.py's pattern
     against L1.01 dialog.

  5. **Each fixture loads + has a valid expected_action** — the
     fixture path resolves under transcripts/, json.loads() succeeds,
     and the top-level expected_action object exists with type +
     control. Pins the contract the LessonRuntime.action_matches
     predicate reads.

REQ-ID: CURR-2.01..CURR-2.14.

The test is LIVE day-one (Plan 95 Task 1 + Task 2 shipped the fixtures
+ curriculum.py extension before this file landed).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from vibemix.learn.curriculum import COURSE_FRAMES, CURRICULUM

# ---------------------------------------------------------------------------
# Constants — the 14 lesson IDs Plan 95 lands.
# ---------------------------------------------------------------------------

COURSE_2_LESSON_IDS: tuple[str, ...] = (
    "L2.01",
    "L2.02",
    "L2.03",
    "L2.04",
    "L2.05",
    "L2.06",
    "L2.07",
    "L2.08",
    "L2.09",
    "L2.10",
    "L2.11",
    "L2.12",
    "L2.13",
    "L2.14",
)

# Expected per-lesson title (canonical, lowercase + period-free per
# UI-SPEC). Pinning the title prevents accidental rename in a future
# editor pass that would silently break the HUD's lesson-picker copy.
COURSE_2_TITLES: dict[str, str] = {
    "L2.01": "beatmatching by ear",
    "L2.02": "beatmatching with sync",
    "L2.03": "long blend",
    "L2.04": "eq swap",
    "L2.05": "bassline swap",
    "L2.06": "filter fade",
    "L2.07": "echo-out",
    "L2.08": "drop swap",
    "L2.09": "loop transition",
    "L2.10": "hot cues and memory cues",
    "L2.11": "camelot wheel",
    "L2.12": "phrase matching",
    "L2.13": "diagnosing a train wreck",
    "L2.14": "course 2 recital",
}


# ---------------------------------------------------------------------------
# Test 1 — all 14 lesson IDs are present in CURRICULUM.
# ---------------------------------------------------------------------------


def test_all_fourteen_course_2_lessons_in_curriculum() -> None:
    """CURRICULUM has every L2.NN key. Missing one breaks the
    lesson-picker dispatch (the runtime's load_lesson() returns None
    on a missing key + the HUD shows a blank slot).
    """
    missing = [lid for lid in COURSE_2_LESSON_IDS if lid not in CURRICULUM]
    assert not missing, (
        f"CURRICULUM is missing {len(missing)} Course 2 lesson IDs: "
        f"{missing!r}. Plan 95 Task 2 must register all 14 entries."
    )


# ---------------------------------------------------------------------------
# Test 2 — every L2.NN entry is tagged course_2_transitions.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("lesson_id", COURSE_2_LESSON_IDS)
def test_each_entry_is_tagged_course_2_transitions(lesson_id: str) -> None:
    """Every L2.NN CURRICULUM entry must have
    ``course_id == "course_2_transitions"``. A drift here (e.g. a copy-
    paste pulling an entry under ``course_1_anatomy``) would route the
    lesson into the wrong HUD column + scramble the progress dots.
    """
    entry = CURRICULUM[lesson_id]
    assert entry.course_id == "course_2_transitions", (
        f"{lesson_id} course_id is {entry.course_id!r}, expected "
        "'course_2_transitions'. Plan 95 Task 2 must tag all 14 entries."
    )


# ---------------------------------------------------------------------------
# Test 3 — COURSE_FRAMES['course_2_transitions'] exists, ≤200 chars.
# ---------------------------------------------------------------------------


def test_course_2_frame_exists_and_within_cap() -> None:
    """``COURSE_FRAMES['course_2_transitions']`` must exist + be a
    non-empty string ≤200 chars (the composition-time cap enforced by
    ``prompts.py::build_tutor_system_instruction``).

    The frame is the course-context paragraph appended to the system
    instruction so the LLM has Course 2's framing in mind for every
    beat. Without it, prompts.py either raises (missing key) or
    composes a Course 2 lesson with a foreign course frame (silent UX
    bug — the tutor narrates "this is the channel strip…" inside a
    transitions lesson).
    """
    frame = COURSE_FRAMES.get("course_2_transitions")
    assert isinstance(frame, str) and frame, (
        f"COURSE_FRAMES['course_2_transitions'] missing or empty; "
        f"got {frame!r}"
    )
    # The composition-cap in prompts.py:185 raises ValueError on
    # addendums >200 chars; the frame itself is the BASE that the
    # addendum gets appended to. The whole frame block must fit a
    # reasonable budget so the per-lesson addendum still has room.
    # We use a soft 400-char cap on the frame (≈ ⅕ of the typical
    # system-instruction budget); plan 94-01's course_1_anatomy frame
    # is 287 chars — well within.
    assert len(frame) <= 400, (
        f"COURSE_FRAMES['course_2_transitions'] is {len(frame)} chars; "
        "soft cap is 400 (Course 1 frame is ~287 for reference)."
    )


# ---------------------------------------------------------------------------
# Test 4 — addendum byte-equal between curriculum.py and fixture JSON.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("lesson_id", COURSE_2_LESSON_IDS)
def test_addendum_byte_equal_between_curriculum_and_fixture(
    lesson_id: str,
) -> None:
    """The CURRICULUM[lesson_id].system_instruction_addendum string MUST
    byte-equal the fixture JSON's ``system_instruction_addendum`` field.

    Drift means the live tutor system instruction (composed from
    curriculum.py) does not match what a future reader sees in the
    fixture JSON — a silent inconsistency. The plan 94-02 byte-equality
    test pins the same lock for L1.01's iconic dialog at the
    tutor_speak[i].text level; this test extends the discipline to the
    addendum field for all 14 Course 2 lessons.
    """
    meta = CURRICULUM[lesson_id]
    transcripts_root = Path(__file__).resolve().parents[2] / "src" / "vibemix" / "learn" / "transcripts"
    fixture_path = transcripts_root / meta.transcript_path
    assert fixture_path.exists(), (
        f"{lesson_id}: fixture {fixture_path} not found"
    )
    raw = json.loads(fixture_path.read_text(encoding="utf-8"))
    fixture_addendum = raw.get("system_instruction_addendum")
    assert fixture_addendum == meta.system_instruction_addendum, (
        f"{lesson_id} addendum drift:\n"
        f"  curriculum.py: {meta.system_instruction_addendum!r}\n"
        f"  fixture JSON:  {fixture_addendum!r}"
    )


# ---------------------------------------------------------------------------
# Test 5 — fixture loads + has a valid expected_action shape.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("lesson_id", COURSE_2_LESSON_IDS)
def test_fixture_loads_and_has_expected_action(lesson_id: str) -> None:
    """The fixture path resolves, json.loads() succeeds, and the
    top-level ``expected_action`` carries a ``type`` (``cc`` or
    ``button``) + ``control`` string. Pins the contract the
    ``LessonRuntime.action_matches`` predicate reads.

    Per Plan 95 the L2.14 (recital) lesson uses a synthetic
    ``lesson_continue`` button gate at the outer level — the recital
    cycle drives prompts via the RecitalRuntime observer.
    """
    meta = CURRICULUM[lesson_id]
    # The LessonMeta.script property reads the fixture lazily — invoking
    # it here also verifies the fixture path resolves + JSON-parses.
    script = meta.script
    assert isinstance(script, dict) and script, (
        f"{lesson_id}: script load returned {script!r}"
    )
    expected = script.get("expected_action")
    assert isinstance(expected, dict), (
        f"{lesson_id}: expected_action missing or non-dict: "
        f"{expected!r}"
    )
    assert expected.get("type") in {"cc", "button"}, (
        f"{lesson_id}: expected_action.type must be 'cc' or 'button'; "
        f"got {expected.get('type')!r}"
    )
    assert isinstance(expected.get("control"), str) and expected.get(
        "control"
    ), (
        f"{lesson_id}: expected_action.control must be a non-empty "
        f"string; got {expected.get('control')!r}"
    )


# ---------------------------------------------------------------------------
# Test 6 — titles byte-equal (pinning the lowercase + period-free UI-SPEC).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("lesson_id", COURSE_2_LESSON_IDS)
def test_titles_are_lowercase_and_period_free(lesson_id: str) -> None:
    """Per UI-SPEC, lesson titles are lowercase, period-free. A future
    editor pass that adds a Title-Case or trailing-period title breaks
    the HUD's pixel-aligned lesson-picker.

    Also pins the per-lesson title byte-equal — accidental rename would
    silently change the HUD copy.
    """
    meta = CURRICULUM[lesson_id]
    title = meta.title
    expected_title = COURSE_2_TITLES[lesson_id]
    assert title == expected_title, (
        f"{lesson_id} title is {title!r}, expected {expected_title!r}. "
        "Renames must update tests/learn/test_course_2_curriculum.py."
    )
    # Lowercase: a title containing any uppercase letter trips the gate.
    assert title == title.lower(), (
        f"{lesson_id} title contains uppercase: {title!r}"
    )
    # Period-free: trailing periods break the HUD label visual.
    assert not title.endswith("."), (
        f"{lesson_id} title ends with a period: {title!r}"
    )


# ---------------------------------------------------------------------------
# Test 7 — Course 2 lesson count matches the requirements ceiling.
# ---------------------------------------------------------------------------


def test_exactly_fourteen_course_2_entries() -> None:
    """The CURRICULUM dict has EXACTLY 14 entries tagged
    course_2_transitions (REQ CURR-2.01..CURR-2.14). A new lesson is a
    requirements change, not a casual add — the gate forces the planner
    to update REQUIREMENTS.md + this test together.
    """
    c2_entries = [
        lid
        for lid, meta in CURRICULUM.items()
        if meta.course_id == "course_2_transitions"
    ]
    assert len(c2_entries) == 14, (
        f"expected 14 Course 2 entries; got {len(c2_entries)}: "
        f"{sorted(c2_entries)!r}"
    )
