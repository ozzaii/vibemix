# SPDX-License-Identifier: Apache-2.0
"""MidiBackend protocol — MIDI port enumeration + non-blocking message poll.

Lifted from cohost_v3.py:704-730 (midi_listener_thread) and PITFALLS P11 (hot-plug — the
DDJ-FLX4 may be unplugged + replugged mid-session, listener must re-enumerate on a ~2s
cadence). Phase 3 macOS impl wraps mido + python-rtmidi; Phase 8 Windows impl uses the
same backend (mido is cross-platform).

The Protocol is intentionally minimal — ControllerState, deck_snapshot(), moves_since(),
and DDJ-specific CC/Note maps belong to the controller-profile abstraction landing in
Phase 9, NOT this surface.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class MidiMessage(Protocol):
    """Structural minimum of a MIDI message. mido.Message satisfies this.

    Backends MUST emit messages whose attribute names match mido conventions so POC
    decoders port wholesale: `control`/`value` when type == 'control_change';
    `note`/`velocity` when type in {'note_on', 'note_off'}. Additional attributes
    are allowed (Protocol is structural, not nominal).
    """

    type: str
    channel: int


@runtime_checkable
class MidiPort(Protocol):
    """Open MIDI input port handle. poll() is non-blocking; close() releases the OS handle."""

    name: str

    def poll(self) -> MidiMessage | None: ...

    def close(self) -> None: ...


@runtime_checkable
class MidiBackend(Protocol):
    """MIDI input firewall — list ports + open one for polling.

    Hot-plug rescan is the caller's concern: re-invoke list_input_ports() on a ~2s
    cadence per the POC pattern at cohost_v3.py:720-728. The backend does NOT push
    events — pull only.
    """

    def list_input_ports(self) -> list[str]: ...

    def open_input(self, port_name: str) -> MidiPort: ...
