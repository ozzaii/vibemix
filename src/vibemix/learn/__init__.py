# SPDX-License-Identifier: Apache-2.0
"""Phase 91 ``vibemix.learn`` subpackage — controller renderer + MIDI mirror.

Backend half of the Learn surface (RENDER-01 / RENDER-02). The Tauri Learn
window subscribes to the ipc.learn.* envelopes produced here over the shared
ws:8765 socket (Invariant #4 preserved — no second WS listener bound here).

Public surface:

* :class:`MidiMirror` — the 30 Hz delta-coalesced controller-position
  snapshotter + thread-safe ``controller_detected`` queue. Sole writer of
  ``ipc.learn.midi_position`` envelopes; read-only consumer of
  :class:`vibemix.midi.state.ControllerState`.

Single-writer invariant (#1): :class:`MidiMirror` never mutates
``MusicState``, ``ControllerState``, or any other state. Pure reader of
``ControllerState.deck_snapshot()``; pure builder of the envelope dicts.
"""
from __future__ import annotations

from vibemix.learn.midi_mirror import MidiMirror

__all__ = ["MidiMirror"]
