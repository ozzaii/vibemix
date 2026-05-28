# SPDX-License-Identifier: Apache-2.0
"""``vibemix.learn`` subpackage — controller renderer + lesson runtime.

Backend half of the Learn surface. The Tauri Learn window subscribes to
the ipc.learn.* envelopes produced here over the shared ws:8765 socket
(Invariant #4 preserved — no second WS listener bound).

Public surface (Phase 91):

* :class:`MidiMirror` — the 30 Hz delta-coalesced controller-position
  snapshotter + thread-safe ``controller_detected`` queue. Sole writer of
  ``ipc.learn.midi_position`` envelopes; read-only consumer of
  :class:`vibemix.midi.state.ControllerState`.

Public surface (Phase 92):

* :class:`LearnState` — the mutable single-writer dataclass tracking the
  active lesson position. LessonRuntime is the SOLE writer (Invariant #1
  binding, enforced by ``tests/learn/test_runtime_invariants.py``).
* :data:`COURSE_FRAMES` — course-context text fragments keyed by
  ``course_id``.
* :data:`CURRICULUM` — per-lesson :class:`LessonMeta` records keyed by
  ``lesson_id``.
* :class:`LessonMeta` — the per-lesson metadata dataclass; ``.script``
  property lazy-loads the JSON fixture.
* :func:`build_tutor_system_instruction` — composes the tutor LLM system
  instruction (LESSON-05 / TONE-04). The 4-forbidden-moves lock lands
  LAST for strongest recency (mirrors the COACH_CLOSING_BLOCK pattern).
* :class:`LessonRuntime` — the deterministic FSM driving the lesson
  lifecycle (LESSON-01 / LESSON-04). 8 states / 5 transitions /
  1 Hz tick_loop; sole writer of :class:`LearnState`.

Single-writer invariant (#1): nothing in this package writes
``MusicState`` or ``ControllerState``. Pure reader of
``ControllerState.deck_snapshot()`` + ``MidiMirror.snapshot()``; pure
builder of the envelope dicts.
"""
from __future__ import annotations

from vibemix.learn.curriculum import COURSE_FRAMES, CURRICULUM, LessonMeta
from vibemix.learn.midi_mirror import MidiMirror
from vibemix.learn.prompts import build_tutor_system_instruction
from vibemix.learn.runtime import LessonRuntime
from vibemix.learn.state import LearnState

__all__ = [
    "COURSE_FRAMES",
    "CURRICULUM",
    "LearnState",
    "LessonMeta",
    "LessonRuntime",
    "MidiMirror",
    "build_tutor_system_instruction",
]
