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
* :class:`LearnProgress` + :func:`load_progress` / :func:`save_progress`
  / :func:`reset_progress` / :func:`progress_path` / :data:`SCHEMA_VERSION`
  — atomic JSON persistence for lesson completion at
  ``~/.cache/vibemix/learn-progress.json`` (LESSON-03 / Plan 92-04).

Single-writer invariant (#1): nothing in this package writes
``MusicState`` or ``ControllerState``. Pure reader of
``ControllerState.deck_snapshot()`` + ``MidiMirror.snapshot()``; pure
builder of the envelope dicts.
"""
from __future__ import annotations

from vibemix.learn.audio_cue import ExemplarPlayer
from vibemix.learn.band_share_store import (
    BAND_SHARE_TABLE,
    init_schema,
    open_default_db,
    top_for_band,
)
from vibemix.learn.band_share_store import upsert as upsert_band_shares
from vibemix.learn.curriculum import COURSE_FRAMES, CURRICULUM, LessonMeta
from vibemix.learn.exemplar import ExemplarFinder, ExemplarPick, compute_band_shares
from vibemix.learn.midi_mirror import MidiMirror
from vibemix.learn.progress import (
    SCHEMA_VERSION,
    LearnProgress,
    load_progress,
    progress_path,
    reset_progress,
    save_progress,
)
from vibemix.learn.prompts import build_tutor_system_instruction
from vibemix.learn.runtime import LessonRuntime
from vibemix.learn.settings import read_learn_headphone_device_index
from vibemix.learn.state import LearnState

__all__ = [
    "BAND_SHARE_TABLE",
    "COURSE_FRAMES",
    "CURRICULUM",
    "ExemplarFinder",
    "ExemplarPick",
    "ExemplarPlayer",
    "LearnProgress",
    "LearnState",
    "LessonMeta",
    "LessonRuntime",
    "MidiMirror",
    "SCHEMA_VERSION",
    "build_tutor_system_instruction",
    "compute_band_shares",
    "init_schema",
    "load_progress",
    "open_default_db",
    "progress_path",
    "read_learn_headphone_device_index",
    "reset_progress",
    "save_progress",
    "top_for_band",
    "upsert_band_shares",
]
