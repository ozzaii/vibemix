# SPDX-License-Identifier: Apache-2.0
"""LessonRuntime — deterministic FSM driving the lesson lifecycle.

Phase 92 (LESSON-01 / LESSON-04). Cardinal invariants this module pins:

  Invariant #1 (single-writer of LearnState) — LessonRuntime is the SOLE
    writer of :class:`vibemix.learn.state.LearnState`. The AST gate
    ``tests/learn/test_runtime_invariants.py`` greps
    ``src/vibemix/learn/`` for any ``learn_state.<field> =`` /
    ``self._learn.<field> =`` assignment outside ``runtime.py`` /
    ``state.py`` and fails red on any match.

  Invariant #3 (trust the audio / live state) — LessonRuntime NEVER
    writes :class:`MusicState` or :class:`ControllerState`. It READS via
    ``MidiMirror.snapshot()`` (P91) + ``ControllerState.deck_snapshot()``
    (P91). The same AST gate confirms zero writes.

  Invariant #4 (one socket) — LessonRuntime does NOT open a second
    websocket listener. It emits via the existing ``ipc_router`` (the
    IpcRouterBus that already binds ws:8765). The AST gate
    ``tests/learn/test_no_new_ws_port.py`` enforces.

  No second MIDI listener — LessonRuntime does NOT call mido's port-
    binding APIs (open-input / set-callback). P91 already binds the
    single MIDI listener that drives ControllerState; LessonRuntime is
    a pure consumer of the lock-guarded snapshot. The CI grep gate
    confirms zero matches for the canonical literal tokens in this file.

States (8):

  ``idle``           — no lesson active; LearnState.current_lesson_id is None.
  ``loaded``         — lesson script loaded; HUD mounted; tutor beat 0 prepared.
  ``awaiting_action`` — highlight painted, waiting for user MIDI action.
  ``hint_strike_1``  — first hint surfaced (after 30 s of no action).
  ``hint_strike_2``  — second hint surfaced (after another 30 s).
  ``hint_strike_3``  — third hint surfaced (last automatic prompt).
  ``advancing``      — user matched action OR clicked "I got it";
                       sequencing the dot-fill + tutor-line ghost-recede
                       before settling into ``completed``.
  ``completed``      — final state. Lesson is finished.

Transitions (5):

  ``load(lesson_id, course_id, controller_id)``
      idle | completed → loaded
  ``begin()``
      loaded → awaiting_action
  ``strike()``
      awaiting_action → hint_strike_1
      | hint_strike_1 → hint_strike_2
      | hint_strike_2 → hint_strike_3
      (no further transition from hint_strike_3 — silently noops with
      ``allow_event_without_transition``)
  ``ack_action(midi)``
      awaiting_action | hint_strike_{1,2,3} → advancing
      (guard: ``action_matches(midi)`` reads CURRICULUM expected_action
      and returns True iff midi matches)
  ``skip()``
      awaiting_action | hint_strike_{1,2,3} → advancing
      (guard: ``min_dwell_elapsed()`` — 45 s anti-speedrun floor)
  ``finish()``
      advancing → completed

Threading model: lives on the asyncio main loop (instantiated in
``__main__.main()`` — P92-04 wires it). The 1 Hz ``tick_loop`` coroutine
drives the 30 s strike escalation timer. There is no thread spawned by
this class; we rely on:

  * the existing 30 Hz ws_broadcast loop for position pushes (P91 + P92);
  * the existing MIDI daemon thread feeding ControllerState (P91);
  * the existing asyncio event loop for emit / tick_loop sleep.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any

from statemachine import State, StateMachine

from vibemix.learn.curriculum import CURRICULUM
from vibemix.learn.state import LearnState
from vibemix.ui_bus.learn_messages import (
    LearnAdvance,
    LearnCompleteLesson,
    LearnHighlight,
    LearnLessonLoaded,
    LearnProgressState,
    LearnTutorSpeak,
)


# ---------------------------------------------------------------------------
# CC drop default threshold — 30% of the 127 CC range
# ---------------------------------------------------------------------------
# A CC delta of ≥38 (= ceil(127 * 0.30)) is the "the user actually moved
# this control" floor. The fixture may override per-lesson via the
# ``expected_action.min_delta`` field (used by P94+ for finer-grained
# tempo / filter sweeps). When the lesson's expected_action omits
# ``min_delta``, this default applies.
_CC_DEFAULT_MIN_DELTA = 38


class LessonRuntime(StateMachine):
    """Deterministic FSM for the lesson lifecycle. Sole writer of
    :class:`LearnState` (Invariant #1).
    """

    # When a guard returns False, ``send`` returns None instead of
    # raising ``TransitionNotAllowed``. This matches the test contract:
    # ``rt.send("skip")`` before the 45 s floor must NOT raise — it must
    # silently leave the state untouched.
    allow_event_without_transition = True

    # --- States (class attributes — python-statemachine convention) -------
    idle = State(initial=True)
    loaded = State()
    awaiting_action = State()
    hint_strike_1 = State()
    hint_strike_2 = State()
    hint_strike_3 = State()
    advancing = State()
    # ``completed`` is NOT marked ``final=True`` because the ``load``
    # transition lets a freshly-completed runtime re-load a new lesson
    # (the post-skip / post-completion relaunch flow). python-
    # statemachine's trap-state check requires every non-final state to
    # have at least one outgoing transition; ``load`` satisfies that.
    completed = State()

    # --- Transitions (5; chained with ``|``) ------------------------------
    # ``load`` from completed → loaded handles the post-skip relaunch
    # flow (Plan 92-04 wires it).
    load = idle.to(loaded) | completed.to(loaded)
    begin = loaded.to(awaiting_action)
    strike = (
        awaiting_action.to(hint_strike_1)
        | hint_strike_1.to(hint_strike_2)
        | hint_strike_2.to(hint_strike_3)
    )
    # Guarded transition: only advances if ``action_matches(midi)`` is
    # True. python-statemachine evaluates ``cond=`` on each
    # ``send("ack_action", midi=...)``.
    ack_action = (
        awaiting_action.to(advancing, cond="action_matches")
        | hint_strike_1.to(advancing, cond="action_matches")
        | hint_strike_2.to(advancing, cond="action_matches")
        | hint_strike_3.to(advancing, cond="action_matches")
    )
    # Skip path — guarded ONLY by the 45 s min-dwell floor. The
    # ``allow_event_without_transition`` flag converts a False guard into
    # a silent no-op (state stays put).
    skip = (
        awaiting_action.to(advancing, cond="min_dwell_elapsed")
        | hint_strike_1.to(advancing, cond="min_dwell_elapsed")
        | hint_strike_2.to(advancing, cond="min_dwell_elapsed")
        | hint_strike_3.to(advancing, cond="min_dwell_elapsed")
    )
    finish = advancing.to(completed)

    # ------------------------------------------------------------------
    # __init__
    # ------------------------------------------------------------------
    def __init__(
        self,
        *,
        learn_state: LearnState,
        midi_mirror: Any,
        controller_state: Any,
        ipc_router: Any,
        progress_store: Any,
    ) -> None:
        """Build a LessonRuntime bound to its 5 collaborators.

        Args:
            learn_state: The single-writer dataclass. LessonRuntime is
                the SOLE writer (Invariant #1).
            midi_mirror: The 30 Hz controller-position snapshotter
                (P91 :class:`MidiMirror`). Read-only consumer.
            controller_state: The lock-guarded MIDI decoder state
                (P91 :class:`vibemix.midi.state.ControllerState`).
                Read-only consumer.
            ipc_router: The existing :class:`IpcRouterBus` interface
                that already binds ws:8765. LessonRuntime emits via
                ``ipc_router.emit(<envelope_dict>)`` — no new socket
                (Invariant #4).
            progress_store: The P92-04
                :class:`vibemix.learn.progress.ProgressStore` (lands
                in Plan 92-04). LessonRuntime calls
                ``progress_store.mark_completed(course_id, lesson_id)``
                + ``progress_store.snapshot()`` +
                ``progress_store.dots_for_course(course_id)``. P92-03
                tests pass a Mock; the live wire-in is P92-04.
        """
        self._learn = learn_state
        self._mirror = midi_mirror
        self._cs = controller_state
        self._ipc = ipc_router
        self._progress = progress_store
        # The wall-clock anchor for the 30 s strike escalation timer.
        # Reset on every ``on_enter_<state>`` callback for the states
        # that the tick_loop watches (awaiting_action, hint_strike_*).
        self._state_entered_at = time.monotonic()
        # Tracks whether the latest ack/skip event was a real match.
        # ``on_ack_action`` / ``on_skip`` set this flag BEFORE
        # ``on_enter_advancing`` fires, so the advance envelope's
        # ``reason`` field carries the right token.
        self._last_was_match: bool = False
        super().__init__()

    # ------------------------------------------------------------------
    # Guards — both predicates accept ``**kwargs`` because python-
    # statemachine forwards framework metadata (event_data, machine,
    # transition, state, source, target) alongside user kwargs.
    # ------------------------------------------------------------------
    def action_matches(
        self,
        midi: dict[str, Any] | None = None,
        expected: dict[str, Any] | None = None,
        **_kwargs: Any,
    ) -> bool:
        """Return True iff the supplied MIDI event matches the lesson's
        ``expected_action``.

        Dual-use signature:

          * When ``expected`` is omitted (the FSM-internal call path),
            the expected action is read from
            ``CURRICULUM[self._learn.current_lesson_id].script[
            "expected_action"]``. This is how the ``ack_action`` guard
            uses it.
          * When ``expected`` is supplied (the direct-test call path
            from ``tests/learn/test_advancement_gates.py``), it is used
            as-is. This lets tests drive the predicate without first
            walking through the full FSM lifecycle.

        CC branch: matches when

          * ``midi["type"] == "cc"``,
          * ``midi["control"] == expected["control"]``, AND
          * ``abs(midi["value"] - midi["prev_value"])`` >=
            ``expected.get("min_delta", 38)`` (30% of the 127 CC range
            by default).

        Button branch: matches when

          * ``midi["type"] == "button"``,
          * ``midi["control"] == expected["control"]``,
          * ``midi["direction"] == expected["direction"]``, AND
          * ``midi["deck"] == expected["deck"]`` (when both sides
            declare a deck).
        """
        if midi is None:
            return False

        # Lookup expected from the active lesson if the caller didn't
        # supply one. This is the FSM ``cond=`` path.
        if expected is None:
            lesson_id = self._learn.current_lesson_id
            if lesson_id is None or lesson_id not in CURRICULUM:
                return False
            expected = CURRICULUM[lesson_id].script.get("expected_action")
            if not isinstance(expected, dict):
                return False

        expected_type = expected.get("type")
        midi_type = midi.get("type")
        if midi_type != expected_type:
            return False

        # ---- CC delta branch -----------------------------------------
        if expected_type == "cc":
            if midi.get("control") != expected.get("control"):
                return False
            cur = int(midi.get("value", 0))
            prev = int(midi.get("prev_value", cur))
            min_delta = int(expected.get("min_delta", _CC_DEFAULT_MIN_DELTA))
            return abs(cur - prev) >= min_delta

        # ---- Button branch -------------------------------------------
        if expected_type == "button":
            if midi.get("control") != expected.get("control"):
                return False
            if midi.get("direction") != expected.get("direction"):
                return False
            # Only enforce deck match when both sides declared a deck.
            expected_deck = expected.get("deck")
            if expected_deck is not None and expected_deck != "":
                if midi.get("deck") != expected_deck:
                    return False
            return True

        return False

    def min_dwell_elapsed(self, **_kwargs: Any) -> bool:
        """45 s anti-speedrun floor. Returns True iff
        ``time.monotonic() - self._learn.lesson_started_at >= 45.0``.
        """
        return (
            time.monotonic() - self._learn.lesson_started_at >= 45.0
        )

    # ------------------------------------------------------------------
    # Transition action callbacks (``on_<event>``) — these fire DURING
    # the transition, before ``on_enter_<state>``. We use them to set
    # the ``_last_was_match`` flag the advance envelope reads.
    # ------------------------------------------------------------------
    def on_ack_action(self, **_kwargs: Any) -> None:
        self._last_was_match = True

    def on_skip(self, **_kwargs: Any) -> None:
        self._last_was_match = False

    # ------------------------------------------------------------------
    # State-entry callbacks — the sole-writer surface for LearnState
    # ------------------------------------------------------------------
    def on_enter_loaded(
        self,
        lesson_id: str | None = None,
        course_id: str | None = None,
        controller_id: str | None = None,
        **_kwargs: Any,
    ) -> None:
        """Mutate :class:`LearnState` fields for the new lesson, then
        emit :class:`LearnLessonLoaded`.

        Sole-writer site for: ``current_course_id``,
        ``current_lesson_id``, ``current_controller_id``,
        ``current_beat_index``, ``strike_count``, ``lesson_started_at``.
        """
        # Update LearnState — Invariant #1 binding (sole writer).
        if lesson_id is not None:
            self._learn.current_lesson_id = lesson_id
        if course_id is not None:
            self._learn.current_course_id = course_id
        if controller_id is not None:
            self._learn.current_controller_id = controller_id
        self._learn.current_beat_index = 0
        self._learn.strike_count = 0
        self._learn.lesson_started_at = time.monotonic()
        self._state_entered_at = self._learn.lesson_started_at

        # Emit the HUD-mount envelope. Progress dots come from the
        # progress store; tests mock it (returning a MagicMock that
        # iterates to empty tuple — schema-acceptable empty array).
        lesson = CURRICULUM[self._learn.current_lesson_id]
        dots = self._progress.dots_for_course(self._learn.current_course_id)
        try:
            envelope = LearnLessonLoaded.make(
                course_id=self._learn.current_course_id or "",
                lesson_id=self._learn.current_lesson_id or "",
                title=lesson.title,
                controller_id=self._learn.current_controller_id or "",
                progress_dots=dots,
            ).to_dict()
            self._ipc.emit(envelope)
        except Exception as exc:  # pragma: no cover — defensive
            # An invalid progress-dots payload should not wedge the FSM.
            # Surface the failure on stderr and continue; the HUD will
            # simply not mount this lesson's progress strip.
            import sys

            print(f"[learn.runtime] lesson_loaded emit failed: {exc!r}", file=sys.stderr)

    def on_enter_awaiting_action(self, **_kwargs: Any) -> None:
        """Paint the highlight on the expected control, then speak
        beat 0 of the tutor narration. Resets the state-entry timer
        the tick_loop reads.
        """
        lesson = CURRICULUM[self._learn.current_lesson_id]
        expected = lesson.script["expected_action"]
        # Build the highlight envelope. ``LearnHighlight.make`` accepts
        # a raw dict for ``expected_action`` and normalises it into a
        # validated nested struct.
        try:
            highlight = LearnHighlight.make(
                control_id=expected.get("control", ""),
                deck=expected.get("deck", ""),
                cue_color="amber",
                cue_shape="pulse-ring",
                annotation=expected.get("annotation", ""),
                expected_action=expected,
            ).to_dict()
            self._ipc.emit(highlight)
        except Exception as exc:  # pragma: no cover — defensive
            import sys

            print(f"[learn.runtime] highlight emit failed: {exc!r}", file=sys.stderr)

        # Speak beat 0 — text comes from the JSON fixture (TONE-02).
        self._emit_tutor_beat(0)
        # Reset the strike timer's state-entry anchor.
        self._state_entered_at = time.monotonic()

    def on_enter_hint_strike_1(self, **_kwargs: Any) -> None:
        self._learn.strike_count = 1
        self._emit_hint(1)
        self._state_entered_at = time.monotonic()

    def on_enter_hint_strike_2(self, **_kwargs: Any) -> None:
        self._learn.strike_count = 2
        self._emit_hint(2)
        self._state_entered_at = time.monotonic()

    def on_enter_hint_strike_3(self, **_kwargs: Any) -> None:
        self._learn.strike_count = 3
        self._emit_hint(3)
        self._state_entered_at = time.monotonic()

    def on_enter_advancing(self, **_kwargs: Any) -> None:
        """Emit :class:`LearnAdvance` with the reason set by the
        triggering transition (``on_ack_action`` → ``"action_matched"``;
        ``on_skip`` → ``"user_skip"``). Then schedule
        ``_finish_when_dwelled`` to move into ``completed`` after the
        45 s min-dwell + a small settle for the UI advance animation.

        Scheduling falls back to a no-op when no asyncio event loop is
        running (the synchronous unit-test path) — state stays in
        ``advancing``, which is one of the two acceptable terminal
        observations per the test contract.
        """
        reason = "action_matched" if self._last_was_match else "user_skip"
        try:
            advance = LearnAdvance.make(
                lesson_id=self._learn.current_lesson_id or "",
                reason=reason,
            ).to_dict()
            self._ipc.emit(advance)
        except Exception as exc:  # pragma: no cover — defensive
            import sys

            print(f"[learn.runtime] advance emit failed: {exc!r}", file=sys.stderr)

        # Schedule the dwell-then-finish chain. No-op outside an async
        # loop (tests run synchronously); the live path (Plan 92-04
        # __main__) always has a loop. Probe the loop FIRST so we don't
        # create an orphan coroutine that pytest warns about.
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            # No running event loop — synchronous test path. State
            # remains in ``advancing`` which satisfies the contract.
            pass
        else:
            asyncio.create_task(self._finish_when_dwelled())

    async def _finish_when_dwelled(self) -> None:
        """Wait for the remaining min-dwell window + ~0.7 s UI settle,
        then send ``finish``."""
        remaining = max(
            0.0,
            45.0 - (time.monotonic() - self._learn.lesson_started_at),
        )
        await asyncio.sleep(remaining + 0.7)
        self.send("finish")

    def on_enter_completed(self, **_kwargs: Any) -> None:
        """Persist progress + emit terminal envelopes."""
        try:
            self._progress.mark_completed(
                self._learn.current_course_id,
                self._learn.current_lesson_id,
            )
        except Exception as exc:  # pragma: no cover — defensive
            import sys

            print(f"[learn.runtime] mark_completed failed: {exc!r}", file=sys.stderr)

        try:
            done = LearnCompleteLesson.make(
                lesson_id=self._learn.current_lesson_id or "",
                reason="completed" if self._last_was_match else "user_skip",
            ).to_dict()
            self._ipc.emit(done)
        except Exception as exc:  # pragma: no cover — defensive
            import sys

            print(f"[learn.runtime] complete_lesson emit failed: {exc!r}", file=sys.stderr)

        # Snapshot the progress store. Tests mock it (returning a
        # MagicMock); the snapshot envelope's ``progress`` field is
        # optional schema-side, so a non-dict-shaped Mock would fail
        # validation. Be defensive: only emit when the snapshot is a
        # dict-like mapping.
        try:
            snapshot = self._progress.snapshot()
            if not isinstance(snapshot, dict):
                snapshot = None
            progress_env = LearnProgressState.make(
                action="snapshot",
                progress=snapshot,
            ).to_dict()
            self._ipc.emit(progress_env)
        except Exception as exc:  # pragma: no cover — defensive
            import sys

            print(f"[learn.runtime] progress snapshot emit failed: {exc!r}", file=sys.stderr)

    # ------------------------------------------------------------------
    # Helpers — tutor + hint emit sites
    # ------------------------------------------------------------------
    def _emit_tutor_beat(self, beat: int) -> None:
        """Emit :class:`LearnTutorSpeak` with text read VERBATIM from
        the JSON fixture (TONE-02). The text is never LLM-generated at
        runtime; the AST gate ``tests/learn/test_scripts_are_fixtures.py``
        confirms zero generative writes here.
        """
        lesson = CURRICULUM[self._learn.current_lesson_id]
        beats = lesson.script.get("tutor_speak", [])
        if beat >= len(beats):
            return
        fixture = beats[beat]
        try:
            speak = LearnTutorSpeak.make(
                text=fixture["text"],
                tts_marker=fixture["tts_marker"],
                citations=tuple(fixture.get("citations", [])),
                data_state="active",
            ).to_dict()
            self._ipc.emit(speak)
        except Exception as exc:  # pragma: no cover — defensive
            import sys

            print(f"[learn.runtime] tutor_speak emit failed: {exc!r}", file=sys.stderr)

    def _emit_hint(self, strike: int) -> None:
        """Emit :class:`LearnTutorSpeak` with the per-strike hint text
        (``data_state="hint"`` so the UI styles it italic / muted).
        """
        lesson = CURRICULUM[self._learn.current_lesson_id]
        hints = lesson.script.get("hints", [])
        # ``strike`` is 1-indexed; hints[] is 0-indexed.
        if strike - 1 >= len(hints):
            return
        hint = hints[strike - 1]
        try:
            speak = LearnTutorSpeak.make(
                text=hint["text"],
                tts_marker=hint["tts_marker"],
                citations=tuple(hint.get("citations", [])),
                data_state="hint",
            ).to_dict()
            self._ipc.emit(speak)
        except Exception as exc:  # pragma: no cover — defensive
            import sys

            print(f"[learn.runtime] hint emit failed: {exc!r}", file=sys.stderr)

    # ------------------------------------------------------------------
    # 1 Hz tick loop — strike escalation timer
    # ------------------------------------------------------------------
    async def tick_loop(self, stop_event: asyncio.Event) -> None:
        """Drive the 30 s strike escalation timer.

        Polled once per second. When the current state is
        ``awaiting_action`` / ``hint_strike_1`` / ``hint_strike_2`` AND
        the time since the last state-entry is ≥30 s AND fewer than 3
        strikes have fired, fire the ``strike`` transition.

        The loop is a SEPARATE coroutine that lives alongside the 30 Hz
        ``ws_broadcast`` task — no shared-state contention; the strike
        cadence is far slower than the broadcast cadence and the
        callback-side emits are cheap.
        """
        while not stop_event.is_set():
            await asyncio.sleep(1.0)
            cur = self.current_state.id
            if cur in ("awaiting_action", "hint_strike_1", "hint_strike_2"):
                elapsed_in_state = (
                    time.monotonic() - self._state_entered_at
                )
                if (
                    elapsed_in_state >= 30.0
                    and self._learn.strike_count < 3
                ):
                    self.send("strike")
