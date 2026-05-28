# SPDX-License-Identifier: Apache-2.0
"""Curriculum metadata — course frames + lesson dispatch.

Phase 92 (LESSON-05). Ships ONLY Course 0 (the "hello world" 1-step demo)
for the press-play proof-of-life. Courses 1 / 2 / 3 add their entries in
P94 (anatomy) / P95 (transitions) / P96 (play mode) respectively.

Two top-level tables:

* :data:`COURSE_FRAMES` — short course-context paragraphs appended to the
  tutor system instruction so the LLM has the course frame in mind for
  every beat. Keyed by ``course_id`` (e.g. ``"course_0"``).

* :data:`CURRICULUM` — per-lesson :class:`LessonMeta` records. Keyed by
  ``lesson_id`` (e.g. ``"L0.00-press-play"``). Each :class:`LessonMeta`
  carries the lesson title, course pointer, ≤200-char system instruction
  addendum, and a ``transcript_path`` pointing at the hand-authored JSON
  fixture under ``src/vibemix/learn/transcripts/``.

The :class:`LessonMeta.script` ``@property`` lazy-loads the JSON fixture
on demand. Since :class:`LessonMeta` is ``frozen=True``, the property
re-reads from disk each access — fine for P92 (1 read per lesson start);
P94+ can layer ``functools.lru_cache`` on the property if needed.

TONE-02 binding: the lesson script JSON files are the SOLE source of
``tutor_speak[].text`` content; the AST gate
``tests/learn/test_scripts_are_fixtures.py`` rejects any code path that
writes that field from a generative API call.

# P94 adds L1.01..L1.16 (Course 1 — Anatomy), P95 adds L2.01..L2.14
# (Course 2 — Transitions), P96 adds L3.01..L3.07 (Course 3 — Play Mode).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Course frames — appended into the tutor system instruction
# ---------------------------------------------------------------------------

COURSE_FRAMES: dict[str, str] = {
    "course_0": (
        "Course 0 is the hello-world tutorial — a one-lesson demo proving "
        "the runtime end-to-end."
    ),
    # P94 adds course_1 (anatomy: decks, mixer, transport, EQ).
    # P95 adds course_2 (transitions: blends, EQ swap, filter, fade).
    # P96 adds course_3 (play mode: free-form jam with grounded reactions).
}


# ---------------------------------------------------------------------------
# Per-lesson metadata
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LessonMeta:
    """Per-lesson metadata record.

    Fields:
        title: HUD title — lowercase, period-free (UI-SPEC).
        course_id: Key into :data:`COURSE_FRAMES`.
        system_instruction_addendum: ≤200 char suffix appended to the
            tutor system instruction by
            :func:`vibemix.learn.prompts.build_tutor_system_instruction`.
            Tested against the 200-char cap at composition time —
            ``build_tutor_system_instruction`` raises ``ValueError`` when
            an entry exceeds the cap.
        transcript_path: Relative path under
            ``src/vibemix/learn/transcripts/`` pointing at the hand-
            authored JSON fixture for this lesson. The ``script`` property
            reads + json-decodes the file lazily.
    """

    title: str
    course_id: str
    system_instruction_addendum: str
    transcript_path: str

    @property
    def script(self) -> dict[str, Any]:
        """Lazy-load the JSON fixture from disk.

        Re-reads on every access (frozen dataclass = no instance cache).
        For P92 this is called at most once per lesson start; the I/O is
        a single small read. If the load pattern broadens in P94+, layer
        a ``functools.lru_cache`` on a free function that the property
        delegates to.

        Raises:
            FileNotFoundError: ``transcript_path`` resolves outside the
                ``transcripts/`` directory or the file is missing.
            json.JSONDecodeError: The fixture is not valid JSON.
        """
        base = Path(__file__).parent / "transcripts"
        return json.loads(
            (base / self.transcript_path).read_text(encoding="utf-8")
        )


# ---------------------------------------------------------------------------
# Curriculum dispatch table — keyed by lesson_id
# ---------------------------------------------------------------------------

CURRICULUM: dict[str, LessonMeta] = {
    "L0.00-press-play": LessonMeta(
        title="press play",
        course_id="course_0",
        system_instruction_addendum=(
            "HELLO WORLD ADDENDUM: Wait for the user to press deck A's play "
            "button. Do not narrate over them. Stay quiet between beats."
        ),
        transcript_path="hello_world/01_press_play.json",
    ),
    # P94 adds L1.01..L1.16, P95 adds L2.01..L2.14, P96 adds L3.01..L3.07.
}
