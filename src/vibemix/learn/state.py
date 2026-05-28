# SPDX-License-Identifier: Apache-2.0
"""LearnState — single-writer dataclass for the lesson runtime.

Phase 92 (LESSON-01). Invariant #1 binding: ONLY :class:`LessonRuntime`
(``vibemix.learn.runtime``) writes these fields. The AST gate
``tests/learn/test_runtime_invariants.py`` greps ``src/vibemix/learn/`` for
any ``learn_state.<field> =`` or ``self._learn.<field> =`` assignment
outside ``runtime.py`` / ``state.py`` and fails red on any match.

This dataclass is MUTABLE (NOT ``frozen=True``) — ``LessonRuntime`` writes
its fields inside the ``on_enter_<state>`` callbacks. The single-writer
invariant is enforced statically (grep gate), not by Python typing.

Reads are unrestricted: any module may read these fields. The lesson
HUD, the tutor LLM emit site, the 30 Hz ws broadcast — all consume.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LearnState:
    """Runtime state of the currently-active lesson.

    Six fields tracking lesson lifecycle position + the wall-clock anchor
    used by the 45 s anti-speedrun min-dwell gate and the 30 s strike
    escalation timer.

    All fields default to a "no lesson active" state. ``LessonRuntime``
    populates them inside ``on_enter_loaded`` when a lesson begins.
    """

    # The active course + lesson IDs. Both None when the runtime is idle.
    current_course_id: str | None = None
    current_lesson_id: str | None = None
    # The MIDI controller id (e.g. "pioneer_ddj_flx4") this lesson was
    # loaded for. Captured at load time so renderer reads stay consistent
    # even if the user replugs mid-lesson (P91 ControllerState handles
    # the live rebind separately; LearnState pins the lesson-frame id).
    current_controller_id: str | None = None

    # Beat index inside the current lesson's ``tutor_speak`` array. P92
    # only has 1 beat per lesson (the "hello world" demo); P94+ add
    # multi-beat lessons. Always 0 at lesson start.
    current_beat_index: int = 0

    # Strike count 0..3. Escalates via the ``strike`` FSM transition
    # (driven by the 1 Hz ``tick_loop`` after 30 s of no expected action).
    strike_count: int = 0

    # Wall-clock anchor (``time.monotonic()``) for the 45 s anti-speedrun
    # min-dwell gate. ``LessonRuntime.min_dwell_elapsed()`` returns True
    # when ``time.monotonic() - lesson_started_at >= 45.0``.
    lesson_started_at: float = 0.0
