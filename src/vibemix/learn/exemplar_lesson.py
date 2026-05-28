# SPDX-License-Identifier: Apache-2.0
"""ExemplarLessonController — drives the L1.14 EQ-as-Tutor 3-band cycle.

Phase 94 Plan 03 (CURR-1.14 binding).

Architecture
============

This controller is an OBSERVER of :class:`LessonRuntime`. It reads the
``exemplar_cycle`` field from the active lesson's script, calls
:class:`ExemplarFinder.find(band)` (P93) for each band, plays the picked
track via :class:`ExemplarPlayer` (P93), and emits the
``[exemplar:<track_id>]`` citation that makes the tutor's narration
resolve through :class:`EvidenceRegistry` (Invariant #2 binding).

The controller NEVER writes :class:`LearnState`. Invariant #1
(single-writer) stays bound to ``LessonRuntime`` alone; the AST gate
``tests/learn/test_runtime_invariants.py`` greps ``src/vibemix/learn/``
for forbidden writes and stays green — this module reads from
:class:`ExemplarPick` results + emits IPC envelopes; it never touches
``self._learn.<field> = ...`` or ``learn_state.<field> = ...``.

The controller is wired into LessonRuntime via the
:meth:`LessonRuntime.register_lesson_observer` seam: when the active
lesson is ``L1.14``, the runtime delegates ``on_enter_awaiting_action``
to the controller's ``.start()``, ``on_ack_action`` to the controller's
``.ack()`` (when ``.matches(midi)`` returns True), and the
``on_enter_completed`` teardown to the controller's ``.stop()``.

Cycle
=====

For each band in fixture order (low → mid → high):

  1. ``ExemplarFinder.find(band, k=1)`` — pre-registers the pick in
     :class:`EvidenceRegistry` (P93-04 behavior).
  2. Emit ``ipc.learn.exemplar_play`` with the pick's track_id +
     duration (best-effort 30 s default; the player decodes the real
     length at playback time but the envelope is shape-only — the
     duration_s field documents the EXPECTED listen time, not the
     authoritative decoded length).
  3. ``ExemplarPlayer.play(file_path)`` — owns its own
     ``sd.OutputStream`` on the user's headphone device (P93-03 contract;
     does NOT reuse the mic-gated co-host PlaybackQueue per Pitfall 2).
  4. Emit ``ipc.learn.tutor_speak`` with the fixture's per-band copy +
     a ``citations[]`` containing the ``[exemplar:<track_id>]`` atom.

On user MIDI matching the current band's ``expected_action``: emits
``ipc.learn.exemplar_stop`` for the active pick + ``ipc.learn.advance``,
advances the cycle index. After all 3 bands: emits
``ipc.learn.complete_lesson`` and stops the player.

Honest-null fallback
====================

If ``ExemplarFinder.find()`` returns ``[]`` (degraded install — neither
library NOR packaged bank has audio), the controller:

  * skips the ``exemplar_play`` emit (no audio chip to paint on the UI),
  * emits a controller-baked ``tutor_speak`` with the honest-null
    phrasing ("i don't have an example of the <band> band ready right
    now; turn the knob anyway — you'll still feel the change"),
  * leaves the ``citations[]`` EMPTY (Rule: never fabricate
    ``[exemplar:_packaged:<band>:null]`` — the citation atom MUST
    resolve through a real EvidenceRegistry write),
  * STILL gates cycle advance on the user's MIDI; the lesson completes
    after all 3 bands regardless of audio availability.

REQ-ID: CURR-1.14 (EQ-as-Tutor marquee demo backend).
"""
from __future__ import annotations

import sys
import time
from typing import Any, Callable, Protocol

from vibemix.learn.exemplar import ExemplarFinder, ExemplarPick
from vibemix.ui_bus.learn_messages import (
    LearnAdvance,
    LearnCompleteLesson,
    LearnExemplarPlay,
    LearnExemplarStop,
    LearnTutorSpeak,
)


# ---------------------------------------------------------------------------
# Constants (CONTEXT.md locks)
# ---------------------------------------------------------------------------

# Default expected listen-time per band — the envelope's ``duration_s``
# field is shape-only in P92 (the schema accepts 0..300); the controller
# does not authoritatively know the decoded length of the picked track
# at emit time. 30 s is a reasonable default that lets the UI surface a
# "now playing — ~30 s" hint without misleading the user about precise
# track length. ExemplarPlayer decodes the real length; this constant
# only feeds the envelope shape.
_DEFAULT_EXEMPLAR_DURATION_S: float = 30.0

# Default gain — the envelope's ``gain_db`` field carries the gain
# policy summary. The actual gain applied is decided by ExemplarPlayer's
# ``_choose_gain_db`` based on master RMS; -12 dB is the safe-default
# the policy converges on for a silent master (CONTEXT.md lock; see
# audio_cue.py:_DEFAULT_GAIN_DB).
_DEFAULT_EXEMPLAR_GAIN_DB: float = -12.0


# CC delta floor used by the controller's MIDI matcher — mirrors the
# LessonRuntime default at runtime.py:_CC_DEFAULT_MIN_DELTA. Kept as a
# private duplicate to keep this module decoupled from runtime.py's
# private constant (the public contract is the matching semantics, not
# the numeric value).
_CC_DEFAULT_MIN_DELTA: int = 38


# ---------------------------------------------------------------------------
# Player protocol — duck-typed seam for testability
# ---------------------------------------------------------------------------


class _PlayerLike(Protocol):
    """Duck-type protocol the controller needs from ExemplarPlayer.

    The real implementation in :mod:`vibemix.learn.audio_cue` exposes more
    surface (can_play, callbacks, gain policy); the controller only needs
    ``.play(file_path)`` + ``.stop()`` to drive the cycle.
    """

    def play(self, file_path: str, /) -> None: ...
    def stop(self) -> None: ...


# ---------------------------------------------------------------------------
# MIDI matcher — local duplicate of the runtime's action_matches predicate.
# Kept here (not imported from runtime.py) so the controller stays
# decoupled from the runtime's private callable shape — the contract is
# the matching SEMANTICS, not a shared Python callable.
# ---------------------------------------------------------------------------


def _midi_matches(midi: dict[str, Any], expected: dict[str, Any]) -> bool:
    """Return True iff ``midi`` matches ``expected``.

    Mirrors :meth:`LessonRuntime.action_matches` (runtime.py:223-300):

      * CC branch: ``midi["control"] == expected["control"]`` AND
        ``abs(midi["value"] - midi["prev_value"]) >=
        expected.get("min_delta", 38)``.
      * Button branch: ``midi["control"] == expected["control"]`` AND
        ``midi["direction"] == expected["direction"]`` AND
        ``midi["deck"] == expected["deck"]`` (when both sides declare
        a deck).
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
# ExemplarLessonController
# ---------------------------------------------------------------------------


class ExemplarLessonController:
    """Drives the L1.14 EQ-as-Tutor 3-band cycle.

    Public surface (the seam :class:`LessonRuntime` registers against via
    ``register_lesson_observer``):

      * ``.start(*, script, lesson_id="L1.14")`` — begin the cycle from
        a loaded lesson script. Reads ``script["exemplar_cycle"]`` and
        primes the first band.
      * ``.matches(midi)`` — returns True iff a MIDI event matches the
        active band's expected_action. The runtime calls this to decide
        whether to delegate to ``.ack()`` or run its normal action gate.
      * ``.ack(*, lesson_id="L1.14")`` — advance to the next band; on
        the last band, emits ``ipc.learn.complete_lesson``.
      * ``.stop(*, lesson_id="L1.14")`` — clean teardown; emits a final
        ``ipc.learn.exemplar_stop`` if a pick was active. Idempotent.

    Constructor:

      :param finder: ExemplarFinder (P93-04). The controller calls
          ``finder.find(band, k=1, t_session=time.time())`` once per
          band; the finder is responsible for the EvidenceRegistry
          pre-write that makes the citation atom resolve.
      :param player: ExemplarPlayer-like (P93-03). Must expose ``.play(path)``
          + ``.stop()``. Wrapped in defensive try/except — a player
          exception NEVER wedges the cycle.
      :param ipc_emit: a one-shot callable that accepts a dict-shaped
          IPC envelope. Typically ``ipc_router.emit`` or
          ``recorded.append`` for tests.
    """

    def __init__(
        self,
        *,
        finder: ExemplarFinder,
        player: _PlayerLike,
        ipc_emit: Callable[[dict[str, Any]], None],
    ) -> None:
        self._finder = finder
        self._player = player
        self._emit = ipc_emit
        # The per-band cycle entries (list of dicts) — loaded from the
        # script's ``exemplar_cycle`` field at .start() time.
        self._cycle: list[dict[str, Any]] = []
        # Index into self._cycle; -1 means "not started yet". After
        # advancing past the last band, _active_idx == len(self._cycle)
        # AND _active_pick is None.
        self._active_idx: int = -1
        # The currently-playing ExemplarPick (or None when degraded-install
        # branch fired OR when the cycle is between bands / stopped).
        self._active_pick: ExemplarPick | None = None

    # ------------------------------------------------------------------
    # Public API — the .register_lesson_observer seam contract
    # ------------------------------------------------------------------

    def start(self, *, script: dict[str, Any], lesson_id: str = "L1.14-eq-as-tutor") -> None:
        """Begin the 3-band cycle from a loaded lesson script.

        ``script`` is the JSON dict from
        :attr:`CURRICULUM["L1.14"].script`. Defensive: if
        ``exemplar_cycle`` is missing or empty, the controller emits an
        immediate ``ipc.learn.complete_lesson`` (degraded fixture) and
        bails — the runtime sees the lesson as completed and proceeds.
        """
        cycle = script.get("exemplar_cycle")
        if not isinstance(cycle, list) or not cycle:
            self._emit_complete(
                lesson_id=lesson_id, reason_token="exemplar_cycle_missing"
            )
            return
        self._cycle = list(cycle)
        self._active_idx = -1
        self._active_pick = None
        self._advance(lesson_id=lesson_id)

    def matches(self, midi: dict[str, Any]) -> bool:
        """Return True iff ``midi`` matches the active band's
        ``expected_action``. The runtime calls this to decide whether
        to delegate to ``.ack()``.
        """
        if self._active_idx < 0 or self._active_idx >= len(self._cycle):
            return False
        expected = self._cycle[self._active_idx].get("expected_action")
        if not isinstance(expected, dict):
            return False
        return _midi_matches(midi, expected)

    def ack(self, *, lesson_id: str = "L1.14-eq-as-tutor") -> None:
        """Advance the cycle to the next band (or finish if done).

        Emits ``ipc.learn.exemplar_stop`` for the prior pick (if any),
        then ``ipc.learn.advance`` (reason="action_matched"), then either
        primes the next band OR emits ``ipc.learn.complete_lesson``.
        """
        self._stop_active(lesson_id=lesson_id)
        self._emit_advance(lesson_id=lesson_id, reason="action_matched")
        self._advance(lesson_id=lesson_id)

    def stop(self, *, lesson_id: str = "L1.14-eq-as-tutor") -> None:
        """Tear down — stop player + emit exemplar_stop + reset state.

        Idempotent: safe to call from any state (pre-start, mid-cycle,
        post-cycle, post-stop). The first call from an active state
        emits a final ``ipc.learn.exemplar_stop``; subsequent calls are
        silent no-ops.
        """
        self._stop_active(lesson_id=lesson_id)
        self._active_idx = -1
        self._cycle = []

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _advance(self, *, lesson_id: str) -> None:
        """Move to the next band (or finalize if all bands done)."""
        self._active_idx += 1
        if self._active_idx >= len(self._cycle):
            # All bands done — emit complete_lesson + reset state.
            self._emit_complete(
                lesson_id=lesson_id, reason_token="completed"
            )
            self._active_idx = -1
            self._cycle = []
            return

        entry = self._cycle[self._active_idx]
        band = str(entry.get("band", ""))
        try:
            picks = self._finder.find(band, k=1, t_session=time.time())
        except Exception as exc:  # pragma: no cover — defensive
            print(
                f"[learn.exemplar_lesson] finder.find({band!r}) failed: {exc!r}",
                file=sys.stderr,
            )
            picks = []

        if not picks:
            # Honest-null fallback — no audio for this band. Emit a
            # controller-baked tutor copy with EMPTY citations; cycle
            # advances on user MIDI normally.
            self._active_pick = None
            self._emit_honest_null_speak(
                band=band, entry=entry, lesson_id=lesson_id
            )
            return

        pick = picks[0]
        self._active_pick = pick

        # Emit ipc.learn.exemplar_play — the UI uses this to paint a
        # "now playing" chip with the track_id + estimated duration.
        try:
            envelope = LearnExemplarPlay.make(
                track_id=pick.track_id,
                duration_s=_DEFAULT_EXEMPLAR_DURATION_S,
                gain_db=_DEFAULT_EXEMPLAR_GAIN_DB,
            ).to_dict()
            self._emit(envelope)
        except Exception as exc:  # pragma: no cover — defensive
            print(
                f"[learn.exemplar_lesson] exemplar_play emit failed: {exc!r}",
                file=sys.stderr,
            )

        # Start playback — owns its own sd.OutputStream on the headphone
        # device. Wrapped in try/except — a player exception NEVER wedges
        # the cycle (the user can still complete the lesson by reading
        # the tutor copy + sweeping the knob).
        if pick.file_path:
            try:
                self._player.play(pick.file_path)
            except Exception as exc:  # pragma: no cover — defensive
                print(
                    f"[learn.exemplar_lesson] player.play failed: {exc!r}",
                    file=sys.stderr,
                )

        # Emit tutor_speak with the [exemplar:<track_id>] citation —
        # Invariant #2 binding. ExemplarFinder.find() pre-registered the
        # pick in EvidenceRegistry; this citation atom resolves through
        # that write.
        tutor_text = str(entry.get("tutor_speak", "")).strip()
        if not tutor_text:
            # Fixture missing per-band tutor_speak — fall back to a
            # generic copy. Should not happen in production (Plan
            # 94-01 ships every band with copy), but defensive.
            tutor_text = f"listening to the {band} band on a track from your library."
        try:
            envelope = LearnTutorSpeak.make(
                text=tutor_text,
                tts_marker=f"L114.band_{band}",
                citations=(f"[exemplar:{pick.track_id}]",),
                data_state="active",
            ).to_dict()
            self._emit(envelope)
        except Exception as exc:  # pragma: no cover — defensive
            print(
                f"[learn.exemplar_lesson] tutor_speak emit failed: {exc!r}",
                file=sys.stderr,
            )

    def _emit_honest_null_speak(
        self, *, band: str, entry: dict[str, Any], lesson_id: str
    ) -> None:
        """Tutor copy for the degraded-install branch — neither library
        nor packaged bank had a track. NO citation (no exemplar to cite —
        we MUST NOT fabricate a ``[exemplar:_packaged:<band>:null]``
        atom; it wouldn't resolve through EvidenceRegistry).
        """
        fallback_text = (
            f"i don't have an example of the {band} band ready right now. "
            f"turn deck a's {band} eq knob anyway — you'll still feel the change."
        )
        try:
            envelope = LearnTutorSpeak.make(
                text=fallback_text,
                tts_marker=f"L114.band_{band}_honest_null",
                citations=(),  # EMPTY — Rule: never fabricate citations.
                data_state="active",
            ).to_dict()
            self._emit(envelope)
        except Exception as exc:  # pragma: no cover — defensive
            print(
                f"[learn.exemplar_lesson] honest-null tutor_speak emit failed: {exc!r}",
                file=sys.stderr,
            )

    def _stop_active(self, *, lesson_id: str) -> None:
        """Emit exemplar_stop for the active pick (if any) + stop the
        player. Idempotent — leaves self._active_pick = None on exit.
        """
        if self._active_pick is not None:
            try:
                envelope = LearnExemplarStop.make(
                    track_id=self._active_pick.track_id,
                    reason="interrupted",
                ).to_dict()
                self._emit(envelope)
            except Exception as exc:  # pragma: no cover — defensive
                print(
                    f"[learn.exemplar_lesson] exemplar_stop emit failed: {exc!r}",
                    file=sys.stderr,
                )
        try:
            self._player.stop()
        except Exception as exc:  # pragma: no cover — defensive
            print(
                f"[learn.exemplar_lesson] player.stop failed: {exc!r}",
                file=sys.stderr,
            )
        self._active_pick = None

    def _emit_advance(self, *, lesson_id: str, reason: str) -> None:
        """Emit ipc.learn.advance for a band-cycle step.

        ``reason`` is the schema-enum value ("action_matched" or
        "user_skip"). The runtime emits its own ipc.learn.advance on
        FSM transitions; the controller emits ITS OWN to flag the
        per-band advance (which the runtime's main FSM doesn't see —
        the cycle is entirely inside the controller).
        """
        try:
            envelope = LearnAdvance.make(
                lesson_id=lesson_id, reason=reason
            ).to_dict()
            self._emit(envelope)
        except Exception as exc:  # pragma: no cover — defensive
            print(
                f"[learn.exemplar_lesson] advance emit failed: {exc!r}",
                file=sys.stderr,
            )

    def _emit_complete(self, *, lesson_id: str, reason_token: str) -> None:
        """Emit ipc.learn.complete_lesson when the cycle finishes.

        ``reason_token`` is informational only — the schema-enum reason
        is ``"completed"`` for the happy path; degraded fixtures (no
        exemplar_cycle field) also surface as ``"completed"`` so the
        runtime treats them the same way. We log the informational token
        to stderr for debug telemetry but the wire field is enum-bounded.
        """
        # Always emit player.stop() FIRST (defensive teardown).
        try:
            self._player.stop()
        except Exception as exc:  # pragma: no cover — defensive
            print(
                f"[learn.exemplar_lesson] player.stop on complete failed: {exc!r}",
                file=sys.stderr,
            )
        try:
            envelope = LearnCompleteLesson.make(
                lesson_id=lesson_id, reason="completed"
            ).to_dict()
            self._emit(envelope)
        except Exception as exc:  # pragma: no cover — defensive
            print(
                f"[learn.exemplar_lesson] complete_lesson emit failed: {exc!r}",
                file=sys.stderr,
            )


__all__ = [
    "ExemplarLessonController",
]
