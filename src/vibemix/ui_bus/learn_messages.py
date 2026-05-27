# SPDX-License-Identifier: Apache-2.0
"""Phase 91 — ipc.learn.* envelope dataclasses.

Two envelopes land in P91:
  - LearnControllerDetected (sidecar→shell, single-fire per plug)
  - LearnMidiPosition       (sidecar→shell, 30 Hz delta-suppressed)

Mirrors of ``messages.schema.json::LearnControllerDetected`` +
``messages.schema.json::LearnMidiPosition``. Validation by the shared
``_VALIDATOR`` already loaded in :mod:`vibemix.ui_bus.messages` — we re-use,
not re-instantiate (Draft-07 ref-resolver is cached internally; compiling
twice would double the import cost for zero gain).

Convention parity with :mod:`vibemix.ui_bus.messages`:

* ``@dataclass(frozen=True, slots=True)`` everywhere (hashable wrappers,
  no per-instance ``__dict__``).
* Each top-level envelope has a ``.make(*, ...)`` keyword-only factory
  that stamps ``ts`` via :func:`vibemix.ui_bus.messages._now_iso`.
* ``.to_json()`` delegates to :func:`vibemix.ui_bus.messages._serialize`
  which asdict's, tuple→list normalises, validates against the shared
  schema, and json-dumps with compact separators (the wire form).
* ``.to_dict()`` is the convenience round-trip used by ipc_bus emitters
  that prefer a plain dict over a JSON string (matches the
  ``SessionOverlayHighlight.to_dict()`` pattern in messages.py).

Phase 91 RENDER-01 / RENDER-02 / RENDER-07. Plan 03 (Python backend
mirror service) consumes both wrappers; Plan 02 lands their unit tests
under TDD.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Literal

from vibemix.ui_bus.messages import _now_iso, _serialize


# ---------------------------------------------------------------------------
# Payload structs
# ---------------------------------------------------------------------------


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
