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
import math
import time
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

from statemachine import State, StateMachine

from vibemix.audio.grid import BeatGrid
from vibemix.audio.miniplayer import DeckState
from vibemix.learn.control_practice import (
    CONTROL_PRACTICE_GRADED_EVENT,
    ControlPracticeResult,
    grade_matched_control_practice,
)
from vibemix.learn.cue_practice import (
    CUE_PLACEMENT_EVIDENCE_SOURCE,
    CUE_PLACEMENT_GRADED_EVENT,
    CuePlacementPracticeResult,
    grade_owned_cue_placement_attempt,
    grade_owned_cue_placement_state,
    is_creditable_cue_placement_grade,
)
from vibemix.learn.curriculum import CURRICULUM, course_lesson_ids
from vibemix.learn.graduation import (
    GraduationSummary,
    build_graduation_summary,
    build_graduation_tutor_line,
    graduation_citations,
)
from vibemix.learn.harmonic_practice import (
    HARMONIC_PRACTICE_GRADED_EVENT,
    HarmonicPracticePair,
    HarmonicPracticeResult,
    build_harmonic_practice_prompt,
    grade_harmonic_practice_pair,
    harmonic_practice_citations,
)
from vibemix.learn.lesson_flow import LessonFlow, LessonStep, build_lesson_flow
from vibemix.learn.mastered_vocal import mastered_unlock_line
from vibemix.learn.observability import learn_tutor_speak_observability_events
from vibemix.learn.practice_loop import (
    BEATMATCH_EVIDENCE_SOURCE,
    BEATMATCH_GRADED_EVENT,
    BeatmatchPracticeResult,
    grade_owned_beatmatch_attempt,
    grade_owned_beatmatch_state,
    is_creditable_locked_grade,
)
from vibemix.learn.skill_recognizer import recognize
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
    LearnLiveGrade,
    LearnPlayheadTick,
    LearnProgressState,
    LearnTeachingFocus,
    LearnTeachingLoopPayload,
    LearnTeachingObservationPayload,
    LearnTeachingVerificationPayload,
    LearnTutorSpeak,
    LearnWaveformReady,
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
_BEATMATCH_PRACTICE_LOCK_REQUIRED_LESSONS = frozenset({"L2.01", "L2.02"})
_BEATMATCH_PRACTICE_GRADE_STATES = frozenset(
    {"awaiting_action", "hint_strike_1", "hint_strike_2", "hint_strike_3", "advancing"}
)
_RECOVERY_DRILL_ARMED_EVENT = "RECOVERY_DRILL_ARMED"
_RECOVERY_DRILL_RECOVERED_EVENT = "RECOVERY_DRILL_RECOVERED"
_RECOVERY_BAILOUT_MIN_DELTA = 8
_RECOVERY_FILTER_CENTER_MIN_DELTA = 18
_RECOVERY_CHANNEL_CUT_CC = 32
_RECOVERY_XFADER_CUT_CC = 38
_BEATMATCH_SAVE_DIFFICULTY_MIN = 1
_BEATMATCH_SAVE_DIFFICULTY_MAX = 5
_BEATMATCH_SAVE_FLOOR_BASE_S = 14.0
_BEATMATCH_SAVE_FLOOR_STEP_S = 2.0
_BEATMATCH_SAVE_FLOOR_MIN_S = 6.0
_PRACTICE_AUDIO_CONTROLS = frozenset(
    {
        "cue",
        "eq_hi",
        "eq_low",
        "eq_mid",
        "filter",
        "fx_echo",
        "headphone_cue",
        "hotcue",
        "jog",
        "loop_in",
        "loop_out",
        "play",
        "sync",
        "tempo",
        "vol",
        "xfader",
    }
)
_FREE_PRACTICE_CONTROL_LESSON_IDS = {
    "cue": "L1.06",
    "eq_hi": "L1.03",
    "eq_low": "L1.03",
    "eq_mid": "L1.03",
    "filter": "L1.03",
    "headphone_cue": "L1.08",
    "jog": "L1.07",
    "jog_touch": "L1.07",
    "jog_touched": "L1.07",
    "master_vol": "L1.09",
    "play": "L1.06",
    "sync": "L1.06",
    "tap_tempo": "L1.05",
    "tempo": "L1.05",
    "vol": "L1.03",
    "xfader": "L1.04",
}
_PRACTICE_AUDIO_DEMO_LESSONS = frozenset(
    {
        "L1.09",
        "L1.10",
        "L1.11",
        "L1.12",
        "L1.13",
        "L1.15",
        "L2.11",
        "L2.13",
    }
)
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


@dataclass(frozen=True, slots=True)
class BeatmatchPracticeSnapshot:
    """One owned-deck beatmatch practice tick supplied by a lesson driver."""

    grid_a: BeatGrid
    grid_b: BeatGrid
    deck_state: DeckState


@dataclass(frozen=True, slots=True)
class CuePlacementPracticeSnapshot:
    """One owned-deck cue-placement practice tick supplied by a lesson driver."""

    grid: BeatGrid
    cue_frame: float
    target_frame: float | None = None


def _control_and_deck(action: dict[str, Any]) -> tuple[str, str]:
    """Return normalized ``(control, deck)`` from either field style."""
    control = str(action.get("control", "")).strip()
    deck = str(action.get("deck", "") or "").strip()
    if not deck and ":" in control:
        control, _, parsed_deck = control.rpartition(":")
        deck = parsed_deck.strip()
    return control, deck


def _practice_source_key(source: Any) -> str | None:
    raw = str(source or "midi").strip().lower()
    if raw in {"midi", "hardware", "controller"}:
        return "hardware"
    if raw in {"click", "screen", "onscreen", "on_screen"}:
        return "screen"
    return None


def _nonnegative_int(value: Any) -> int:
    try:
        raw = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, raw)


def _practice_bank_counts(row: Any) -> dict[str, int]:
    counts = {"hardware": 0, "screen": 0}
    if not isinstance(row, dict):
        return counts
    sources = row.get("practice_sources")
    if not isinstance(sources, dict):
        return counts
    counts["hardware"] = _nonnegative_int(sources.get("hardware"))
    counts["screen"] = _nonnegative_int(sources.get("screen"))
    return counts


def _practice_bank_total(row: Any) -> int:
    counts = _practice_bank_counts(row)
    return min(3, counts["hardware"] + counts["screen"])


def _practice_bank_source_label(counts: dict[str, int]) -> str:
    if counts["hardware"] > 0 and counts["screen"] > 0:
        return "screen + hardware"
    if counts["hardware"] > 0:
        return "controller"
    return "screen"


def _practice_bank_preface_text(row: Any) -> str | None:
    count = _practice_bank_total(row)
    if count <= 0:
        return None
    counts = _practice_bank_counts(row)
    source = _practice_bank_source_label(counts)
    unit = "rep" if count == 1 else "reps"
    verb = "is" if count == 1 else "are"
    return f"{count} {source} {unit} {verb} banked. prove one clean move here."


def _observable_control_id(control: str, deck: str) -> str:
    return f"{control}:{deck}" if deck else control


def _cc_int(value: Any, *, default: int = 64) -> int:
    try:
        raw = int(value)
    except (TypeError, ValueError):
        raw = default
    return max(0, min(127, raw))


# EQ band lookup for the organism teaching-focus swirl. A control like
# ``eq_low``/``eq_mid``/``eq_hi`` carries a band so the mascot can localise
# the focus glow + knob swirl to the right EQ region; everything else is
# bandless (``None``).
_EQ_BAND_BY_CONTROL: dict[str, str] = {
    "eq_low": "low",
    "eq_mid": "mid",
    "eq_hi": "hi",
}


def _eq_band_for_control(control: str) -> str | None:
    """Return the EQ band for a control, or ``None`` when it is not an EQ knob."""
    head = control.split(":", 1)[0].strip()
    return _EQ_BAND_BY_CONTROL.get(head)


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


def _mismatch_feedback_signature(
    *,
    expected: dict[str, Any],
    midi: dict[str, Any],
) -> tuple[str, str, str] | None:
    """Return a repeat-suppression key for wrong-control feedback.

    Correct control but insufficient movement is intentionally not latched:
    the learner may need another "move farther" cue after trying again. The
    noisy live class is a repeated wrong control against the same highlighted
    target, which should keep recording evidence but not keep speaking the
    same authored correction.
    """
    expected_control, expected_deck = _control_and_deck(expected)
    midi_control, midi_deck = _control_and_deck(midi)
    if midi_control == expected_control and (
        not expected_deck or midi_deck == expected_deck
    ):
        return None
    return (
        _observable_control_id(expected_control, expected_deck),
        _observable_control_id(midi_control, midi_deck),
        str(midi.get("source", "midi") or "midi"),
    )


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
    recovery_complete = (
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
        beatmatch_practice_loader: Callable[[], BeatmatchPracticeSnapshot | None] | None = None,
        beatmatch_practice_sandbox_loader: Callable[[], BeatmatchPracticeSnapshot | None]
        | None = None,
        beatmatch_practice_action_recorder: Callable[[str | None, dict[str, Any]], bool | None]
        | None = None,
        beatmatch_practice_prepare: Callable[[], None] | None = None,
        beatmatch_practice_difficulty_setter: Callable[[int], None] | None = None,
        waveform_payload_loader: Callable[[], dict[str, Any] | None] | None = None,
        playhead_payload_loader: Callable[[], dict[str, Any] | None] | None = None,
        cue_placement_practice_loader: Callable[[], CuePlacementPracticeSnapshot | None] | None = None,
        cue_placement_practice_action_recorder: Callable[[str | None, dict[str, Any]], bool | None]
        | None = None,
        session_event_logger: Callable[[str, dict[str, Any]], None] | None = None,
        tutor_speak_audio: Callable[[str, str], None] | None = None,
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
            beatmatch_practice_loader: Optional owned-deck lesson hook. When it
                returns a :class:`BeatmatchPracticeSnapshot`, the 1 Hz loop grades
                that owned deck through ``learn.practice_loop`` and lets the
                existing recognizer/progress gate decide whether beatmatching
                earns a live proof.
            beatmatch_practice_sandbox_loader: Optional free-practice hook. It
                returns the same owned-deck shape but is graded as meter/tutor
                feedback only; it never writes ``BEATMATCH_GRADED`` evidence and
                never changes progress.
            beatmatch_practice_action_recorder: Optional hook called after a
                matched Learn action. It lets the live boot driver arm the
                owned-deck beatmatch snapshot and immediately grade that attempt
                through the same evidence path, rather than waiting for the next
                1 Hz tick after the lesson may have advanced.
            beatmatch_practice_difficulty_setter: Optional hook that lets the
                runtime push Save-mode escalation back into the owned-deck
                driver. None keeps fixture-only and sandbox tests unchanged.
            cue_placement_practice_loader: Optional owned-deck hot-cue lesson
                hook. When it returns a :class:`CuePlacementPracticeSnapshot`,
                the 1 Hz loop grades cue timing against the owned beatgrid and
                lets the recognizer/progress gate decide whether phrasing earns
                a live proof.
            cue_placement_practice_action_recorder: Optional hook called after
                a matched Learn action. It lets the live boot driver arm the
                owned-deck cue-placement snapshot and immediately grade that
                attempt through the same evidence path, rather than waiting for
                the next 1 Hz tick after the lesson may have advanced.
            session_event_logger: Optional existing session-recorder seam. Live
                wiring passes ``VoiceRecorder.log_event`` through a fail-soft
                adapter so Learn milestones land in ``events.jsonl`` for later
                debrief/profile tooling.
            tutor_speak_audio: Optional local-audio hook. When wired at boot,
                every emitted ``LearnTutorSpeak`` line is also synthesized by
                the product co-host voice. None preserves silent-subtitle behavior
                for tests and installs without a local voice.
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
        self._beatmatch_practice_loader = beatmatch_practice_loader
        self._beatmatch_practice_sandbox_loader = beatmatch_practice_sandbox_loader
        self._beatmatch_practice_action_recorder = beatmatch_practice_action_recorder
        self._beatmatch_practice_prepare = beatmatch_practice_prepare
        self._beatmatch_practice_difficulty_setter = beatmatch_practice_difficulty_setter
        self._waveform_payload_loader = waveform_payload_loader
        self._playhead_payload_loader = playhead_payload_loader
        self._cue_placement_practice_loader = cue_placement_practice_loader
        self._cue_placement_practice_action_recorder = cue_placement_practice_action_recorder
        self._session_event_logger = session_event_logger
        self._tutor_speak_audio = tutor_speak_audio
        # The wall-clock anchor for the 30 s strike escalation timer.
        # Reset on every ``on_enter_<state>`` callback for the states
        # that the tick_loop watches (awaiting_action, hint_strike_*).
        self._state_entered_at = time.monotonic()
        # Tracks whether the latest ack/skip event was a real match.
        # ``on_ack_action`` / ``on_skip`` set this flag BEFORE
        # ``on_enter_advancing`` fires, so the advance envelope's
        # ``reason`` field carries the right token.
        self._last_was_match: bool = False
        self._last_completion_can_advance: bool = False
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
        self._last_mismatch_hint_signature: tuple[str, str, str] | None = None
        self._beatmatch_practice_lock_active = False
        self._last_beatmatch_live_grade_verdict: str | None = None
        self._last_beatmatch_live_grade_signature: tuple[Any, ...] | None = None
        self._last_beatmatch_save_candidate: tuple[str, float] | None = None
        self._beatmatch_save_attempt_started_at: float | None = None
        self._beatmatch_save_attempt_window_s: float | None = None
        self._beatmatch_save_difficulty_level = _BEATMATCH_SAVE_DIFFICULTY_MIN
        self._beatmatch_save_streak = 0
        self._beatmatch_practice_ack_prehandled = False
        self._beatmatch_practice_player: Any | None = None
        self._beatmatch_practice_player_active = False
        self._free_practice_receipts: set[tuple[str, str, str]] = set()
        self._waveform_ready_lesson_id: str | None = None
        self._active_harmonic_pair: HarmonicPracticePair | None = None
        self._recovery_drill_armed_step_key: tuple[str, int] | None = None
        self._recovery_drill_armed_citation: str | None = None
        self._cue_placement_practice_lock_active = False
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
                evidence_time = self._record_action_evidence(
                    expected=None,
                    midi=midi,
                    matched=True,
                )
                self._mark_progress_practice_source(midi)
                self._record_learn_control_practice_action(
                    midi,
                    expected=None,
                    evidence_time=evidence_time,
                )
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

    def set_beatmatch_practice_player(self, player: Any | None) -> None:
        """Install or clear the optional audible practice player."""
        if player is self._beatmatch_practice_player:
            return
        self._stop_beatmatch_practice_player()
        self._beatmatch_practice_player = player
        if self._is_beatmatch_practice_audio_lesson() and self.current_state.id in (
            "awaiting_action",
            "hint_strike_1",
            "hint_strike_2",
            "hint_strike_3",
        ):
            self._start_beatmatch_practice_player()

    def _is_beatmatch_practice_audio_lesson(self) -> bool:
        lesson_id = self._learn.current_lesson_id
        if lesson_id is None:
            return False
        lesson_meta = CURRICULUM.get(lesson_id)
        if lesson_meta is not None and lesson_meta.course_id == "course_0":
            return False
        if lesson_id in _PRACTICE_AUDIO_DEMO_LESSONS:
            return True
        try:
            flow = build_lesson_flow(lesson_id)
        except Exception:
            flow = None
        actions: list[dict[str, Any]] = []
        if flow is not None:
            if flow.drill_shapes:
                return True
            actions.extend(step.expected_action for step in flow.steps)
            actions.append(flow.primary_expected_action)
        elif lesson_id in CURRICULUM:
            expected = CURRICULUM[lesson_id].script.get("expected_action")
            if isinstance(expected, dict):
                actions.append(expected)
        for action in actions:
            control, deck = _control_and_deck(action)
            if control not in _PRACTICE_AUDIO_CONTROLS:
                continue
            if deck or control == "xfader":
                return True
        return False

    def _is_beatmatch_practice_lock_action(self, expected: dict[str, Any] | None) -> bool:
        """Return True for L2 beatmatch actions that must prove a locked grade."""

        if self._learn.current_lesson_id not in _BEATMATCH_PRACTICE_LOCK_REQUIRED_LESSONS:
            return False
        if not isinstance(expected, dict):
            return False
        control, deck = _control_and_deck(expected)
        if self._learn.current_lesson_id == "L2.01":
            return expected.get("type") == "cc" and control == "tempo" and deck == "B"
        if self._learn.current_lesson_id == "L2.02":
            return expected.get("type") == "button" and control == "sync" and deck == "B"
        return False

    def _start_beatmatch_practice_player(self) -> None:
        if (
            not self._is_beatmatch_practice_audio_lesson()
            or self._beatmatch_practice_player_active
        ):
            return
        try:
            self._prepare_beatmatch_practice_audio()
            if self._beatmatch_practice_player is None:
                return
            self._emit_waveform_ready()
            self._beatmatch_practice_player.start()
            self._beatmatch_practice_player_active = True
        except Exception as exc:  # pragma: no cover - defensive
            import sys

            print(
                f"[learn.runtime] beatmatch practice player start failed: {exc!r}",
                file=sys.stderr,
            )

    def _prepare_beatmatch_practice_audio(self) -> None:
        if self._beatmatch_practice_prepare is None:
            return
        try:
            self._beatmatch_practice_prepare()
        except Exception as exc:  # pragma: no cover - defensive
            import sys

            print(
                f"[learn.runtime] beatmatch practice prepare failed: {exc!r}",
                file=sys.stderr,
            )

    def _stop_beatmatch_practice_player(self) -> None:
        if self._beatmatch_practice_player is None or not self._beatmatch_practice_player_active:
            return
        try:
            self._beatmatch_practice_player.stop()
        except Exception as exc:  # pragma: no cover - defensive
            import sys

            print(
                f"[learn.runtime] beatmatch practice player stop failed: {exc!r}",
                file=sys.stderr,
            )
        finally:
            self._beatmatch_practice_player_active = False

    def _emit_waveform_ready(self, scope_id: str | None = None) -> None:
        lesson_id = scope_id if scope_id is not None else self._learn.current_lesson_id
        if (
            lesson_id is None
            or self._waveform_ready_lesson_id == lesson_id
            or self._waveform_payload_loader is None
        ):
            return
        try:
            payload = self._waveform_payload_loader()
            if not isinstance(payload, dict):
                return
            envelope = LearnWaveformReady.make(
                sample_rate=int(payload.get("sample_rate", 44_100)),
                beat_interval_s=float(payload.get("beat_interval_s", 60.0 / 128.0)),
                decks=payload.get("decks", {}),
            ).to_dict()
            self._ipc.emit(envelope)
            self._waveform_ready_lesson_id = lesson_id
        except Exception as exc:  # pragma: no cover - defensive
            import sys

            print(
                f"[learn.runtime] waveform_ready emit failed: {exc!r}",
                file=sys.stderr,
            )

    def _emit_playhead_tick(self) -> None:
        if self._playhead_payload_loader is None:
            return
        lesson_playing = (
            self._is_beatmatch_practice_audio_lesson()
            and self.current_state.id in _BEATMATCH_PRACTICE_GRADE_STATES
        )
        sandbox_playing = (
            self._learn.current_lesson_id is None
            and self._beatmatch_practice_player_active
        )
        if not lesson_playing and not sandbox_playing:
            return
        try:
            payload = self._playhead_payload_loader()
            if not isinstance(payload, dict):
                return
            self._ipc.emit(
                LearnPlayheadTick.make(
                    sample_rate=int(payload.get("sample_rate", 44_100)),
                    decks=payload.get("decks", {}),
                ).to_dict()
            )
        except Exception as exc:  # pragma: no cover - defensive
            import sys

            print(
                f"[learn.runtime] playhead_tick emit failed: {exc!r}",
                file=sys.stderr,
            )

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
        self._last_mismatch_hint_signature = None
        self._state_entered_at = time.monotonic()
        self._emit_advance(reason="action_matched")
        self._emit_highlight(next_step.expected_action)
        self._emit_step_tutor(next_step)
        self._arm_recovery_drill_if_needed()
        return True

    def handle_recovery_drill_ack(self, midi: dict[str, Any]) -> bool:
        """Consume L3 recovery-drill bailout moves.

        The authored L3.05 prompt asks for echo-out, filter sweep, or a hard
        cut. The generic lesson gate still expects ``lesson_continue`` between
        drill beats, so without this hook real corrective fader/filter moves
        were treated as mismatches. This path only credits moves that actually
        remove the problem deck from the owned MiniDeck mix.
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
        drill = self._active_recovery_drill()
        if drill is None:
            return False
        control, _deck = _control_and_deck(midi)
        if control == "lesson_continue":
            return False

        problem_deck = (drill.deck or "B").upper()
        bailout_label = self._recovery_bailout_label(midi, problem_deck=problem_deck)
        if bailout_label is None:
            self._emit_recovery_drill_hint(midi, problem_deck=problem_deck)
            return True

        self._record_recovery_drill_success(
            midi,
            drill=drill,
            bailout_label=bailout_label,
            problem_deck=problem_deck,
        )
        next_index = self._active_step_index + 1
        next_step = self._flow_step(next_index)
        flow = self._active_flow
        if flow is not None and next_step is not None and next_index < len(flow.drill_shapes):
            self._advance_recovery_drill_step(next_step)
        else:
            self._complete_recovery_drill_lesson()
        return True

    def handle_beatmatch_practice_ack(self, midi: dict[str, Any]) -> bool:
        """Consume L2 beatmatch acks until the measured grade is actually locked.

        Before the owned-deck judge existed, a matched L2.01/L2.02 control move
        was enough to finish the lesson. Now those lessons have real phase/tempo
        ground truth, so a matched but uncredited grade must keep the lesson open:
        Sven can coach the measured miss, the audio keeps playing, and the learner
        can keep correcting until the cited ``BEATMATCH_GRADED`` lock lands.
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
        if not self._is_beatmatch_practice_lock_action(expected):
            return False
        if (
            self._beatmatch_practice_action_recorder is None
            or self._beatmatch_practice_loader is None
            or self._evidence_registry is None
        ):
            return False
        if not self.action_matches(midi=midi, expected=expected):
            return False

        self._record_action_evidence(expected=expected, midi=midi, matched=True)
        self._mark_progress_practice_source(midi)
        result = self._record_beatmatch_practice_action(midi)
        if result is not None and result.event is None:
            self._state_entered_at = time.monotonic()
            return True

        # Locked (or fail-soft ungradeable) goes through the normal advance
        # transition, but ``on_ack_action`` must not re-record/re-grade it.
        if result is not None and result.event is not None:
            self._last_completion_can_advance = True
        self._beatmatch_practice_ack_prehandled = True
        self.send("ack_action", midi=midi)
        return True

    def handle_practice_audio_ack(self, midi: dict[str, Any]) -> None:
        """Apply practice-audio controls to the owned deck before lesson gating.

        The normal step-ack path may consume a matching action for dwell /
        advancement reasons. Audio cannot wait for that: a learner dragging a
        pitch fader, EQ, filter, channel fader, or xfader should hear the deck
        change on the first ack frame.

        With no lesson active, the same path becomes free practice: it starts
        the Learn-owned deck and applies the gesture without emitting progress,
        completion, or tutor credit. The FSM can still ignore the ack later.
        """

        if self._learn.current_lesson_id is None:
            self._start_practice_sandbox_player()
            self._apply_beatmatch_practice_action(midi)
            if self._beatmatch_practice_player_active:
                self._emit_live_beatmatch_grade(self._grade_beatmatch_sandbox_tick())
            self._record_free_practice_receipt(midi)
            return
        if not self._is_beatmatch_practice_audio_lesson():
            return
        self._apply_beatmatch_practice_action(midi)

    def _start_practice_sandbox_player(self) -> None:
        """Start the Learn-owned deck for free practice outside a lesson."""

        if self._beatmatch_practice_player_active:
            return
        try:
            self._prepare_beatmatch_practice_audio()
            if self._beatmatch_practice_player is None:
                return
            self._emit_waveform_ready("sandbox")
            self._beatmatch_practice_player.start()
            self._beatmatch_practice_player_active = True
        except Exception as exc:  # pragma: no cover - defensive
            import sys

            print(
                f"[learn.runtime] practice sandbox player start failed: {exc!r}",
                file=sys.stderr,
            )

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
        signature = _mismatch_feedback_signature(expected=expected, midi=midi)
        if signature is not None and signature == self._last_mismatch_hint_signature:
            observed_id = signature[1]
            expected_id = signature[0]
            self._log_session_event(
                "learn_mismatch_hint_suppressed",
                reason="repeat_same_wrong_control",
                lesson_id=self._learn.current_lesson_id or "",
                course_id=self._learn.current_course_id or "",
                step_id=self._current_step_id(),
                observed_control_id=observed_id,
                expected_control_id=expected_id,
                source=signature[2],
                evidence_time=evidence_time,
            )
            return True
        self._last_mismatch_hint_signature = signature
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
            ``expected.get("min_delta", 38)`` (30% of the 127 CC range by
            default). Small but correct moves are still observed evidence;
            they route through adaptive coaching as "move farther" instead
            of completing the lesson.

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
        prehandled_beatmatch_ack = self._beatmatch_practice_ack_prehandled
        self._beatmatch_practice_ack_prehandled = False
        if isinstance(midi, dict) and not prehandled_beatmatch_ack:
            expected = self._current_expected_action()
            evidence_time = self._record_action_evidence(
                expected=expected,
                midi=midi,
                matched=True,
            )
            self._mark_progress_practice_source(midi)
            self._record_learn_control_practice_action(
                midi,
                expected=expected,
                evidence_time=evidence_time,
            )
            self._record_harmonic_practice_action(
                midi,
                expected=expected,
                evidence_time=evidence_time,
            )
            self._record_beatmatch_practice_action(midi)
            self._record_cue_placement_practice_action(midi)

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

    def _record_beatmatch_practice_action(
        self,
        midi: dict[str, Any],
    ) -> BeatmatchPracticeResult | None:
        """Arm and grade an owned-deck beatmatch practice attempt, if wired."""

        should_grade = self._apply_beatmatch_practice_action(midi)
        if not should_grade:
            return None
        self._beatmatch_practice_lock_active = False
        result = self._grade_beatmatch_practice_tick()
        self._emit_live_beatmatch_grade(result)
        return result

    def _record_learn_control_practice_action(
        self,
        midi: dict[str, Any],
        *,
        expected: dict[str, Any] | None,
        evidence_time: float | None = None,
    ) -> ControlPracticeResult | None:
        """Credit a matched Learn control action through the cited skill spine."""

        if self._evidence_registry is None:
            return None
        t_session = self._evidence_time() if evidence_time is None else evidence_time
        before_mastered = self._mastered_flags()
        try:
            result = grade_matched_control_practice(
                expected=expected,
                midi=midi,
                evidence_registry=self._evidence_registry,
                t_session=t_session,
                progress=self._progress,
                now=datetime.now(UTC).isoformat(),
                lesson_id=self._learn.current_lesson_id or "",
            )
        except Exception as exc:  # pragma: no cover - defensive
            import sys

            print(
                f"[learn.runtime] control practice grade failed: {exc!r}",
                file=sys.stderr,
            )
            return None
        if result.event is None:
            return result
        self._emit_live_control_practice_grade(result)
        if result.credited:
            self._emit_mastered_unlocks(
                result.credited,
                before_mastered,
                citations=(
                    f"[ev:{CONTROL_PRACTICE_GRADED_EVENT}@{result.t_session:.3f}]",
                ),
            )
            try:
                from vibemix.learn.progress import LearnProgress, save_progress

                if isinstance(self._progress, LearnProgress):
                    save_progress(self._progress)
            except Exception as exc:  # pragma: no cover - defensive
                import sys

                print(
                    f"[learn.runtime] control practice progress save failed: {exc!r}",
                    file=sys.stderr,
                )
            self._emit_progress_snapshot()
        self._emit_control_practice_feedback(result, before_mastered=before_mastered)
        self._log_session_event(
            "learn_control_practice_graded",
            lesson_id=self._learn.current_lesson_id or "",
            course_id=self._learn.current_course_id or "",
            step_id=self._current_step_id(),
            evidence_time=result.t_session,
            control=result.control,
            deck=result.deck,
            skill_id=result.skill_id or "",
            credited=list(result.credited),
        )
        return result

    def _record_harmonic_practice_action(
        self,
        midi: dict[str, Any],
        *,
        expected: dict[str, Any] | None,
        evidence_time: float,
    ) -> HarmonicPracticeResult | None:
        """Credit L2.11 harmonic practice only from the final grounded pair step."""

        if (
            self._learn.current_lesson_id != "L2.11"
            or self._evidence_registry is None
            or self._active_harmonic_pair is None
            or expected is None
        ):
            return None
        expected_control, _expected_deck = _control_and_deck(expected)
        midi_control, _midi_deck = _control_and_deck(midi)
        if expected_control != "lesson_continue" or midi_control != "lesson_continue":
            return None
        if self._flow_step(self._active_step_index + 1) is not None:
            return None

        before_mastered = self._mastered_flags()
        try:
            result = grade_harmonic_practice_pair(
                self._active_harmonic_pair,
                evidence_registry=self._evidence_registry,
                t_session=evidence_time,
                progress=self._progress,
                now=datetime.now(UTC).isoformat(),
                lesson_id=self._learn.current_lesson_id or "",
            )
        except Exception as exc:  # pragma: no cover - defensive
            import sys

            print(
                f"[learn.runtime] harmonic practice grade failed: {exc!r}",
                file=sys.stderr,
            )
            return None
        if result.event is None:
            return result
        self._emit_live_harmonic_practice_grade(result)
        if result.credited:
            citation = f"[ev:{HARMONIC_PRACTICE_GRADED_EVENT}@{result.t_session:.3f}]"
            self._emit_mastered_unlocks(
                result.credited,
                before_mastered,
                citations=(citation,),
            )
            try:
                from vibemix.learn.progress import LearnProgress, save_progress

                if isinstance(self._progress, LearnProgress):
                    save_progress(self._progress)
            except Exception as exc:  # pragma: no cover - defensive
                import sys

                print(
                    f"[learn.runtime] harmonic practice progress save failed: {exc!r}",
                    file=sys.stderr,
                )
            self._emit_progress_snapshot()
        self._emit_harmonic_practice_feedback(result, before_mastered=before_mastered)
        pair = result.pair
        self._log_session_event(
            "learn_harmonic_practice_graded",
            lesson_id=self._learn.current_lesson_id or "",
            course_id=self._learn.current_course_id or "",
            step_id=self._current_step_id(),
            evidence_time=result.t_session,
            source_track_id=pair.source.track_id if pair is not None else "",
            target_track_id=pair.target.track_id if pair is not None else "",
            relation=pair.why if pair is not None else "",
            credited=list(result.credited),
        )
        return result

    def _emit_live_control_practice_grade(self, result: ControlPracticeResult) -> None:
        """Emit a live-grade HUD tick for a grounded matched control action."""

        if result.event is None:
            return
        citation = f"[ev:{CONTROL_PRACTICE_GRADED_EVENT}@{result.t_session:.3f}]"
        try:
            live_grade = LearnLiveGrade.make(
                verdict="locked",
                phase_error_beats=0.0,
                score=1.0,
                citation=citation,
            ).to_dict()
            self._ipc.emit(live_grade)
        except Exception as exc:  # pragma: no cover - defensive
            import sys

            print(
                f"[learn.runtime] control practice live grade emit failed: {exc!r}",
                file=sys.stderr,
            )

    def _emit_live_harmonic_practice_grade(self, result: HarmonicPracticeResult) -> None:
        """Emit a live-grade HUD tick for a grounded compatible-key receipt."""

        if result.event is None:
            return
        citation = f"[ev:{HARMONIC_PRACTICE_GRADED_EVENT}@{result.t_session:.3f}]"
        try:
            live_grade = LearnLiveGrade.make(
                verdict="locked",
                phase_error_beats=0.0,
                score=1.0,
                citation=citation,
            ).to_dict()
            self._ipc.emit(live_grade)
        except Exception as exc:  # pragma: no cover - defensive
            import sys

            print(
                f"[learn.runtime] harmonic practice live grade emit failed: {exc!r}",
                file=sys.stderr,
            )

    def _apply_beatmatch_practice_action(self, midi: dict[str, Any]) -> bool | None:
        """Apply one practice action to the owned deck without grading it."""

        if self._beatmatch_practice_action_recorder is None:
            return None
        try:
            return self._beatmatch_practice_action_recorder(
                self._learn.current_lesson_id,
                midi,
            )
        except Exception as exc:  # pragma: no cover - defensive
            import sys

            print(
                f"[learn.runtime] beatmatch practice recorder failed: {exc!r}",
                file=sys.stderr,
            )
            return None

    def _arm_recovery_drill_if_needed(self) -> None:
        """Arm the authored Course 3 recovery drill for the active step."""

        flow = self._active_flow
        lesson_id = self._learn.current_lesson_id
        if (
            flow is None
            or lesson_id is None
            or self._beatmatch_practice_action_recorder is None
            or not flow.drill_shapes
        ):
            return
        step_index = self._active_step_index
        if step_index >= len(flow.drill_shapes):
            return
        key = (lesson_id, step_index)
        if key == self._recovery_drill_armed_step_key:
            return
        drill = flow.drill_shapes[step_index]
        midi = {
            "type": "recovery_drill",
            "control": "recovery_drill",
            "deck": drill.deck or "B",
            "drill": drill.drill,
            "shape": drill.shape,
            "source": "learn_runtime",
        }
        try:
            should_grade = self._beatmatch_practice_action_recorder(lesson_id, midi)
        except Exception as exc:  # pragma: no cover - defensive
            import sys

            print(
                f"[learn.runtime] recovery drill arm failed: {exc!r}",
                file=sys.stderr,
            )
            return
        self._recovery_drill_armed_step_key = key
        t_session = self._evidence_time()
        self._recovery_drill_armed_citation = None
        if self._evidence_registry is not None:
            self._record_evidence(
                source=BEATMATCH_EVIDENCE_SOURCE,
                key=_RECOVERY_DRILL_ARMED_EVENT,
                t_session=t_session,
            )
            self._recovery_drill_armed_citation = (
                f"[{BEATMATCH_EVIDENCE_SOURCE}:{_RECOVERY_DRILL_ARMED_EVENT}@"
                f"{t_session:.3f}]"
            )
        self._log_session_event(
            "learn_recovery_drill_armed",
            lesson_id=lesson_id,
            course_id=self._learn.current_course_id or "",
            step_id=self._current_step_id(),
            drill=drill.drill,
            deck=drill.deck or "B",
            shape=drill.shape,
            evidence_time=t_session,
        )
        if should_grade:
            self._beatmatch_practice_lock_active = False
            self._emit_live_beatmatch_grade(self._grade_beatmatch_practice_tick())

    def _active_recovery_drill(self) -> Any | None:
        flow = self._active_flow
        lesson_id = self._learn.current_lesson_id
        if flow is None or lesson_id is None or not flow.drill_shapes:
            return None
        step_index = self._active_step_index
        if step_index >= len(flow.drill_shapes):
            return None
        if (lesson_id, step_index) != self._recovery_drill_armed_step_key:
            return None
        return flow.drill_shapes[step_index]

    def _recovery_bailout_label(
        self,
        midi: dict[str, Any],
        *,
        problem_deck: str,
    ) -> str | None:
        control, deck = _control_and_deck(midi)
        midi_deck = (deck or "").upper()
        cur = _cc_int(midi.get("value"))
        prev = _cc_int(midi.get("prev_value"), default=cur)
        delta = abs(cur - prev)

        if (
            control == "fx_echo"
            and midi.get("type") == "button"
            and midi.get("direction") == "down"
        ):
            return "echo-out"
        if (
            control == "filter"
            and midi_deck == problem_deck
            and abs(cur - 64) >= _RECOVERY_FILTER_CENTER_MIN_DELTA
            and delta >= _RECOVERY_BAILOUT_MIN_DELTA
        ):
            return f"deck {problem_deck} filter sweep"
        if (
            control == "vol"
            and midi_deck == problem_deck
            and cur <= _RECOVERY_CHANNEL_CUT_CC
            and prev - cur >= _RECOVERY_BAILOUT_MIN_DELTA
        ):
            return f"deck {problem_deck} volume cut"
        if control == "xfader":
            if (
                problem_deck == "B"
                and cur <= _RECOVERY_XFADER_CUT_CC
                and prev - cur >= _RECOVERY_BAILOUT_MIN_DELTA
            ):
                return "crossfader cut to deck A"
            if (
                problem_deck == "A"
                and cur >= 127 - _RECOVERY_XFADER_CUT_CC
                and cur - prev >= _RECOVERY_BAILOUT_MIN_DELTA
            ):
                return "crossfader cut to deck B"
        return None

    def _emit_recovery_drill_hint(
        self,
        midi: dict[str, Any],
        *,
        problem_deck: str,
    ) -> None:
        now = time.monotonic()
        self._state_entered_at = now
        if now - self._last_mismatch_hint_at < _MISMATCH_HINT_THROTTLE_S:
            return
        self._last_mismatch_hint_at = now
        self._record_action_evidence(expected=None, midi=midi, matched=False)
        self._mark_progress_practice_source(midi)
        citations = (
            (self._recovery_drill_armed_citation,)
            if self._recovery_drill_armed_citation is not None
            else ()
        )
        text = (
            f"That move does not get deck {problem_deck} out. Use echo-out, "
            f"sweep deck {problem_deck}'s filter, pull its volume down, or "
            "cut the crossfader away."
        )
        try:
            speak = LearnTutorSpeak.make(
                text=text,
                tts_marker=f"{self._learn.current_lesson_id or 'learn'}.recovery_hint",
                citations=citations,
                data_state="hint",
            ).to_dict()
            self._emit_tutor_speak(speak)
        except Exception as exc:  # pragma: no cover - defensive
            import sys

            print(
                f"[learn.runtime] recovery drill hint emit failed: {exc!r}",
                file=sys.stderr,
            )

    def _record_recovery_drill_success(
        self,
        midi: dict[str, Any],
        *,
        drill: Any,
        bailout_label: str,
        problem_deck: str,
    ) -> None:
        evidence_time = self._record_action_evidence(
            expected=None,
            midi=midi,
            matched=True,
        )
        self._mark_progress_practice_source(midi)
        citation = None
        credited: tuple[str, ...] = ()
        if self._evidence_registry is not None:
            self._record_evidence(
                source=BEATMATCH_EVIDENCE_SOURCE,
                key=_RECOVERY_DRILL_RECOVERED_EVENT,
                t_session=evidence_time,
            )
            citation = (
                f"[{BEATMATCH_EVIDENCE_SOURCE}:{_RECOVERY_DRILL_RECOVERED_EVENT}@"
                f"{evidence_time:.3f}]"
            )
            before_mastered = self._mastered_flags()
            credited = tuple(
                recognize(
                    SimpleNamespace(
                        type=_RECOVERY_DRILL_RECOVERED_EVENT,
                        extra={
                            "drill": getattr(drill, "drill", ""),
                            "deck": problem_deck,
                            "bailout": bailout_label,
                        },
                    ),
                    citation_check=lambda source, key, t: self._evidence_registry.has(
                        source,
                        key,
                        t,
                        tol=1.0,
                    ),
                    progress=self._progress,
                    now=datetime.now(UTC).isoformat(),
                    event_t=evidence_time,
                )
            )
            if credited:
                self._emit_mastered_unlocks(
                    credited,
                    before_mastered,
                    citations=(citation,),
                )
                try:
                    from vibemix.learn.progress import LearnProgress, save_progress

                    if isinstance(self._progress, LearnProgress):
                        save_progress(self._progress)
                except Exception as exc:  # pragma: no cover - defensive
                    import sys

                    print(
                        f"[learn.runtime] recovery drill progress save failed: {exc!r}",
                        file=sys.stderr,
                    )
                self._emit_progress_snapshot()
        self._log_session_event(
            "learn_recovery_drill_recovered",
            lesson_id=self._learn.current_lesson_id or "",
            course_id=self._learn.current_course_id or "",
            step_id=self._current_step_id(),
            drill=getattr(drill, "drill", ""),
            deck=problem_deck,
            bailout=bailout_label,
            evidence_time=evidence_time,
            credited=list(credited),
        )
        citations = (citation,) if citation is not None else ()
        try:
            speak = LearnTutorSpeak.make(
                text=self._recovery_drill_success_text(
                    bailout_label,
                    problem_deck=problem_deck,
                ),
                tts_marker=f"{self._learn.current_lesson_id or 'learn'}.recovery_ok",
                citations=citations,
                data_state="hint",
            ).to_dict()
            self._emit_tutor_speak(speak)
        except Exception as exc:  # pragma: no cover - defensive
            import sys

            print(
                f"[learn.runtime] recovery drill success emit failed: {exc!r}",
                file=sys.stderr,
            )

    def _recovery_drill_success_text(
        self,
        bailout_label: str,
        *,
        problem_deck: str,
    ) -> str:
        clean_deck = "A" if problem_deck == "B" else "B"
        if "filter" in bailout_label:
            return (
                f"that filter sweep pulls deck {problem_deck} out, so "
                f"deck {clean_deck} reads clean."
            )
        if "volume" in bailout_label:
            return (
                f"pulling deck {problem_deck} down removes the bad layer, "
                f"so deck {clean_deck} stays clean."
            )
        if "crossfader" in bailout_label:
            return f"that crossfader cut gets deck {problem_deck} out fast."
        return (
            f"echo-out gives deck {problem_deck} a clean exit instead of "
            "letting it fight the mix."
        )

    def _advance_recovery_drill_step(self, next_step: LessonStep) -> None:
        self._active_step_index += 1
        self._learn.current_beat_index = self._active_step_index
        self._learn.strike_count = 0
        self._state_entered_at = time.monotonic()
        self._emit_advance(reason="action_matched")
        self._emit_highlight(next_step.expected_action)
        self._emit_step_tutor(next_step)
        self._arm_recovery_drill_if_needed()

    def _complete_recovery_drill_lesson(self) -> None:
        self._emit_advance(reason="action_matched")
        self.send("recovery_complete")

    def _record_cue_placement_practice_action(self, midi: dict[str, Any]) -> None:
        """Arm and grade an owned-deck cue placement practice attempt, if wired."""

        if self._cue_placement_practice_action_recorder is None:
            return
        timed_midi = dict(midi)
        cue_frame = self._cue_placement_playhead_frame()
        if cue_frame is not None:
            timed_midi.setdefault("cue_frame", cue_frame)
        try:
            should_grade = self._cue_placement_practice_action_recorder(
                self._learn.current_lesson_id,
                timed_midi,
            )
        except Exception as exc:  # pragma: no cover - defensive
            import sys

            print(
                f"[learn.runtime] cue placement practice recorder failed: {exc!r}",
                file=sys.stderr,
            )
            return
        if not should_grade:
            return
        self._cue_placement_practice_lock_active = False
        self._emit_live_cue_placement_grade(self._grade_cue_placement_practice_tick())

    def _cue_placement_playhead_frame(self) -> float | None:
        """Return deck B's owned practice playhead frame, when available."""

        if self._playhead_payload_loader is None:
            return None
        try:
            payload = self._playhead_payload_loader()
        except Exception as exc:  # pragma: no cover - defensive
            import sys

            print(
                f"[learn.runtime] cue placement playhead lookup failed: {exc!r}",
                file=sys.stderr,
            )
            return None
        if not isinstance(payload, dict):
            return None
        decks = payload.get("decks")
        if not isinstance(decks, dict):
            return None
        deck_b = decks.get("B")
        if not isinstance(deck_b, dict):
            return None
        try:
            frame = float(deck_b.get("frame"))
        except (TypeError, ValueError):
            return None
        if not math.isfinite(frame) or frame < 0.0:
            return None
        return frame

    def on_skip(self, **_kwargs: Any) -> None:
        self._last_was_match = False
        self._last_completion_can_advance = False

    def on_observer_complete(
        self, completed: bool = True, **_kwargs: Any
    ) -> None:
        self._last_was_match = completed
        self._last_completion_can_advance = False

    def on_recovery_complete(self, **_kwargs: Any) -> None:
        self._last_was_match = True
        self._last_completion_can_advance = True

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
        self._stop_beatmatch_practice_player()
        self._waveform_ready_lesson_id = None
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
        self._last_mismatch_hint_signature = None
        self._active_harmonic_pair = None
        self._recovery_drill_armed_step_key = None
        self._recovery_drill_armed_citation = None

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

        self._emit_practice_bank_preface_if_needed()
        self._emit_opening_tutor_beats(expected)
        self._start_beatmatch_practice_player()
        self._arm_recovery_drill_if_needed()
        # Reset the strike timer's state-entry anchor.
        self._state_entered_at = time.monotonic()
        self._last_mismatch_hint_signature = None

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
        ``on_skip`` → ``"user_skip"``). Matched actions finish after a
        short UI settle; only user-skip waits for the 45 s min-dwell.

        Scheduling falls back to a no-op when no asyncio event loop is
        running (the synchronous unit-test path) — state stays in
        ``advancing``, which is one of the two acceptable terminal
        observations per the test contract.
        """
        self._stop_beatmatch_practice_player()
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
            if self._last_was_match:
                self._finish_task = asyncio.create_task(
                    self._finish_after_action_settle()
                )
            else:
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

    async def _finish_after_action_settle(self) -> None:
        """Let the success animation breathe briefly, then complete."""
        await asyncio.sleep(0.7)
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
        self._stop_beatmatch_practice_player()
        try:
            self._progress.mark_completed(
                self._learn.current_course_id,
                self._learn.current_lesson_id,
                strikes_used=self._learn.strike_count,
                demonstrated=self._last_was_match,
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
        self._advance_to_next_lesson_if_needed()

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

    def _advance_to_next_lesson_if_needed(self) -> None:
        """Auto-load the next authored lesson after a demonstrated completion."""
        if not self._last_was_match or not self._last_completion_can_advance:
            return
        self._last_completion_can_advance = False
        course_id = self._learn.current_course_id
        lesson_id = self._learn.current_lesson_id
        controller_id = self._learn.current_controller_id
        if not course_id or not lesson_id or not controller_id:
            return
        lesson_ids = course_lesson_ids(course_id)
        try:
            index = lesson_ids.index(lesson_id)
        except ValueError:
            return
        next_index = index + 1
        if next_index >= len(lesson_ids):
            return
        next_lesson_id = lesson_ids[next_index]
        try:
            self.send(
                "load",
                lesson_id=next_lesson_id,
                course_id=course_id,
                controller_id=controller_id,
            )
            self.send("begin")
        except Exception as exc:  # pragma: no cover - defensive
            import sys

            print(
                f"[learn.runtime] next lesson advance failed: {exc!r}",
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

    def _save_progress_quietly(self, context: str) -> bool:
        try:
            from vibemix.learn.progress import LearnProgress, save_progress

            if not isinstance(self._progress, LearnProgress):
                return False
            save_progress(self._progress)
            return True
        except Exception as exc:  # pragma: no cover — defensive
            import sys

            print(
                f"[learn.runtime] {context} progress save failed: {exc!r}",
                file=sys.stderr,
            )
            return False

    def _mark_progress_practice_feedback(
        self,
        *,
        kind: str,
        label: str,
        message: str,
        detail: str | None = None,
    ) -> bool:
        """Persist one measured miss as the next mission's recovery target."""
        lesson_id = self._learn.current_lesson_id
        course_id = self._learn.current_course_id
        if not lesson_id or not course_id:
            return False
        try:
            from vibemix.learn.progress import LearnProgress

            if not isinstance(self._progress, LearnProgress):
                return False
            changed = self._progress.mark_practice_feedback(
                course_id,
                lesson_id,
                kind=kind,
                label=label,
                message=message,
                detail=detail,
            )
        except Exception as exc:  # pragma: no cover — defensive
            import sys

            print(
                f"[learn.runtime] mark_practice_feedback failed: {exc!r}",
                file=sys.stderr,
            )
            return False
        if not changed:
            return False
        return self._save_progress_quietly("practice feedback")

    def _clear_progress_practice_feedback(self) -> bool:
        """Clear stale miss feedback after a clean measured rep."""
        lesson_id = self._learn.current_lesson_id
        if not lesson_id:
            return False
        try:
            from vibemix.learn.progress import LearnProgress

            if not isinstance(self._progress, LearnProgress):
                return False
            changed = self._progress.clear_practice_feedback(lesson_id)
        except Exception as exc:  # pragma: no cover — defensive
            import sys

            print(
                f"[learn.runtime] clear_practice_feedback failed: {exc!r}",
                file=sys.stderr,
            )
            return False
        if not changed:
            return False
        return self._save_progress_quietly("practice feedback clear")

    def _record_free_practice_receipt(self, midi: dict[str, Any]) -> None:
        """Persist one sandbox practice receipt without completing a lesson."""
        control, deck = _control_and_deck(midi)
        lesson_id = _FREE_PRACTICE_CONTROL_LESSON_IDS.get(control)
        if not lesson_id:
            return
        meta = CURRICULUM.get(lesson_id)
        if meta is None:
            return
        source_key = _practice_source_key(midi.get("source"))
        if source_key is None:
            return
        receipt_key = (lesson_id, source_key, control)
        if receipt_key in self._free_practice_receipts:
            return
        try:
            from vibemix.learn.progress import LearnProgress, save_progress

            if not isinstance(self._progress, LearnProgress):
                return
            self._progress.mark_practice_source(meta.course_id, lesson_id, source_key)
            save_progress(self._progress)
            self._free_practice_receipts.add(receipt_key)
        except Exception as exc:  # pragma: no cover — defensive
            import sys

            print(
                f"[learn.runtime] free practice receipt failed: {exc!r}",
                file=sys.stderr,
            )
            return
        self._emit_progress_snapshot()
        self._log_session_event(
            "learn_free_practice_receipt",
            lesson_id=lesson_id,
            course_id=meta.course_id,
            control=control,
            deck=deck,
            source=source_key,
        )

    def _emit_progress_snapshot(self) -> None:
        """Emit the current progress snapshot when it is schema-shaped."""
        try:
            snapshot = self._progress.snapshot(
                active_lesson_id=self._learn.current_lesson_id
            )
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

    def _mastered_flags(self) -> dict[str, bool]:
        """Snapshot stored Mastered flags before a cited skill-credit mutation."""
        skills = getattr(self._progress, "skills", {}) or {}
        if not isinstance(skills, dict):
            return {}
        return {
            skill_id: bool(row.get("mastered", False))
            for skill_id, row in skills.items()
            if isinstance(row, dict)
        }

    def _emit_mastered_unlocks(
        self,
        credited: tuple[str, ...] | list[str],
        before_mastered: dict[str, bool],
        *,
        citations: tuple[str, ...] = (),
    ) -> None:
        """Speak the one-time Mastered line only for a just-flipped skill."""
        for skill_id in credited:
            row = (getattr(self._progress, "skills", {}) or {}).get(skill_id)
            if not isinstance(row, dict):
                continue
            line = mastered_unlock_line(
                skill_id,
                was_mastered=before_mastered.get(skill_id, False),
                now_mastered=bool(row.get("mastered", False)),
            )
            if not line:
                continue
            try:
                speak = LearnTutorSpeak.make(
                    text=line,
                    tts_marker=(
                        f"{self._learn.current_lesson_id or 'learn'}.mastered.{skill_id}"
                    ),
                    citations=citations,
                    data_state="hint",
                ).to_dict()
                self._emit_tutor_speak(speak)
            except Exception as exc:  # pragma: no cover - defensive
                import sys

                print(
                    f"[learn.runtime] mastered unlock emit failed: {exc!r}",
                    file=sys.stderr,
                )

    def _practice_result_flipped_mastered(
        self,
        skill_ids: tuple[str, ...] | list[str],
        before_mastered: dict[str, bool],
    ) -> bool:
        """Return True when this practice receipt already earned a Mastered line."""
        skills = getattr(self._progress, "skills", {}) or {}
        if not isinstance(skills, dict):
            return False
        for skill_id in skill_ids:
            row = skills.get(skill_id)
            if not isinstance(row, dict):
                continue
            if not before_mastered.get(skill_id, False) and bool(row.get("mastered", False)):
                return True
        return False

    def _emit_control_practice_feedback(
        self,
        result: ControlPracticeResult,
        *,
        before_mastered: dict[str, bool],
    ) -> None:
        """Speak an immediate, cited receipt for grounded control practice."""
        if result.event is None or not result.skill_id:
            return
        if self._practice_result_flipped_mastered(result.credited, before_mastered):
            return
        citation = f"[ev:{CONTROL_PRACTICE_GRADED_EVENT}@{result.t_session:.3f}]"
        text = self._control_practice_feedback_text(result)
        if text is None:
            return
        try:
            speak = LearnTutorSpeak.make(
                text=text,
                tts_marker=f"{self._learn.current_lesson_id or 'learn'}.control_grade",
                citations=(citation,),
                data_state="hint",
            ).to_dict()
            self._emit_tutor_speak(speak)
        except Exception as exc:  # pragma: no cover - defensive
            import sys

            print(
                f"[learn.runtime] control practice feedback emit failed: {exc!r}",
                file=sys.stderr,
            )

    def _control_practice_feedback_text(self, result: ControlPracticeResult) -> str | None:
        """Return concise authored feedback for a cited control-practice receipt."""
        control = (result.control or "control").strip()
        deck = (result.deck or "").strip()
        deck_phrase = f" on deck {deck}" if deck else ""
        if result.skill_id == "eq_mixing":
            band_by_control = {
                "eq_low": "low EQ",
                "eq_mid": "mid EQ",
                "eq_hi": "high EQ",
                "filter": "filter",
            }
            band = band_by_control.get(control, "EQ")
            if control == "filter":
                return f"{band}{deck_phrase} landed - clean space without grabbing the mix."
            return f"{band}{deck_phrase} landed - that is the space-making move."
        if result.skill_id == "deck_control":
            if control in {"cue", "headphone_cue"}:
                return f"cue check{deck_phrase} landed - listen first, commit second."
            if control in {"jog", "jog_touch", "jog_touched"}:
                return f"jog touch{deck_phrase} landed - small correction, real control."
            if control in {"loop_in", "loop_out"}:
                return f"loop point{deck_phrase} landed - you are catching the phrase."
            if control == "xfader":
                return "crossfader move landed - place the blend, do not chase it."
            if control == "play":
                return f"play control{deck_phrase} landed - transport is under your hand."
            return f"{control.replace('_', ' ')}{deck_phrase} landed - keep that touch."
        return None

    def _emit_harmonic_practice_feedback(
        self,
        result: HarmonicPracticeResult,
        *,
        before_mastered: dict[str, bool],
    ) -> None:
        """Speak an immediate, cited receipt for grounded compatible-key practice."""
        if result.event is None or result.pair is None:
            return
        if self._practice_result_flipped_mastered(result.credited, before_mastered):
            return
        pair = result.pair
        receipt = f"[ev:{HARMONIC_PRACTICE_GRADED_EVENT}@{result.t_session:.3f}]"
        citations = (receipt, *harmonic_practice_citations(pair, self._evidence_registry))
        text = (
            f"compatible pair banked: {pair.source.camelot} into {pair.target.camelot}. "
            f"{pair.why}."
        )
        try:
            speak = LearnTutorSpeak.make(
                text=text,
                tts_marker=f"{self._learn.current_lesson_id or 'learn'}.harmonic_grade",
                citations=citations[:4],
                data_state="hint",
            ).to_dict()
            self._emit_tutor_speak(speak)
        except Exception as exc:  # pragma: no cover - defensive
            import sys

            print(
                f"[learn.runtime] harmonic practice feedback emit failed: {exc!r}",
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
            # Sibling emit: drive the particle-organism focus dissolve toward
            # this control. Kept thin + caused-only — the organism animates
            # ONLY on this real teaching event (visual grounding contract).
            focus = LearnTeachingFocus.make(
                control_id=control,
                deck=deck,
                band=_eq_band_for_control(control),
                phase="focus",
            ).to_dict()
            self._ipc.emit(focus)
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

    def _emit_tutor_speak(self, speak: dict[str, Any]) -> None:
        """Emit a Learn tutor line and, when wired, voice it through the co-host voice."""
        self._ipc.emit(speak)
        self._log_tutor_speak_event(speak)
        if self._tutor_speak_audio is None:
            return
        payload = speak.get("payload")
        if not isinstance(payload, dict):
            return
        text = payload.get("text")
        tts_marker = payload.get("tts_marker")
        if not isinstance(text, str) or not text.strip():
            return
        if not isinstance(tts_marker, str) or not tts_marker.strip():
            return
        try:
            self._tutor_speak_audio(text, tts_marker)
        except Exception as exc:  # pragma: no cover - defensive
            import sys

            print(
                f"[learn.runtime] tutor audio callback failed: {exc!r}",
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

    def _grade_beatmatch_practice_tick(self) -> BeatmatchPracticeResult | None:
        """Grade the optional owned-deck beatmatch practice lane on a lock edge.

        Normal live co-host audio is observational and cannot honestly grade
        beatmatching. This hook only runs when Learn owns both practice decks and
        an explicit loader supplies exact grids + deck state. A sustained locked
        state credits once; the edge re-arms only after the grade stops being
        creditable.
        """
        if self._beatmatch_practice_loader is None or self._evidence_registry is None:
            self._last_beatmatch_live_grade_verdict = None
            self._last_beatmatch_live_grade_signature = None
            self._last_beatmatch_save_candidate = None
            self._reset_beatmatch_save_attempt(reset_streak=True)
            return None
        try:
            snapshot = self._beatmatch_practice_loader()
        except Exception as exc:  # pragma: no cover - defensive
            import sys

            print(
                f"[learn.runtime] beatmatch practice loader failed: {exc!r}",
                file=sys.stderr,
            )
            self._last_beatmatch_save_candidate = None
            self._reset_beatmatch_save_attempt()
            return None
        if snapshot is None:
            self._beatmatch_practice_lock_active = False
            self._last_beatmatch_live_grade_verdict = None
            self._last_beatmatch_live_grade_signature = None
            self._last_beatmatch_save_candidate = None
            self._reset_beatmatch_save_attempt()
            return None

        t_session = self._evidence_time()
        grade = grade_owned_beatmatch_state(
            snapshot.grid_a,
            snapshot.grid_b,
            snapshot.deck_state,
        )
        if not is_creditable_locked_grade(grade):
            self._beatmatch_practice_lock_active = False
            save_state = self._beatmatch_save_state_for_miss(grade, t_session)
            if save_state["save_floor_expired"]:
                self._last_beatmatch_save_candidate = None
            else:
                self._remember_beatmatch_save_candidate(grade.verdict, grade.phase_error_beats)
            feedback = self._beatmatch_recovery_feedback(grade)
            if feedback is not None and self._mark_progress_practice_feedback(**feedback):
                self._emit_progress_snapshot()
            return BeatmatchPracticeResult(
                grade=grade,
                event=None,
                credited=(),
                t_session=t_session,
                **save_state,
            )
        feedback_cleared = self._clear_progress_practice_feedback()
        if self._beatmatch_practice_lock_active:
            self._remember_beatmatch_save_candidate(grade.verdict, grade.phase_error_beats)
            if feedback_cleared:
                self._emit_progress_snapshot()
            return BeatmatchPracticeResult(
                grade=grade,
                event=None,
                credited=(),
                t_session=t_session,
                **self._beatmatch_save_payload(),
            )

        self._beatmatch_practice_lock_active = True
        save_edge = self._beatmatch_save_edge_for(grade.verdict, grade.phase_error_beats)
        self._remember_beatmatch_save_candidate(grade.verdict, grade.phase_error_beats)
        before_mastered = self._mastered_flags()
        result = grade_owned_beatmatch_attempt(
            snapshot.grid_a,
            snapshot.grid_b,
            snapshot.deck_state,
            evidence_registry=self._evidence_registry,
            t_session=t_session,
            progress=self._progress,
            now=datetime.now(UTC).isoformat(),
        )
        result = replace(result, **self._beatmatch_save_payload())
        if save_edge is not None:
            landed_payload = self._beatmatch_save_landed_payload(
                t_session=t_session,
                from_verdict=str(save_edge["from_verdict"]),
                from_phase_error_beats=float(save_edge["from_phase_error_beats"]),
                recovery_delta_beats=float(save_edge["recovery_delta_beats"]),
            )
            result = replace(
                result,
                save_landed=True,
                save_from_verdict=save_edge["from_verdict"],
                save_from_phase_error_beats=save_edge["from_phase_error_beats"],
                save_recovery_delta_beats=save_edge["recovery_delta_beats"],
                **landed_payload,
            )
        if result.credited:
            self._emit_mastered_unlocks(
                result.credited,
                before_mastered,
                citations=(
                    f"[{BEATMATCH_EVIDENCE_SOURCE}:{BEATMATCH_GRADED_EVENT}@"
                    f"{result.t_session:.3f}]",
                ),
            )
            try:
                from vibemix.learn.progress import LearnProgress, save_progress

                if isinstance(self._progress, LearnProgress):
                    save_progress(self._progress)
            except Exception as exc:  # pragma: no cover - defensive
                import sys

                print(
                    f"[learn.runtime] beatmatch practice progress save failed: {exc!r}",
                    file=sys.stderr,
                )
            self._emit_progress_snapshot()
        elif feedback_cleared:
            self._emit_progress_snapshot()
        self._log_session_event(
            "learn_beatmatch_practice_graded",
            lesson_id=self._learn.current_lesson_id or "",
            course_id=self._learn.current_course_id or "",
            step_id=self._current_step_id(),
            evidence_time=t_session,
            verdict=result.grade.verdict,
            credited=list(result.credited),
        )
        return result

    def _remember_beatmatch_save_candidate(self, verdict: str, phase_error_beats: float) -> None:
        if verdict not in {"drifting", "trainwreck"}:
            self._last_beatmatch_save_candidate = None
            return
        phase = float(phase_error_beats)
        if not math.isfinite(phase):
            self._last_beatmatch_save_candidate = None
            return
        self._last_beatmatch_save_candidate = (verdict, max(-0.5, min(0.5, phase)))

    def _beatmatch_save_edge_for(
        self,
        verdict: str,
        phase_error_beats: float,
    ) -> dict[str, float | str] | None:
        if verdict != "locked" or self._last_beatmatch_save_candidate is None:
            return None
        from_verdict, from_phase = self._last_beatmatch_save_candidate
        if from_verdict not in {"drifting", "trainwreck"}:
            return None
        phase = float(phase_error_beats)
        if not math.isfinite(phase):
            phase = 0.0
        phase = max(-0.5, min(0.5, phase))
        return {
            "from_verdict": from_verdict,
            "from_phase_error_beats": from_phase,
            "recovery_delta_beats": max(0.0, min(0.5, abs(from_phase) - abs(phase))),
        }

    def _beatmatch_save_window_seconds(self) -> float:
        level = max(
            _BEATMATCH_SAVE_DIFFICULTY_MIN,
            min(_BEATMATCH_SAVE_DIFFICULTY_MAX, self._beatmatch_save_difficulty_level),
        )
        return max(
            _BEATMATCH_SAVE_FLOOR_MIN_S,
            _BEATMATCH_SAVE_FLOOR_BASE_S - ((level - 1) * _BEATMATCH_SAVE_FLOOR_STEP_S),
        )

    def _set_beatmatch_save_difficulty(self, level: int) -> None:
        bounded = max(
            _BEATMATCH_SAVE_DIFFICULTY_MIN,
            min(_BEATMATCH_SAVE_DIFFICULTY_MAX, int(level)),
        )
        self._beatmatch_save_difficulty_level = bounded
        if self._beatmatch_practice_difficulty_setter is None:
            return
        try:
            self._beatmatch_practice_difficulty_setter(bounded)
        except Exception as exc:  # pragma: no cover - defensive
            import sys

            print(
                f"[learn.runtime] beatmatch save difficulty setter failed: {exc!r}",
                file=sys.stderr,
            )

    def _reset_beatmatch_save_attempt(self, *, reset_streak: bool = False) -> None:
        self._beatmatch_save_attempt_started_at = None
        self._beatmatch_save_attempt_window_s = None
        if reset_streak:
            self._beatmatch_save_streak = 0

    def _beatmatch_save_payload(
        self,
        *,
        active: bool | None = None,
        total_s: float | None = None,
        remaining_s: float | None = None,
        expired: bool = False,
        difficulty_level: int | None = None,
        streak: int | None = None,
    ) -> dict[str, object]:
        if active is None:
            active = self._beatmatch_save_attempt_started_at is not None
        if total_s is None:
            total_s = self._beatmatch_save_attempt_window_s
        if remaining_s is None and active and total_s is not None:
            remaining_s = total_s
        if remaining_s is not None:
            remaining_s = max(0.0, round(float(remaining_s), 2))
        if total_s is not None:
            total_s = max(0.0, round(float(total_s), 2))
        return {
            "save_attempt_active": bool(active),
            "save_floor_seconds_total": total_s,
            "save_floor_seconds_remaining": remaining_s,
            "save_floor_expired": bool(expired),
            "save_difficulty_level": int(
                self._beatmatch_save_difficulty_level
                if difficulty_level is None
                else difficulty_level
            ),
            "save_streak": int(self._beatmatch_save_streak if streak is None else streak),
        }

    def _beatmatch_save_state_for_miss(
        self,
        grade,
        t_session: float,
    ) -> dict[str, object]:
        verdict = getattr(grade, "verdict", "")
        if verdict not in {"drifting", "trainwreck"}:
            self._reset_beatmatch_save_attempt()
            return self._beatmatch_save_payload(active=False)

        if (
            self._beatmatch_save_attempt_started_at is None
            or self._beatmatch_save_attempt_window_s is None
        ):
            self._beatmatch_save_attempt_started_at = float(t_session)
            self._beatmatch_save_attempt_window_s = self._beatmatch_save_window_seconds()

        started_at = self._beatmatch_save_attempt_started_at
        total_s = self._beatmatch_save_attempt_window_s
        elapsed_s = max(0.0, float(t_session) - started_at)
        remaining_s = max(0.0, total_s - elapsed_s)
        if remaining_s > 0.0:
            return self._beatmatch_save_payload(
                active=True,
                total_s=total_s,
                remaining_s=remaining_s,
            )

        level = self._beatmatch_save_difficulty_level
        self._beatmatch_save_streak = 0
        self._log_session_event(
            "learn_beatmatch_save_floor_expired",
            lesson_id=self._learn.current_lesson_id or "",
            course_id=self._learn.current_course_id or "",
            step_id=self._current_step_id(),
            evidence_time=float(t_session),
            verdict=verdict,
            difficulty_level=level,
            floor_seconds_total=total_s,
        )
        self._reset_beatmatch_save_attempt()
        return self._beatmatch_save_payload(
            active=False,
            total_s=total_s,
            remaining_s=0.0,
            expired=True,
            difficulty_level=level,
            streak=0,
        )

    def _beatmatch_save_landed_payload(
        self,
        *,
        t_session: float,
        from_verdict: str,
        from_phase_error_beats: float,
        recovery_delta_beats: float,
    ) -> dict[str, object]:
        level_won = self._beatmatch_save_difficulty_level
        total_s = self._beatmatch_save_attempt_window_s
        remaining_s: float | None = None
        if (
            total_s is not None
            and self._beatmatch_save_attempt_started_at is not None
        ):
            elapsed_s = max(0.0, float(t_session) - self._beatmatch_save_attempt_started_at)
            remaining_s = max(0.0, total_s - elapsed_s)
        next_streak = self._beatmatch_save_streak + 1
        self._beatmatch_save_streak = next_streak
        self._log_session_event(
            "learn_beatmatch_save_landed",
            lesson_id=self._learn.current_lesson_id or "",
            course_id=self._learn.current_course_id or "",
            step_id=self._current_step_id(),
            evidence_time=float(t_session),
            from_verdict=from_verdict,
            from_phase_error_beats=from_phase_error_beats,
            recovery_delta_beats=recovery_delta_beats,
            difficulty_level=level_won,
            streak=next_streak,
        )
        self._reset_beatmatch_save_attempt()
        self._set_beatmatch_save_difficulty(level_won + 1)
        return self._beatmatch_save_payload(
            active=False,
            total_s=total_s,
            remaining_s=remaining_s,
            difficulty_level=level_won,
            streak=next_streak,
        )

    def _grade_beatmatch_sandbox_tick(self) -> BeatmatchPracticeResult | None:
        """Grade free practice for feedback only, never evidence or progress."""

        if self._beatmatch_practice_sandbox_loader is None:
            return None
        try:
            snapshot = self._beatmatch_practice_sandbox_loader()
        except Exception as exc:  # pragma: no cover - defensive
            import sys

            print(
                f"[learn.runtime] beatmatch sandbox loader failed: {exc!r}",
                file=sys.stderr,
            )
            return None
        if snapshot is None:
            return None
        grade = grade_owned_beatmatch_state(
            snapshot.grid_a,
            snapshot.grid_b,
            snapshot.deck_state,
        )
        return BeatmatchPracticeResult(
            grade=grade,
            event=None,
            credited=(),
            t_session=self._evidence_time(),
        )

    def _emit_live_beatmatch_grade(self, result: BeatmatchPracticeResult | None) -> None:
        """Voice the owned-deck beatmatch grade through the tutor speak channel.

        The grade engine is deterministic and already writes the
        ``BEATMATCH_GRADED`` evidence atom only for the credited locked edge.
        Drift / tempo / trainwreck coaching is authored from measured state but
        intentionally uncited, so this method never fabricates an ``ev`` atom.
        """
        if result is None or result.grade.abstain:
            self._last_beatmatch_live_grade_verdict = None
            self._last_beatmatch_live_grade_signature = None
            return

        verdict = result.grade.verdict
        text = self._recovery_drill_grade_text(verdict) or self._beatmatch_grade_text(
            result
        )
        if text is None:
            return

        citations: tuple[str, ...] = ()
        if result.event is not None:
            citations = (
                f"[{BEATMATCH_EVIDENCE_SOURCE}:{BEATMATCH_GRADED_EVENT}@{result.t_session:.3f}]",
            )
        elif self._recovery_drill_armed_citation is not None:
            citations = (self._recovery_drill_armed_citation,)
        citation = citations[0] if citations else None

        phase_error = float(result.grade.phase_error_beats)
        if not math.isfinite(phase_error):
            phase_error = 0.0
        phase_error = max(-0.5, min(0.5, phase_error))
        score = float(result.grade.score)
        if not math.isfinite(score):
            score = 0.0
        score = max(0.0, min(1.0, score))
        signature = (
            verdict,
            round(phase_error, 3),
            round(score, 3),
            citation,
            result.save_landed,
            result.save_floor_expired,
            result.save_attempt_active,
            (
                None
                if result.save_floor_seconds_remaining is None
                else round(float(result.save_floor_seconds_remaining), 1)
            ),
            result.save_difficulty_level,
            result.save_streak,
        )

        lesson_id = self._learn.current_lesson_id or "learn"
        try:
            if signature != self._last_beatmatch_live_grade_signature:
                self._last_beatmatch_live_grade_signature = signature
                live_grade = LearnLiveGrade.make(
                    verdict=verdict,
                    phase_error_beats=phase_error,
                    score=score,
                    citation=citation,
                    save_landed=result.save_landed,
                    save_from_verdict=result.save_from_verdict,
                    save_from_phase_error_beats=result.save_from_phase_error_beats,
                    save_recovery_delta_beats=result.save_recovery_delta_beats,
                    save_attempt_active=result.save_attempt_active,
                    save_floor_seconds_total=result.save_floor_seconds_total,
                    save_floor_seconds_remaining=result.save_floor_seconds_remaining,
                    save_floor_expired=result.save_floor_expired,
                    save_difficulty_level=result.save_difficulty_level,
                    save_streak=result.save_streak,
                ).to_dict()
                self._ipc.emit(live_grade)

            if verdict == self._last_beatmatch_live_grade_verdict:
                return
            self._last_beatmatch_live_grade_verdict = verdict

            speak = LearnTutorSpeak.make(
                text=text,
                tts_marker=f"{lesson_id}.grade",
                citations=citations,
                data_state="hint",
            ).to_dict()
            self._emit_tutor_speak(speak)
        except Exception as exc:  # pragma: no cover - defensive
            import sys

            print(
                f"[learn.runtime] beatmatch live grade emit failed: {exc!r}",
                file=sys.stderr,
            )

    def _beatmatch_grade_text(self, result: BeatmatchPracticeResult) -> str | None:
        """Return authored beatmatch feedback grounded in the measured grade."""
        grade = result.grade
        verdict = grade.verdict
        if verdict == "locked":
            if result.event is not None:
                return "that's the pocket - tempo and phase are sitting together."
            return "pocket is centered - keep it there until proof lands."
        if verdict == "drifting":
            try:
                phase_error = float(grade.phase_error_beats)
            except (TypeError, ValueError):
                phase_error = 0.0
            if not math.isfinite(phase_error):
                phase_error = 0.0
            if abs(phase_error) < 0.08:
                if phase_error > 0:
                    return "deck B is just late - nudge forward without touching tempo."
                if phase_error < 0:
                    return "deck B is just early - drag it back without touching tempo."
                return "phase is close - listen for the kicks to sit together."
            if phase_error > 0:
                return "deck B is dragging - jog it forward until the kicks meet."
            return "deck B is rushing - drag it back until the kicks meet."
        if verdict == "tempo_off":
            try:
                tempo_error = float(grade.tempo_error)
            except (TypeError, ValueError):
                tempo_error = 0.0
            if math.isfinite(tempo_error) and tempo_error >= 0.08:
                return "tempo is far out - fix pitch before chasing phase."
            return "tempo is close but off - ease the pitch until drift stops."
        if verdict == "trainwreck":
            try:
                phase_error = float(grade.phase_error_beats)
            except (TypeError, ValueError):
                phase_error = 0.0
            if math.isfinite(phase_error) and phase_error < 0:
                return "deck B jumped early - pull back and re-find the 1."
            return "deck B missed the 1 late - reset on the next downbeat."
        return None

    def _recovery_drill_grade_text(self, verdict: str) -> str | None:
        """Return drill-specific feedback for authored recovery misses."""

        flow = self._active_flow
        if flow is None or not flow.drill_shapes:
            return None
        step_index = self._active_step_index
        if step_index >= len(flow.drill_shapes):
            return None
        key = (self._learn.current_lesson_id or "", step_index)
        if key != self._recovery_drill_armed_step_key:
            return None
        drill = flow.drill_shapes[step_index].drill
        if drill == "key_clash" and verdict == "tempo_off":
            return (
                "I pitched deck B up into the clash - hear that pull, then bail out clean."
            )
        if drill == "misaligned_phrase" and verdict == "trainwreck":
            return (
                "Deck B is a quarter-beat off - the kicks are fighting, so cut or filter out."
            )
        return None

    def _beatmatch_recovery_feedback(self, grade) -> dict[str, str] | None:
        """Return a durable mission target for a measured beatmatch miss."""
        verdict = getattr(grade, "verdict", "")
        if verdict == "tempo_off":
            try:
                tempo_error = float(getattr(grade, "tempo_error", 0.0) or 0.0)
            except (TypeError, ValueError):
                tempo_error = 0.0
            detail = ""
            if math.isfinite(tempo_error) and tempo_error > 0:
                detail = f"tempo is {round(tempo_error * 100)}% off"
            return {
                "kind": "beatmatch",
                "label": "tempo miss",
                "message": "Match tempo first; ease deck B's pitch until the drift stops.",
                "detail": detail,
            }
        if verdict in {"drifting", "trainwreck"}:
            try:
                phase_error = float(getattr(grade, "phase_error_beats", 0.0) or 0.0)
            except (TypeError, ValueError):
                phase_error = 0.0
            if not math.isfinite(phase_error):
                phase_error = 0.0
            if verdict == "drifting":
                if phase_error > 0:
                    message = "Deck B is late; nudge it forward before chasing proof."
                elif phase_error < 0:
                    message = "Deck B is early; drag it back before chasing proof."
                else:
                    message = "The phase is drifting; nudge the jog until the kicks lock."
                return {
                    "kind": "beatmatch",
                    "label": "phase drift",
                    "message": message,
                    "detail": f"{abs(phase_error):.2f} beats from lock",
                }
            return {
                "kind": "beatmatch",
                "label": "lost the one",
                "message": "Restart on the downbeat, then lock phase before you blend.",
                "detail": f"{abs(phase_error):.2f} beats from lock",
            }
        return None

    def _emit_live_beatmatch_grade_tick(self) -> None:
        """Emit the Learn-owned beatmatch HUD tick only while the lesson is active."""
        lesson_playing = (
            self._is_beatmatch_practice_audio_lesson()
            and self.current_state.id in _BEATMATCH_PRACTICE_GRADE_STATES
        )
        sandbox_playing = (
            self._learn.current_lesson_id is None
            and self._beatmatch_practice_player_active
        )
        if lesson_playing:
            self._emit_live_beatmatch_grade(self._grade_beatmatch_practice_tick())
            return
        if sandbox_playing:
            self._beatmatch_practice_lock_active = False
            self._emit_live_beatmatch_grade(self._grade_beatmatch_sandbox_tick())
            return
        self._beatmatch_practice_lock_active = False
        self._last_beatmatch_live_grade_verdict = None
        self._last_beatmatch_live_grade_signature = None
        self._last_beatmatch_save_candidate = None
        self._reset_beatmatch_save_attempt()

    def _emit_live_cue_placement_grade(
        self, result: CuePlacementPracticeResult | None
    ) -> None:
        """Voice measured cue-placement feedback without fabricating evidence.

        Beat/drop-locked cues carry the cited ``CUE_PLACEMENT_GRADED`` receipt.
        Misses are still useful coaching because Learn owns the practice grid,
        but they stay uncited and never imply proof was banked.
        """

        if result is None:
            return
        citations: tuple[str, ...] = ()
        if result.event is not None:
            citations = (
                f"[{CUE_PLACEMENT_EVIDENCE_SOURCE}:"
                f"{CUE_PLACEMENT_GRADED_EVENT}@{result.t_session:.3f}]",
            )
            text = "hot cue landed on the drop."
            if result.grade.verdict == "beat_locked":
                text = "hot cue landed on the beat."
        else:
            text = self._cue_placement_miss_text(result.grade)
        if text is None:
            return
        lesson_id = self._learn.current_lesson_id or "learn"
        try:
            speak = LearnTutorSpeak.make(
                text=text,
                tts_marker=f"{lesson_id}.cue_grade",
                citations=citations,
                data_state="hint",
            ).to_dict()
            self._emit_tutor_speak(speak)
        except Exception as exc:  # pragma: no cover - defensive
            import sys

            print(
                f"[learn.runtime] cue placement live grade emit failed: {exc!r}",
                file=sys.stderr,
            )

    def _cue_placement_recovery_feedback(self, grade) -> dict[str, str] | None:
        """Return a durable mission target for a measured cue-placement miss."""
        text = self._cue_placement_miss_text(grade)
        if text is None:
            return None
        verdict = getattr(grade, "verdict", "")
        if verdict == "off_beat":
            beat_error = float(getattr(grade, "beat_error_beats", 0.0) or 0.0)
            if beat_error > 0:
                label = "late cue"
            elif beat_error < 0:
                label = "early cue"
            else:
                label = "off-beat cue"
            detail = f"{abs(beat_error):.2f} beats from the grid"
        elif verdict == "wrong_drop":
            label = "drop timing"
            target_error = getattr(grade, "target_error_beats", None)
            detail = ""
            if target_error is not None:
                try:
                    beats = float(target_error)
                except (TypeError, ValueError):
                    beats = 0.0
                if math.isfinite(beats):
                    distance = max(1, round(abs(beats)))
                    unit = "beat" if distance == 1 else "beats"
                    detail = f"{distance} {unit} from the target drop"
        else:
            return None
        return {
            "kind": "cue_placement",
            "label": label,
            "message": text,
            "detail": detail,
        }

    def _cue_placement_miss_text(self, grade) -> str | None:
        """Return short, measured cue-placement correction copy for misses."""

        verdict = getattr(grade, "verdict", "")
        if verdict == "off_beat":
            beat_error = float(getattr(grade, "beat_error_beats", 0.0) or 0.0)
            if beat_error > 0:
                return "hot cue is late - move it back onto the beat."
            if beat_error < 0:
                return "hot cue is early - wait for the beat before setting it."
            return "hot cue is off the beat - set it on the kick."
        if verdict == "wrong_drop":
            target_error = getattr(grade, "target_error_beats", None)
            if target_error is not None:
                try:
                    beats = float(target_error)
                except (TypeError, ValueError):
                    beats = 0.0
                if math.isfinite(beats):
                    distance = max(1, round(abs(beats)))
                    unit = "beat" if distance == 1 else "beats"
                    if beats > 0:
                        return f"on beat, but {distance} {unit} late - aim at the drop."
                    if beats < 0:
                        return f"on beat, but {distance} {unit} early - wait for the drop."
            return "on beat, but wrong drop - aim for the target phrase."
        return None

    def _grade_cue_placement_practice_tick(self) -> CuePlacementPracticeResult | None:
        """Grade the optional owned-deck cue-placement lane on a lock edge.

        This hook only runs when a lesson driver owns the deck/grid and supplies
        an explicit cue frame. A sustained beat/drop-locked cue credits once; the
        edge re-arms only after the grade stops being creditable.
        """
        if self._cue_placement_practice_loader is None or self._evidence_registry is None:
            return None
        try:
            snapshot = self._cue_placement_practice_loader()
        except Exception as exc:  # pragma: no cover - defensive
            import sys

            print(
                f"[learn.runtime] cue placement practice loader failed: {exc!r}",
                file=sys.stderr,
            )
            return None
        if snapshot is None:
            self._cue_placement_practice_lock_active = False
            return None

        t_session = self._evidence_time()
        grade = grade_owned_cue_placement_state(
            snapshot.grid,
            snapshot.cue_frame,
            target_frame=snapshot.target_frame,
        )
        if not is_creditable_cue_placement_grade(grade):
            self._cue_placement_practice_lock_active = False
            feedback = self._cue_placement_recovery_feedback(grade)
            if feedback is not None and self._mark_progress_practice_feedback(**feedback):
                self._emit_progress_snapshot()
            return CuePlacementPracticeResult(
                grade=grade,
                event=None,
                credited=(),
                t_session=t_session,
            )
        feedback_cleared = self._clear_progress_practice_feedback()
        if self._cue_placement_practice_lock_active:
            if feedback_cleared:
                self._emit_progress_snapshot()
            return CuePlacementPracticeResult(
                grade=grade,
                event=None,
                credited=(),
                t_session=t_session,
            )

        self._cue_placement_practice_lock_active = True
        before_mastered = self._mastered_flags()
        result = grade_owned_cue_placement_attempt(
            snapshot.grid,
            snapshot.cue_frame,
            target_frame=snapshot.target_frame,
            evidence_registry=self._evidence_registry,
            t_session=t_session,
            progress=self._progress,
            now=datetime.now(UTC).isoformat(),
        )
        if result.credited:
            self._emit_mastered_unlocks(
                result.credited,
                before_mastered,
                citations=(
                    f"[{CUE_PLACEMENT_EVIDENCE_SOURCE}:{CUE_PLACEMENT_GRADED_EVENT}@"
                    f"{result.t_session:.3f}]",
                ),
            )
            try:
                from vibemix.learn.progress import LearnProgress, save_progress

                if isinstance(self._progress, LearnProgress):
                    save_progress(self._progress)
            except Exception as exc:  # pragma: no cover - defensive
                import sys

                print(
                    f"[learn.runtime] cue placement practice progress save failed: {exc!r}",
                    file=sys.stderr,
                )
            self._emit_progress_snapshot()
        elif feedback_cleared:
            self._emit_progress_snapshot()
        self._log_session_event(
            "learn_cue_placement_practice_graded",
            lesson_id=self._learn.current_lesson_id or "",
            course_id=self._learn.current_course_id or "",
            step_id=self._current_step_id(),
            evidence_time=t_session,
            verdict=result.grade.verdict,
            credited=list(result.credited),
        )
        return result

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
            # Sibling emit: reform the particle organism back into the mask.
            # The matched action is the real cause — same grounding principle
            # as the focus dissolve. The mascot's reform() ignores the target,
            # but the envelope still carries the just-completed control so the
            # control_id minLength contract holds and review tooling can pair
            # the focus/reform legs.
            expected = self._current_expected_action()
            control = ""
            deck = ""
            if isinstance(expected, dict):
                control, deck = _control_and_deck(expected)
            focus = LearnTeachingFocus.make(
                control_id=control or "lesson",
                deck=deck,
                band=_eq_band_for_control(control),
                phase="reform",
            ).to_dict()
            self._ipc.emit(focus)
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

    def _emit_practice_bank_preface_if_needed(self) -> None:
        """Name banked free-practice reps before the authored lesson line."""
        lesson_id = self._learn.current_lesson_id
        if lesson_id is None:
            return
        lessons = getattr(self._progress, "lessons", {})
        if not isinstance(lessons, dict):
            return
        row = lessons.get(lesson_id)
        if not isinstance(row, dict) or row.get("completed") is True:
            return
        text = _practice_bank_preface_text(row)
        if text is None:
            return
        try:
            speak = LearnTutorSpeak.make(
                text=text,
                tts_marker=f"{lesson_id}.practice_bank",
                citations=(),
                data_state="active",
            ).to_dict()
            self._emit_tutor_speak(speak)
            self._log_session_event(
                "learn_practice_bank_preface",
                lesson_id=lesson_id,
                course_id=self._learn.current_course_id or "",
                practice_bank_count=_practice_bank_total(row),
            )
        except Exception as exc:  # pragma: no cover - defensive
            import sys

            print(
                f"[learn.runtime] practice bank preface emit failed: {exc!r}",
                file=sys.stderr,
            )

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
            self._emit_tutor_speak(speak)
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
            self._emit_tutor_speak(speak)
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
        self._active_harmonic_pair = pair
        try:
            speak = LearnTutorSpeak.make(
                text=build_harmonic_practice_prompt(pair),
                tts_marker="L211.library_pair",
                citations=harmonic_practice_citations(pair, self._evidence_registry),
                data_state="active",
            ).to_dict()
            self._emit_tutor_speak(speak)
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
            self._emit_tutor_speak(speak)
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
            self._emit_tutor_speak(speak)
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
            self._emit_tutor_speak(speak)
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
            self._emit_tutor_speak(speak)
        except Exception as exc:  # pragma: no cover — defensive
            import sys

            print(
                f"[learn.runtime] adaptive mismatch hint emit failed: {exc!r}",
                file=sys.stderr,
            )

    # ------------------------------------------------------------------
    # Fast grade loop + 1 Hz strike escalation timer
    # ------------------------------------------------------------------
    async def live_grade_loop(self, stop_event: asyncio.Event) -> None:
        """Drive Learn-owned beatmatch feedback at a practice-control cadence."""

        while not stop_event.is_set():
            await asyncio.sleep(0.15)
            self._emit_playhead_tick()
            self._emit_live_beatmatch_grade_tick()

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
            self._grade_cue_placement_practice_tick()
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
