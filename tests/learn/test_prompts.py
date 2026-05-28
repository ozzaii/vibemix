# SPDX-License-Identifier: Apache-2.0
"""Phase 92 Plan 02 — LESSON-05 build_tutor_system_instruction wiring.

Five tests cover the tutor-prompt composition contract:

1. ``test_compose_order`` — the returned instruction contains the
   COURSE_FRAMES text, the controller frame, the addendum, AND the
   four-forbidden-moves lock IN THAT ORDER (lock last for recency).
2. ``test_teacher_persona_present`` — the teacher persona from
   ``MOOD_PERSONAS["teacher"]`` is reused (v8.1 LENS-03 reuse, NO new
   lens) — a known persona substring must appear.
3. ``test_addendum_max_length`` — a fixture addendum > 200 chars
   raises ``ValueError`` mentioning the cap.
4. ``test_unknown_course_id_raises`` — unknown course_id raises
   ``ValueError``.
5. ``test_unknown_lesson_id_raises`` — unknown lesson_id raises
   ``ValueError``.

The companion file ``tests/learn/test_tutor_system_instruction_lock.py``
pins the four-forbidden-moves lock tokens; THIS file pins the
composition order + the persona reuse + the addendum cap.

REQ-ID: LESSON-05 (tutor persona reuse + system instruction composition).
"""
from __future__ import annotations

import pytest

try:
    from vibemix.learn.prompts import build_tutor_system_instruction  # P92-03
    from vibemix.learn.curriculum import COURSE_FRAMES, CURRICULUM, LessonMeta  # P92-03
except ImportError:
    pytest.skip(
        "tests/learn/test_prompts.py awaits Plan 92-03 (LESSON-05 "
        "build_tutor_system_instruction + curriculum.py). When prompts.py "
        "+ curriculum.py land, this module-level skip flips to live "
        "assertions.",
        allow_module_level=True,
    )


# ---------------------------------------------------------------------------
# Order: COURSE_FRAMES → controller → addendum → lock
# ---------------------------------------------------------------------------


def test_compose_order() -> None:
    """The instruction contains the four expected blocks in order:

    1. COURSE_FRAMES["course_0"] substring
    2. controller-frame mention of "pioneer_ddj_flx4" OR "FLX4"
    3. addendum sentinel "HELLO WORLD ADDENDUM"
    4. four-forbidden-moves lock (verifying any one of the lock tokens
       is AFTER the addendum)
    """
    instruction = build_tutor_system_instruction(
        course_id="course_0",
        lesson_id="L0.00-press-play",
        controller_id="pioneer_ddj_flx4",
    )

    course_frame_text = COURSE_FRAMES["course_0"]
    course_idx = instruction.find(course_frame_text)
    assert course_idx >= 0, (
        f"COURSE_FRAMES['course_0'] text not found in instruction"
    )

    # Controller frame anchor — accept either the registry id OR the
    # display name; Plan 92-03 chooses one (Claude's discretion).
    lower = instruction.lower()
    assert ("pioneer_ddj_flx4" in lower or "ddj-flx4" in lower or "flx4" in lower), (
        "controller frame for pioneer_ddj_flx4 not present in instruction"
    )

    addendum_idx = instruction.find("HELLO WORLD ADDENDUM")
    assert addendum_idx >= 0, (
        "addendum sentinel 'HELLO WORLD ADDENDUM' missing from instruction"
    )
    assert addendum_idx > course_idx, (
        "addendum should appear AFTER the course frame "
        f"(addendum_idx={addendum_idx}, course_idx={course_idx})"
    )

    # Lock anchor — one of the 4 required tokens must appear after the
    # addendum (the strongest-recency contract).
    for token in ("COMPLIMENT", "SUMMARIZE", "PREVIEW"):
        token_idx = instruction.find(token)
        assert token_idx >= 0 and token_idx > addendum_idx, (
            f"lock token {token!r} not positioned AFTER the addendum "
            f"(token_idx={token_idx}, addendum_idx={addendum_idx})"
        )


# ---------------------------------------------------------------------------
# Persona reuse — teacher lens from v8.1 LENS-03
# ---------------------------------------------------------------------------


def test_teacher_persona_present() -> None:
    """A distinctive substring of ``MOOD_PERSONAS["teacher"]`` is
    present in the composed instruction — confirms the persona is
    re-used, not re-written."""
    from vibemix.prompts.matrix import MOOD_PERSONAS

    teacher_persona = MOOD_PERSONAS.get("teacher", "")
    assert teacher_persona, (
        "MOOD_PERSONAS['teacher'] missing — Plan 92-05 contract broken"
    )
    # Take a 32-char distinctive slice from somewhere mid-text. We avoid
    # the start (which often has a generic header). If the persona is
    # short, fall back to the full string.
    needle = (
        teacher_persona[30:62]
        if len(teacher_persona) > 62
        else teacher_persona
    )
    instruction = build_tutor_system_instruction(
        course_id="course_0",
        lesson_id="L0.00-press-play",
        controller_id="pioneer_ddj_flx4",
    )
    assert needle in instruction, (
        "teacher persona substring missing from instruction — "
        "build_tutor_system_instruction MUST reuse MOOD_PERSONAS['teacher'] "
        "(v8.1 LENS-03 reuse, NO new lens)"
    )


# ---------------------------------------------------------------------------
# Addendum cap — 200 chars
# ---------------------------------------------------------------------------


def test_addendum_max_length(monkeypatch: pytest.MonkeyPatch) -> None:
    """An addendum > 200 chars raises ``ValueError``."""
    overlong = "X" * 201
    fake_meta = LessonMeta(
        title="overlong",
        course_id="course_0",
        system_instruction_addendum=overlong,
        transcript_path="hello_world/01_press_play.json",
    )
    # Replace the curriculum entry with our overlong fixture.
    monkeypatch.setitem(CURRICULUM, "L0.00-press-play", fake_meta)
    with pytest.raises(ValueError) as excinfo:
        build_tutor_system_instruction(
            course_id="course_0",
            lesson_id="L0.00-press-play",
            controller_id="pioneer_ddj_flx4",
        )
    assert "200" in str(excinfo.value), (
        "ValueError message should mention the 200-char cap, got "
        f"{excinfo.value!r}"
    )


# ---------------------------------------------------------------------------
# Unknown course / lesson ids raise
# ---------------------------------------------------------------------------


def test_unknown_course_id_raises() -> None:
    """Unknown course_id raises ``ValueError`` (NOT KeyError)."""
    with pytest.raises(ValueError):
        build_tutor_system_instruction(
            course_id="course_99",  # not in COURSE_FRAMES
            lesson_id="L0.00-press-play",
            controller_id="pioneer_ddj_flx4",
        )


def test_unknown_lesson_id_raises() -> None:
    """Unknown lesson_id raises ``ValueError``."""
    with pytest.raises(ValueError):
        build_tutor_system_instruction(
            course_id="course_0",
            lesson_id="L99.99-fake",  # not in CURRICULUM
            controller_id="pioneer_ddj_flx4",
        )
