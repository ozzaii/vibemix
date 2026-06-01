# SPDX-License-Identifier: Apache-2.0
"""DEBRIEF IPC schema roundtrip + validation tests.

Covers the shippable debrief wrapper that opens the debrief window session.

The wrappers' ``.to_json()`` method runs through ``_serialize`` which in
turn calls ``jsonschema.Draft7Validator.validate`` — so a wrapper produced
with invalid field values raises ``jsonschema.ValidationError`` at JSON
emit time. Each "rejects" test exploits that path.
"""

from __future__ import annotations

import json

import jsonschema
import pytest

from vibemix.ui_bus import (
    DebriefSessionLoaded,
)
from vibemix.ui_bus.messages import _SCHEMA


def test_debrief_session_loaded_roundtrip():
    """Wrapper → JSON → parse → schema-validate."""
    msg = DebriefSessionLoaded.make(
        session_id="20260513-210410",
        started_at=1715616250.0,
        duration_s=5040.0,
    )
    raw = msg.to_json()
    parsed = json.loads(raw)
    assert parsed["type"] == "ipc.debrief.session-loaded"
    assert parsed["payload"]["session_id"] == "20260513-210410"
    assert parsed["payload"]["started_at"] == 1715616250.0
    assert parsed["payload"]["duration_s"] == 5040.0
    jsonschema.validate(parsed, _SCHEMA)


def test_debrief_session_loaded_rejects_negative_started_at():
    """Schema enforces ``started_at: number minimum: 0``."""
    msg = DebriefSessionLoaded.make(
        session_id="x", started_at=-1.0, duration_s=10.0
    )
    with pytest.raises(jsonschema.ValidationError):
        msg.to_json()


def test_debrief_session_loaded_rejects_negative_duration():
    """Schema enforces ``duration_s: number minimum: 0``."""
    msg = DebriefSessionLoaded.make(
        session_id="x", started_at=1.0, duration_s=-5.0
    )
    with pytest.raises(jsonschema.ValidationError):
        msg.to_json()


def test_debrief_session_loaded_rejects_empty_session_id():
    """``session_id`` schema has ``minLength: 1``."""
    msg = DebriefSessionLoaded.make(
        session_id="", started_at=1.0, duration_s=10.0
    )
    with pytest.raises(jsonschema.ValidationError):
        msg.to_json()


def test_debrief_wrappers_are_frozen_dataclasses():
    """``frozen=True`` + ``slots=True`` matches the Phase 11 dataclass convention."""
    msg = DebriefSessionLoaded.make(session_id="x", started_at=1.0, duration_s=10.0)
    with pytest.raises((AttributeError, Exception)):
        msg.type = "different"  # type: ignore[misc]
