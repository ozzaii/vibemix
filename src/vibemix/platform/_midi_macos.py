# SPDX-License-Identifier: Apache-2.0
"""MidiMacOS — MidiBackend implementation for macOS via ``mido`` + python-rtmidi.

Verbatim port of cohost_v4.py:580-757 (DDJ-FLX4 CC/Note maps + ControllerState
+ midi_listener_thread).

KNOWN ISSUE (Phase 9): Pioneer DDJ-FLX4 play-state propagation
-----------------------------------------------------------------
The _NOTE_MAP DOES map note ``0x0B`` → ``'play'``. ``ControllerState.handle_msg``
DOES toggle ``deck[deck]['play']`` on ``note_on``. BUT when djay Pro is the
active controlling app, the FLX4 firmware sometimes consumes play presses
locally without forwarding ``note_on`` to other listeners. Result:
``deck['play']`` stays at boot-default ``False`` → ``derive_audible_deck``
returns ``"none"`` → ``derive_audible_track`` confidence capped at ``0.3`` →
``TRACK_CHANGE`` event (which requires ``audible_track_confidence >=
TRACK_CHANGE_MIN_CONFIDENCE = 0.5``) never fires.

Phase 3 reproduces v4 verbatim. Phase 9 fix is the docket — likely cross-
reference with nowplaying-cli's playback-state, IAC port if available, or
audio-side "deck has signal energy" fallback.

Phase 9 also: curated 10-controller library (Pioneer DDJ-400/FLX4/FLX6/FLX10/
1000/SX3 + XDJ-RX3 + Numark Party Mix Live + Hercules Inpulse 300/500) +
generic positional fallback + hot-plug rescan. Phase 3 ships the DDJ-FLX4
maps only and enumerates the port once at listener-thread start (with retry-
every-2s on disconnect).
"""

from __future__ import annotations

import sys
import threading
import time

try:
    import mido

    _HAS_MIDO = True
except ImportError:
    mido = None  # type: ignore[assignment]
    _HAS_MIDO = False

from vibemix.platform.midi import MidiMessage, MidiPort

# ---- DDJ-FLX4 controller maps (verbatim from cohost_v4.py:582-598) ----
# (midi_channel, cc_number) → (deck, field). Channels 0/1 = decks A/B,
# channel 6 = master section (filter knobs + xfader). All values 0..127.
_CC_MAP = {
    (0, 0x13): ("A", "vol"),
    (1, 0x13): ("B", "vol"),
    (0, 0x07): ("A", "eq_hi"),
    (1, 0x07): ("B", "eq_hi"),
    (0, 0x0B): ("A", "eq_mid"),
    (1, 0x0B): ("B", "eq_mid"),
    (0, 0x0F): ("A", "eq_low"),
    (1, 0x0F): ("B", "eq_low"),
    (0, 0x00): ("A", "tempo"),
    (1, 0x00): ("B", "tempo"),
    (6, 0x17): ("A", "filter"),
    (6, 0x18): ("B", "filter"),
    (6, 0x1F): ("M", "xfader"),
}
_NOTE_MAP = {
    (0, 0x0B): ("A", "play"),
    (1, 0x0B): ("B", "play"),
    (0, 0x0C): ("A", "cue"),
    (1, 0x0C): ("B", "cue"),
    (0, 0x60): ("A", "sync"),
    (1, 0x60): ("B", "sync"),
    (0, 0x36): ("A", "jog_touch"),
    (1, 0x36): ("B", "jog_touch"),
    (0, 0x10): ("A", "loop_in"),
    (1, 0x10): ("B", "loop_in"),
    (0, 0x11): ("A", "loop_out"),
    (1, 0x11): ("B", "loop_out"),
}


def _knob_label(v: int) -> str:
    """6-tier EQ/filter knob mapping (v4:601-607 verbatim)."""
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
    """5-tier xfader mapping (v4:610-615 verbatim)."""
    if v < 16:
        return "full-A"
    if v < 48:
        return "A-side"
    if v <= 80:
        return "center"
    if v <= 112:
        return "B-side"
    return "full-B"


class ControllerState:
    """Live decoded DDJ-FLX4 state. Lock-protected. Tracks recent moves only —
    the AI sees deltas, never static positions (those are background context).

    Verbatim port of cohost_v4.py:618-727.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self.deck = {
            "A": {
                "vol": 0,
                "eq_low": 64,
                "eq_mid": 64,
                "eq_hi": 64,
                "filter": 64,
                "tempo": 64,
                "play": False,
                "cue": False,
                "jog_touched": False,
            },
            "B": {
                "vol": 0,
                "eq_low": 64,
                "eq_mid": 64,
                "eq_hi": 64,
                "filter": 64,
                "tempo": 64,
                "play": False,
                "cue": False,
                "jog_touched": False,
            },
        }
        self.xfader = 64
        self._moves: list[tuple[float, str]] = []
        self._connected = False
        self.port_name = ""

    def mark_connected(self, port_name: str):
        with self._lock:
            self._connected = True
            self.port_name = port_name

    def is_connected(self) -> bool:
        with self._lock:
            return self._connected

    def _record_move(self, label: str, now: float):
        # Dedupe: same label within 0.4s collapses (prevents jog-wheel spam).
        if self._moves and (now - self._moves[-1][0] < 0.4) and self._moves[-1][1] == label:
            return
        self._moves.append((now, label))
        cutoff = now - 12.0
        while self._moves and self._moves[0][0] < cutoff:
            self._moves.pop(0)

    def handle_msg(self, msg) -> None:
        now = time.time()
        try:
            if msg.type == "control_change":
                key = (msg.channel, msg.control)
                if key not in _CC_MAP:
                    return
                deck, field = _CC_MAP[key]
                v = msg.value
                with self._lock:
                    if deck == "M":
                        prev = self.xfader
                        self.xfader = v
                        if _xfader_label(prev) != _xfader_label(v):
                            self._record_move(f"xfader→{_xfader_label(v)}", now)
                    else:
                        prev = self.deck[deck][field]
                        self.deck[deck][field] = v
                        abs_d = abs(v - prev)
                        mag = "small" if abs_d < 15 else ("medium" if abs_d < 40 else "big")
                        if field in ("vol", "tempo"):
                            if abs_d > 15:
                                direction = "up" if v > prev else "down"
                                self._record_move(f"{deck}_{field} {direction} ({mag})", now)
                        elif field in ("eq_low", "eq_mid", "eq_hi", "filter"):
                            if _knob_label(prev) != _knob_label(v):
                                self._record_move(
                                    f"{deck}_{field.replace('eq_', '')}: "
                                    f"{_knob_label(prev)}→{_knob_label(v)} ({mag} twist)",
                                    now,
                                )
            elif msg.type == "note_on":
                key = (msg.channel, msg.note)
                if key not in _NOTE_MAP:
                    return
                deck, field = _NOTE_MAP[key]
                with self._lock:
                    if field == "play":
                        # KNOWN ISSUE (Phase 9): the FLX4 firmware sometimes
                        # doesn't emit note_on for play while djay Pro is in
                        # focus → play flag stays at boot default False. See
                        # module docstring.
                        self.deck[deck]["play"] = not self.deck[deck]["play"]
                        self._record_move(
                            f"{deck}_play→{'ON' if self.deck[deck]['play'] else 'OFF'}", now
                        )
                    elif field == "cue":
                        self._record_move(f"{deck}_cue_hit", now)
                    elif field == "sync":
                        self._record_move(f"{deck}_sync_hit", now)
                    elif field == "jog_touch":
                        self.deck[deck]["jog_touched"] = msg.velocity > 0
                    elif field == "loop_in":
                        # Workaround — loop_in implicitly starts play.
                        self.deck[deck]["play"] = True
                        self._record_move(f"{deck}_loop_in_hit (play=ON)", now)
                    elif field == "loop_out":
                        self._record_move(f"{deck}_loop_out_hit", now)
            elif msg.type == "note_off":
                key = (msg.channel, msg.note)
                if key in _NOTE_MAP:
                    deck, field = _NOTE_MAP[key]
                    if field == "jog_touch":
                        with self._lock:
                            self.deck[deck]["jog_touched"] = False
        except Exception as e:
            print(f"[midi handle err] {e}", file=sys.stderr)

    def deck_snapshot(self) -> dict:
        """Static snapshot — used by MusicState to compute audible deck weights.

        Returns a fresh dict with copies of deck A and B (caller cannot mutate
        listener-thread state through the returned dict)."""
        with self._lock:
            return {
                "A": dict(self.deck["A"]),
                "B": dict(self.deck["B"]),
                "xfader": self.xfader,
                "connected": self._connected,
            }

    def moves_since(self, t: float) -> list[tuple[float, str]]:
        """Returns ``[(seconds_ago_rounded_to_0.1, label), ...]`` — note the
        time-relative conversion (v4:724-727)."""
        with self._lock:
            now = time.time()
            return [(round(now - mt, 1), label) for mt, label in self._moves if mt > t]


class _MidoPortAdapter:
    """Wraps ``mido.IOPort`` to satisfy the Phase 1 ``MidiPort`` Protocol.

    Phase 1 Protocol requires: ``name: str``, ``poll() -> MidiMessage | None``,
    ``close() -> None``. mido provides ``poll`` and ``close`` directly; we just
    pin ``name`` as an attribute.
    """

    def __init__(self, port, name: str):
        self._port = port
        self.name = name

    def poll(self) -> MidiMessage | None:
        return self._port.poll()

    def close(self) -> None:
        self._port.close()


class MidiMacOS:
    """MidiBackend impl wrapping ``mido`` + the v4 ControllerState.

    Exposes:
    - ``controller_state`` (the v4 ControllerState instance) so state_refresh_loop
      can call ``.deck_snapshot()`` + ``.moves_since(t)`` directly.
    - ``list_input_ports()`` / ``open_input(name)`` (Phase 1 Protocol surface).
    - ``start_listener_thread(stop_event)`` — spawns the v4:730-756 daemon
      thread for the DDJ-FLX4 polling loop. Returns the Thread object so
      callers can join on shutdown.
    """

    def __init__(self):
        self.controller_state = ControllerState()

    def list_input_ports(self) -> list[str]:
        if not _HAS_MIDO:
            return []
        return list(mido.get_input_names())

    def open_input(self, port_name: str) -> MidiPort:
        if not _HAS_MIDO:
            raise RuntimeError("mido not installed; cannot open MIDI input")
        port = mido.open_input(port_name)
        return _MidoPortAdapter(port, port_name)

    def start_listener_thread(self, stop_event: threading.Event) -> threading.Thread:
        """Spawn the v4:730-756 daemon thread. Retries every 2s on disconnect.

        Port hint: ``"DDJ-FLX4"`` (case-insensitive substring match).
        """

        def _run():
            if not _HAS_MIDO:
                print("-> mido not installed, MIDI controller disabled", file=sys.stderr)
                return

            port_hint = "DDJ-FLX4"
            while not stop_event.is_set():
                try:
                    ports = mido.get_input_names()
                    match = next((p for p in ports if port_hint.lower() in p.lower()), None)
                    if not match:
                        time.sleep(2.0)
                        continue
                    with mido.open_input(match) as port:
                        self.controller_state.mark_connected(match)
                        print(f"-> MIDI controller in: {match!r}")
                        while not stop_event.is_set():
                            msg = port.poll()
                            if msg is None:
                                time.sleep(0.005)
                                continue
                            self.controller_state.handle_msg(msg)
                except Exception as e:
                    print(f"[midi listener err] {e} — retrying in 2s", file=sys.stderr)
                    time.sleep(2.0)

        t = threading.Thread(target=_run, name="midi-listener", daemon=True)
        t.start()
        return t
