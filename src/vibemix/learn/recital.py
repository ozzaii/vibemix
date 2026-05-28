# SPDX-License-Identifier: Apache-2.0
"""RecitalRuntime — drives the L1.16 Course 1 Recital gate.

Phase 94 Plan 03 (CURR-1.16 binding).

Architecture
============

This controller is an OBSERVER of :class:`LessonRuntime` for the L1.16
lesson. It reads ``recital_pool`` (≥5 entries) + ``recital_outcomes``
from the active lesson's script, samples
``_RECITAL_SUBSET_SIZE = 5`` entries deterministically using a daily-
rotating seed, drives each prompt, scores correctness honestly (no
partial-credit), and on a 5/5 pass flips
:class:`LearnProgress.course_2_unlocked` to ``True`` + calls
``save_progress`` (the Course 2 unlock gate).

The controller NEVER writes :class:`LearnState`. Invariant #1
(single-writer) stays bound to ``LessonRuntime`` alone; the AST gate
``tests/learn/test_runtime_invariants.py`` greps ``src/vibemix/learn/``
for forbidden writes and stays green — this module reads from
``script`` dicts + writes to ``LearnProgress`` (via save_fn) + emits IPC
envelopes; it never touches ``self._learn.<field> = ...``.

The controller is wired into LessonRuntime via the
:meth:`LessonRuntime.register_lesson_observer` seam: when the active
lesson is the L1.16 recital, the runtime delegates
``on_enter_awaiting_action`` to the controller's ``.start()``,
``on_ack_action`` to the controller's ``.ack()`` (when ``.matches(midi)``
returns True), and the ``on_enter_completed`` teardown to the
controller's ``.stop()``.

Determinism + day-rolling
=========================

The recital subset is sampled via ``random.Random(seed).sample(pool, 5)``.
The seed defaults to ``int(time.time() // 86400)`` — day-of-Unix-epoch.
Why same subset on same-day replay?

* A user who fails the recital today gets the SAME 5 prompts if they
  replay today (no retry-grinding for a favorable combination).
* A user who comes back tomorrow gets a FRESH combination
  (anti-frustration: "sleep on it" works).

The ``seed`` ctor kwarg is for hermetic testing — pin a known seed,
get a known subset.

Honest grading
==============

Score-on-match-only. Non-matching MIDI doesn't penalise (no negative
score; the user keeps the active prompt until they perform it
correctly OR they ``skip_remaining()`` — the public path the UI calls
when the user gives up). A 5/5 pass is the only path to
``course_2_unlocked = True``; any score < 5 leaves it locked.

Outcome copy
============

The fixture's ``recital_outcomes`` dict provides the pass/fail copy:

  * ``recital_outcomes.pass`` — verbatim text emitted on 5/5
    (e.g. "5 of 5. course 2 unlocked.").
  * ``recital_outcomes.fail`` — text with ``{score}`` substituted
    (e.g. "{score} of 5. replay when you're ready." → "3 of 5. replay
    when you're ready.").

REQ-ID: CURR-1.16 (Course 1 Recital — gate to unlock Course 2).
"""
from __future__ import annotations

import random
import sys
import time
from typing import Any, Callable

from vibemix.learn.progress import LearnProgress, save_progress
from vibemix.ui_bus.learn_messages import (
    LearnAdvance,
    LearnCompleteLesson,
    LearnHighlight,
    LearnProgressState,
    LearnTutorSpeak,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# CURR-1.16 lock — recital surfaces EXACTLY 5 prompts. Locked here as a
# module-level constant so the AST tests can grep it.
_RECITAL_SUBSET_SIZE: int = 5

# CC delta floor — mirrors runtime.py and exemplar_lesson.py.
_CC_DEFAULT_MIN_DELTA: int = 38


# ---------------------------------------------------------------------------
# MIDI matcher — local copy of the runtime's action_matches predicate.
# Decoupled from runtime.py's private callable for the same reason as
# exemplar_lesson._midi_matches: the contract is the matching SEMANTICS,
# not a shared Python callable.
# ---------------------------------------------------------------------------


def _midi_matches(midi: dict[str, Any], expected: dict[str, Any]) -> bool:
    """Return True iff ``midi`` matches ``expected``.

    Mirrors :meth:`LessonRuntime.action_matches` (runtime.py:223-300).
    Identical implementation lives in :mod:`exemplar_lesson._midi_matches`
    — kept duplicated rather than centralised because both controllers
    are otherwise independent islands (no shared module dependency
    needed beyond the envelope dataclasses).
    """
    if not isinstance(midi, dict) or not isinstance(expected, dict):
        return False
    expected_type = expected.get("type")
    midi_type = midi.get("type")
    if midi_type != expected_type:
        return False

    if expected_type == "cc":
        if midi.get("control") != expected.get("control"):
            return False
        cur = int(midi.get("value", 0))
        prev = int(midi.get("prev_value", cur))
        min_delta = int(expected.get("min_delta", _CC_DEFAULT_MIN_DELTA))
        return abs(cur - prev) >= min_delta

    if expected_type == "button":
        if midi.get("control") != expected.get("control"):
            return False
        if midi.get("direction") != expected.get("direction"):
            return False
        expected_deck = expected.get("deck")
        if expected_deck is not None and expected_deck != "":
            if midi.get("deck") != expected_deck:
                return False
        return True

    return False


# ---------------------------------------------------------------------------
# RecitalRuntime
# ---------------------------------------------------------------------------


class RecitalRuntime:
    """Drives the L1.16 Course 1 Recital — 5-prompt mixed gate.

    Public surface (the seam :class:`LessonRuntime` registers against
    via ``register_lesson_observer``):

      * ``.start(*, script, lesson_id)`` — begin the recital from a
        loaded lesson script. Samples 5 prompts deterministically.
      * ``.matches(midi)`` — returns True iff a MIDI event matches the
        active prompt's expected_action.
      * ``.ack(*, lesson_id)`` — score the active prompt as correct,
        advance to the next prompt OR finalize.
      * ``.skip_remaining(*, lesson_id)`` — finalize at the current
        score (the user gave up). Public path for the UI's "end
        recital" button when the user is mid-cycle and wants to see
        their score.
      * ``.stop(*, lesson_id)`` — clean teardown. Idempotent.

    Constructor:

      :param ipc_emit: callable receiving dict-shaped envelopes.
      :param progress: the live :class:`LearnProgress` instance. The
          controller flips ``progress.course_2_unlocked = True`` on a
          5/5 pass + calls ``save_fn(progress)`` (defaults to
          :func:`save_progress`).
      :param seed: optional integer seed. Default ``None`` → derives
          ``int(time.time() // 86400)`` at start() time.
      :param save_fn: callable that persists the progress. Defaults
          to :func:`save_progress` (atomic file write).
      :param rng_class: rng factory. Defaults to :class:`random.Random`;
          tests can inject a deterministic alternative.
    """

    def __init__(
        self,
        *,
        ipc_emit: Callable[[dict[str, Any]], None],
        progress: LearnProgress,
        seed: int | None = None,
        save_fn: Callable[[LearnProgress], Any] = save_progress,
        rng_class: type = random.Random,
    ) -> None:
        self._emit = ipc_emit
        self._progress = progress
        self._seed = seed
        self._save = save_fn
        self._rng_class = rng_class
        # The sampled subset (list of dicts) — populated at .start().
        self._sampled: list[dict[str, Any]] = []
        # Index into self._sampled; -1 means "not started".
        self._active_idx: int = -1
        # Running correctness score (0..5).
        self._score: int = 0
        # The fixture's recital_outcomes dict — pass/fail copy.
        self._outcomes: dict[str, str] = {}
        # Flag: has the recital been finalised? Prevents double-emit
        # if .ack() is somehow called past the last prompt.
        self._finalised: bool = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(
        self,
        *,
        script: dict[str, Any],
        lesson_id: str = "L1.16-course-1-recital",
    ) -> None:
        """Begin the recital. Samples 5 entries from ``recital_pool``
        deterministically; emits the first prompt as tutor_speak +
        highlight.
        """
        pool = script.get("recital_pool")
        self._outcomes = dict(script.get("recital_outcomes") or {})
        if not isinstance(pool, list) or len(pool) < _RECITAL_SUBSET_SIZE:
            # Degraded fixture — pool too small. Emit complete_lesson
            # with the schema-enum "user_skip" reason (no honest fail
            # copy to surface; the lesson is fundamentally broken).
            self._emit_complete(
                lesson_id=lesson_id, schema_reason="user_skip"
            )
            return

        seed = (
            self._seed
            if self._seed is not None
            else int(time.time() // 86400)
        )
        rng = self._rng_class(seed)
        self._sampled = rng.sample(pool, k=_RECITAL_SUBSET_SIZE)
        self._active_idx = -1
        self._score = 0
        self._finalised = False
        self._advance(lesson_id=lesson_id)

    def matches(self, midi: dict[str, Any]) -> bool:
        """Return True iff ``midi`` matches the active prompt's
        ``expected_action``. Returns False when the recital is not
        started, finalised, or past the last prompt.
        """
        if (
            self._finalised
            or self._active_idx < 0
            or self._active_idx >= len(self._sampled)
        ):
            return False
        expected = self._sampled[self._active_idx].get("expected_action")
        if not isinstance(expected, dict):
            return False
        return _midi_matches(midi, expected)

    def ack(
        self, *, lesson_id: str = "L1.16-course-1-recital"
    ) -> None:
        """Score the active prompt as correct (+1) and advance to the
        next prompt OR finalize.

        Honest grading: ack() is the ONLY path that increments score.
        Non-matching MIDI never reaches here (the runtime's hook only
        forwards when ``.matches()`` returns True).
        """
        if self._finalised:
            return
        self._score += 1
        self._emit_advance(lesson_id=lesson_id, reason="action_matched")
        self._advance(lesson_id=lesson_id)

    def skip_remaining(
        self, *, lesson_id: str = "L1.16-course-1-recital"
    ) -> None:
        """User gave up — finalize at the current score.

        Public path for the UI's "end recital" button. The remaining
        prompts are skipped without scoring; the controller emits the
        fail copy (or pass copy if somehow score==5 already) and
        complete_lesson.
        """
        if self._finalised:
            return
        self._emit_advance(lesson_id=lesson_id, reason="user_skip")
        self._finalize(lesson_id=lesson_id)

    def stop(
        self, *, lesson_id: str = "L1.16-course-1-recital"
    ) -> None:
        """Clean teardown — reset internal state. Idempotent.

        Does NOT emit anything (stop() is called by the runtime's
        on_enter_completed AFTER complete_lesson; emitting again
        would double-fire). The complete_lesson + outcome copy is the
        responsibility of finalize(), invoked by ack()/skip_remaining()
        when the cycle ends.
        """
        self._sampled = []
        self._active_idx = -1
        self._score = 0
        self._outcomes = {}
        # Leave _finalised = True so subsequent ack()/skip_remaining()
        # are no-ops if the runtime's hooks fire after stop().
        self._finalised = True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _advance(self, *, lesson_id: str) -> None:
        """Move to the next prompt OR finalize if the cycle ended."""
        self._active_idx += 1
        if self._active_idx >= len(self._sampled):
            self._finalize(lesson_id=lesson_id)
            return
        entry = self._sampled[self._active_idx]

        # Emit prompt text as tutor_speak.
        try:
            envelope = LearnTutorSpeak.make(
                text=str(entry.get("prompt", "")).strip(),
                tts_marker=f"L116.recital{self._active_idx + 1}",
                citations=(),
                data_state="active",
            ).to_dict()
            self._emit(envelope)
        except Exception as exc:  # pragma: no cover — defensive
            print(
                f"[learn.recital] tutor_speak emit failed: {exc!r}",
                file=sys.stderr,
            )

        # Emit highlight when the expected_action carries a control.
        expected = entry.get("expected_action") or {}
        control = expected.get("control")
        if control:
            try:
                envelope = LearnHighlight.make(
                    control_id=str(control),
                    deck=str(expected.get("deck", "")),
                    cue_color="amber",
                    cue_shape="pulse-ring",
                    annotation="",
                    expected_action=expected,
                ).to_dict()
                self._emit(envelope)
            except Exception as exc:  # pragma: no cover — defensive
                print(
                    f"[learn.recital] highlight emit failed: {exc!r}",
                    file=sys.stderr,
                )

    def _finalize(self, *, lesson_id: str) -> None:
        """Surface pass/fail copy + persist unlock on 5/5 + emit
        complete_lesson. Idempotent — guarded by self._finalised.
        """
        if self._finalised:
            return
        self._finalised = True

        passed = self._score >= _RECITAL_SUBSET_SIZE
        if passed:
            # Flip the unlock bit + persist atomically.
            self._progress.course_2_unlocked = True
            try:
                self._save(self._progress)
            except Exception as exc:  # pragma: no cover — defensive
                print(
                    f"[learn.recital] save_progress failed: {exc!r}",
                    file=sys.stderr,
                )

            # Surface pass copy.
            pass_copy = str(
                self._outcomes.get(
                    "pass", "5 of 5. course 2 unlocked."
                )
            )
            self._emit_outcome_speak(
                text=pass_copy, tts_marker="L116.outcome_pass"
            )
            # Repaint the lesson dots + signal unlock to the shell.
            try:
                snapshot = self._progress.snapshot()
                if not isinstance(snapshot, dict):
                    snapshot = None
                envelope = LearnProgressState.make(
                    action="snapshot",
                    was_recovered=False,
                    progress=snapshot,
                ).to_dict()
                self._emit(envelope)
            except Exception as exc:  # pragma: no cover — defensive
                print(
                    f"[learn.recital] progress_state emit failed: {exc!r}",
                    file=sys.stderr,
                )
            self._emit_complete(
                lesson_id=lesson_id, schema_reason="completed"
            )
        else:
            # Fail copy with {score} substituted.
            fail_template = str(
                self._outcomes.get(
                    "fail", "{score} of 5. replay when you're ready."
                )
            )
            fail_copy = fail_template.replace("{score}", str(self._score))
            self._emit_outcome_speak(
                text=fail_copy, tts_marker="L116.outcome_fail"
            )
            # The runtime's on_enter_completed will fire its own
            # complete_lesson with reason="user_skip" (because
            # _last_was_match stayed False on the FSM side). Our emit
            # here uses "user_skip" to signal "the recital did not
            # award the unlock" — same schema enum, different semantic
            # to the UI (it reads the fail copy that preceded this).
            self._emit_complete(
                lesson_id=lesson_id, schema_reason="user_skip"
            )

    def _emit_advance(
        self, *, lesson_id: str, reason: str
    ) -> None:
        """Emit ipc.learn.advance for a recital-prompt step.

        ``reason`` ∈ {"action_matched", "user_skip"} — schema-enum
        bounded.
        """
        try:
            envelope = LearnAdvance.make(
                lesson_id=lesson_id, reason=reason
            ).to_dict()
            self._emit(envelope)
        except Exception as exc:  # pragma: no cover — defensive
            print(
                f"[learn.recital] advance emit failed: {exc!r}",
                file=sys.stderr,
            )

    def _emit_outcome_speak(self, *, text: str, tts_marker: str) -> None:
        """Emit the pass/fail outcome copy as tutor_speak."""
        try:
            envelope = LearnTutorSpeak.make(
                text=text,
                tts_marker=tts_marker,
                citations=(),
                data_state="active",
            ).to_dict()
            self._emit(envelope)
        except Exception as exc:  # pragma: no cover — defensive
            print(
                f"[learn.recital] outcome tutor_speak emit failed: {exc!r}",
                file=sys.stderr,
            )

    def _emit_complete(
        self, *, lesson_id: str, schema_reason: str
    ) -> None:
        """Emit ipc.learn.complete_lesson. ``schema_reason`` ∈
        {"completed", "user_skip"} per the schema enum.
        """
        try:
            envelope = LearnCompleteLesson.make(
                lesson_id=lesson_id, reason=schema_reason
            ).to_dict()
            self._emit(envelope)
        except Exception as exc:  # pragma: no cover — defensive
            print(
                f"[learn.recital] complete_lesson emit failed: {exc!r}",
                file=sys.stderr,
            )


__all__ = [
    "RecitalRuntime",
    "_RECITAL_SUBSET_SIZE",
]
