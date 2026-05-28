# SPDX-License-Identifier: Apache-2.0
"""RecitalRuntime — drives Recital lessons (Course 1 + Course 2 gates).

Phase 94 Plan 03 (CURR-1.16 binding — Course 1 unlock gate).
Phase 95          (CURR-2.14 binding — Course 2 unlock gate).

Architecture
============

This controller is an OBSERVER of :class:`LessonRuntime` for recital
lessons. It reads ``recital_pool`` (≥5 entries) + ``recital_outcomes``
from the active lesson's script, samples
``_RECITAL_SUBSET_SIZE = 5`` entries deterministically using a daily-
rotating seed, drives each prompt, scores correctness honestly (no
partial-credit), and on a pass flips the appropriate
:class:`LearnProgress.course_N_unlocked` to ``True`` + calls
``save_progress`` (the course-N unlock gate).

Course detection
================

The recital lesson script declares its course implicitly via the pool
entries' shape:

* **Course 1 mode (L1.16)** — pool entries carry only ``prompt`` +
  ``expected_action``. Pass criteria: ``score >= 5``. Unlock target:
  ``course_2_unlocked``. Outcome copy uses ``{score}`` substitution.
* **Course 2 mode (L2.14)** — pool entries also carry
  ``transition_type``. Pass criteria: ``score >= 5`` AND
  ``len(distinct transition_types performed) >= 3``. Unlock target:
  ``course_3_unlocked``. Outcome copy uses ``{score}`` AND ``{types}``
  substitution.

Mode detection happens at ``start()`` time by inspecting the first pool
entry's keys — no explicit course-id flag in the fixture. Future
courses (C4+) can extend the predicate without breaking the C1/C2
contracts.

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

# CURR-1.16 / CURR-2.14 lock — recital surfaces EXACTLY 5 prompts.
# Locked here as a module-level constant so the AST tests can grep it.
_RECITAL_SUBSET_SIZE: int = 5

# CURR-2.14 lock — Course 2 recital requires at least this many DISTINCT
# transition types across the 5 correctly-performed prompts to award the
# unlock. The 5 sampled prompts may include duplicates of the same
# transition_type (pool size = 7; deterministic sample may pick e.g.
# {long_blend, eq_swap, eq_swap, filter_fade, drop_swap} — that scores
# 5/5 by count but only 4 distinct types). The Course 2 product
# constraint is "the user has demonstrated genuine variety", so the
# distinct-type floor is the gate that prevents grinding the same
# transition five times.
_COURSE_2_DISTINCT_TYPES_REQUIRED: int = 3

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
        # Course detection — derived at .start() from the first pool
        # entry. "course_1" if entries lack ``transition_type``;
        # "course_2" if every entry carries one. Used by _finalize()
        # to pick the unlock field + outcome-copy template.
        self._mode: str = "course_1"
        # Course 2 only: the set of distinct ``transition_type`` values
        # the user has correctly performed. Populated in ack() when in
        # course_2 mode; ignored otherwise.
        self._seen_transition_types: set[str] = set()

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

        Course detection (Plan 95): if any pool entry carries a
        ``transition_type`` field, switch to ``course_2`` mode — pass
        requires score>=5 AND >=3 distinct transition types; unlock
        target is ``course_3_unlocked``; outcome copy supports the
        ``{types}`` placeholder in addition to ``{score}``. Otherwise
        the controller stays in ``course_1`` mode (L1.16 contract).
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

        # Detect course mode by inspecting pool entries. If ANY entry
        # carries ``transition_type``, this is a Course 2 recital. We
        # use "any" rather than "all" so a mixed-shape fixture (legacy
        # entry + new entries) still routes through the Course 2 path
        # and the distinct-types floor catches the legacy entry as
        # "no type recorded" — defensive on fixture drift.
        has_transition_type = any(
            isinstance(entry, dict) and "transition_type" in entry
            for entry in pool
        )
        self._mode = "course_2" if has_transition_type else "course_1"

        seed = (
            self._seed
            if self._seed is not None
            else int(time.time() // 86400)
        )
        rng = self._rng_class(seed)
        self._sampled = rng.sample(pool, k=_RECITAL_SUBSET_SIZE)
        self._active_idx = -1
        self._score = 0
        self._seen_transition_types = set()
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

        Course 2 mode (Plan 95): the active prompt's
        ``transition_type`` (if present) is recorded in
        ``self._seen_transition_types`` — this is the set the finalizer
        compares against ``_COURSE_2_DISTINCT_TYPES_REQUIRED`` to gate
        the unlock. Course 1 mode ignores transition_type entirely.
        """
        if self._finalised:
            return
        # Record the transition_type BEFORE advancing the index — the
        # current ``self._active_idx`` still points at the prompt the
        # user just satisfied. Only meaningful in course_2 mode (the
        # set goes unread in course_1).
        if 0 <= self._active_idx < len(self._sampled):
            entry = self._sampled[self._active_idx]
            ttype = entry.get("transition_type") if isinstance(entry, dict) else None
            if isinstance(ttype, str) and ttype:
                self._seen_transition_types.add(ttype)
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
        self._mode = "course_1"
        self._seen_transition_types = set()
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

        # Emit prompt text as tutor_speak. Course-aware tts_marker
        # prefix so TTS caching / log scraping can distinguish C1 vs
        # C2 recital beats.
        tts_prefix = "L214" if self._mode == "course_2" else "L116"
        try:
            envelope = LearnTutorSpeak.make(
                text=str(entry.get("prompt", "")).strip(),
                tts_marker=f"{tts_prefix}.recital{self._active_idx + 1}",
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
        """Surface pass/fail copy + persist unlock on pass + emit
        complete_lesson. Idempotent — guarded by self._finalised.

        Pass criteria differ by mode (Plan 95):

        * Course 1 (L1.16): ``score >= 5``. Unlock target:
          ``course_2_unlocked``.
        * Course 2 (L2.14): ``score >= 5`` AND
          ``len(seen_transition_types) >= 3``. Unlock target:
          ``course_3_unlocked``. Distinct-type floor is the anti-grind
          gate — a user who hits the same transition 5 times in a row
          scores 5 by count but fails the variety floor.

        Outcome-copy substitution mirrors the mode:

        * Course 1 fail: ``{score}`` substituted.
        * Course 2 pass: ``{types}`` substituted (in case the fixture
          author wants to surface the count). Course 2 fail:
          ``{score}`` AND ``{types}`` substituted.
        """
        if self._finalised:
            return
        self._finalised = True

        # Score floor (both modes).
        score_passed = self._score >= _RECITAL_SUBSET_SIZE
        n_types = len(self._seen_transition_types)
        # Course-2-only variety floor; in course_1 the floor is
        # vacuously satisfied (no transition_type field to count).
        if self._mode == "course_2":
            variety_passed = n_types >= _COURSE_2_DISTINCT_TYPES_REQUIRED
        else:
            variety_passed = True
        passed = score_passed and variety_passed

        # Pick the unlock field + default copy by mode.
        if self._mode == "course_2":
            unlock_field = "course_3_unlocked"
            default_pass = "5 of 5. course 3 unlocked."
            default_fail = (
                "{score} of 5 with {types} different transition types. "
                "replay when you're ready."
            )
            tts_pass_marker = "L214.outcome_pass"
            tts_fail_marker = "L214.outcome_fail"
        else:
            unlock_field = "course_2_unlocked"
            default_pass = "5 of 5. course 2 unlocked."
            default_fail = "{score} of 5. replay when you're ready."
            tts_pass_marker = "L116.outcome_pass"
            tts_fail_marker = "L116.outcome_fail"

        if passed:
            # Flip the unlock bit on the SHIPPED progress dataclass
            # field (course_2_unlocked or course_3_unlocked) +
            # persist atomically.
            setattr(self._progress, unlock_field, True)
            try:
                self._save(self._progress)
            except Exception as exc:  # pragma: no cover — defensive
                print(
                    f"[learn.recital] save_progress failed: {exc!r}",
                    file=sys.stderr,
                )

            # Surface pass copy — both {score} and {types} substituted
            # so a fixture author can use either placeholder.
            pass_template = str(self._outcomes.get("pass", default_pass))
            pass_copy = pass_template.replace(
                "{score}", str(self._score)
            ).replace("{types}", str(n_types))
            self._emit_outcome_speak(
                text=pass_copy, tts_marker=tts_pass_marker
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
            # Fail copy with {score} + {types} substituted. Both
            # placeholders are replaced even when the fixture author
            # only uses one — extra-placeholder substitutions are
            # no-ops on a template lacking the placeholder.
            fail_template = str(self._outcomes.get("fail", default_fail))
            fail_copy = fail_template.replace(
                "{score}", str(self._score)
            ).replace("{types}", str(n_types))
            self._emit_outcome_speak(
                text=fail_copy, tts_marker=tts_fail_marker
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
    "_COURSE_2_DISTINCT_TYPES_REQUIRED",
    "_RECITAL_SUBSET_SIZE",
]
