# SPDX-License-Identifier: Apache-2.0
"""Phase 24-02 Task 5 — SessionOverlayHighlight IPC schema + wrapper coverage.

Pins the OVERLAY-01 contract: schema oneOf entry + 3-field payload +
``additionalProperties: false`` + color enum lock + duration range + Python
wrapper round-trip + the Phase 11 W0 count-parity invariant.

Mirrors tests/ui_bus/test_citation_schema.py — same shape, different
domain. The shared assertions exist to keep both wrappers under the same
linting eye and to catch a future drift where one wrapper's schema is
patched without the other being kept in sync.
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import jsonschema
import pytest

from vibemix.ui_bus import (
    SessionOverlayHighlight,
    SessionOverlayHighlightPayload,
    parse_message,
    validate_message,
)
from vibemix.ui_bus import messages as ui_bus_messages

_SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "tauri"
    / "ui"
    / "src"
    / "ipc"
    / "messages.schema.json"
)
_SCHEMA: dict = json.loads(_SCHEMA_PATH.read_text())


def test_schema_oneOf_includes_session_overlay_highlight() -> None:
    """The schema's top-level oneOf list MUST reference SessionOverlayHighlight."""
    assert {"$ref": "#/definitions/SessionOverlayHighlight"} in _SCHEMA["oneOf"]


def test_schema_session_overlay_highlight_definition_shape() -> None:
    """The SessionOverlayHighlight definition has the locked 3-field
    payload + the const type literal + ``additionalProperties: false``
    at all three levels."""
    defn = _SCHEMA["definitions"]["SessionOverlayHighlight"]
    assert defn["type"] == "object"
    assert defn["additionalProperties"] is False
    assert set(defn["required"]) == {"type", "ts", "payload"}
    assert defn["properties"]["type"]["const"] == "ipc.session.overlay-highlight"

    payload = defn["properties"]["payload"]
    assert payload["type"] == "object"
    assert payload["additionalProperties"] is False
    assert set(payload["required"]) == {"element_id", "color", "duration_ms"}

    props = payload["properties"]
    assert props["element_id"]["type"] == "string"
    assert props["element_id"]["minLength"] == 1
    assert props["element_id"]["maxLength"] == 64
    assert props["color"]["type"] == "string"
    assert set(props["color"]["enum"]) == {"amber", "red", "green", "blue"}
    assert props["duration_ms"]["type"] == "integer"
    assert props["duration_ms"]["minimum"] == 0
    assert props["duration_ms"]["maximum"] == 8000


def test_python_wrapper_make_and_serialize() -> None:
    """SessionOverlayHighlight.make(...) → .to_json() → parse_message round-trip."""
    msg = SessionOverlayHighlight.make(
        element_id="waveform_a",
        color="amber",
        duration_ms=1300,
    )
    raw = msg.to_json()
    parsed = parse_message(raw)
    assert parsed["type"] == "ipc.session.overlay-highlight"
    assert parsed["payload"]["element_id"] == "waveform_a"
    assert parsed["payload"]["color"] == "amber"
    assert parsed["payload"]["duration_ms"] == 1300


def test_make_defaults_to_amber_and_1300ms() -> None:
    """The .make() factory uses CDJ Whisper v5 amber + 200/800/300ms timing."""
    msg = SessionOverlayHighlight.make(element_id="deck_a_low_eq")
    parsed = parse_message(msg.to_json())
    assert parsed["payload"]["color"] == "amber"
    assert parsed["payload"]["duration_ms"] == 1300


def test_to_dict_roundtrips_through_json() -> None:
    """``to_dict()`` matches ``json.loads(to_json())`` exactly — the
    coach.py + dj_cohost.py publish path relies on this contract."""
    msg = SessionOverlayHighlight.make(
        element_id="deck_b_mid_eq",
        color="red",
        duration_ms=500,
    )
    assert msg.to_dict() == json.loads(msg.to_json())


@pytest.mark.parametrize("color", ["amber", "red", "green", "blue"])
def test_all_allowlisted_colors_round_trip(color: str) -> None:
    msg = SessionOverlayHighlight.make(
        element_id="waveform_b", color=color, duration_ms=800  # type: ignore[arg-type]
    )
    parsed = parse_message(msg.to_json())
    assert parsed["payload"]["color"] == color


def test_unknown_color_rejected_by_schema() -> None:
    """Color enum lock — ``magenta`` is not in the allowlist."""
    bogus = {
        "type": "ipc.session.overlay-highlight",
        "ts": "2026-05-14T12:00:00+00:00",
        "payload": {
            "element_id": "waveform_a",
            "color": "magenta",
            "duration_ms": 1300,
        },
    }
    with pytest.raises(jsonschema.ValidationError):
        validate_message(bogus)


def test_duration_ms_over_8000_rejected() -> None:
    """duration_ms > 8000 trips the schema's ``maximum: 8000`` bound —
    runaway rings cannot freeze on screen."""
    bogus = {
        "type": "ipc.session.overlay-highlight",
        "ts": "2026-05-14T12:00:00+00:00",
        "payload": {
            "element_id": "waveform_a",
            "color": "amber",
            "duration_ms": 20000,
        },
    }
    with pytest.raises(jsonschema.ValidationError):
        validate_message(bogus)


def test_negative_duration_rejected() -> None:
    """duration_ms < 0 trips the schema's ``minimum: 0`` bound."""
    bogus = {
        "type": "ipc.session.overlay-highlight",
        "ts": "2026-05-14T12:00:00+00:00",
        "payload": {
            "element_id": "waveform_a",
            "color": "amber",
            "duration_ms": -1,
        },
    }
    with pytest.raises(jsonschema.ValidationError):
        validate_message(bogus)


def test_empty_element_id_rejected() -> None:
    """element_id minLength=1 — empty strings rejected."""
    bogus = {
        "type": "ipc.session.overlay-highlight",
        "ts": "2026-05-14T12:00:00+00:00",
        "payload": {
            "element_id": "",
            "color": "amber",
            "duration_ms": 1300,
        },
    }
    with pytest.raises(jsonschema.ValidationError):
        validate_message(bogus)


def test_oversize_element_id_rejected() -> None:
    """element_id maxLength=64 — guards against unbounded growth."""
    bogus = {
        "type": "ipc.session.overlay-highlight",
        "ts": "2026-05-14T12:00:00+00:00",
        "payload": {
            "element_id": "x" * 65,
            "color": "amber",
            "duration_ms": 1300,
        },
    }
    with pytest.raises(jsonschema.ValidationError):
        validate_message(bogus)


def test_extra_payload_field_rejected() -> None:
    """``additionalProperties: false`` on the payload object — extra keys raise."""
    bogus = {
        "type": "ipc.session.overlay-highlight",
        "ts": "2026-05-14T12:00:00+00:00",
        "payload": {
            "element_id": "waveform_a",
            "color": "amber",
            "duration_ms": 1300,
            "extra_field": "not-allowed",
        },
    }
    with pytest.raises(jsonschema.ValidationError):
        validate_message(bogus)


def test_payload_struct_is_frozen_slots() -> None:
    """SessionOverlayHighlightPayload must be a frozen+slots dataclass
    per project convention (no pydantic)."""
    assert hasattr(SessionOverlayHighlightPayload, "__dataclass_fields__")
    assert hasattr(SessionOverlayHighlightPayload, "__slots__")
    p = SessionOverlayHighlightPayload(
        element_id="waveform_a",
        color="amber",
        duration_ms=1300,
    )
    with pytest.raises(Exception):  # FrozenInstanceError subclasses AttributeError
        p.element_id = "deck_b_mid_eq"  # type: ignore[misc]


def test_count_parity_python_vs_schema() -> None:
    """Phase 11 W0 invariant — schema oneOf count == wrapper-class count.
    Adding SessionOverlayHighlight bumps both sides by one; the test
    re-asserts the invariant holds at all times."""
    oneof_count = len(_SCHEMA["oneOf"])
    wrapper_count = sum(
        1
        for _, obj in inspect.getmembers(ui_bus_messages, inspect.isclass)
        if hasattr(obj, "__dataclass_fields__") and "type" in obj.__dataclass_fields__
    )
    assert oneof_count == wrapper_count, (
        f"schema/wrapper drift — {oneof_count} oneOf entries vs "
        f"{wrapper_count} wrapper classes"
    )
