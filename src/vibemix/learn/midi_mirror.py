# SPDX-License-Identifier: Apache-2.0
"""MidiMirror — 30 Hz delta-coalesced controller-position snapshotter.

Phase 91 RENDER-01 + RENDER-02. Reads (read-only) the existing
:class:`vibemix.midi.state.ControllerState` updated by
:meth:`ControllerState.handle_msg`, integer-LSB-suppresses identical frames,
and produces a :class:`vibemix.ui_bus.learn_messages.LearnMidiPosition`
envelope dict for ``ws_broadcast`` to emit on its existing 30 Hz outbound
tick. Also exposes a thread-safe queue for
:class:`vibemix.ui_bus.learn_messages.LearnControllerDetected` envelopes that
the port-watcher callback enqueues on connect/disconnect; the same 30 Hz tick
drains the queue immediately before pulling the position snapshot, so both
envelope types ride the SAME ``_send_all`` consumer (Invariant #4 preserved
— no second WS listener bound here).

Threading discipline (per CLAUDE.md §Conventions):

* :meth:`snapshot` + :meth:`drain_pending_detected` are called from
  ``ws_broadcast``'s 30 Hz tick on the ASYNCIO MAIN LOOP. They never
  ``await``, never hold the internal lock across a yield point.

* :meth:`queue_controller_detected` is safe to call from ANY caller —
  the asyncio main loop (``port_watcher`` callback path), a daemon thread,
  or a future Rust-direct ``midir`` path. ``_pending_detected`` is guarded
  by :class:`threading.Lock` (the same primitive
  :class:`vibemix.midi.state.ControllerState` uses for its dict in
  ``state.py:144`` — keeping the threading discipline uniform across the
  Learn island).

* :class:`vibemix.midi.state.ControllerState` reads via
  ``deck_snapshot()`` are safe because ``ControllerState`` itself
  lock-guards that read (``state.py:144``) — :class:`MidiMirror` does not
  re-lock that path.

Cardinal invariants:

* **Single-writer (Invariant #1)**: :class:`MidiMirror` is the SOLE writer
  of ``ipc.learn.midi_position`` envelopes. It NEVER writes to
  :class:`vibemix.state.MusicState`. It NEVER writes to
  :class:`vibemix.midi.state.ControllerState`. Read-only consumer of both.

* **One socket (Invariant #4)**: :class:`MidiMirror` NEVER opens a second
  WS listener. The 30 Hz tick in ``ws_broadcast`` is the SOLE consumer of
  both ``snapshot()`` and ``drain_pending_detected()``; the emit path is
  ``ws_broadcast``'s closed-over ``_send_all`` helper. The
  ``tests/learn/test_no_new_ws_port.py`` grep gate pins this.

* **Trust the existing midi listener (Invariant #3 corollary)**:
  :class:`MidiMirror` NEVER opens a second ``mido.open_input``, never
  spawns a second listener thread. The existing daemon thread (started
  by :meth:`vibemix.platform._midi_macos.MidiMacOS.start_listener_thread`)
  is the single source of MIDI events; :class:`MidiMirror` only reads
  the resulting :class:`ControllerState`.
"""
from __future__ import annotations

import threading
from typing import Any

from vibemix.midi.profile import ControllerProfile
from vibemix.ui_bus.learn_messages import (
    LearnControllerDetected,
    LearnMidiPosition,
)


class MidiMirror:
    """Snapshot the live :class:`ControllerState` into a delta-coalesced
    position dict suitable for the ``ipc.learn.midi_position`` envelope,
    plus a thread-safe controller_detected queue drained per ws_broadcast
    tick.

    Owner: :func:`vibemix.__main__.main` instantiates ONE :class:`MidiMirror`
    after :class:`vibemix.platform.MidiMacOS` is up (alongside
    ``midi_macos``). Hands the instance to ``ws_broadcast`` via a new kwarg
    so the broadcast loop can drain then snapshot at 30 Hz; wires the
    existing ``port_watcher`` callback to ENQUEUE (not emit) connect /
    disconnect envelopes via :meth:`queue_controller_detected`.

    Methods:
        ``bind_profile(profile)`` — called from the port_watcher callback
            on each ``('connected', port, profile)`` event. Stores the
            current profile and resets the delta cache (so the first frame
            after bind always emits a fresh full position snapshot —
            "fill the freshly-rendered SVG with current state").

        ``unbind()`` — called on ``('disconnected', port)``. Clears profile
            + delta cache.

        ``snapshot() -> dict | None`` — read the live :class:`ControllerState`
            via ``deck_snapshot()``; integer-LSB delta-compare against
            ``self._last_positions``; if any field changed (or this is the
            first frame after bind), return a ``LearnMidiPosition.make(...)
            .to_dict()`` envelope and advance the cache. Else return
            ``None`` (caller suppresses emit).

        ``controller_detected(*, connected, profile, port_name) -> dict``
            — pure builder. Returns a ``LearnControllerDetected.make(...)
            .to_dict()`` envelope. Does NOT enqueue, does NOT emit.

        ``queue_controller_detected(*, connected, profile, port_name) -> None``
            — thread-safe enqueue path. Builds the envelope via
            :meth:`controller_detected` and appends to the locked
            ``_pending_detected`` list. Safe from ANY thread / coroutine.

        ``drain_pending_detected() -> list[dict]`` — locked copy + clear.
            Returns a shallow copy of pending envelopes; clears the
            underlying list. Called from ``ws_broadcast``'s 30 Hz tick
            BEFORE :meth:`snapshot` so a fresh plug-in's
            ``controller_detected`` envelope reaches the webview before
            the first ``midi_position`` envelope from the same controller.
    """

    def __init__(self, controller_state: Any) -> None:
        # Read-only reference to the live ControllerState (the existing
        # daemon-thread MIDI decoder hosted by MidiMacOS). We only call
        # `.deck_snapshot()` on this — never assign back. The reference is
        # captured ONCE; the live-session single-state hot-plug callback
        # (`handle_port_change_single_state`) mutates this object in place,
        # so the captured reference stays valid across unplug/replug.
        self._cs = controller_state
        # Cache of last-sent positions (integer values). The LSB-delta gate.
        # Reset to `{}` on every `bind_profile` and `unbind` so the first
        # snapshot after a (re)connect always emits a fresh full frame
        # ("fill the freshly-rendered SVG with current state").
        self._last_positions: dict[str, int] = {}
        # Profile binding can change on hot-plug; midi_mirror tracks the
        # currently-bound profile so it knows which controls to surface.
        # Updated by the port_watcher callback hook (see __main__ wiring).
        self._profile: ControllerProfile | None = None
        # Thread-safe queue for `controller_detected` envelopes. The
        # `port_watcher` callback enqueues here from the asyncio main loop;
        # the 30 Hz `ws_broadcast` tick drains it. The lock window is
        # microseconds (locked append, locked copy+clear) — never held
        # across an await, never held while computing. Same primitive shape
        # as ControllerState's `threading.Lock` (state.py:144) so the
        # threading discipline is uniform across the Learn island and a
        # future daemon-thread or Rust-direct caller works without rework.
        self._pending_detected: list[dict] = []
        self._detected_lock = threading.Lock()

    # ------------------------------------------------------------------
    # Profile lifecycle (called from the port_watcher callback in __main__)
    # ------------------------------------------------------------------

    def bind_profile(self, profile: ControllerProfile) -> None:
        """Called once on each ``('connected', port, profile)`` event.

        Stores the profile and resets the delta cache so the very next
        :meth:`snapshot` call emits a fresh full position frame — the
        "fill the freshly-rendered SVG with current state" contract that
        ``tests/learn/test_midi_mirror_unit.py::test_first_frame_after_bind``
        pins.
        """
        self._profile = profile
        self._last_positions = {}

    def unbind(self) -> None:
        """Called on ``('disconnected', port)`` — clears cached profile
        and delta cache. After :meth:`unbind`, :meth:`snapshot` returns
        ``None`` (defensive: a None profile means "no schema to read").
        Callers MUST enqueue the disconnect envelope BEFORE calling
        :meth:`unbind` so the envelope payload's ``controller_id`` /
        ``display_name`` are still well-formed.
        """
        self._profile = None
        self._last_positions = {}

    # ------------------------------------------------------------------
    # Position snapshot path (called from ws_broadcast 30 Hz tick)
    # ------------------------------------------------------------------

    def snapshot(self) -> dict | None:
        """Return a ``LearnMidiPosition`` envelope dict if any tracked
        position changed since last call; else ``None`` (caller should
        not emit).

        Delta gate: integer-LSB equality (dict equality on int values —
        exact-byte semantics from RESEARCH §Pattern 2 "Why integer 0..127,
        not float [0,1]"). Floating-point would either lose precision or
        trip false-positive deltas on f64 rounding noise; integer LSB is
        what mido already gives us — exactly the natural unit.
        """
        if self._profile is None:
            return None
        cur = self._read_current_positions()
        # Integer-LSB delta: skip emit if every position is byte-equal to
        # last. dict equality on int values is what we want — no float
        # rounding, no key-order dependence.
        if cur == self._last_positions:
            return None
        self._last_positions = cur
        return LearnMidiPosition.make(
            controller_id=self._profile.id,
            positions=cur,
        ).to_dict()

    # ------------------------------------------------------------------
    # controller_detected path (pure builder + queued path)
    # ------------------------------------------------------------------

    def controller_detected(
        self,
        *,
        connected: bool,
        profile: ControllerProfile,
        port_name: str,
    ) -> dict:
        """Pure builder. Returns the ``LearnControllerDetected`` envelope
        dict. Does NOT enqueue, does NOT emit — callers either use this
        directly (rare; tests / one-shot diagnostics) or, in production,
        use :meth:`queue_controller_detected` which builds-and-enqueues
        in one locked step.
        """
        return LearnControllerDetected.make(
            connected=connected,
            controller_id=profile.id,
            display_name=profile.display_name,
            port_name=port_name,
        ).to_dict()

    def queue_controller_detected(
        self,
        *,
        connected: bool,
        profile: ControllerProfile,
        port_name: str,
    ) -> None:
        """Thread-safe enqueue path. The port_watcher callback in
        ``__main__`` calls this on every ``('connected', port, profile)``
        / ``('disconnected', port, profile)`` event. The 30 Hz tick in
        ``ws_broadcast`` drains via :meth:`drain_pending_detected` and
        emits each pending envelope through the shared ``_send_all``
        closure — there is NO direct cross-coroutine call into
        ``_send_all`` from the callback path (that closure is not
        reachable from outside ``ws_broadcast``).

        Lock window: a single ``list.append`` while ``_detected_lock`` is
        held. Microseconds. Never held across an await. Returns None.
        """
        envelope = self.controller_detected(
            connected=connected,
            profile=profile,
            port_name=port_name,
        )
        with self._detected_lock:
            self._pending_detected.append(envelope)

    def drain_pending_detected(self) -> list[dict]:
        """Locked copy + clear. Returns a shallow copy of the currently
        pending ``controller_detected`` envelopes and clears the
        underlying list. Thread-safe under contention; the lock window
        is O(N) over the pending count (normally 0–1 — plug-in events
        are user-driven, ≤1/s in normal use).

        Called from ``ws_broadcast``'s 30 Hz tick BEFORE :meth:`snapshot`
        so a fresh plug-in's ``controller_detected`` envelope hits the
        wire before any ``midi_position`` envelope from the same
        controller — the webview sees "controller appeared" before it
        sees position data for that controller.
        """
        with self._detected_lock:
            drained = list(self._pending_detected)
            self._pending_detected.clear()
        return drained

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _read_current_positions(self) -> dict[str, int]:
        """Read the live :class:`ControllerState` into the wire shape.

        Uses :meth:`ControllerState.deck_snapshot` which already lock-guards
        the read (``state.py:144``) — a single thread-safe read; we never
        hold any lock outside :meth:`ControllerState.deck_snapshot`'s
        internal lock window.

        Wire shape (RESEARCH §Pattern 2):

        * Deck-bound CC knobs/faders: ``"<field>:<deck>"`` → integer 0..127
          (e.g. ``"eq_hi:A": 64``).
        * Deck-bound buttons: ``"<field>:<deck>"`` → 0 / 1 (e.g.
          ``"play:A": 0``).
        * Master-section: bare ``"<field>"`` → integer 0..127 (e.g.
          ``"xfader": 64``).
        """
        snap = self._cs.deck_snapshot()
        out: dict[str, int] = {}
        # Per-deck CC knobs/faders + boolean buttons. The ControllerState
        # `deck_snapshot()` shape is `{"A": {field: int, ...}, "B": {...},
        # "xfader": int, "connected": bool}` (vibemix/midi/state.py:404).
        # Skip the master-section + bookkeeping keys; everything else is
        # a deck dict.
        for deck_letter, deck_dict in snap.items():
            if deck_letter in ("xfader", "connected"):
                continue
            if not isinstance(deck_dict, dict):
                # Defensive: the shape is documented above; skip stray keys.
                continue
            # CC knobs/faders (0..127 native MIDI range).
            for field in ("vol", "eq_low", "eq_mid", "eq_hi", "filter", "tempo"):
                if field in deck_dict:
                    out[f"{field}:{deck_letter}"] = int(deck_dict[field])
            # Booleans (0/1 — schema accepts integer in [0, 127], so True
            # → 1 / False → 0 fits the same per-position int contract).
            for field in ("play", "cue", "jog_touched"):
                if field in deck_dict:
                    out[f"{field}:{deck_letter}"] = 1 if deck_dict[field] else 0
        # Master-section: xfader (bare field, no deck suffix).
        if "xfader" in snap:
            out["xfader"] = int(snap["xfader"])
        return out


__all__ = ["MidiMirror"]
