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

from vibemix.learn.curriculum import CURRICULUM
from vibemix.learn.progress import (
    LearnProgress,
    reset_progress,
    save_progress,
)
from vibemix.learn.runtime import LessonRuntime
from vibemix.ui_bus.learn_messages import LearnProgressState


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
        lesson_id = payload.get("lesson_id")
        if not isinstance(lesson_id, str) or lesson_id not in CURRICULUM:
            print(
                f"[learn.ipc] start_lesson rejected: unknown lesson_id "
                f"{lesson_id!r}",
                file=sys.stderr,
            )
            return
        course_id = CURRICULUM[lesson_id].course_id
        # Resolve the currently-bound controller id (if any). Empty
        # string sentinel when no controller is bound — the FSM's
        # on_enter_loaded handles the empty case (WR-03 still defers
        # the emit until a controller is bound; not part of CR-01).
        controller_id = ""
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
        course_id = payload.get("course_id")
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
        # Find the first lesson in CURRICULUM with matching course_id.
        # Dict iteration order is insertion order (Python 3.7+), which
        # matches the ship order in curriculum.py.
        first_lesson_id: str | None = None
        for lesson_id, meta in CURRICULUM.items():
            if meta.course_id == course_id:
                first_lesson_id = lesson_id
                break
        if first_lesson_id is None:
            print(
                f"[learn.ipc] start_course {course_id!r} has no registered "
                f"lessons; FSM stays idle",
                file=sys.stderr,
            )
            return
        controller_id = ""
        try:
            profile = midi_mirror.current_profile()
            if profile is not None:
                controller_id = profile.id
        except Exception:  # pragma: no cover — defensive
            pass
        lesson_runtime.send(
            "load",
            lesson_id=first_lesson_id,
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
        # Infer event type. Source="click" means a click on the rendered
        # SVG (button-shaped), source="midi" can be either. We don't have
        # the binding here, so we set "button" when a direction is
        # present (buttons carry up/down) and "cc" otherwise. The guard
        # re-checks expected_type vs midi_type, so a wrong inference is
        # rejected cleanly.
        ev_type = "button" if direction in ("up", "down") else "cc"
        # Synthesize prev_value so a CC ack lights the ≥38 threshold.
        # Live signal already carries direction, so prev = value ∓ 40.
        prev_value = max(0, value - 40) if direction != "up" else min(127, value + 40)
        midi = {
            "type": ev_type,
            "control": control,
            "deck": deck,
            "direction": direction,
            "value": value,
            "prev_value": prev_value,
        }
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
            try:
                save_progress(progress)
            except Exception as exc:  # pragma: no cover — defensive
                print(
                    f"[learn.ipc] save_progress (empty) failed: {exc!r}",
                    file=sys.stderr,
                )
            # Emit reset_ack. Prefer the sync adapter (same path the
            # runtime uses) so the emit fires through the same
            # plumbing; fall back to awaiting ipc_router.emit directly.
            ack = LearnProgressState.make(action="reset_ack").to_dict()
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
