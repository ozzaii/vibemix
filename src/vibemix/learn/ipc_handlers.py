# SPDX-License-Identifier: Apache-2.0
"""Inbound ``ipc.learn.*`` dispatch handlers.

Phase 92 CR-01 fix (REVIEW). The :class:`LessonRuntime` FSM is wired by
``__main__.py`` but no inbound IPC handler was registered for any of the
5 shell→sidecar learn envelopes (``start_lesson``, ``start_course``,
``ack``, ``complete_lesson``, ``progress_state``). The frontend could
emit any of these — ``IpcRouterBus.dispatch()`` would return False
silently and the FSM stayed parked in ``idle``.

This module is the single place that wires the inbound boundary. It
exposes :func:`register_learn_handlers` which takes the live
:class:`LessonRuntime` + :class:`IpcRouterBus` + :class:`MidiMirror` +
:class:`LearnProgress` and registers async handler coroutines for the 5
inbound envelope types.

Design rules:

* No new ws port (Invariant #4) — handlers route through the existing
  :class:`IpcRouterBus`.
* Defensive parsing — malformed payloads NEVER raise out into
  :func:`IpcRouterBus.dispatch`; the dispatch swallows handler faults
  (ws_bus.py:355-358), so we don't strictly need to catch here, but a
  bracket-tagged stderr line for unexpected shapes makes the failure
  mode visible during the live ear-pass.
* No I/O blocking — :class:`LessonRuntime.send` is synchronous and fast;
  handlers wrap it for the async dispatch contract.

REQ-ID: P92 REVIEW CR-01.
"""
from __future__ import annotations

import sys
from typing import Any

from vibemix.learn.curriculum import COURSE_REGISTRY, CURRICULUM, course_lesson_ids
from vibemix.learn.progress import (
    LearnProgress,
    _fresh_skills_block,
    reset_progress,
    save_progress,
)
from vibemix.learn.runtime import LessonRuntime
from vibemix.ui_bus.learn_messages import LearnProgressState

_COURSE_ID_ALIASES = {
    "course_1": "course_1_anatomy",
    "course_2": "course_2_transitions",
    "course_3": "course_3_play_mode",
}

_BUTTON_CONTROLS = {
    "play",
    "cue",
    "sync",
    "jog_touch",
    "jog_touched",
    "loop_in",
    "loop_out",
    "hotcue",
    "filter_fx",
    "fx_echo",
    "tap_tempo",
    "headphone_cue",
    "lesson_continue",
}

_DEFAULT_PRACTICE_CONTROLLER_ID = "pioneer_ddj_flx4"


def _canonical_lesson_id(raw: Any) -> str | None:
    """Return the Python curriculum key for a wire lesson id.

    The rebuilt Learn UI emits canonical short ids (``L1.01``), but older
    frontend/tests may still send slugged ids (``L1.01-opening-dialog``).
    Accept both at the boundary so the sidecar owns normalization.
    """
    if not isinstance(raw, str) or not raw:
        return None
    if raw in CURRICULUM:
        return raw
    head = raw.split("-", 1)[0]
    if head in CURRICULUM:
        return head
    return None


def _canonical_course_id(raw: Any) -> str | None:
    if not isinstance(raw, str) or not raw:
        return None
    return _COURSE_ID_ALIASES.get(raw, raw)


def _lesson_completed(progress: LearnProgress, lesson_id: str) -> bool:
    entry = progress.lessons.get(lesson_id)
    return isinstance(entry, dict) and entry.get("completed") is True


def _course_unlocked(progress: LearnProgress, course_id: str) -> bool:
    course = COURSE_REGISTRY.get(course_id)
    if course is None:
        return False
    if course.unlock_gate is None:
        return True
    return getattr(progress, course.unlock_gate, False) is True


def _lesson_unlocked(
    progress: LearnProgress,
    *,
    lesson_id: str,
    course_id: str,
) -> bool:
    return _course_unlocked(progress, course_id) or _lesson_completed(
        progress,
        lesson_id,
    )


def _zpd_course_lesson_id(
    progress: LearnProgress,
    *,
    course_id: str,
    fallback_lesson_id: str,
) -> str:
    """Return the course lesson that matches the current ZPD aim, if any."""
    try:
        from vibemix.learn.coaching_aim import resolve_coaching_aim
        from vibemix.learn.skill_tree import SKILL_MANIFEST

        aim = resolve_coaching_aim(progress)
        if aim is None:
            return fallback_lesson_id
        spec = SKILL_MANIFEST.get(aim.skill_id)
        if spec is None:
            return fallback_lesson_id
        course_lessons = set(course_lesson_ids(course_id))
        aim_lessons = tuple(lid for lid in spec.lesson_ids if lid in course_lessons)
        for lesson_id in aim_lessons:
            if not _lesson_completed(progress, lesson_id):
                return lesson_id
        return aim_lessons[0] if aim_lessons else fallback_lesson_id
    except Exception:
        return fallback_lesson_id


def _ack_event_type(control: str, direction: Any) -> str:
    if control in {"jog_touch", "jog_touched"}:
        return "cc"
    if control in _BUTTON_CONTROLS:
        return "button"
    if direction in ("", "up", "down"):
        return "cc"
    return "cc"


def _normalize_ack_control(
    *,
    control: str,
    value: int,
    direction: Any,
    raw_prev: Any,
) -> tuple[str, int, int | None]:
    """Normalize wire-only control spellings to lesson curriculum controls."""
    if control == "filter_fx":
        prev = int(raw_prev) if raw_prev is not None else None
        return "fx_echo", value, prev
    if control not in {"jog_touch", "jog_touched"}:
        prev = int(raw_prev) if raw_prev is not None else None
        return control, value, prev

    # Controller profiles expose jog wheels as touch events. Beginner lessons
    # teach the motion as ``jog``; treat a touch-down as a full CC sweep so the
    # deterministic min_delta gate can verify it.
    if direction == "up" or value <= 0:
        return "jog", 0, 127
    return "jog", 127, 0


def register_learn_handlers(
    *,
    ipc_router: Any,
    lesson_runtime: LessonRuntime,
    midi_mirror: Any,
    progress: LearnProgress,
    ipc_adapter: Any | None = None,
) -> None:
    """Wire the 5 inbound ``ipc.learn.*`` envelope handlers onto the bus.

    Called once from ``__main__.main()`` immediately after
    :class:`LessonRuntime` is instantiated (and after
    :func:`SessionLoop.register_handlers` has registered its settings /
    profile / recordings handlers — the bus is a single handler bag, so
    insertion order is irrelevant; each type-key registers at most one
    handler).

    Args:
        ipc_router: The :class:`IpcRouterBus` instance the live ws path
            owns. Must expose ``register_handler(message_type, handler)``
            + an async ``emit(msg)``.
        lesson_runtime: The live :class:`LessonRuntime` FSM. Handlers
            call ``lesson_runtime.send(<event>, **kwargs)``; the
            class's ``allow_event_without_transition`` flag turns
            guard-rejected events into silent no-ops (no exception
            propagation).
        midi_mirror: The :class:`MidiMirror` instance. Handlers read
            the currently-bound controller's id via
            ``midi_mirror.current_profile()`` so the FSM's
            ``on_enter_loaded`` can stamp the lesson_loaded envelope's
            ``controller_id`` field. ``None`` means no controller bound
            yet — handlers fall back to an empty string sentinel.
        progress: The live :class:`LearnProgress` instance. The
            progress-state handler's ``action="reset"`` path wipes the
            on-disk file AND clears the in-memory dict so the snapshot
            envelope emitted afterwards reflects the freshly-reset
            state.
        ipc_adapter: Optional sync→async emit adapter (the same
            ``_LessonRuntimeIpcAdapter`` ``__main__.py`` passes to the
            LessonRuntime constructor). Used by the
            ``progress_state(reset)`` handler so the reset_ack emit
            uses the same plumbing as runtime-internal emits.
            Falls back to ``ipc_router.emit`` (await-able) when None.
    """

    async def _on_start_lesson(msg: dict) -> None:
        """Handle ``ipc.learn.start_lesson { lesson_id, level }``.

        Validates that ``lesson_id`` is present + in :data:`CURRICULUM`
        before driving the FSM; otherwise the runtime's
        ``on_enter_loaded`` would silently fail on the ``CURRICULUM[None]``
        / ``CURRICULUM[<unknown>]`` lookup (the bug WR-02 documents).
        Derives ``course_id`` from ``CURRICULUM[lesson_id].course_id``
        — the authoritative owner — instead of prefix-matching on the
        lesson_id.
        """
        payload = msg.get("payload", {}) if isinstance(msg, dict) else {}
        lesson_id = _canonical_lesson_id(payload.get("lesson_id"))
        if lesson_id is None:
            print(
                f"[learn.ipc] start_lesson rejected: unknown lesson_id "
                f"{payload.get('lesson_id')!r}",
                file=sys.stderr,
            )
            return
        course_id = CURRICULUM[lesson_id].course_id
        if not _lesson_unlocked(
            progress,
            lesson_id=lesson_id,
            course_id=course_id,
        ):
            print(
                f"[learn.ipc] start_lesson rejected: {lesson_id!r} is "
                f"locked for course {course_id!r}",
                file=sys.stderr,
            )
            return
        # Resolve the currently-bound controller id (if any). When no
        # hardware is bound, use the default on-screen practice deck so
        # Learn remains usable without a physical controller.
        controller_id = _DEFAULT_PRACTICE_CONTROLLER_ID
        try:
            profile = midi_mirror.current_profile()
            if profile is not None:
                controller_id = profile.id
        except Exception:  # pragma: no cover — defensive
            pass
        # Drive the FSM. The 2-step load → begin sequence is the
        # canonical wakeup contract pinned by
        # tests/learn/test_lesson_runtime_smoke.py.
        lesson_runtime.send(
            "load",
            lesson_id=lesson_id,
            course_id=course_id,
            controller_id=controller_id,
        )
        lesson_runtime.send("begin")

    async def _on_start_course(msg: dict) -> None:
        """Handle ``ipc.learn.start_course { course_id, controller_id }``.

        Resolves the FIRST lesson of the requested course from
        :data:`CURRICULUM` (ordered insertion = ship order) and drives
        the FSM through ``load`` → ``begin``. Bails with a stderr line
        when the course has no registered lessons (e.g. P94 land-day,
        where the start_course envelope arrives before the lesson
        entries do).
        """
        payload = msg.get("payload", {}) if isinstance(msg, dict) else {}
        course_id = _canonical_course_id(payload.get("course_id"))
        # The shell ALSO supplies controller_id; we trust ours over the
        # client's because the sidecar owns the canonical binding state
        # (midi_mirror). The client's may be stale across hot-plug.
        if not isinstance(course_id, str):
            print(
                f"[learn.ipc] start_course rejected: missing course_id "
                f"in payload {payload!r}",
                file=sys.stderr,
            )
            return
        # Resolve ship order through the curriculum registry helper instead of
        # reimplementing the course walk at the IPC boundary.
        first_lesson_id = next(iter(course_lesson_ids(course_id)), None)
        if first_lesson_id is None:
            print(
                f"[learn.ipc] start_course {course_id!r} has no registered "
                f"lessons; FSM stays idle",
                file=sys.stderr,
            )
            return
        if not _course_unlocked(progress, course_id):
            print(
                f"[learn.ipc] start_course rejected: {course_id!r} is "
                "locked",
                file=sys.stderr,
            )
            return
        lesson_id = _zpd_course_lesson_id(
            progress,
            course_id=course_id,
            fallback_lesson_id=first_lesson_id,
        )
        controller_id = _DEFAULT_PRACTICE_CONTROLLER_ID
        try:
            profile = midi_mirror.current_profile()
            if profile is not None:
                controller_id = profile.id
        except Exception:  # pragma: no cover — defensive
            pass
        lesson_runtime.send(
            "load",
            lesson_id=lesson_id,
            course_id=course_id,
            controller_id=controller_id,
        )
        lesson_runtime.send("begin")

    async def _on_ack(msg: dict) -> None:
        """Handle ``ipc.learn.ack { control_id, source, value, direction }``.

        The shell's ``LearnAck`` envelope is the user-action signal; we
        re-shape it into the ``midi`` dict the FSM's ``action_matches``
        guard expects, then drive ``send("ack_action", midi=...)``. The
        guard does its own matching — if the ack doesn't match the
        currently-expected action, the FSM silently stays put (the
        no-op-on-guard-fail contract).

        Payload re-shape — the wire format differs from the runtime's
        internal midi-event dict:

          wire (LearnAckPayload):       runtime (action_matches input):
            control_id: "play_a"  →     control: "play_a"
            source: "midi"|"click"      type: "cc"|"button" (inferred)
            value: int                  value: int
            direction: ""|"up"|"down"   direction: ""|"up"|"down"
                                        deck: "" (parsed from control_id)
                                        prev_value: 0 (CC delta needs
                                                       prior tracking; the
                                                       sidecar doesn't see
                                                       the prior frame, so
                                                       we synthesize a
                                                       full-range delta
                                                       when source="midi"
                                                       to let the guard's
                                                       ≥38 cap fire when
                                                       the user moves the
                                                       physical control —
                                                       see comment below)

        Re. CC ``prev_value``: the live-window listener in
        ``learn-window.ts`` does its own delta tracking and only emits
        ``ipc.learn.ack`` when ``value != prev``; by the time the ack
        reaches us the user HAS moved the control. To let the
        ``action_matches`` predicate's ≥38 threshold fire correctly, we
        synthesize ``prev_value = value ± min_delta`` so the absolute
        diff exceeds the threshold. The guard re-checks the actual
        movement direction; this approximation is correct for the v9.0
        L0.00 lesson (button-only) and conservative for any future CC
        lesson — the guard rejects ambiguous matches.
        """
        payload = msg.get("payload", {}) if isinstance(msg, dict) else {}
        control_id = payload.get("control_id")
        if not isinstance(control_id, str) or not control_id:
            print(
                f"[learn.ipc] ack rejected: missing control_id in "
                f"payload {payload!r}",
                file=sys.stderr,
            )
            return
        # control_id may be ``<control>:<deck>`` (deck-scoped) or just
        # ``<control>`` (master-section). Split on the last colon.
        if ":" in control_id:
            control, _, deck = control_id.rpartition(":")
        else:
            control = control_id
            deck = ""
        value = int(payload.get("value", 0))
        direction = payload.get("direction", "")
        raw_prev = payload.get("prev_value")
        control, value, normalized_prev = _normalize_ack_control(
            control=control,
            value=value,
            direction=direction,
            raw_prev=raw_prev,
        )
        if control == "fx_echo" and not deck:
            deck = "A"
        ev_type = _ack_event_type(control, direction)
        if normalized_prev is not None:
            prev_value = normalized_prev
        elif raw_prev is None:
            prev_value = (
                max(0, value - 40)
                if direction != "up"
                else min(127, value + 40)
            )
        else:
            prev_value = int(raw_prev)
        midi = {
            "type": ev_type,
            "control": control,
            "deck": deck,
            "direction": direction,
            "value": value,
            "prev_value": prev_value,
            "source": payload.get("source", ""),
        }
        lesson_runtime.handle_practice_audio_ack(midi)
        if lesson_runtime.handle_observer_ack(midi):
            return
        if lesson_runtime.handle_recovery_drill_ack(midi):
            return
        if lesson_runtime.handle_step_ack(midi):
            return
        if lesson_runtime.handle_beatmatch_practice_ack(midi):
            return
        if lesson_runtime.handle_mismatch_ack(midi):
            return
        lesson_runtime.send("ack_action", midi=midi)

    async def _on_complete_lesson(msg: dict) -> None:
        """Handle ``ipc.learn.complete_lesson { lesson_id, reason }``.

        Bidirectional envelope — the shell emits it on user-skip
        (``reason="user_skip"``), the sidecar emits it on
        system-advance. We only care about the user-skip path here; the
        system-advance path is the sidecar's own emit and would never
        be dispatched back into us. Drive ``send("skip")`` — the FSM's
        ``min_dwell_elapsed`` guard owns the 45 s anti-speedrun floor.
        """
        payload = msg.get("payload", {}) if isinstance(msg, dict) else {}
        reason = payload.get("reason")
        if reason != "user_skip":
            # Not a user-skip — ignore. The sidecar-emitted variant
            # (reason="completed") would have come from our own emit,
            # not from the shell.
            return
        lesson_runtime.send("skip")

    async def _on_progress_state(msg: dict) -> None:
        """Handle ``ipc.learn.progress_state { action }``.

        Three actions:

          * ``"reset"`` — the settings drawer reset flow.
            :func:`reset_progress` unlinks the on-disk file; we ALSO
            clear the in-memory ``progress.lessons`` / ``courses``
            dicts so subsequent emits don't paint stale dots. Emit
            ``reset_ack`` so the Learn window's
            ``showLearnToast("learn progress reset.")`` fires (CR-04
            adds an additional local toast in the Session window — both
            run because they're independent surfaces).

          * ``"snapshot"`` — the shell explicitly requests the current
            persisted state. Emit a snapshot envelope.

          * ``"reset_ack"`` — sidecar-only; would only arrive if the
            client echoes back. Ignore.
        """
        payload = msg.get("payload", {}) if isinstance(msg, dict) else {}
        action = payload.get("action")
        if action == "reset":
            # Wipe the on-disk file + clear in-memory state. The
            # in-memory clear MUST happen BEFORE the ack emit so the
            # snapshot embedded in the ack reflects the new empty
            # state.
            try:
                reset_progress()
            except Exception as exc:  # pragma: no cover — defensive
                print(
                    f"[learn.ipc] reset_progress failed: {exc!r}",
                    file=sys.stderr,
                )
            # Clear in-memory dicts so the same LearnProgress instance
            # the runtime holds reflects the new empty state. Persist
            # the empty state so a subsequent boot reads matching disk.
            progress.lessons = {}
            progress.courses = {}
            progress.course_2_unlocked = False
            progress.course_3_unlocked = False
            # DATA-03: clear the in-memory live-portion skill ledger too, so a
            # settings-drawer reset returns the skill tree to defaults without
            # waiting for a process restart. The on-disk file is unlinked by
            # reset_progress() above; the next load re-seeds an empty v2 block.
            progress.skills = _fresh_skills_block()
            try:
                save_progress(progress)
            except Exception as exc:  # pragma: no cover — defensive
                print(
                    f"[learn.ipc] save_progress (empty) failed: {exc!r}",
                    file=sys.stderr,
                )
            # Emit reset_ack with the emptied snapshot. Prefer the sync adapter
            # (same path the runtime uses) so the emit fires through the same
            # plumbing; fall back to awaiting ipc_router.emit directly.
            ack = LearnProgressState.make(
                action="reset_ack",
                progress=progress.snapshot(),
            ).to_dict()
            if ipc_adapter is not None:
                try:
                    ipc_adapter.emit(ack)
                except Exception as exc:  # pragma: no cover — defensive
                    print(
                        f"[learn.ipc] reset_ack emit failed: {exc!r}",
                        file=sys.stderr,
                    )
            else:
                try:
                    await ipc_router.emit(ack)
                except Exception as exc:  # pragma: no cover — defensive
                    print(
                        f"[learn.ipc] reset_ack emit failed: {exc!r}",
                        file=sys.stderr,
                    )
            return
        if action == "snapshot":
            snap = LearnProgressState.make(
                action="snapshot",
                progress=progress.snapshot(),
            ).to_dict()
            if ipc_adapter is not None:
                try:
                    ipc_adapter.emit(snap)
                except Exception as exc:  # pragma: no cover — defensive
                    print(
                        f"[learn.ipc] snapshot emit failed: {exc!r}",
                        file=sys.stderr,
                    )
            else:
                try:
                    await ipc_router.emit(snap)
                except Exception as exc:  # pragma: no cover — defensive
                    print(
                        f"[learn.ipc] snapshot emit failed: {exc!r}",
                        file=sys.stderr,
                    )
            return
        # reset_ack inbound (echo): ignore.

    # Register all 5 handlers onto the bus.
    ipc_router.register_handler("ipc.learn.start_lesson", _on_start_lesson)
    ipc_router.register_handler("ipc.learn.start_course", _on_start_course)
    ipc_router.register_handler("ipc.learn.ack", _on_ack)
    ipc_router.register_handler(
        "ipc.learn.complete_lesson", _on_complete_lesson
    )
    ipc_router.register_handler(
        "ipc.learn.progress_state", _on_progress_state
    )
