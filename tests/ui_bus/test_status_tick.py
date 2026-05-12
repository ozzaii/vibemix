# SPDX-License-Identifier: Apache-2.0
"""Focused tests for the ``ipc.status.tick`` shape.

UX-11 + D-Area-4.3 lock the four-field payload exactly. The plan asserts:

  * ``midi=null`` valid (no MIDI backend available).
  * ``midi=-1`` invalid (``minimum: 0`` in schema).
  * Unknown enum values rejected on every closed-enum field.
  * ``additionalProperties: false`` blocks any payload drift.

These cover the load-bearing invariants for the live UI status badge bar
that Phase 12 will surface. Wave 0 only ships the contract; runtime drift
detection at the WS boundary is Wave 4.
"""

from __future__ import annotations

import json

import jsonschema
import pytest

from vibemix.ui_bus import StatusTick
from vibemix.ui_bus.messages import _SCHEMA
from vibemix.ui_bus.validator import parse_message


def _wrap(payload: dict) -> dict:
    """Return a ``ipc.status.tick`` envelope around ``payload``."""
    return {
        "type": "ipc.status.tick",
        "ts": "2026-05-12T08:00:00+00:00",
        "payload": payload,
    }


def test_midi_null_is_valid() -> None:
    """``midi=null`` valid — sidecar reports null when MIDI backend missing."""
    msg = StatusTick.make(livekit="ok", gemini="ok", midi=None, screen="ok")
    d = json.loads(msg.to_json())
    assert d["payload"]["midi"] is None
    jsonschema.validate(d, _SCHEMA)


def test_midi_zero_is_valid() -> None:
    """``midi=0`` valid — controller registry empty (zero ports)."""
    msg = StatusTick.make(livekit="ok", gemini="ok", midi=0, screen="ok")
    jsonschema.validate(json.loads(msg.to_json()), _SCHEMA)


def test_midi_negative_is_invalid() -> None:
    """``midi=-1`` rejected — schema enforces ``minimum: 0``."""
    d = _wrap({"livekit": "ok", "gemini": "ok", "midi": -1, "screen": "ok"})
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(d, _SCHEMA)


def test_unknown_livekit_value_rejected() -> None:
    """Unknown ``livekit`` enum value (e.g. typo) rejected."""
    d = _wrap({"livekit": "wat", "gemini": "ok", "midi": 1, "screen": "ok"})
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(d, _SCHEMA)


def test_unknown_gemini_value_rejected() -> None:
    """Unknown ``gemini`` enum value rejected (only ok/down)."""
    d = _wrap({"livekit": "ok", "gemini": "connecting", "midi": 1, "screen": "ok"})
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(d, _SCHEMA)


def test_unknown_screen_value_rejected() -> None:
    """Unknown ``screen`` enum value rejected (only ok/denied)."""
    d = _wrap({"livekit": "ok", "gemini": "ok", "midi": 1, "screen": "down"})
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(d, _SCHEMA)


def test_additional_properties_in_payload_rejected() -> None:
    """``additionalProperties: false`` blocks drift via stray field."""
    d = _wrap(
        {
            "livekit": "ok",
            "gemini": "ok",
            "midi": 1,
            "screen": "ok",
            "extra": "drift",  # not in schema — must reject
        }
    )
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(d, _SCHEMA)


def test_missing_required_field_rejected() -> None:
    """Removing any of the four required fields fails validation."""
    for missing in ("livekit", "gemini", "midi", "screen"):
        payload = {"livekit": "ok", "gemini": "ok", "midi": 1, "screen": "ok"}
        del payload[missing]
        d = _wrap(payload)
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(d, _SCHEMA)


def test_top_level_additional_properties_rejected() -> None:
    """Top-level envelope is also closed — no stray fields next to type/ts/payload."""
    d = {
        "type": "ipc.status.tick",
        "ts": "2026-05-12T08:00:00+00:00",
        "payload": {"livekit": "ok", "gemini": "ok", "midi": 1, "screen": "ok"},
        "stowaway": True,
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(d, _SCHEMA)


def test_parse_message_accepts_json_string() -> None:
    """``parse_message`` accepts a raw JSON string (typical ws_bus payload)."""
    msg = StatusTick.make(livekit="connecting", gemini="ok", midi=2, screen="ok")
    parsed = parse_message(msg.to_json())
    assert parsed["type"] == "ipc.status.tick"
    assert parsed["payload"]["livekit"] == "connecting"


def test_parse_message_rejects_invalid_dict() -> None:
    """``parse_message`` raises on schema violation (Wave 4 WizardLoop will catch)."""
    bad = _wrap({"livekit": "ok", "gemini": "ok", "midi": -7, "screen": "ok"})
    with pytest.raises(jsonschema.ValidationError):
        parse_message(bad)


def test_parse_message_rejects_non_dict_type() -> None:
    """``parse_message`` raises ``TypeError`` on non-dict / non-str input."""
    with pytest.raises(TypeError):
        parse_message(42)  # type: ignore[arg-type]
