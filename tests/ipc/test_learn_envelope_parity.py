# SPDX-License-Identifier: Apache-2.0
"""Phase 91 Plan 02 — ipc.learn.* envelope parity tests.

The two envelopes landed in Plan 01 (commits ``905e1550`` + ``de4808ce``):

* ``LearnControllerDetected`` — single-fire per MIDI port-bind / unbind
* ``LearnMidiPosition``       — 30 Hz delta-suppressed position snapshot

This file pins their wire shapes via four targeted tests, mirroring the
shape of ``tests/ipc/test_session_messages.py`` (the canonical envelope
round-trip + reject-on-invalid-field pattern in this repo):

1. ``test_controller_detected_roundtrip`` — happy-path: ``.make(...)`` →
   ``.to_dict()`` → ``_VALIDATOR.validate(...)`` passes.
2. ``test_controller_detected_rejects_missing_field`` — drop a required
   field on the payload; validation MUST raise ``jsonschema.ValidationError``.
3. ``test_midi_position_roundtrip`` — happy-path with a realistic 13-key
   ``positions`` dict (FLX4 deck-bound + master-section shape from
   RESEARCH §Pattern 2).
4. ``test_midi_position_rejects_out_of_range`` — mutate one position to
   ``128`` (above the schema's ``maximum: 127``); validation MUST raise.

The schema enforces ``additionalProperties: false`` on every payload and
``minLength: 1`` on string identifiers; the per-position values are
``additionalProperties: {type: integer, minimum: 0, maximum: 127}`` (native
MIDI CC range — Plan 01 SUMMARY §Decisions).

This is a TEST FILE — it expects Plan 01's ``learn_messages.py`` to exist
already. The ``pytest.importorskip`` at module top guards the case where
this file is executed against a pre-Plan-01 checkout (defensive only —
shouldn't fire on the live branch).

REQ-ID: RENDER-01 (controller_detected wire shape) + RENDER-02
(midi_position wire shape).
"""
from __future__ import annotations

import json

import jsonschema
import pytest

# Defensive importorskip — Plan 01 already landed learn_messages.py on
# live-tuning-or-brain; this guard only fires on a pre-91-01 checkout.
learn_messages = pytest.importorskip(
    "vibemix.ui_bus.learn_messages",
    reason="Plan 91-01 lands src/vibemix/ui_bus/learn_messages.py",
)

LearnControllerDetected = learn_messages.LearnControllerDetected
LearnMidiPosition = learn_messages.LearnMidiPosition

# Shared validator from the canonical messages module (Draft-07; cached).
from vibemix.ui_bus.messages import _VALIDATOR  # noqa: E402

# ---------------------------------------------------------------------------
# LearnControllerDetected
# ---------------------------------------------------------------------------


def _make_controller_detected() -> LearnControllerDetected:
    return LearnControllerDetected.make(
        connected=True,
        controller_id="pioneer_ddj_flx4",
        display_name="Pioneer DDJ-FLX4",
        port_name="DDJ-FLX4 USB MIDI Input",
    )


def test_controller_detected_roundtrip() -> None:
    """Happy path — ``.make(...)`` → ``.to_dict()`` validates cleanly."""
    msg = _make_controller_detected()
    raw = msg.to_json()
    parsed = json.loads(raw)
    assert parsed["type"] == "ipc.learn.controller_detected"
    assert parsed["payload"]["controller_id"] == "pioneer_ddj_flx4"
    assert parsed["payload"]["connected"] is True
    assert parsed["payload"]["display_name"] == "Pioneer DDJ-FLX4"
    assert parsed["payload"]["port_name"] == "DDJ-FLX4 USB MIDI Input"
    _VALIDATOR.validate(parsed)


def test_controller_detected_rejects_missing_field() -> None:
    """Dropping a required payload field must fail schema validation
    (``additionalProperties: false`` + ``required`` array on the
    LearnControllerDetected payload struct)."""
    parsed = json.loads(_make_controller_detected().to_json())
    del parsed["payload"]["controller_id"]  # required field
    with pytest.raises(jsonschema.ValidationError):
        _VALIDATOR.validate(parsed)


# ---------------------------------------------------------------------------
# LearnMidiPosition
# ---------------------------------------------------------------------------


def _flx4_positions() -> dict[str, int]:
    """Representative wire shape — FLX4 deck-bound + master-section keys
    per RESEARCH §Pattern 2 ``midi_position`` example."""
    return {
        "eq_hi:A": 64, "eq_mid:A": 64, "eq_low:A": 64,
        "vol:A": 0, "filter:A": 64, "tempo:A": 64,
        "eq_hi:B": 64, "eq_mid:B": 64, "eq_low:B": 64,
        "vol:B": 0, "filter:B": 64, "tempo:B": 64,
        "xfader": 64,
    }


def _make_midi_position() -> LearnMidiPosition:
    return LearnMidiPosition.make(
        controller_id="pioneer_ddj_flx4",
        positions=_flx4_positions(),
    )


def test_midi_position_roundtrip() -> None:
    """Happy path — 13-key FLX4 wire shape validates cleanly."""
    msg = _make_midi_position()
    parsed = json.loads(msg.to_json())
    assert parsed["type"] == "ipc.learn.midi_position"
    assert parsed["payload"]["controller_id"] == "pioneer_ddj_flx4"
    assert parsed["payload"]["positions"]["eq_hi:A"] == 64
    assert parsed["payload"]["positions"]["xfader"] == 64
    _VALIDATOR.validate(parsed)


def test_midi_position_rejects_out_of_range() -> None:
    """A ``positions`` value of ``128`` is above the schema's
    ``additionalProperties: {type: integer, minimum: 0, maximum: 127}`` —
    native MIDI CC max. Validation MUST reject."""
    parsed = json.loads(_make_midi_position().to_json())
    parsed["payload"]["positions"]["eq_hi:A"] = 128  # out of range (max 127)
    with pytest.raises(jsonschema.ValidationError):
        _VALIDATOR.validate(parsed)
