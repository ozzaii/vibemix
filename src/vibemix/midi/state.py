# SPDX-License-Identifier: Apache-2.0
"""ControllerState — live MIDI decoder, parameterized by ControllerProfile.

Phase 9 Wave 1 extraction: previously hardcoded to the v4 DDJ-FLX4
``_CC_MAP`` / ``_NOTE_MAP`` constants in ``vibemix.platform._midi_macos``,
this module is now the single source of truth for the live decoder. The
constants live in ``vibemix.midi.profiles/<id>.json`` and are loaded into
``self._cc_lookup`` / ``self._note_lookup`` at construction time.

What's preserved byte-equivalently from v4:
- ``_knob_label`` 6-tier mapping (v4:601-607).
- ``_xfader_label`` 5-tier mapping (v4:610-615).
- ``deck_snapshot()`` shape: ``{deck_letter: {vol/eq/filter/tempo/play/cue/jog_touched}, xfader, connected}``.
- ``moves_since(t)`` output: ``[(seconds_ago_rounded_to_0.1, label), ...]``.
- The dedup-within-400ms collapse (v4:646-648).
- The 12s ring trim (v4:650-652).
- The loop_in→play implicit-start workaround (v4:700).
- The jog_touch velocity gate (v4:697-698 + v4:707-710).
- The vol/tempo big-delta-threshold (>15) gate.
- The EQ tier-cross gate.

What's new in Wave 1 (additive — moves ring is byte-equivalent):
- ``MidiEvent`` typed records with magnitude in ``[-1.0, 1.0]`` (signed for
  direction). For ``axis='unipolar'``: ``mag = (v - prev) / 127`` (signed
  delta — surface direction-of-twist for Coach prompts; ``abs(mag)`` is in
  ``[0, 1]`` by convention). For ``axis='bipolar'``: ``mag = (v - 64) / 63``
  (signed absolute position from center). Buttons emit MidiEvent with
  ``magnitude=None``.
- ``events_since(t)`` symmetric to ``moves_since(t)`` returning ``list[MidiEvent]``.

Threading: ``threading.Lock`` protects ``deck`` / ``xfader`` / ``_moves`` /
``_events`` / ``_connected`` / ``port_name`` — same pattern as v4. The
listener thread (``_midi_common.midi_listener_thread``) calls ``handle_msg``
on every polled MIDI message; the asyncio state-refresh loop reads
``deck_snapshot()`` and ``moves_since(t)`` / ``events_since(t)`` from the
main event loop.
"""

from __future__ import annotations

import sys
import threading
import time
from dataclasses import dataclass

from vibemix.midi.generic import GENERIC_MIDI_ID
from vibemix.midi.profile import ButtonBinding, ControlBinding, ControllerProfile


def _knob_label(v: int) -> str:
    """6-tier EQ/filter knob mapping (v4:601-607 verbatim — DO NOT TUNE)."""
    if v < 8:
        return "killed"
    if v < 30:
        return "deep-cut"
    if v < 55:
        return "cut"
    if v <= 73:
        return "flat"
    if v <= 100:
        return "boost"
    return "max"


def _xfader_label(v: int) -> str:
    """5-tier xfader mapping (v4:610-615 verbatim — DO NOT TUNE)."""
    if v < 16:
        return "full-A"
    if v < 48:
        return "A-side"
    if v <= 80:
        return "center"
    if v <= 112:
        return "B-side"
    return "full-B"


def _clamp(value: float, lo: float, hi: float) -> float:
    """Clamp a float into the inclusive [lo..hi] range."""
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


@dataclass(frozen=True)
class MidiEvent:
    """Typed MIDI event emitted by ControllerState — additive to the v4 moves
    ring. Hashable + frozen so consumers can stash references freely.

    Fields:
        id: monotonic counter, unique per ControllerState instance.
        at: epoch seconds (``time.time()`` at handle_msg dispatch).
        kind: ``'cc'`` for knobs/faders/xfader, OR a button kind from the
            profile (``'play'``, ``'cue'``, ``'sync'``, ``'jog_touch'``,
            ``'loop_in'``, ``'loop_out'``, ...).
        deck: ``'A'`` / ``'B'`` / ... or None for master-section controls
            (xfader has ``deck=None``).
        field: semantic field name (``'eq_hi'``, ``'xfader'``, ``'vol'``,
            ...). None for buttons.
        value_raw: 0..127 raw MIDI value (CC value or note velocity).
        magnitude: signed unit-interval delta. Set for ``kind='cc'``:
            unipolar = ``(v - prev) / 127`` (signed); bipolar = ``(v - 64) / 63``
            (signed-from-center). None for buttons + jog_touch.
    """

    id: int
    at: float
    kind: str
    deck: str | None
    field: str | None
    value_raw: int
    magnitude: float | None


class ControllerState:
    """Live decoded controller state — lock-protected, profile-parameterized.

    Replaces the v4 module-globals (``_CC_MAP`` / ``_NOTE_MAP``) with per-
    instance lookup tables built from the bound ``ControllerProfile``. The
    decoder body is byte-equivalent to v4 (cohost_v4.py:618-727); the
    additional ``MidiEvent`` ring is purely additive.

    Constructor:
        ``ControllerState(profile=load_profile('pioneer_ddj_flx4'))``

    Public surface (matches Phase 7 + adds events_since):
        - ``mark_connected(port_name)`` — listener thread signals device open.
        - ``is_connected() -> bool``.
        - ``handle_msg(msg)`` — dispatch a MIDI message (``mido.Message`` or
          structurally equivalent SimpleNamespace).
        - ``deck_snapshot() -> dict`` — deep-copy snapshot with deck letters
          from ``profile.decks`` plus ``xfader`` + ``connected``.
        - ``moves_since(t) -> list[(age_secs, label)]`` — v4 string ring.
        - ``events_since(t) -> list[MidiEvent]`` — Wave 1 typed-event ring.

    Threading: ``threading.Lock`` guards the mutable state. v4 pattern preserved.
    """

    def __init__(self, *, profile: ControllerProfile):
        self._profile = profile
        self._lock = threading.Lock()

        # Per-deck dict — keys derive from profile.decks (FLX4 → A,B; future
        # 4-deck profiles → A,B,C,D). Defaults match v4: vol=0, EQ/filter/tempo=64,
        # play/cue/jog_touched=False.
        self.deck: dict[str, dict] = {
            d: {
                "vol": 0,
                "eq_low": 64,
                "eq_mid": 64,
                "eq_hi": 64,
                "filter": 64,
                "tempo": 64,
                "play": False,
                "cue": False,
                "jog_touched": False,
            }
            for d in profile.decks
        }
        self.xfader = 64
        self._moves: list[tuple[float, str]] = []
        self._events: list[MidiEvent] = []
        self._next_event_id = 0
        self._connected = False
        self.port_name = ""

        # Build lookup tables from the profile bindings (replaces v4 module
        # globals). Keys are (channel, cc) and (channel, note) tuples — same
        # shape as v4 _CC_MAP / _NOTE_MAP so existing call patterns transfer.
        self._cc_lookup: dict[tuple[int, int], ControlBinding] = {
            (b.channel, b.cc): b for b in profile.controls.values()
        }
        self._note_lookup: dict[tuple[int, int], ButtonBinding] = {
            (b.channel, b.note): b for b in profile.buttons.values()
        }

    def mark_connected(self, port_name: str) -> None:
        with self._lock:
            self._connected = True
            self.port_name = port_name

    def mark_disconnected(self) -> None:
        """Symmetric to ``mark_connected`` — clears the connected flag (used
        by the Phase 9 Wave 2 ``handle_port_change`` callback when the bound
        port disappears mid-session)."""
        with self._lock:
            self._connected = False

    def is_connected(self) -> bool:
        with self._lock:
            return self._connected

    def _record_move(self, label: str, now: float) -> None:
        """Append to v4 moves ring. Dedup same-label-within-400ms; trim 12s.

        Caller must hold ``self._lock``.
        """
        if self._moves and (now - self._moves[-1][0] < 0.4) and self._moves[-1][1] == label:
            return
        self._moves.append((now, label))
        cutoff = now - 12.0
        while self._moves and self._moves[0][0] < cutoff:
            self._moves.pop(0)

    def _record_event(
        self,
        *,
        kind: str,
        deck: str | None,
        field: str | None,
        value_raw: int,
        magnitude: float | None,
        now: float,
    ) -> None:
        """Append to MidiEvent ring (Wave 1 additive). Trim 12s like _moves.

        Caller must hold ``self._lock``.
        """
        ev = MidiEvent(
            id=self._next_event_id,
            at=now,
            kind=kind,
            deck=deck,
            field=field,
            value_raw=value_raw,
            magnitude=magnitude,
        )
        self._next_event_id += 1
        self._events.append(ev)
        cutoff = now - 12.0
        while self._events and self._events[0].at < cutoff:
            self._events.pop(0)

    def _compute_magnitude(self, axis: str, prev: int, v: int) -> float:
        """Compute signed magnitude per CONTEXT §Magnitude semantics.

        - unipolar: ``(v - prev) / 127`` — signed delta surfaces direction.
        - bipolar: ``(v - 64) / 63`` — signed absolute position from center.

        Both clamped to ``[-1.0, 1.0]``.
        """
        if axis == "unipolar":
            mag = (v - prev) / 127.0
        elif axis == "bipolar":
            mag = (v - 64) / 63.0
        else:
            mag = 0.0
        return _clamp(mag, -1.0, 1.0)

    def handle_msg(self, msg) -> None:
        """Decode a single MIDI message — verbatim v4 control flow with
        per-instance lookup tables instead of module globals, plus additive
        MidiEvent emission.

        Phase 9 Wave 2: when the bound profile is the synthesized
        GENERIC_MIDI fallback (id == 'generic_midi'), dispatch goes to
        ``_handle_generic`` which decodes any CC into a positional event
        + move label (no semantic deck/field assignment). Keeps the v4
        byte-equivalent path strictly separate from the generic path so
        the FLX4 golden tests stay immutable.
        """
        if self._profile.id == GENERIC_MIDI_ID:
            return self._handle_generic(msg)
        now = time.time()
        try:
            if msg.type == "control_change":
                key = (msg.channel, msg.control)
                binding = self._cc_lookup.get(key)
                if binding is None:
                    return
                v = msg.value
                deck = binding.deck if binding.deck is not None else "M"
                field = binding.field
                with self._lock:
                    if field == "xfader":
                        prev = self.xfader
                        self.xfader = v
                        if _xfader_label(prev) != _xfader_label(v):
                            self._record_move(f"xfader→{_xfader_label(v)}", now)
                        mag = self._compute_magnitude(binding.axis, prev, v)
                        self._record_event(
                            kind="cc",
                            deck=binding.deck,
                            field=field,
                            value_raw=v,
                            magnitude=mag,
                            now=now,
                        )
                    else:
                        prev = self.deck[deck][field]
                        self.deck[deck][field] = v
                        abs_d = abs(v - prev)
                        mag_label = "small" if abs_d < 15 else ("medium" if abs_d < 40 else "big")
                        if field in ("vol", "tempo"):
                            if abs_d > 15:
                                direction = "up" if v > prev else "down"
                                self._record_move(f"{deck}_{field} {direction} ({mag_label})", now)
                        elif field in ("eq_low", "eq_mid", "eq_hi", "filter"):
                            if _knob_label(prev) != _knob_label(v):
                                self._record_move(
                                    f"{deck}_{field.replace('eq_', '')}: "
                                    f"{_knob_label(prev)}→{_knob_label(v)} "
                                    f"({mag_label} twist)",
                                    now,
                                )
                        mag = self._compute_magnitude(binding.axis, prev, v)
                        self._record_event(
                            kind="cc",
                            deck=binding.deck,
                            field=field,
                            value_raw=v,
                            magnitude=mag,
                            now=now,
                        )
            elif msg.type == "note_on":
                key = (msg.channel, msg.note)
                binding = self._note_lookup.get(key)
                if binding is None:
                    return
                deck = binding.deck if binding.deck is not None else "M"
                kind = binding.kind
                with self._lock:
                    if kind == "play":
                        # KNOWN ISSUE (Phase 9): the FLX4 firmware sometimes
                        # doesn't emit note_on for play while djay Pro is in
                        # focus → play flag stays at boot default False. See
                        # _midi_macos module docstring.
                        self.deck[deck]["play"] = not self.deck[deck]["play"]
                        self._record_move(
                            f"{deck}_play→{'ON' if self.deck[deck]['play'] else 'OFF'}", now
                        )
                    elif kind == "cue":
                        self._record_move(f"{deck}_cue_hit", now)
                    elif kind == "sync":
                        self._record_move(f"{deck}_sync_hit", now)
                    elif kind == "jog_touch":
                        self.deck[deck]["jog_touched"] = msg.velocity > 0
                    elif kind == "loop_in":
                        # Workaround — loop_in implicitly starts play (v4:700).
                        self.deck[deck]["play"] = True
                        self._record_move(f"{deck}_loop_in_hit (play=ON)", now)
                    elif kind == "loop_out":
                        self._record_move(f"{deck}_loop_out_hit", now)
                    # Always record the typed event (no magnitude for buttons).
                    self._record_event(
                        kind=kind,
                        deck=binding.deck,
                        field=None,
                        value_raw=msg.velocity,
                        magnitude=None,
                        now=now,
                    )
            elif msg.type == "note_off":
                key = (msg.channel, msg.note)
                binding = self._note_lookup.get(key)
                if binding is None:
                    return
                deck = binding.deck if binding.deck is not None else "M"
                if binding.kind == "jog_touch":
                    with self._lock:
                        self.deck[deck]["jog_touched"] = False
        except Exception as e:
            print(f"[midi handle err] {e}", file=sys.stderr)

    def deck_snapshot(self) -> dict:
        """Static snapshot — used by MusicState to compute audible deck weights.

        Returns a fresh dict with copies of every deck plus ``xfader`` and
        ``connected`` (caller cannot mutate listener-thread state through the
        returned dict).
        """
        with self._lock:
            snap: dict = {d: dict(self.deck[d]) for d in self.deck}
            snap["xfader"] = self.xfader
            snap["connected"] = self._connected
            return snap

    def moves_since(self, t: float) -> list[tuple[float, str]]:
        """Returns ``[(seconds_ago_rounded_to_0.1, label), ...]`` — note the
        time-relative conversion (v4:724-727)."""
        with self._lock:
            now = time.time()
            return [(round(now - mt, 1), label) for mt, label in self._moves if mt > t]

    def events_since(self, t: float) -> list[MidiEvent]:
        """Returns the typed-event ring filtered to ``event.at > t``.

        Symmetric to ``moves_since`` but returns ``MidiEvent`` records (with
        magnitude for cc events, None for buttons). Phase 10 prompt rendering
        thresholds on ``abs(magnitude)``.
        """
        with self._lock:
            return [ev for ev in self._events if ev.at > t]

    def _handle_generic(self, msg) -> None:
        """Generic-MIDI decode path (Phase 9 Wave 2).

        Emits positional events for every CC + note_on (velocity > 0)
        without consulting profile.controls / profile.buttons (both empty
        for the generic profile). Field names encode channel + cc/note so
        Phase 10's prompt rendering can disambiguate the moves even
        without semantic deck/field assignment.

        Silent / no-op for: note_off, note_on velocity=0, any other
        message type (pitchwheel, program_change, aftertouch, sysex).
        Graceful degradation is the whole point of the generic fallback.
        """
        now = time.time()
        try:
            mtype = getattr(msg, "type", None)
            if mtype == "control_change":
                ch = msg.channel
                cc = msg.control
                v = msg.value
                field = f"cc_{ch}_{cc}"
                magnitude = v / 127.0
                pct = int(magnitude * 100)
                label = f"{field}→{v} ({pct}%)"
                with self._lock:
                    self._record_move(label, now)
                    self._record_event(
                        kind="generic_cc",
                        deck=None,
                        field=field,
                        value_raw=v,
                        magnitude=magnitude,
                        now=now,
                    )
            elif mtype == "note_on":
                if getattr(msg, "velocity", 0) <= 0:
                    return  # note_on velocity=0 == note_off alias
                ch = msg.channel
                n = msg.note
                v = msg.velocity
                field = f"note_{ch}_{n}"
                label = f"{field}_pressed"
                with self._lock:
                    self._record_move(label, now)
                    self._record_event(
                        kind="generic_note",
                        deck=None,
                        field=field,
                        value_raw=v,
                        magnitude=None,
                        now=now,
                    )
            # note_off + every other message type: silent.
        except Exception as e:
            print(f"[midi handle err] {e}", file=sys.stderr)


__all__ = ["ControllerState", "MidiEvent", "_knob_label", "_xfader_label"]
