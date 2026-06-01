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
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from statemachine import State, StateMachine

from vibemix.learn.curriculum import CURRICULUM
from vibemix.learn.graduation import (
    GraduationSummary,
    build_graduation_summary,
    build_graduation_tutor_line,
    graduation_citations,
)
from vibemix.learn.harmonic_practice import (
    HarmonicPracticePair,
    build_harmonic_practice_prompt,
    harmonic_practice_citations,
)
from vibemix.learn.lesson_flow import LessonFlow, LessonStep, build_lesson_flow
from vibemix.learn.observability import learn_tutor_speak_observability_events
from vibemix.learn.state import LearnState
from vibemix.learn.teaching_loop import (
    TeachingTurn,
    plan_adaptive_turn,
    plan_hint_turn,
    plan_teaching_turn,
)
from vibemix.library.prepared_pool import (
    MIN_PREPARED_POOL_TRACKS,
    PreparedPool,
    build_prepared_pool_prompt,
)
from vibemix.ui_bus.learn_messages import (
    LearnAdvance,
    LearnCompleteLesson,
    LearnHighlight,
    LearnLessonLoaded,
    LearnProgressState,
    LearnTeachingLoopPayload,
    LearnTeachingObservationPayload,
    LearnTeachingVerificationPayload,
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
_MISMATCH_HINT_THROTTLE_S = 1.5
_CONTROL_LABELS = {
    "cue": "cue",
    "eq_hi": "high EQ",
    "eq_low": "low EQ",
    "eq_mid": "mid EQ",
    "filter": "filter",
    "filter_fx": "filter FX",
    "fx_echo": "echo FX",
    "headphone_cue": "headphone cue",
    "hotcue": "hot cue",
    "jog": "jog wheel",
    "jog_touch": "jog wheel",
    "jog_touched": "jog wheel",
    "lesson_continue": "continue",
    "loop_in": "loop in",
    "loop_out": "loop out",
    "master_vol": "master volume",
    "play": "play",
    "sync": "sync",
    "tap_tempo": "tap tempo",
    "tempo": "pitch fader",
    "vol": "channel fader",
    "xfader": "crossfader",
}


@dataclass(frozen=True, slots=True)
class _AdaptiveMismatchHint:
    text: str
    citations: tuple[str, ...]


def _control_and_deck(action: dict[str, Any]) -> tuple[str, str]:
    """Return normalized ``(control, deck)`` from either field style."""
    control = str(action.get("control", "")).strip()
    deck = str(action.get("deck", "") or "").strip()
    if not deck and ":" in control:
        control, _, parsed_deck = control.rpartition(":")
        deck = parsed_deck.strip()
    return control, deck


def _observable_control_id(control: str, deck: str) -> str:
    return f"{control}:{deck}" if deck else control


def _format_evidence_time(t_session: float) -> str:
    return f"{max(0.0, float(t_session)):.1f}"


def _format_control_label(control: str, deck: str = "") -> str:
    """Return a short learner-facing label for a MIDI control."""
    control, parsed_deck = _control_and_deck(
        {"control": control, "deck": deck}
    )
    deck = parsed_deck
    label = _CONTROL_LABELS.get(control, control.replace("_", " ").strip())
    if not label:
        return ""
    if deck:
        return f"deck {deck} {label}"
    return label


def _int_field(row: dict[str, Any], field: str, default: int) -> int:
    try:
        return int(row.get(field, default))
    except (TypeError, ValueError):
        return default


def _expected_action_verb(expected: dict[str, Any]) -> str:
    expected_type = expected.get("type")
    direction = str(expected.get("direction", "down") or "down")
    if expected_type == "button":
        return "release" if direction == "up" else "press"
    return "move"


def _mismatch_citations(
    *,
    expected_control: str,
    expected_deck: str,
    midi_control: str,
    midi_deck: str,
    source: str,
    evidence_time: float,
) -> tuple[str, ...]:
    citations: list[str] = []
    observed_id = _observable_control_id(midi_control, midi_deck)
    expected_id = _observable_control_id(expected_control, expected_deck)
    if observed_id:
        observed_kind = "screen" if source == "click" else "midi"
        if observed_kind == "midi":
            citations.append(
                f"[midi:{observed_id}@{_format_evidence_time(evidence_time)}]"
            )
        else:
            citations.append(f"[screen:{observed_id}]")
    if expected_id and f"[screen:{expected_id}]" not in citations:
        citations.append(f"[screen:{expected_id}]")
    return tuple(citations[:4])


def _adaptive_mismatch_hint(
    *,
    expected: dict[str, Any],
    midi: dict[str, Any],
    evidence_time: float,
) -> _AdaptiveMismatchHint:
    """Build the deterministic hint for a guard-rejected action."""
    expected_control, expected_deck = _control_and_deck(expected)
    midi_control, midi_deck = _control_and_deck(midi)
    expected_label = _format_control_label(expected_control, expected_deck)
    observed_label = _format_control_label(midi_control, midi_deck)
    expected_type = expected.get("type")
    midi_type = midi.get("type")
    source = str(midi.get("source", "midi") or "midi")
    citations = _mismatch_citations(
        expected_control=expected_control,
        expected_deck=expected_deck,
        midi_control=midi_control,
        midi_deck=midi_deck,
        source=source,
        evidence_time=evidence_time,
    )

    if not expected_label:
        return _AdaptiveMismatchHint(
            text="use the highlighted control.",
            citations=citations,
        )

    same_control = midi_control == expected_control
    same_deck = not expected_deck or midi_deck == expected_deck
    if same_control and not same_deck:
        verb = _expected_action_verb(expected)
        if expected_type == "button":
            return _AdaptiveMismatchHint(
                text=f"{verb} {expected_label}.",
                citations=citations,
            )
        return _AdaptiveMismatchHint(
            text=f"use {expected_label}.",
            citations=citations,
        )

    if same_control:
        verb = _expected_action_verb(expected)
        if midi_type != expected_type:
            return _AdaptiveMismatchHint(
                text=f"{verb} {expected_label}.",
                citations=citations,
            )
        if expected_type == "cc":
            cur = _int_field(midi, "value", 0)
            prev = _int_field(midi, "prev_value", cur)
            min_delta = _int_field(expected, "min_delta", _CC_DEFAULT_MIN_DELTA)
            if abs(cur - prev) < min_delta:
                return _AdaptiveMismatchHint(
                    text=f"move {expected_label} farther.",
                    citations=citations,
                )
        if expected_type == "button":
            return _AdaptiveMismatchHint(
                text=f"{verb} {expected_label}.",
                citations=citations,
            )
        return _AdaptiveMismatchHint(
            text=f"use {expected_label}.",
            citations=citations,
        )

    if observed_label:
        return _AdaptiveMismatchHint(
            text=f"that was {observed_label}. use {expected_label}.",
            citations=citations,
        )
    return _AdaptiveMismatchHint(
        text=f"use {expected_label}.",
        citations=citations,
    )


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
    observer_complete = (
        awaiting_action.to(completed)
        | hint_strike_1.to(completed)
        | hint_strike_2.to(completed)
        | hint_strike_3.to(completed)
    )
    finish = advancing.to(completed)

    @property
    def current_state(self) -> State:
        """Compatibility shim without python-statemachine's deprecation noise.

        Older Learn tests and diagnostics read ``runtime.current_state.id``.
        Upstream now warns for its inherited property and prefers
        ``current_state_value``; returning the same ``State`` object from our
        subclass keeps that existing surface quiet and explicit.
        """
        return self.states_map[self.current_state_value]

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
        evidence_registry: Any | None = None,
        evidence_clock: Callable[[], float] | None = None,
        prepared_pool_loader: Callable[[], PreparedPool | None] | None = None,
        harmonic_pair_loader: Callable[[], HarmonicPracticePair | None] | None = None,
        graduation_summary_loader: Callable[[Any], GraduationSummary | None] | None = None,
        session_event_logger: Callable[[str, dict[str, Any]], None] | None = None,
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
                ``progress_store.dots_for_course(course_id, current_lesson_id=...)``. P92-03
                tests pass a Mock; the live wire-in is P92-04.
            evidence_registry: Optional shared EvidenceRegistry. When
                supplied, lesson highlights and learner actions are
                recorded before tutor hints cite them.
            evidence_clock: Optional session-time supplier for registry
                writes. Live wiring passes ``MusicState.set_seconds``;
                tests can pass a fixed clock for deterministic citations.
            prepared_pool_loader: Optional Course 3 hook that returns the
                newest real saved playlist/set-prep pool. None keeps the
                runtime byte-identical for tests and installs without a pool.
            harmonic_pair_loader: Optional Course 2 hook that returns one
                deterministic library-grounded Camelot pair for L2.11. None
                keeps the fixture-only path unchanged when no library exists.
            graduation_summary_loader: Optional L3.06 hook that reads the
                existing progress/profile/debrief seams. None uses the shipped
                local storage readers.
            session_event_logger: Optional existing session-recorder seam. Live
                wiring passes ``VoiceRecorder.log_event`` through a fail-soft
                adapter so Learn milestones land in ``events.jsonl`` for later
                debrief/profile tooling.
        """
        self._learn = learn_state
        self._mirror = midi_mirror
        self._cs = controller_state
        self._ipc = ipc_router
        self._progress = progress_store
        self._evidence_registry = evidence_registry
        self._evidence_clock = evidence_clock
        self._prepared_pool_loader = prepared_pool_loader
        self._harmonic_pair_loader = harmonic_pair_loader
        self._graduation_summary_loader = graduation_summary_loader
        self._session_event_logger = session_event_logger
        # The wall-clock anchor for the 30 s strike escalation timer.
        # Reset on every ``on_enter_<state>`` callback for the states
        # that the tick_loop watches (awaiting_action, hint_strike_*).
        self._state_entered_at = time.monotonic()
        # Tracks whether the latest ack/skip event was a real match.
        # ``on_ack_action`` / ``on_skip`` set this flag BEFORE
        # ``on_enter_advancing`` fires, so the advance envelope's
        # ``reason`` field carries the right token.
        self._last_was_match: bool = False
        # WR-04 fix (P92 REVIEW): track the in-flight _finish_when_dwelled
        # task so re-load can cancel it. Without this, a post-completion
        # replay can have a stale finish task wake up ~45 s later and
        # silently no-op via allow_event_without_transition — the task
        # itself is a single coroutine but the strong-ref pattern via
        # bare ``asyncio.create_task`` drops the handle, so long-lived
        # sessions with multiple lesson replays slowly leak coroutines.
        self._finish_task: asyncio.Task | None = None
        # Plan 94-03 — per-lesson observer registry. Maps lesson_id to a
        # controller object exposing .start(script, lesson_id) /
        # .matches(midi) / .ack(lesson_id) / .stop(lesson_id). When the
        # active lesson has a registered observer, the runtime delegates
        # on_enter_awaiting_action / on_ack_action / on_enter_completed
        # to it. The observer NEVER writes LearnState; Invariant #1
        # remains bound to LessonRuntime alone (AST gate stays green).
        self._lesson_observers: dict[str, Any] = {}
        self._active_flow: LessonFlow | None = None
        self._active_step_index: int = 0
        self._last_mismatch_hint_at: float = 0.0
        super().__init__()

    @property
    def current_step_id(self) -> str | None:
        """Return the active structured-flow step id, if any."""
        step = self._active_step()
        return step.step_id if step is not None else None

    # ------------------------------------------------------------------
    # Plan 94-03 — per-lesson observer registry (CURR-1.14 / CURR-1.16)
    # ------------------------------------------------------------------
    def register_lesson_observer(
        self, lesson_id: str, observer: Any
    ) -> None:
        """Register a per-lesson observer that intercepts cycle lifecycle.

        The observer MUST expose:

          * ``.start(*, script: dict[str, Any], lesson_id: str) -> None``
          * ``.matches(midi: dict[str, Any]) -> bool``
          * ``.ack(*, lesson_id: str) -> None``
          * ``.stop(*, lesson_id: str) -> None``

        When the active lesson matches ``lesson_id``, the runtime:

          * calls ``observer.start(script=..., lesson_id=...)`` AFTER the
            normal ``on_enter_awaiting_action`` emit (highlight +
            tutor_speak) — observer envelopes land last for strongest
            recency on the wire.
          * delegates ``ack_action`` MIDI to ``observer.ack()`` when
            ``observer.matches(midi)`` returns True (the runtime
            SUPPRESSES its normal advancing transition to let the
            observer drive the per-cycle advance).
          * calls ``observer.stop()`` on the ``on_enter_completed``
            teardown.

        The observer is an EMIT-only collaborator — it MUST NOT write
        :class:`LearnState`. The AST gate
        ``tests/learn/test_runtime_invariants.py`` continues to grep
        ``src/vibemix/learn/`` for forbidden writes and stays green.

        Plan 94-03 binds:
          * ``L1.14`` → :class:`ExemplarLessonController` (3-band cycle)
          * ``L1.16`` → :class:`RecitalRuntime` (5-prompt recital)
        """
        self._lesson_observers[lesson_id] = observer

    def _active_observer(self) -> Any | None:
        """Return the registered observer for the active lesson, or None.

        Reads :class:`LearnState` (NEVER writes); returns None when no
        lesson is active OR no observer is registered for the active
        lesson_id. Internal helper.
        """
        lesson_id = self._learn.current_lesson_id
        if lesson_id is None:
            return None
        return self._lesson_observers.get(lesson_id)

    def handle_observer_ack(self, midi: dict[str, Any]) -> bool:
        """Let an active lesson observer consume a user action.

        Observer lessons (EQ exemplar cycle + recitals) are multi-prompt
        flows riding on top of the one-step lesson FSM. While one is
        active, the observer owns ack matching; otherwise the outer
        lesson-level ``expected_action`` would see a synthetic
        ``lesson_continue`` or first-band action and prematurely advance
        the whole lesson.

        Returns ``True`` when an observer is active and the ack has been
        handled or intentionally ignored. The caller should not also send
        the ack through the normal FSM gate in that case.
        """
        if self.current_state.id not in (
            "awaiting_action",
            "hint_strike_1",
            "hint_strike_2",
            "hint_strike_3",
        ):
            return False
        observer = self._active_observer()
        if observer is None:
            return False
        try:
            if observer.matches(midi):
                self._mark_progress_practice_source(midi)
                observer.ack(lesson_id=self._learn.current_lesson_id or "")
        except Exception as exc:  # pragma: no cover — defensive
            import sys

            print(
                f"[learn.runtime] lesson observer ack failed: {exc!r}",
                file=sys.stderr,
            )
        return True

    def complete_observer_lesson(self, *, completed: bool = True) -> None:
        """Move an observer-driven lesson to runtime completion.

        Observer controllers emit their own ``ipc.learn.complete_lesson``
        when a multi-prompt cycle ends. The live wiring intercepts that
        envelope and calls this method so the canonical runtime still
        persists lesson progress, emits a progress snapshot, and returns
        to the completed state.
        """
        self.send("observer_complete", completed=completed)

    def handle_step_ack(self, midi: dict[str, Any]) -> bool:
        """Advance an authored lesson beat without completing the lesson.

        Several beginner lessons are short dialogs driven by the
        synthetic ``lesson_continue`` button. The outer FSM still sees
        those lessons as one lesson, but the learner should receive every
        authored ``tutor_speak`` beat, not only beat 0. When another beat
        remains, consume the ack in-place, emit an advance pulse, repaint
        the same expected action, and speak the next fixture line.
        """
        if self.current_state.id not in (
            "awaiting_action",
            "hint_strike_1",
            "hint_strike_2",
            "hint_strike_3",
        ):
            return False
        lesson_id = self._learn.current_lesson_id
        if lesson_id is None or lesson_id not in CURRICULUM:
            return False
        if self._active_observer() is not None:
            return False

        step = self._active_step()
        if step is None:
            return False
        expected = step.expected_action
        if expected.get("control") != "lesson_continue":
            return False
        if not self.action_matches(midi=midi, expected=expected):
            return False

        next_step = self._flow_step(self._active_step_index + 1)
        if next_step is None:
            return False

        self._record_action_evidence(expected=expected, midi=midi, matched=True)
        self._mark_progress_practice_source(midi)
        self._active_step_index += 1
        self._learn.current_beat_index = self._active_step_index
        self._learn.strike_count = 0
        self._state_entered_at = time.monotonic()
        self._emit_advance(reason="action_matched")
        self._emit_highlight(next_step.expected_action)
        self._emit_step_tutor(next_step)
        return True

    def handle_mismatch_ack(self, midi: dict[str, Any]) -> bool:
        """Emit one deterministic adaptive hint for a wrong user action.

        A guard-rejected ``ack_action`` used to leave beginners with no
        feedback: the highlighted control stayed lit, but the tutor said
        nothing. This consumes mismatched acks before the FSM no-ops,
        emits a short hint, and resets the strike timer so active
        attempts do not immediately trigger a timed hint too.
        """
        if self.current_state.id not in (
            "awaiting_action",
            "hint_strike_1",
            "hint_strike_2",
            "hint_strike_3",
        ):
            return False
        if self._active_observer() is not None:
            return False
        expected = self._current_expected_action()
        if expected is None:
            return False
        if self.action_matches(midi=midi, expected=expected):
            return False

        now = time.monotonic()
        self._state_entered_at = now
        if now - self._last_mismatch_hint_at < _MISMATCH_HINT_THROTTLE_S:
            return True
        self._last_mismatch_hint_at = now
        evidence_time = self._record_action_evidence(
            expected=expected,
            midi=midi,
            matched=False,
        )
        self._mark_progress_practice_source(midi)
        self._emit_adaptive_mismatch_hint(
            expected=expected,
            midi=midi,
            evidence_time=evidence_time,
        )
        return True

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
            expected = self._current_expected_action()
            if expected is None:
                return False

        expected_type = expected.get("type")
        midi_type = midi.get("type")
        if midi_type != expected_type:
            return False
        expected_control, expected_deck = _control_and_deck(expected)
        midi_control, midi_deck = _control_and_deck(midi)

        # ---- CC delta branch -----------------------------------------
        if expected_type == "cc":
            if midi_control != expected_control:
                return False
            if expected_deck is not None and expected_deck != "":
                if midi_deck != expected_deck:
                    return False
            cur = int(midi.get("value", 0))
            prev = int(midi.get("prev_value", cur))
            min_delta = int(expected.get("min_delta", _CC_DEFAULT_MIN_DELTA))
            return abs(cur - prev) >= min_delta

        # ---- Button branch -------------------------------------------
        if expected_type == "button":
            if midi_control != expected_control:
                return False
            if midi.get("direction") != expected.get("direction"):
                return False
            # Only enforce deck match when both sides declared a deck.
            if expected_deck is not None and expected_deck != "":
                if midi_deck != expected_deck:
                    return False
            return True

        return False

    def min_dwell_elapsed(self, **_kwargs: Any) -> bool:
        """45 s anti-speedrun floor. Returns True iff
        ``time.monotonic() - self._learn.lesson_started_at >= 44.5``.

        WR-06 fix (P92 REVIEW): the TS skip-button (``skip-button.ts``)
        starts its own ``setTimeout(45_000)`` lockout from the moment
        it's mounted. The Python ``lesson_started_at`` anchor is set
        inside ``on_enter_loaded`` — when the lesson_loaded envelope is
        delayed (network burst, slow ws-client startup), the TS clock
        starts BEFORE the Python clock. A user clicking "i got it" at
        TS clock+46s = Python clock+44.5s would otherwise: TS button
        unlocks → emit reaches sidecar → predicate returns False → silent
        no-op via allow_event_without_transition → user clicks again,
        then it works. Confusing UX.

        Cheaper than re-anchoring TS lockouts on lesson_loaded.ts: add
        a 0.5 s grace margin here so the Python predicate is forgiving
        of TS-side clock drift. The 45 s anti-speedrun product
        constraint is preserved (44.5 s is functionally identical to
        45 s from the user's perspective; the floor is the visible
        countdown badge, not the predicate).
        """
        return (
            time.monotonic() - self._learn.lesson_started_at >= 44.5
        )

    # ------------------------------------------------------------------
    # Transition action callbacks (``on_<event>``) — these fire DURING
    # the transition, before ``on_enter_<state>``. We use them to set
    # the ``_last_was_match`` flag the advance envelope reads.
    # ------------------------------------------------------------------
    def on_ack_action(self, **kwargs: Any) -> None:
        self._last_was_match = True
        midi = kwargs.get("midi")
        if isinstance(midi, dict):
            self._record_action_evidence(
                expected=self._current_expected_action(),
                midi=midi,
                matched=True,
            )
            self._mark_progress_practice_source(midi)

        # Defensive legacy path: the IPC handler normally gives active
        # observers first claim on acks via handle_observer_ack(), which
        # keeps multi-prompt observer lessons in awaiting_action until
        # their own completion signal. This hook remains for direct
        # runtime.send("ack_action", ...) callers in tests/devtools.
        observer = self._active_observer()
        if observer is not None:
            try:
                if midi is not None and observer.matches(midi):
                    observer.ack(
                        lesson_id=self._learn.current_lesson_id or ""
                    )
            except Exception as exc:  # pragma: no cover — defensive
                import sys

                print(
                    f"[learn.runtime] lesson observer ack failed: {exc!r}",
                    file=sys.stderr,
                )

    def on_skip(self, **_kwargs: Any) -> None:
        self._last_was_match = False

    def on_observer_complete(
        self, completed: bool = True, **_kwargs: Any
    ) -> None:
        self._last_was_match = completed

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
        # WR-04 fix (P92 REVIEW): cancel any in-flight finish task from a
        # prior lesson. The completed→loaded transition is the replay
        # flow; without this, the prior lesson's _finish_when_dwelled
        # would wake up post-load and fire send("finish") into the new
        # lesson's awaiting_action (silent no-op via
        # allow_event_without_transition, but a leaked coroutine).
        if self._finish_task is not None and not self._finish_task.done():
            self._finish_task.cancel()
            self._finish_task = None
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
        self._active_flow = None
        self._active_step_index = 0

        # WR-02 fix (P92 REVIEW): defend against an invalid lesson_id
        # reaching the CURRICULUM lookup. The boundary (ipc_handlers.py)
        # already rejects unknown ids, but a direct caller (tests,
        # devtools-invoke) could still send("load") with a None or
        # unknown id; without this guard, ``CURRICULUM[None]`` /
        # ``CURRICULUM[<unknown>]`` raises KeyError which the broad
        # try/except catches but the FSM already transitioned. The
        # bracket-tagged stderr line surfaces the failure during ear-
        # pass; the FSM stays in ``loaded`` with no HUD mounted — the
        # webview displays a no-lesson surface rather than wedging in
        # awaiting_action with no highlight.
        lesson_id = self._learn.current_lesson_id
        if lesson_id is None or lesson_id not in CURRICULUM:
            import sys

            print(
                f"[learn.runtime] on_enter_loaded: invalid lesson_id "
                f"{lesson_id!r} (not in CURRICULUM); HUD not mounted",
                file=sys.stderr,
            )
            return
        try:
            self._active_flow = build_lesson_flow(lesson_id)
        except Exception as exc:  # pragma: no cover — defensive
            import sys

            print(
                f"[learn.runtime] build_lesson_flow failed for "
                f"{lesson_id!r}: {exc!r}",
                file=sys.stderr,
            )
            self._active_flow = None
        self._mark_progress_started()
        # WR-03 fix (P92 REVIEW): the lesson_loaded schema requires
        # ``controller_id: {minLength: 1}`` — an empty-string fallback
        # made the envelope fail validation, which the broad except
        # caught, leaving the HUD un-mounted with only a bracket-
        # tagged stderr line as the only signal. When no controller is
        # bound yet (first-run flow, controller unplugged mid-load),
        # defer the lesson_loaded emit — the webview's empty-state stays
        # visible. The expected pattern is: user plugs controller →
        # MidiMirror.bind_profile fires → port_watcher callback
        # re-drives the runtime via send("load", ...).
        controller_id = self._learn.current_controller_id
        if not controller_id:
            # Cannot emit a schema-valid lesson_loaded without a real
            # controller id. The webview stays in empty-state until the
            # controller_detected envelope wakes it up.
            return
        # Emit the HUD-mount envelope. Progress dots come from the
        # progress store; tests mock it (returning a MagicMock that
        # iterates to empty tuple — schema-acceptable empty array).
        lesson = CURRICULUM[lesson_id]
        dots = self._progress.dots_for_course(
            self._learn.current_course_id,
            current_lesson_id=lesson_id,
        )
        try:
            envelope = LearnLessonLoaded.make(
                course_id=self._learn.current_course_id or "",
                lesson_id=lesson_id,
                title=lesson.title,
                controller_id=controller_id,
                progress_dots=dots,
            ).to_dict()
            self._ipc.emit(envelope)
            self._log_session_event(
                "learn_lesson_loaded",
                course_id=self._learn.current_course_id or "",
                lesson_id=lesson_id,
                title=lesson.title,
                controller_id=controller_id,
            )
        except Exception as exc:  # pragma: no cover — defensive
            # An invalid progress-dots payload should not wedge the FSM.
            # Surface the failure on stderr and continue; the HUD will
            # simply not mount this lesson's progress strip.
            import sys

            print(f"[learn.runtime] lesson_loaded emit failed: {exc!r}", file=sys.stderr)
        self._emit_progress_snapshot()

    def on_enter_awaiting_action(self, **_kwargs: Any) -> None:
        """Paint the highlight on the expected control, then speak
        beat 0 of the tutor narration. Resets the state-entry timer
        the tick_loop reads.
        """
        # WR-02 fix (P92 REVIEW): defend against transitioning from a
        # loaded state that itself was entered with an invalid
        # lesson_id (where the on_enter_loaded guard above bailed
        # before validating the curriculum lookup). Without this, a
        # follow-up send("begin") would CURRICULUM[None]/KeyError into
        # the broad except and the FSM would silently fail to mount
        # the highlight.
        lesson_id = self._learn.current_lesson_id
        if lesson_id is None or lesson_id not in CURRICULUM:
            import sys

            print(
                f"[learn.runtime] on_enter_awaiting_action: invalid "
                f"lesson_id {lesson_id!r}; highlight not painted",
                file=sys.stderr,
            )
            self._state_entered_at = time.monotonic()
            return
        lesson = CURRICULUM[lesson_id]
        expected = self._current_expected_action() or lesson.script["expected_action"]
        self._emit_highlight(expected)

        self._emit_opening_tutor_beats(expected)
        # Reset the strike timer's state-entry anchor.
        self._state_entered_at = time.monotonic()

        # Plan 94-03 — notify any registered lesson observer that the
        # awaiting_action state has been entered. Observers extend the
        # runtime's behavior WITHOUT changing it (LessonRuntime stays
        # the sole writer of LearnState; the observer reads + emits to
        # ipc_router). For L1.14 the ExemplarLessonController.start()
        # call kicks off the 3-band cycle; for L1.16 the
        # RecitalRuntime.start() call samples 5 prompts.
        observer = self._active_observer()
        if observer is not None:
            try:
                observer.start(script=lesson.script, lesson_id=lesson_id)
            except Exception as exc:  # pragma: no cover — defensive
                import sys

                print(
                    f"[learn.runtime] lesson observer start failed: {exc!r}",
                    file=sys.stderr,
                )

    def on_enter_hint_strike_1(self, **_kwargs: Any) -> None:
        self._learn.strike_count = 1
        self._mark_progress_hint_strike()
        self._emit_hint(1)
        self._state_entered_at = time.monotonic()

    def on_enter_hint_strike_2(self, **_kwargs: Any) -> None:
        self._learn.strike_count = 2
        self._mark_progress_hint_strike()
        self._emit_hint(2)
        self._state_entered_at = time.monotonic()

    def on_enter_hint_strike_3(self, **_kwargs: Any) -> None:
        self._learn.strike_count = 3
        self._mark_progress_hint_strike()
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
        self._emit_advance(reason=reason)

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
            # WR-04 fix (P92 REVIEW): cancel any stale finish task from
            # a prior advancing→completed cycle BEFORE scheduling the
            # new one. Replay flows (completed→loaded→awaiting_action→
            # advancing) would otherwise stack a finish task per cycle;
            # each old task wakes up post-stale-deadline and silently
            # no-ops, but the leaked coroutine references accumulate.
            if self._finish_task is not None and not self._finish_task.done():
                self._finish_task.cancel()
            self._finish_task = asyncio.create_task(
                self._finish_when_dwelled()
            )

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
        """Persist progress + emit terminal envelopes.

        CR-02 fix (P92 REVIEW): mark_completed mutates the in-memory dict
        only; without a save_progress() call the completion is lost on
        next boot (load_progress() reads the un-changed JSON). Persist
        atomically via save_progress() right after the mutation; the
        save_progress import is local so the synchronous test path that
        never reaches this state (e.g. min-dwell skip tests) doesn't
        force a save_progress import side-effect.

        Defensive: progress_store may be a MagicMock (unit-test path) —
        the inner save_progress(self._progress) call works on a real
        LearnProgress dataclass; for a Mock progress_store this branch
        is silently no-op'd because save_progress(mock) would write a
        Mock-shaped dict and the test fixture redirects progress_path()
        to tmp anyway. The bracket-tagged stderr line surfaces save
        failures without wedging the FSM.
        """
        try:
            self._progress.mark_completed(
                self._learn.current_course_id,
                self._learn.current_lesson_id,
                strikes_used=self._learn.strike_count,
            )
            # CR-02: persist to disk via atomic save (tmp + os.replace).
            # Skip save when progress_store isn't a real LearnProgress
            # (unit-test MagicMock path); the live boot in __main__.py
            # always passes a real LearnProgress instance.
            from vibemix.learn.progress import LearnProgress, save_progress

            if isinstance(self._progress, LearnProgress):
                save_progress(self._progress)
        except Exception as exc:  # pragma: no cover — defensive
            import sys

            print(f"[learn.runtime] mark_completed failed: {exc!r}", file=sys.stderr)

        try:
            done = LearnCompleteLesson.make(
                lesson_id=self._learn.current_lesson_id or "",
                reason="completed" if self._last_was_match else "user_skip",
            ).to_dict()
            self._ipc.emit(done)
            self._log_session_event(
                "learn_lesson_completed",
                course_id=self._learn.current_course_id or "",
                lesson_id=self._learn.current_lesson_id or "",
                reason=done.get("payload", {}).get("reason", ""),
                strikes_used=self._learn.strike_count,
            )
        except Exception as exc:  # pragma: no cover — defensive
            import sys

            print(f"[learn.runtime] complete_lesson emit failed: {exc!r}", file=sys.stderr)

        self._emit_progress_snapshot()

        # Plan 94-03 — tear down any registered lesson observer. The
        # observer's .stop() emits a final exemplar_stop (if a pick was
        # active) and resets internal cycle state. Safe to call from
        # any observer state (idempotent contract).
        observer = self._active_observer()
        if observer is not None:
            try:
                observer.stop(
                    lesson_id=self._learn.current_lesson_id or ""
                )
            except Exception as exc:  # pragma: no cover — defensive
                import sys

                print(
                    f"[learn.runtime] lesson observer stop failed: {exc!r}",
                    file=sys.stderr,
                )

    # ------------------------------------------------------------------
    # Helpers — tutor + hint emit sites
    # ------------------------------------------------------------------
    def _mark_progress_started(self) -> None:
        """Best-effort durable progress update for a started attempt."""
        lesson_id = self._learn.current_lesson_id
        course_id = self._learn.current_course_id
        if not lesson_id or not course_id:
            return
        try:
            from vibemix.learn.progress import LearnProgress, save_progress

            if isinstance(self._progress, LearnProgress):
                self._progress.mark_started(course_id, lesson_id)
                save_progress(self._progress)
        except Exception as exc:  # pragma: no cover — defensive
            import sys

            print(
                f"[learn.runtime] mark_started failed: {exc!r}",
                file=sys.stderr,
            )

    def _mark_progress_hint_strike(self) -> None:
        """Best-effort durable progress update for live hint count."""
        lesson_id = self._learn.current_lesson_id
        course_id = self._learn.current_course_id
        if not lesson_id or not course_id:
            return
        try:
            from vibemix.learn.progress import LearnProgress, save_progress

            if isinstance(self._progress, LearnProgress):
                self._progress.mark_hint_strike(
                    course_id,
                    lesson_id,
                    self._learn.strike_count,
                )
                save_progress(self._progress)
        except Exception as exc:  # pragma: no cover — defensive
            import sys

            print(
                f"[learn.runtime] mark_hint_strike failed: {exc!r}",
                file=sys.stderr,
            )
        self._emit_progress_snapshot()

    def _mark_progress_practice_source(self, midi: dict[str, Any]) -> None:
        """Best-effort durable update for hardware/screen practice memory."""
        lesson_id = self._learn.current_lesson_id
        course_id = self._learn.current_course_id
        if not lesson_id or not course_id:
            return
        try:
            from vibemix.learn.progress import LearnProgress, save_progress

            if isinstance(self._progress, LearnProgress):
                self._progress.mark_practice_source(
                    course_id,
                    lesson_id,
                    str(midi.get("source", "midi") or "midi"),
                )
                save_progress(self._progress)
        except Exception as exc:  # pragma: no cover — defensive
            import sys

            print(
                f"[learn.runtime] mark_practice_source failed: {exc!r}",
                file=sys.stderr,
            )

    def _emit_progress_snapshot(self) -> None:
        """Emit the current progress snapshot when it is schema-shaped."""
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

            print(
                f"[learn.runtime] progress snapshot emit failed: {exc!r}",
                file=sys.stderr,
            )

    def _emit_highlight(self, expected: dict[str, Any]) -> None:
        """Emit the current expected-action highlight."""
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
            control, deck = _control_and_deck(expected)
            self._record_evidence(
                source="screen",
                key=_observable_control_id(control, deck),
                t_session=self._evidence_time(),
            )
        except Exception as exc:  # pragma: no cover — defensive
            import sys

            print(f"[learn.runtime] highlight emit failed: {exc!r}", file=sys.stderr)

    def _log_session_event(self, kind: str, **fields: Any) -> None:
        """Best-effort bridge into the existing session recording spine."""
        if self._session_event_logger is None:
            return
        try:
            self._session_event_logger(kind, fields)
        except Exception as exc:  # pragma: no cover — defensive
            import sys

            print(
                f"[learn.runtime] session event log failed: {exc!r}",
                file=sys.stderr,
            )

    def _current_step_id(self) -> str | None:
        step = self._active_step()
        return step.step_id if step is not None else None

    def _log_tutor_speak_event(self, speak: dict[str, Any]) -> None:
        lesson_id = self._learn.current_lesson_id or ""
        course_id = self._learn.current_course_id or ""
        step_id = self._current_step_id()
        try:
            events = learn_tutor_speak_observability_events(
                speak,
                lesson_id=lesson_id,
                course_id=course_id,
                step_id=step_id,
                source="learn_runtime",
            )
            for kind, fields in events:
                self._log_session_event(kind, **fields)
        except Exception as exc:  # pragma: no cover — defensive
            import sys

            print(
                f"[learn.runtime] tutor ai_message log failed: {exc!r}",
                file=sys.stderr,
            )

    def _evidence_time(self) -> float:
        """Return session-relative time for lesson evidence writes."""
        if self._evidence_clock is not None:
            try:
                return max(0.0, float(self._evidence_clock()))
            except Exception as exc:  # pragma: no cover — defensive
                import sys

                print(
                    f"[learn.runtime] evidence clock failed: {exc!r}",
                    file=sys.stderr,
                )
        return max(0.0, time.monotonic() - self._learn.lesson_started_at)

    def _record_evidence(
        self,
        *,
        source: str,
        key: str,
        t_session: float,
    ) -> None:
        """Best-effort EvidenceRegistry write for a lesson observation."""
        if self._evidence_registry is None or not key:
            return
        try:
            self._evidence_registry.write(source, key, t_session)
        except Exception as exc:  # pragma: no cover — defensive
            import sys

            print(
                f"[learn.runtime] evidence write failed: {exc!r}",
                file=sys.stderr,
            )

    def _record_action_evidence(
        self,
        *,
        expected: dict[str, Any] | None,
        midi: dict[str, Any],
        matched: bool | None = None,
    ) -> float:
        """Record the observed learner action and expected highlight."""
        t_session = self._evidence_time()
        midi_control, midi_deck = _control_and_deck(midi)
        observed_id = _observable_control_id(midi_control, midi_deck)
        source = str(midi.get("source", "midi") or "midi")
        observed_source = "screen" if source == "click" else "midi"
        self._record_evidence(
            source=observed_source,
            key=observed_id,
            t_session=t_session,
        )
        if expected is not None:
            expected_control, expected_deck = _control_and_deck(expected)
            expected_id = _observable_control_id(expected_control, expected_deck)
            self._record_evidence(source="screen", key=expected_id, t_session=t_session)
        else:
            expected_id = None
        self._log_session_event(
            "learn_action_observed",
            lesson_id=self._learn.current_lesson_id or "",
            course_id=self._learn.current_course_id or "",
            step_id=self._current_step_id(),
            observed_control_id=observed_id,
            expected_control_id=expected_id,
            source=source,
            matched=matched,
            evidence_time=t_session,
        )
        return t_session

    def _emit_advance(self, *, reason: str) -> None:
        """Emit an advance pulse for the active lesson."""
        try:
            advance = LearnAdvance.make(
                lesson_id=self._learn.current_lesson_id or "",
                reason=reason,
            ).to_dict()
            self._ipc.emit(advance)
        except Exception as exc:  # pragma: no cover — defensive
            import sys

            print(f"[learn.runtime] advance emit failed: {exc!r}", file=sys.stderr)

    def _teaching_loop_payload(self, turn: TeachingTurn) -> LearnTeachingLoopPayload:
        """Convert a planned teaching turn into socket-safe metadata."""
        observation = turn.observation
        verification = turn.verification
        return LearnTeachingLoopPayload(
            stages=tuple(turn.loop),
            turn_kind=turn.turn_kind,
            route_path=turn.route.path,
            observation=LearnTeachingObservationPayload(
                lesson_id=observation.lesson_id,
                step_id=observation.step_id,
                kind=observation.kind,
                control_id=observation.control_id,
                input_surfaces=observation.input_surfaces,
                backstage_lenses=observation.backstage_lenses,
                strikes_used=observation.strikes_used,
            ),
            verification=LearnTeachingVerificationPayload(
                kind=verification.kind,
                control=verification.control,
                deck=verification.deck,
                observable_control_ids=verification.observable_control_ids,
                input_surfaces=verification.input_surfaces,
                direction=verification.direction,
                min_delta=verification.min_delta,
            ),
        )

    def _flow_step(self, index: int) -> LessonStep | None:
        """Return a structured lesson step by index, if available."""
        if self._active_flow is None:
            return None
        if index < 0 or index >= len(self._active_flow.steps):
            return None
        return self._active_flow.steps[index]

    def _active_step(self) -> LessonStep | None:
        """Return the active structured-flow step, if available."""
        return self._flow_step(self._active_step_index)

    def _step_for_tutor_beat(self, beat: int, total_beats: int) -> LessonStep | None:
        """Return the structured step represented by a fixture tutor beat."""
        expected = self._current_expected_action()
        if expected is None:
            return None
        if expected.get("control") == "lesson_continue":
            return self._flow_step(beat)
        if beat == total_beats - 1:
            return self._active_step()
        return None

    def _current_expected_action(self) -> dict[str, Any] | None:
        """Return the expected action for the current structured step."""
        step = self._active_step()
        if step is not None:
            return step.expected_action
        lesson_id = self._learn.current_lesson_id
        if lesson_id is None or lesson_id not in CURRICULUM:
            return None
        expected = CURRICULUM[lesson_id].script.get("expected_action")
        return expected if isinstance(expected, dict) else None

    def _emit_opening_tutor_beats(self, expected: dict[str, Any]) -> None:
        """Speak the authored opening in the right lesson rhythm.

        ``lesson_continue`` lessons advance beat-by-beat on the on-screen
        continue button. Lessons with a real control action surface every
        authored setup line immediately so the dock lands on the actionable
        prompt before verification starts.
        """
        lesson_id = self._learn.current_lesson_id
        if lesson_id is None or lesson_id not in CURRICULUM:
            return
        beats = CURRICULUM[lesson_id].script.get("tutor_speak", [])
        if not isinstance(beats, list) or not beats:
            return
        if (
            expected.get("control") == "lesson_continue"
            and self._active_observer() is None
        ):
            self._learn.current_beat_index = 0
            self._emit_tutor_beat(0)
            self._emit_harmonic_pair_prompt_if_needed()
            self._emit_prepared_pool_prompt_if_needed()
            self._emit_graduation_summary_if_needed()
            return
        for beat_idx, _row in enumerate(beats):
            self._learn.current_beat_index = beat_idx
            self._emit_tutor_beat(beat_idx)

    def _emit_step_tutor(self, step: LessonStep) -> None:
        """Emit tutor text from a compiled structured-flow step."""
        lesson_id = self._learn.current_lesson_id or "unknown"
        turn = plan_teaching_turn(
            lesson_id=lesson_id,
            step=step,
            strikes_used=self._learn.strike_count,
        )
        try:
            speak = LearnTutorSpeak.make(
                text=turn.text,
                tts_marker=turn.tts_marker,
                citations=turn.citations,
                data_state="active",
                teaching_loop=self._teaching_loop_payload(turn),
            ).to_dict()
            self._ipc.emit(speak)
            self._log_tutor_speak_event(speak)
        except Exception as exc:  # pragma: no cover — defensive
            import sys

            print(f"[learn.runtime] step tutor emit failed: {exc!r}", file=sys.stderr)

    def _emit_prepared_pool_prompt_if_needed(self) -> None:
        """Emit L3.02's deterministic prepared-pool line when grounded."""
        if self._learn.current_lesson_id != "L3.02":
            return
        loader = self._prepared_pool_loader
        if loader is None:
            return
        try:
            pool = loader()
        except Exception as exc:  # pragma: no cover — defensive
            import sys

            print(
                f"[learn.runtime] prepared pool lookup failed: {exc!r}",
                file=sys.stderr,
            )
            return
        if pool is None or pool.track_count < MIN_PREPARED_POOL_TRACKS:
            return
        citations = self._prepared_pool_citations(pool)
        try:
            speak = LearnTutorSpeak.make(
                text=build_prepared_pool_prompt(pool),
                tts_marker="L302.prepared_pool",
                citations=citations,
                data_state="active",
            ).to_dict()
            self._ipc.emit(speak)
            self._log_tutor_speak_event(speak)
        except Exception as exc:  # pragma: no cover — defensive
            import sys

            print(
                f"[learn.runtime] prepared pool tutor emit failed: {exc!r}",
                file=sys.stderr,
            )

    def _emit_harmonic_pair_prompt_if_needed(self) -> None:
        """Emit L2.11's deterministic user-library Camelot pair when available."""
        if self._learn.current_lesson_id != "L2.11":
            return
        loader = self._harmonic_pair_loader
        if loader is None:
            return
        try:
            pair = loader()
        except Exception as exc:  # pragma: no cover - defensive
            import sys

            print(
                f"[learn.runtime] harmonic pair lookup failed: {exc!r}",
                file=sys.stderr,
            )
            return
        if pair is None:
            return
        try:
            speak = LearnTutorSpeak.make(
                text=build_harmonic_practice_prompt(pair),
                tts_marker="L211.library_pair",
                citations=harmonic_practice_citations(pair, self._evidence_registry),
                data_state="active",
            ).to_dict()
            self._ipc.emit(speak)
            self._log_tutor_speak_event(speak)
        except Exception as exc:  # pragma: no cover - defensive
            import sys

            print(
                f"[learn.runtime] harmonic pair tutor emit failed: {exc!r}",
                file=sys.stderr,
            )

    def _emit_graduation_summary_if_needed(self) -> None:
        """Emit L3.06's truthful progress/profile/debrief status line."""
        if self._learn.current_lesson_id != "L3.06":
            return
        try:
            if self._graduation_summary_loader is not None:
                summary = self._graduation_summary_loader(self._progress)
            else:
                summary = build_graduation_summary(self._progress)
        except Exception as exc:  # pragma: no cover - defensive
            import sys

            print(
                f"[learn.runtime] graduation summary lookup failed: {exc!r}",
                file=sys.stderr,
            )
            return
        if summary is None:
            return
        self._record_evidence(
            source="screen",
            key="learn-progress",
            t_session=self._evidence_time(),
        )
        if summary.debrief_available:
            self._record_evidence(
                source="screen",
                key="learn-debrief",
                t_session=self._evidence_time(),
            )
        if summary.profile_available:
            self._record_evidence(
                source="screen",
                key="learn-profile",
                t_session=self._evidence_time(),
            )
        try:
            speak = LearnTutorSpeak.make(
                text=build_graduation_tutor_line(summary),
                tts_marker="L306.graduation_status",
                citations=graduation_citations(
                    summary,
                    registry_available=self._evidence_registry is not None,
                ),
                data_state="active",
            ).to_dict()
            self._ipc.emit(speak)
            self._log_tutor_speak_event(speak)
        except Exception as exc:  # pragma: no cover - defensive
            import sys

            print(
                f"[learn.runtime] graduation status tutor emit failed: {exc!r}",
                file=sys.stderr,
            )

    def _prepared_pool_citations(self, pool: PreparedPool) -> tuple[str, ...]:
        registry = self._evidence_registry
        if registry is None or not pool.tracks:
            return ()
        track_id = pool.tracks[0].track_id
        if any(ch.isspace() or ch in ",]" for ch in track_id):
            return ()
        try:
            if not registry.has("track", track_id, 0.0, tol=0.5):
                return ()
        except Exception:  # pragma: no cover — defensive
            return ()
        return (f"[track:{track_id}]",)

    def _emit_tutor_beat(self, beat: int) -> None:
        """Emit :class:`LearnTutorSpeak` with text read VERBATIM from
        the JSON fixture (TONE-02). The text is never LLM-generated at
        runtime; the AST gate ``tests/learn/test_scripts_are_fixtures.py``
        confirms zero generative writes here.
        """
        # WR-02 fix (P92 REVIEW): defend against missing CURRICULUM
        # entry (the on_enter_* guards above already short-circuit, but
        # a sibling caller (e.g. _emit_hint via on_enter_hint_strike_*)
        # could still reach here on a stale state).
        lesson_id = self._learn.current_lesson_id
        if lesson_id is None or lesson_id not in CURRICULUM:
            return
        lesson = CURRICULUM[lesson_id]
        beats = lesson.script.get("tutor_speak", [])
        if beat >= len(beats):
            return
        fixture = beats[beat]
        step = self._step_for_tutor_beat(beat, len(beats))
        turn = None
        if step is not None:
            turn = plan_teaching_turn(
                lesson_id=lesson_id,
                step=step,
                strikes_used=self._learn.strike_count,
            )
        try:
            speak = LearnTutorSpeak.make(
                text=fixture["text"],
                tts_marker=fixture["tts_marker"],
                citations=turn.citations
                if turn is not None
                else tuple(fixture.get("citations", [])),
                data_state="active",
                teaching_loop=self._teaching_loop_payload(turn)
                if turn is not None
                else None,
            ).to_dict()
            self._ipc.emit(speak)
            self._log_tutor_speak_event(speak)
        except Exception as exc:  # pragma: no cover — defensive
            import sys

            print(f"[learn.runtime] tutor_speak emit failed: {exc!r}", file=sys.stderr)

    def _emit_hint(self, strike: int) -> None:
        """Emit :class:`LearnTutorSpeak` with the per-strike hint text
        (``data_state="hint"`` so the UI styles it italic / muted).
        """
        # WR-02 fix (P92 REVIEW): same defensive guard as
        # _emit_tutor_beat; missing CURRICULUM entry → silent no-op.
        lesson_id = self._learn.current_lesson_id
        if lesson_id is None or lesson_id not in CURRICULUM:
            return
        lesson = CURRICULUM[lesson_id]
        hints = lesson.script.get("hints", [])
        # ``strike`` is 1-indexed; hints[] is 0-indexed.
        if strike - 1 >= len(hints):
            return
        step = self._active_step()
        turn = None
        if step is not None:
            turn = plan_hint_turn(
                lesson_id=lesson_id,
                step=step,
                strike=strike,
            )
        hint = hints[strike - 1]
        try:
            speak = LearnTutorSpeak.make(
                text=turn.text if turn is not None else hint["text"],
                tts_marker=turn.tts_marker if turn is not None else hint["tts_marker"],
                citations=turn.citations
                if turn is not None
                else tuple(hint.get("citations", [])),
                data_state="hint",
                teaching_loop=self._teaching_loop_payload(turn)
                if turn is not None
                else None,
            ).to_dict()
            self._ipc.emit(speak)
            self._log_tutor_speak_event(speak)
        except Exception as exc:  # pragma: no cover — defensive
            import sys

            print(f"[learn.runtime] hint emit failed: {exc!r}", file=sys.stderr)

    def _emit_adaptive_mismatch_hint(
        self,
        *,
        expected: dict[str, Any],
        midi: dict[str, Any],
        evidence_time: float,
    ) -> None:
        """Emit a grounded hint for the specific wrong action observed."""
        lesson_id = self._learn.current_lesson_id or "unknown"
        hint = _adaptive_mismatch_hint(
            expected=expected,
            midi=midi,
            evidence_time=evidence_time,
        )
        step = self._active_step()
        turn = None
        if step is not None:
            turn = plan_adaptive_turn(
                lesson_id=lesson_id,
                step=step,
                text=hint.text,
                tts_marker=f"{lesson_id}.adapt.mismatch",
                citations=hint.citations,
                strikes_used=self._learn.strike_count,
            )
        try:
            speak = LearnTutorSpeak.make(
                text=turn.text if turn is not None else hint.text,
                tts_marker=turn.tts_marker
                if turn is not None
                else f"{lesson_id}.adapt.mismatch",
                citations=turn.citations if turn is not None else hint.citations,
                data_state="hint",
                teaching_loop=self._teaching_loop_payload(turn)
                if turn is not None
                else None,
            ).to_dict()
            self._ipc.emit(speak)
            self._log_tutor_speak_event(speak)
        except Exception as exc:  # pragma: no cover — defensive
            import sys

            print(
                f"[learn.runtime] adaptive mismatch hint emit failed: {exc!r}",
                file=sys.stderr,
            )

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
