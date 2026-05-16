# SPDX-License-Identifier: Apache-2.0
"""Phase 20-04 Task 1 — SessionCitation IPC schema + wrapper coverage.

Pins the GROUND-06 anti-slop diagnostics contract: schema-side oneOf entry +
4-field payload + ``additionalProperties: false`` + numeric bounds + Python
wrapper round-trip + the Phase 11 W0 count-parity invariant.
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import jsonschema
import pytest

from vibemix.ui_bus import (
    SessionCitation,
    SessionCitationPayload,
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


def test_schema_oneOf_includes_session_citation() -> None:
    """The schema's top-level oneOf list MUST reference SessionCitation."""
    assert {"$ref": "#/definitions/SessionCitation"} in _SCHEMA["oneOf"]


def test_schema_session_citation_definition_shape() -> None:
    """The SessionCitation definition has the locked 4-field payload + the
    const type literal + ``additionalProperties: false`` at all 3 levels."""
    defn = _SCHEMA["definitions"]["SessionCitation"]
    assert defn["type"] == "object"
    assert defn["additionalProperties"] is False
    assert set(defn["required"]) == {"type", "ts", "payload"}
    assert defn["properties"]["type"]["const"] == "ipc.session.citation"

    payload = defn["properties"]["payload"]
    assert payload["type"] == "object"
    assert payload["additionalProperties"] is False
    assert set(payload["required"]) == {
        "slop_ratio",
        "stripped_rate_15s",
        "last_unverified_response",
        "bypass_active",
    }

    props = payload["properties"]
    assert props["slop_ratio"]["type"] == "number"
    assert props["slop_ratio"]["minimum"] == 0
    assert props["slop_ratio"]["maximum"] == 1
    assert props["stripped_rate_15s"]["type"] == "number"
    assert props["stripped_rate_15s"]["minimum"] == 0
    assert props["stripped_rate_15s"]["maximum"] == 1
    assert props["last_unverified_response"]["type"] == ["string", "null"]
    assert props["bypass_active"]["type"] == "boolean"


def test_python_wrapper_make_and_serialize() -> None:
    """SessionCitation.make(...) → .to_json() → parse_message round-trip."""
    msg = SessionCitation.make(
        slop_ratio=0.1,
        stripped_rate_15s=0.05,
        last_unverified_response=None,
        bypass_active=False,
    )
    raw = msg.to_json()
    parsed = parse_message(raw)
    assert parsed["type"] == "ipc.session.citation"
    assert parsed["payload"]["slop_ratio"] == pytest.approx(0.1)
    assert parsed["payload"]["stripped_rate_15s"] == pytest.approx(0.05)
    assert parsed["payload"]["last_unverified_response"] is None
    assert parsed["payload"]["bypass_active"] is False


def test_payload_with_unverified_text() -> None:
    """``last_unverified_response`` + ``bypass_active=True`` must round-trip."""
    sample = "This drop is wild — actually I have no evidence for that."
    msg = SessionCitation.make(
        slop_ratio=0.42,
        stripped_rate_15s=0.55,
        last_unverified_response=sample,
        bypass_active=True,
    )
    parsed = parse_message(msg.to_json())
    assert parsed["payload"]["last_unverified_response"] == sample
    assert parsed["payload"]["bypass_active"] is True
    assert parsed["payload"]["slop_ratio"] == pytest.approx(0.42)
    assert parsed["payload"]["stripped_rate_15s"] == pytest.approx(0.55)


def test_slop_ratio_out_of_range_rejected() -> None:
    """slop_ratio > 1.0 must trip the schema's ``maximum: 1`` bound."""
    msg = SessionCitation.make(
        slop_ratio=1.5,
        stripped_rate_15s=0.05,
        last_unverified_response=None,
        bypass_active=False,
    )
    with pytest.raises(jsonschema.ValidationError):
        msg.to_json()


def test_stripped_rate_negative_rejected() -> None:
    """stripped_rate_15s < 0.0 must trip the schema's ``minimum: 0`` bound."""
    msg = SessionCitation.make(
        slop_ratio=0.1,
        stripped_rate_15s=-0.01,
        last_unverified_response=None,
        bypass_active=False,
    )
    with pytest.raises(jsonschema.ValidationError):
        msg.to_json()


def test_extra_payload_field_rejected() -> None:
    """``additionalProperties: false`` on the payload object — extra keys raise."""
    bogus = {
        "type": "ipc.session.citation",
        "ts": "2026-05-14T12:00:00+00:00",
        "payload": {
            "slop_ratio": 0.1,
            "stripped_rate_15s": 0.05,
            "last_unverified_response": None,
            "bypass_active": False,
            "extra_field": "not-allowed",
        },
    }
    with pytest.raises(jsonschema.ValidationError):
        validate_message(bogus)


def test_payload_struct_is_frozen_slots() -> None:
    """SessionCitationPayload must be a frozen+slots dataclass per project
    convention (no pydantic)."""
    assert hasattr(SessionCitationPayload, "__dataclass_fields__")
    assert hasattr(SessionCitationPayload, "__slots__")
    p = SessionCitationPayload(
        slop_ratio=0.1,
        stripped_rate_15s=0.05,
        last_unverified_response=None,
        bypass_active=False,
    )
    with pytest.raises(Exception):  # FrozenInstanceError subclasses AttributeError
        p.slop_ratio = 0.5  # type: ignore[misc]


def test_count_parity_python_vs_schema() -> None:
    """Phase 11 W0 invariant — schema oneOf count == wrapper-class count."""
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
