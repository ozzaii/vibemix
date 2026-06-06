# SPDX-License-Identifier: Apache-2.0
"""ipc.learn.* envelope dataclasses (Phase 91 + Phase 92).

Phase 91 (2 envelopes):
  - LearnControllerDetected (sidecar→shell, single-fire per plug)
  - LearnMidiPosition       (sidecar→shell, 30 Hz delta-suppressed)

Phase 92 (11 envelopes — lesson runtime + AI highlight contract):
  - LearnStartCourse        (shell→sidecar)
  - LearnStartLesson        (shell→sidecar)
  - LearnCompleteLesson     (bidirectional)
  - LearnLessonLoaded       (sidecar→shell)
  - LearnHighlight          (sidecar→shell — dual-channel cue paint)
  - LearnAdvance            (bidirectional)
  - LearnAck                (shell→sidecar)
  - LearnTutorSpeak         (sidecar→shell — narration; text from fixture)
  - LearnLiveGrade          (sidecar→shell — beatmatch grade HUD signal)
  - LearnWaveformReady      (sidecar→shell — compact practice waveform peaks)
  - LearnPlayheadTick       (sidecar→shell — owned-deck playhead/BPM tick)
  - LearnExemplarPlay       (sidecar→shell — shape only; engine in P93)
  - LearnExemplarStop       (sidecar→shell — shape only)
  - LearnProgressState      (bidirectional — snapshot/reset/reset_ack)

Mirrors of the corresponding entries in ``messages.schema.json``.
Validation by the shared ``_VALIDATOR`` already loaded in
:mod:`vibemix.ui_bus.messages` — we re-use, not re-instantiate (Draft-07
ref-resolver is cached internally; compiling twice would double the
import cost for zero gain).

Convention parity with :mod:`vibemix.ui_bus.messages`:

* ``@dataclass(frozen=True, slots=True)`` everywhere (hashable wrappers,
  no per-instance ``__dict__``). For payload fields that the JSON Schema
  declares as arrays-of-objects, we use ``tuple[<NestedDataclass>, ...]``
  so the wrapper stays hashable while ``_serialize`` (via ``asdict`` +
  ``_tuples_to_lists``) round-trips it back to a JSON array.
* Each top-level envelope has a ``.make(*, ...)`` keyword-only factory
  that stamps ``ts`` via :func:`vibemix.ui_bus.messages._now_iso`.
* ``.to_json()`` delegates to :func:`vibemix.ui_bus.messages._serialize`
  which asdict's, tuple→list normalises, validates against the shared
  schema, and json-dumps with compact separators (the wire form).
* ``.to_dict()`` is the convenience round-trip used by ipc_bus emitters
  that prefer a plain dict over a JSON string (matches the
  ``SessionOverlayHighlight.to_dict()`` pattern in messages.py).

REQ-IDs: Phase 91 — RENDER-01 / RENDER-02 / RENDER-07; Phase 92 —
TONE-02 / TONE-04 / LESSON-01..LESSON-06 / RENDER-04.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Literal

from vibemix.ui_bus.messages import _now_iso, _serialize, _tuples_to_lists, _validate

# ---------------------------------------------------------------------------
# Payload structs
# ---------------------------------------------------------------------------


def _optional_text(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None


def _optional_float(value: object) -> float | None:
    try:
        out = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return out


@dataclass(frozen=True, slots=True)
class LearnControllerDetectedPayload:
    """Payload of ``ipc.learn.controller_detected``.

    Single-fire per MIDI port-bind / unbind event. ``connected=True`` is the
    bind path; ``connected=False`` carries the same identification fields so
    the webview can clean up the rendered controller in place.
    """

    connected: bool
    controller_id: str
    display_name: str
    port_name: str


@dataclass(frozen=True, slots=True)
class LearnMidiPositionPayload:
    """Payload of ``ipc.learn.midi_position``.

    30 Hz delta-suppressed snapshot of every tracked physical control on the
    currently-bound controller. Keys in ``positions`` follow ``<field>:<deck>``
    (deck-bound) or bare ``<field>`` (master-section) convention; values are
    integer MIDI CC ticks in the 0..127 range.

    The schema enforces ``additionalProperties: {type: integer, minimum: 0,
    maximum: 127}`` so an out-of-range payload (e.g. 128) is rejected by the
    shared validator at serialize time.
    """

    controller_id: str
    # dict[str, int] — schema uses additionalProperties: {type: integer,
    # minimum: 0, maximum: 127} to express "any field key → MIDI int".
    # asdict serialises as-is.
    positions: dict[str, int]


# ---------------------------------------------------------------------------
# Envelope wrappers
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LearnControllerDetected:
    """``ipc.learn.controller_detected`` envelope wrapper."""

    type: Literal["ipc.learn.controller_detected"]
    ts: str
    payload: LearnControllerDetectedPayload

    @classmethod
    def make(
        cls,
        *,
        connected: bool,
        controller_id: str,
        display_name: str,
        port_name: str,
    ) -> LearnControllerDetected:
        return cls(
            type="ipc.learn.controller_detected",
            ts=_now_iso(),
            payload=LearnControllerDetectedPayload(
                connected=connected,
                controller_id=controller_id,
                display_name=display_name,
                port_name=port_name,
            ),
        )

    def to_json(self) -> str:
        return _serialize(self)

    def to_dict(self) -> dict:
        """Convenience: serialize + reparse to a plain dict for ipc_bus.emit
        callers that prefer not to JSON-roundtrip themselves. Mirrors the
        :meth:`SessionOverlayHighlight.to_dict` pattern in messages.py."""
        return json.loads(self.to_json())


@dataclass(frozen=True, slots=True)
class LearnMidiPosition:
    """``ipc.learn.midi_position`` envelope wrapper."""

    type: Literal["ipc.learn.midi_position"]
    ts: str
    payload: LearnMidiPositionPayload

    @classmethod
    def make(
        cls,
        *,
        controller_id: str,
        positions: dict[str, int],
    ) -> LearnMidiPosition:
        return cls(
            type="ipc.learn.midi_position",
            ts=_now_iso(),
            payload=LearnMidiPositionPayload(
                controller_id=controller_id,
                positions=positions,
            ),
        )

    def to_json(self) -> str:
        return _serialize(self)

    def to_dict(self) -> dict:
        """Convenience: serialize + reparse to a plain dict for ipc_bus.emit
        callers that prefer not to JSON-roundtrip themselves."""
        return json.loads(self.to_json())


# ---------------------------------------------------------------------------
# Phase 92 — 11 lesson-runtime envelopes
# ---------------------------------------------------------------------------


# -- ipc.learn.start_course -------------------------------------------------


@dataclass(frozen=True, slots=True)
class LearnStartCoursePayload:
    """Payload of ``ipc.learn.start_course``. User picked a course in the HUD."""

    course_id: Literal["course_0", "course_1", "course_2", "course_3"]
    controller_id: str


@dataclass(frozen=True, slots=True)
class LearnStartCourse:
    """``ipc.learn.start_course`` envelope wrapper (shell → sidecar)."""

    type: Literal["ipc.learn.start_course"]
    ts: str
    payload: LearnStartCoursePayload

    @classmethod
    def make(
        cls,
        *,
        course_id: str,
        controller_id: str,
    ) -> LearnStartCourse:
        return cls(
            type="ipc.learn.start_course",
            ts=_now_iso(),
            payload=LearnStartCoursePayload(
                course_id=course_id,  # type: ignore[arg-type]
                controller_id=controller_id,
            ),
        )

    def to_json(self) -> str:
        return _serialize(self)

    def to_dict(self) -> dict:
        return json.loads(self.to_json())


# -- ipc.learn.start_lesson -------------------------------------------------


@dataclass(frozen=True, slots=True)
class LearnStartLessonPayload:
    """Payload of ``ipc.learn.start_lesson``. User skipped into a specific lesson.

    ``level="fresh"`` loads a clean slate; ``"replay"`` starts the lesson at
    completed-but-revisit mode (skip-button immediate availability).
    """

    lesson_id: str  # pattern ^L[0-9]+\.[0-9]+-.+$
    level: Literal["fresh", "replay"]


@dataclass(frozen=True, slots=True)
class LearnStartLesson:
    """``ipc.learn.start_lesson`` envelope wrapper (shell → sidecar)."""

    type: Literal["ipc.learn.start_lesson"]
    ts: str
    payload: LearnStartLessonPayload

    @classmethod
    def make(
        cls,
        *,
        lesson_id: str,
        level: str,
    ) -> LearnStartLesson:
        return cls(
            type="ipc.learn.start_lesson",
            ts=_now_iso(),
            payload=LearnStartLessonPayload(
                lesson_id=lesson_id,
                level=level,  # type: ignore[arg-type]
            ),
        )

    def to_json(self) -> str:
        return _serialize(self)

    def to_dict(self) -> dict:
        return json.loads(self.to_json())


# -- ipc.learn.complete_lesson ----------------------------------------------


@dataclass(frozen=True, slots=True)
class LearnCompleteLessonPayload:
    """Payload of ``ipc.learn.complete_lesson``. Bidirectional: shell emits
    on user-skip; sidecar emits on system-advance."""

    lesson_id: str  # pattern ^L[0-9]+\.[0-9]+-.+$
    reason: Literal["completed", "user_skip"]


@dataclass(frozen=True, slots=True)
class LearnCompleteLesson:
    """``ipc.learn.complete_lesson`` envelope wrapper (bidirectional)."""

    type: Literal["ipc.learn.complete_lesson"]
    ts: str
    payload: LearnCompleteLessonPayload

    @classmethod
    def make(
        cls,
        *,
        lesson_id: str,
        reason: str,
    ) -> LearnCompleteLesson:
        return cls(
            type="ipc.learn.complete_lesson",
            ts=_now_iso(),
            payload=LearnCompleteLessonPayload(
                lesson_id=lesson_id,
                reason=reason,  # type: ignore[arg-type]
            ),
        )

    def to_json(self) -> str:
        return _serialize(self)

    def to_dict(self) -> dict:
        return json.loads(self.to_json())


# -- ipc.learn.lesson_loaded ------------------------------------------------


@dataclass(frozen=True, slots=True)
class LearnProgressDot:
    """Single HUD progress-dot entry. Mirrors the schema's
    ``LearnLessonLoaded.payload.progress_dots[].properties`` shape."""

    lesson_id: str
    status: Literal["pending", "current", "completed"]


@dataclass(frozen=True, slots=True)
class LearnLessonLoadedPayload:
    """Payload of ``ipc.learn.lesson_loaded``. Sidecar emits when a lesson
    starts loading; carries HUD metadata + per-lesson progress dots
    (maxItems 32 enforced schema-side)."""

    course_id: str
    lesson_id: str
    title: str  # ≤80 chars
    controller_id: str
    progress_dots: tuple[LearnProgressDot, ...]


@dataclass(frozen=True, slots=True)
class LearnLessonLoaded:
    """``ipc.learn.lesson_loaded`` envelope wrapper (sidecar → shell)."""

    type: Literal["ipc.learn.lesson_loaded"]
    ts: str
    payload: LearnLessonLoadedPayload

    @classmethod
    def make(
        cls,
        *,
        course_id: str,
        lesson_id: str,
        title: str,
        controller_id: str,
        progress_dots: tuple[LearnProgressDot, ...] | list[dict] | tuple[dict, ...],
    ) -> LearnLessonLoaded:
        # Accept either pre-built LearnProgressDot tuples OR raw dicts (the
        # JSON-fixture-loaded path); normalise to a tuple of LearnProgressDot.
        dots: tuple[LearnProgressDot, ...]
        if progress_dots and isinstance(progress_dots[0], dict):  # type: ignore[index]
            dots = tuple(
                LearnProgressDot(
                    lesson_id=d["lesson_id"],
                    status=d["status"],  # type: ignore[arg-type]
                )
                for d in progress_dots  # type: ignore[union-attr]
            )
        else:
            dots = tuple(progress_dots)  # type: ignore[arg-type]
        return cls(
            type="ipc.learn.lesson_loaded",
            ts=_now_iso(),
            payload=LearnLessonLoadedPayload(
                course_id=course_id,
                lesson_id=lesson_id,
                title=title,
                controller_id=controller_id,
                progress_dots=dots,
            ),
        )

    def to_json(self) -> str:
        return _serialize(self)

    def to_dict(self) -> dict:
        return json.loads(self.to_json())


# -- ipc.learn.highlight ----------------------------------------------------


@dataclass(frozen=True, slots=True)
class LearnExpectedAction:
    """Nested ``expected_action`` object inside ``LearnHighlight.payload``.

    The schema marks ``deck`` / ``direction`` / ``min_delta`` as optional;
    we model defaults so the dataclass stays ergonomic while ``_serialize``
    drops nothing (the schema's ``additionalProperties: false`` would reject
    spurious keys, so we ALWAYS emit all four — empty-string sentinels are
    the schema-allowed "absent" value for the enum fields)."""

    type: Literal["cc", "button"]
    control: str
    deck: Literal["", "A", "B", "C", "D"] = ""
    # WR-05 (P92 REVIEW) convention — the empty-string sentinel is the
    # documented "no direction" value for CC controls. The TS-generated
    # type, the Python dataclass, and the JSON Schema (enum
    # ["", "up", "down"]) all agree on this convention. CC payloads
    # carry direction="" not because direction data is missing but
    # because the field is meaningless for a CC delta-match check
    # (the runtime's action_matches predicate ignores direction when
    # expected_type == "cc"). Do NOT change to Optional — every wire
    # frame carries the field explicitly to satisfy
    # additionalProperties: false.
    direction: Literal["", "up", "down"] = ""
    min_delta: int = 0  # 0..127; 0 means "no minimum delta requirement"


@dataclass(frozen=True, slots=True)
class LearnHighlightPayload:
    """Payload of ``ipc.learn.highlight``. Dual-channel cue (color + shape)
    for color-blind a11y; ≤16 ms paint budget pinned by
    ``tauri/ui/tests/learn/highlight-paint.test.ts``."""

    control_id: str
    deck: Literal["", "A", "B", "C", "D"]
    cue_color: Literal["amber", "warning"]
    cue_shape: Literal["pulse-ring", "static-glow"]
    annotation: str  # ≤200 chars
    expected_action: LearnExpectedAction


@dataclass(frozen=True, slots=True)
class LearnHighlight:
    """``ipc.learn.highlight`` envelope wrapper (sidecar → shell)."""

    type: Literal["ipc.learn.highlight"]
    ts: str
    payload: LearnHighlightPayload

    @classmethod
    def make(
        cls,
        *,
        control_id: str,
        deck: str,
        cue_color: str,
        cue_shape: str,
        annotation: str = "",
        expected_action: LearnExpectedAction | dict,
    ) -> LearnHighlight:
        # Accept dataclass OR raw dict (the JSON-fixture-loaded path).
        ea: LearnExpectedAction
        if isinstance(expected_action, dict):
            ea = LearnExpectedAction(
                type=expected_action["type"],  # type: ignore[arg-type]
                control=expected_action["control"],
                deck=expected_action.get("deck", ""),  # type: ignore[arg-type]
                direction=expected_action.get("direction", ""),  # type: ignore[arg-type]
                min_delta=int(expected_action.get("min_delta", 0)),
            )
        else:
            ea = expected_action
        return cls(
            type="ipc.learn.highlight",
            ts=_now_iso(),
            payload=LearnHighlightPayload(
                control_id=control_id,
                deck=deck,  # type: ignore[arg-type]
                cue_color=cue_color,  # type: ignore[arg-type]
                cue_shape=cue_shape,  # type: ignore[arg-type]
                annotation=annotation,
                expected_action=ea,
            ),
        )

    def to_json(self) -> str:
        return _serialize(self)

    def to_dict(self) -> dict:
        return json.loads(self.to_json())


# -- ipc.learn.advance ------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LearnAdvancePayload:
    """Payload of ``ipc.learn.advance``. Bidirectional: shell emits on
    user-initiated skip; sidecar emits on MIDI-matched advance."""

    lesson_id: str
    reason: Literal["action_matched", "user_skip"]


@dataclass(frozen=True, slots=True)
class LearnAdvance:
    """``ipc.learn.advance`` envelope wrapper (bidirectional)."""

    type: Literal["ipc.learn.advance"]
    ts: str
    payload: LearnAdvancePayload

    @classmethod
    def make(
        cls,
        *,
        lesson_id: str,
        reason: str,
    ) -> LearnAdvance:
        return cls(
            type="ipc.learn.advance",
            ts=_now_iso(),
            payload=LearnAdvancePayload(
                lesson_id=lesson_id,
                reason=reason,  # type: ignore[arg-type]
            ),
        )

    def to_json(self) -> str:
        return _serialize(self)

    def to_dict(self) -> dict:
        return json.loads(self.to_json())


# -- ipc.learn.teaching_focus -----------------------------------------------


@dataclass(frozen=True, slots=True)
class LearnTeachingFocusPayload:
    """Payload of ``ipc.learn.teaching_focus``.

    Sibling of :class:`LearnHighlight` that drives the particle-organism
    focus mechanic — NOT an overload of the highlight (which carries a
    16ms SVG paint budget). ``phase="focus"`` dissolves + streams the
    organism to the named control; ``phase="reform"`` pulls it home on
    advance. ``band`` carries the EQ band (``"low"``/``"mid"``/``"hi"``) or
    ``None`` for non-EQ controls. The organism animates ONLY on a real
    teaching-focus event — visual grounding, the anti-slop contract.
    """

    control_id: str
    deck: Literal["", "A", "B", "C", "D"]
    band: Literal["low", "mid", "hi"] | None
    phase: Literal["focus", "reform"]


@dataclass(frozen=True, slots=True)
class LearnTeachingFocus:
    """``ipc.learn.teaching_focus`` envelope wrapper (sidecar → shell)."""

    type: Literal["ipc.learn.teaching_focus"]
    ts: str
    payload: LearnTeachingFocusPayload

    @classmethod
    def make(
        cls,
        *,
        control_id: str,
        deck: str,
        band: str | None,
        phase: str,
    ) -> LearnTeachingFocus:
        return cls(
            type="ipc.learn.teaching_focus",
            ts=_now_iso(),
            payload=LearnTeachingFocusPayload(
                control_id=control_id,
                deck=deck,  # type: ignore[arg-type]
                band=band,  # type: ignore[arg-type]
                phase=phase,  # type: ignore[arg-type]
            ),
        )

    def to_json(self) -> str:
        return _serialize(self)

    def to_dict(self) -> dict:
        return json.loads(self.to_json())


# -- ipc.learn.control_rect -------------------------------------------------


@dataclass(frozen=True, slots=True)
class LearnControlRectPayload:
    """Payload of ``ipc.learn.control_rect``.

    Learn window → mascot window. Screen-space center of a highlighted
    control's ``getBoundingClientRect``, relayed over the ws bus so the
    separate mascot webview can convert screen→world and aim the focus
    stream. Stored in the mascot's ``controlRectRegistry`` keyed
    ``control_id:deck``.
    """

    control_id: str
    deck: Literal["", "A", "B", "C", "D"]
    cx: float
    cy: float


@dataclass(frozen=True, slots=True)
class LearnControlRect:
    """``ipc.learn.control_rect`` envelope wrapper (learn window → mascot)."""

    type: Literal["ipc.learn.control_rect"]
    ts: str
    payload: LearnControlRectPayload

    @classmethod
    def make(
        cls,
        *,
        control_id: str,
        deck: str,
        cx: float,
        cy: float,
    ) -> LearnControlRect:
        return cls(
            type="ipc.learn.control_rect",
            ts=_now_iso(),
            payload=LearnControlRectPayload(
                control_id=control_id,
                deck=deck,  # type: ignore[arg-type]
                cx=float(cx),
                cy=float(cy),
            ),
        )

    def to_json(self) -> str:
        return _serialize(self)

    def to_dict(self) -> dict:
        return json.loads(self.to_json())


# -- ipc.learn.ack ----------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LearnAckPayload:
    """Payload of ``ipc.learn.ack``. User touched a physical control (source
    = "midi") or clicked a control in the rendered SVG (source = "click").
    ``value`` is the MIDI CC value 0..127; ``direction`` distinguishes
    encoder turns when relevant."""

    control_id: str
    source: Literal["midi", "click"]
    # Schema marks these optional; we keep dataclass-side defaults so call
    # sites stay ergonomic. The schema's additionalProperties: false ensures
    # only declared fields land on the wire.
    value: int = 0
    prev_value: int = 0
    direction: Literal["", "up", "down"] = ""


@dataclass(frozen=True, slots=True)
class LearnAck:
    """``ipc.learn.ack`` envelope wrapper (shell → sidecar)."""

    type: Literal["ipc.learn.ack"]
    ts: str
    payload: LearnAckPayload

    @classmethod
    def make(
        cls,
        *,
        control_id: str,
        source: str,
        value: int = 0,
        prev_value: int = 0,
        direction: str = "",
    ) -> LearnAck:
        return cls(
            type="ipc.learn.ack",
            ts=_now_iso(),
            payload=LearnAckPayload(
                control_id=control_id,
                source=source,  # type: ignore[arg-type]
                value=int(value),
                prev_value=int(prev_value),
                direction=direction,  # type: ignore[arg-type]
            ),
        )

    def to_json(self) -> str:
        return _serialize(self)

    def to_dict(self) -> dict:
        return json.loads(self.to_json())


# -- ipc.learn.tutor_speak --------------------------------------------------


@dataclass(frozen=True, slots=True)
class LearnTutorSpeakPayload:
    """Payload of ``ipc.learn.tutor_speak``. Narration from the AI tutor.

    The ``text`` ALWAYS comes from a JSON fixture (anti-slop invariant —
    NEVER LLM-generated at runtime). ``citations[]`` is empty in P92;
    P93+ populates with ``[exemplar:<id>]`` entries; P96+ may add
    ``[cue:<anchor_id>]``. Schema regex already pre-allows both sources.
    """

    text: str  # 1..280 chars
    tts_marker: str  # 1..64 chars
    # tuple of citation tokens, each matching ^\[(track|exemplar|cue|ev|
    # aud|midi|screen|mix|key|recall):.+\]$ — maxItems 4 schema-side.
    citations: tuple[str, ...]
    data_state: Literal["active", "hint"]
    teaching_loop: LearnTeachingLoopPayload | None = None


@dataclass(frozen=True, slots=True)
class LearnTeachingObservationPayload:
    """Socket-visible observation record for one backstage teaching turn."""

    lesson_id: str
    step_id: str
    kind: str
    control_id: str
    input_surfaces: tuple[str, ...]
    backstage_lenses: tuple[str, ...]
    strikes_used: int


@dataclass(frozen=True, slots=True)
class LearnTeachingVerificationPayload:
    """Socket-visible deterministic verification record for a teaching turn."""

    kind: Literal["button_press", "cc_delta"]
    control: str
    deck: str
    observable_control_ids: tuple[str, ...]
    input_surfaces: tuple[str, ...]
    direction: Literal["", "up", "down"]
    min_delta: int


@dataclass(frozen=True, slots=True)
class LearnTeachingLoopPayload:
    """Optional backstage loop metadata carried beside tutor text.

    The Learn frontstage ignores this by default. It gives proof tooling and
    future dev surfaces a citable observe -> decide -> teach -> verify -> adapt
    record without adding copy to the learner's booth.
    """

    stages: tuple[str, ...]
    turn_kind: Literal["teach", "hint", "adapt"]
    route_path: str
    observation: LearnTeachingObservationPayload
    verification: LearnTeachingVerificationPayload


@dataclass(frozen=True, slots=True)
class LearnTutorSpeak:
    """``ipc.learn.tutor_speak`` envelope wrapper (sidecar → shell)."""

    type: Literal["ipc.learn.tutor_speak"]
    ts: str
    payload: LearnTutorSpeakPayload

    @classmethod
    def make(
        cls,
        *,
        text: str,
        tts_marker: str,
        citations: tuple[str, ...] | list[str] = (),
        data_state: str = "active",
        teaching_loop: LearnTeachingLoopPayload | None = None,
    ) -> LearnTutorSpeak:
        return cls(
            type="ipc.learn.tutor_speak",
            ts=_now_iso(),
            payload=LearnTutorSpeakPayload(
                text=text,
                tts_marker=tts_marker,
                citations=tuple(citations),
                data_state=data_state,  # type: ignore[arg-type]
                teaching_loop=teaching_loop,
            ),
        )

    def to_json(self) -> str:
        d = _tuples_to_lists(asdict(self))
        if d["payload"].get("teaching_loop") is None:
            d["payload"].pop("teaching_loop", None)
        _validate(d)
        return json.dumps(d, separators=(",", ":"))

    def to_dict(self) -> dict:
        return json.loads(self.to_json())


# -- ipc.learn.live_grade ---------------------------------------------------


@dataclass(frozen=True, slots=True)
class LearnLiveGradePayload:
    """Payload of ``ipc.learn.live_grade``. Deterministic beatmatch HUD tick."""

    verdict: Literal["locked", "drifting", "tempo_off", "trainwreck", "abstain"]
    phase_error_beats: float
    score: float
    citation: str | None
    save_landed: bool = False
    save_from_verdict: Literal["drifting", "trainwreck"] | None = None
    save_from_phase_error_beats: float | None = None
    save_recovery_delta_beats: float | None = None
    save_attempt_active: bool = False
    save_floor_seconds_total: float | None = None
    save_floor_seconds_remaining: float | None = None
    save_floor_expired: bool = False
    save_difficulty_level: int = 1
    save_streak: int = 0
    practice_source: Literal["bundled_demo", "library_save_mode"] | None = None
    deck_a_track_id: str | None = None
    deck_b_track_id: str | None = None
    deck_a_title: str | None = None
    deck_b_title: str | None = None


@dataclass(frozen=True, slots=True)
class LearnLiveGrade:
    """``ipc.learn.live_grade`` envelope wrapper (sidecar → shell)."""

    type: Literal["ipc.learn.live_grade"]
    ts: str
    payload: LearnLiveGradePayload

    @classmethod
    def make(
        cls,
        *,
        verdict: str,
        phase_error_beats: float,
        score: float,
        citation: str | None = None,
        save_landed: bool = False,
        save_from_verdict: str | None = None,
        save_from_phase_error_beats: float | None = None,
        save_recovery_delta_beats: float | None = None,
        save_attempt_active: bool = False,
        save_floor_seconds_total: float | None = None,
        save_floor_seconds_remaining: float | None = None,
        save_floor_expired: bool = False,
        save_difficulty_level: int = 1,
        save_streak: int = 0,
        practice_source: str | None = None,
        deck_a_track_id: str | None = None,
        deck_b_track_id: str | None = None,
        deck_a_title: str | None = None,
        deck_b_title: str | None = None,
    ) -> LearnLiveGrade:
        return cls(
            type="ipc.learn.live_grade",
            ts=_now_iso(),
            payload=LearnLiveGradePayload(
                verdict=verdict,  # type: ignore[arg-type]
                phase_error_beats=float(phase_error_beats),
                score=float(score),
                citation=citation,
                save_landed=bool(save_landed),
                save_from_verdict=save_from_verdict,  # type: ignore[arg-type]
                save_from_phase_error_beats=save_from_phase_error_beats,
                save_recovery_delta_beats=save_recovery_delta_beats,
                save_attempt_active=bool(save_attempt_active),
                save_floor_seconds_total=save_floor_seconds_total,
                save_floor_seconds_remaining=save_floor_seconds_remaining,
                save_floor_expired=bool(save_floor_expired),
                save_difficulty_level=max(1, min(5, int(save_difficulty_level))),
                save_streak=max(0, int(save_streak)),
                practice_source=practice_source,  # type: ignore[arg-type]
                deck_a_track_id=_optional_text(deck_a_track_id),
                deck_b_track_id=_optional_text(deck_b_track_id),
                deck_a_title=_optional_text(deck_a_title),
                deck_b_title=_optional_text(deck_b_title),
            ),
        )

    def to_json(self) -> str:
        d = _tuples_to_lists(asdict(self))
        payload = d["payload"]
        for key in (
            "practice_source",
            "deck_a_track_id",
            "deck_b_track_id",
            "deck_a_title",
            "deck_b_title",
        ):
            if payload.get(key) is None:
                payload.pop(key, None)
        _validate(d)
        return json.dumps(d, separators=(",", ":"))

    def to_dict(self) -> dict:
        return json.loads(self.to_json())


# -- ipc.learn.waveform_ready / ipc.learn.playhead_tick -----------------------


@dataclass(frozen=True, slots=True)
class LearnWaveformDeckCue:
    label: str
    start_s: float
    end_s: float


@dataclass(frozen=True, slots=True)
class LearnWaveformDeck:
    bpm: float
    duration_s: float
    peaks: tuple[tuple[int, int, int], ...]
    cues: tuple[LearnWaveformDeckCue, ...]
    track_id: str | None = None
    title: str | None = None
    artist: str | None = None
    source: Literal["bundled_demo", "library_save_mode"] | None = None
    source_start_s: float | None = None
    source_reason: str | None = None


@dataclass(frozen=True, slots=True)
class LearnWaveformReadyPayload:
    sample_rate: int
    beat_interval_s: float
    decks: dict[str, LearnWaveformDeck]


@dataclass(frozen=True, slots=True)
class LearnWaveformReady:
    """``ipc.learn.waveform_ready`` envelope wrapper (sidecar → shell)."""

    type: Literal["ipc.learn.waveform_ready"]
    ts: str
    payload: LearnWaveformReadyPayload

    @classmethod
    def make(
        cls,
        *,
        sample_rate: int,
        beat_interval_s: float,
        decks: dict[str, dict],
    ) -> LearnWaveformReady:
        return cls(
            type="ipc.learn.waveform_ready",
            ts=_now_iso(),
            payload=LearnWaveformReadyPayload(
                sample_rate=int(sample_rate),
                beat_interval_s=float(beat_interval_s),
                decks={
                    side: LearnWaveformDeck(
                        bpm=float(row.get("bpm", 0.0)),
                        duration_s=float(row.get("duration_s", 0.0)),
                        peaks=tuple(
                            tuple(int(v) for v in peak[:3])  # type: ignore[index]
                            for peak in row.get("peaks", ())
                        ),
                        cues=tuple(
                            LearnWaveformDeckCue(
                                label=str(cue.get("label", "")),
                                start_s=float(cue.get("start_s", 0.0)),
                                end_s=float(cue.get("end_s", 0.0)),
                            )
                            for cue in row.get("cues", ())
                            if isinstance(cue, dict)
                        ),
                        track_id=_optional_text(row.get("track_id")),
                        title=_optional_text(row.get("title")),
                        artist=_optional_text(row.get("artist")),
                        source=row.get("source"),  # type: ignore[arg-type]
                        source_start_s=_optional_float(row.get("source_start_s")),
                        source_reason=_optional_text(row.get("source_reason")),
                    )
                    for side, row in decks.items()
                    if isinstance(row, dict)
                },
            ),
        )

    def to_json(self) -> str:
        d = _tuples_to_lists(asdict(self))
        for deck in d["payload"].get("decks", {}).values():
            if not isinstance(deck, dict):
                continue
            for key in (
                "track_id",
                "title",
                "artist",
                "source",
                "source_start_s",
                "source_reason",
            ):
                if deck.get(key) is None:
                    deck.pop(key, None)
        _validate(d)
        return json.dumps(d, separators=(",", ":"))

    def to_dict(self) -> dict:
        return json.loads(self.to_json())


@dataclass(frozen=True, slots=True)
class LearnPlayheadDeck:
    frame: float
    position_s: float
    bpm: float


@dataclass(frozen=True, slots=True)
class LearnPlayheadTickPayload:
    sample_rate: int
    decks: dict[str, LearnPlayheadDeck]


@dataclass(frozen=True, slots=True)
class LearnPlayheadTick:
    """``ipc.learn.playhead_tick`` envelope wrapper (sidecar → shell)."""

    type: Literal["ipc.learn.playhead_tick"]
    ts: str
    payload: LearnPlayheadTickPayload

    @classmethod
    def make(cls, *, sample_rate: int, decks: dict[str, dict]) -> LearnPlayheadTick:
        return cls(
            type="ipc.learn.playhead_tick",
            ts=_now_iso(),
            payload=LearnPlayheadTickPayload(
                sample_rate=int(sample_rate),
                decks={
                    side: LearnPlayheadDeck(
                        frame=float(row.get("frame", 0.0)),
                        position_s=float(row.get("position_s", 0.0)),
                        bpm=float(row.get("bpm", 0.0)),
                    )
                    for side, row in decks.items()
                    if isinstance(row, dict)
                },
            ),
        )

    def to_json(self) -> str:
        return _serialize(self)

    def to_dict(self) -> dict:
        return json.loads(self.to_json())


# -- ipc.learn.exemplar_play ------------------------------------------------


@dataclass(frozen=True, slots=True)
class LearnExemplarPlayPayload:
    """Payload of ``ipc.learn.exemplar_play``. SHAPE ONLY in P92 — the audio
    engine that actually plays the exemplar ships in P93."""

    track_id: str
    duration_s: float  # 0..300
    gain_db: float  # -24..0
    source: Literal["library", "packaged"] | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class LearnExemplarPlay:
    """``ipc.learn.exemplar_play`` envelope wrapper (sidecar → shell)."""

    type: Literal["ipc.learn.exemplar_play"]
    ts: str
    payload: LearnExemplarPlayPayload

    @classmethod
    def make(
        cls,
        *,
        track_id: str,
        duration_s: float,
        gain_db: float,
        source: Literal["library", "packaged"] | None = None,
        reason: str | None = None,
    ) -> LearnExemplarPlay:
        return cls(
            type="ipc.learn.exemplar_play",
            ts=_now_iso(),
            payload=LearnExemplarPlayPayload(
                track_id=track_id,
                duration_s=float(duration_s),
                gain_db=float(gain_db),
                source=source,
                reason=reason,
            ),
        )

    def to_json(self) -> str:
        return _serialize(self)

    def to_dict(self) -> dict:
        return json.loads(self.to_json())


# -- ipc.learn.exemplar_stop ------------------------------------------------


@dataclass(frozen=True, slots=True)
class LearnExemplarStopPayload:
    """Payload of ``ipc.learn.exemplar_stop``. SHAPE ONLY in P92."""

    track_id: str
    reason: Literal["completed", "interrupted"]


@dataclass(frozen=True, slots=True)
class LearnExemplarStop:
    """``ipc.learn.exemplar_stop`` envelope wrapper (sidecar → shell)."""

    type: Literal["ipc.learn.exemplar_stop"]
    ts: str
    payload: LearnExemplarStopPayload

    @classmethod
    def make(
        cls,
        *,
        track_id: str,
        reason: str,
    ) -> LearnExemplarStop:
        return cls(
            type="ipc.learn.exemplar_stop",
            ts=_now_iso(),
            payload=LearnExemplarStopPayload(
                track_id=track_id,
                reason=reason,  # type: ignore[arg-type]
            ),
        )

    def to_json(self) -> str:
        return _serialize(self)

    def to_dict(self) -> dict:
        return json.loads(self.to_json())


# -- ipc.learn.progress_state -----------------------------------------------


@dataclass(frozen=True, slots=True)
class LearnProgressStatePayload:
    """Payload of ``ipc.learn.progress_state``.

    Tri-mode envelope:
      * ``action="snapshot"`` — sidecar pushes the current persisted state.
      * ``action="reset"``    — shell requests a wipe (settings drawer button).
      * ``action="reset_ack"`` — sidecar confirms wipe complete.

    ``progress`` carries the schema-versioned payload; we model it as a plain
    dict because the schema permits arbitrary string keys under both
    ``courses`` and ``lessons`` (course_id / lesson_id are the dict keys,
    not enum-bounded fields). Schema-side ``additionalProperties: false``
    on the inner objects ensures only declared per-row fields land on the
    wire. ``was_recovered`` flags a corruption-recovery snapshot (the file
    was nuked + re-emit-empty).
    """

    action: Literal["snapshot", "reset", "reset_ack"]
    # Optional fields — defaults keep the dataclass ergonomic; the schema
    # allows them to be absent. We always emit ``was_recovered`` (default
    # False) but only emit ``progress`` when it is materially present.
    was_recovered: bool = False
    progress: dict | None = None


@dataclass(frozen=True, slots=True)
class LearnProgressState:
    """``ipc.learn.progress_state`` envelope wrapper (bidirectional)."""

    type: Literal["ipc.learn.progress_state"]
    ts: str
    payload: LearnProgressStatePayload

    @classmethod
    def make(
        cls,
        *,
        action: str,
        was_recovered: bool = False,
        progress: dict | None = None,
    ) -> LearnProgressState:
        return cls(
            type="ipc.learn.progress_state",
            ts=_now_iso(),
            payload=LearnProgressStatePayload(
                action=action,  # type: ignore[arg-type]
                was_recovered=bool(was_recovered),
                progress=progress,
            ),
        )

    def to_json(self) -> str:
        # The schema marks ``progress`` as optional and only allows
        # ``type: "object"`` (no null union); reset / reset_ack envelopes
        # omit ``progress`` entirely. We strip ``progress`` from the wire
        # payload when it is None — mirrors the SessionMute.to_json
        # pattern in messages.py (file:line src/vibemix/ui_bus/
        # messages.py:864-870) that drops None payload fields before
        # validating.
        from dataclasses import asdict

        from vibemix.ui_bus.messages import _tuples_to_lists, _validate

        d = _tuples_to_lists(asdict(self))
        d["payload"] = {k: v for k, v in d["payload"].items() if v is not None}
        _validate(d)
        return json.dumps(d, separators=(",", ":"))

    def to_dict(self) -> dict:
        return json.loads(self.to_json())
