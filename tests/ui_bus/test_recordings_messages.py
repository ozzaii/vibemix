# SPDX-License-Identifier: Apache-2.0
"""Phase 15-01 — ipc.recordings.* schema + wrapper roundtrip tests.

Covers the 7 new families added by Phase 15 Wave 1 (interface-first):

* ``ipc.recordings.list`` (request, empty payload)
* ``ipc.recordings.list_result`` (response — array of RecordingSummary + bytes_total)
* ``ipc.recordings.delete`` (request — session_dir; V12 path-traversal regex)
* ``ipc.recordings.delete_ack`` (response — session_dir + ok + optional error)
* ``ipc.recordings.usage`` (push — sessions + bytes_total)
* ``ipc.recordings.events`` (request — session_dir; same V12 regex)
* ``ipc.recordings.events_result`` (response — session_dir + array of events.jsonl
  records with open extensibility per kind)

The session_dir regex ``^[0-9]{8}-[0-9]{6}$`` is enforced AT THE SCHEMA
LEVEL — wrappers do not pre-validate, only ``.to_json()`` (which calls
``_validate``) raises ``jsonschema.ValidationError`` on a bad value. This
matches the existing Phase 11 W0 pattern (validation on serialize, never
in the constructor).

Drift-gate count parity (34 == 34) is asserted in ``test_count_parity``
below; ``scripts/check_ipc_schema.py`` is the canonical CI gate.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from vibemix.ui_bus import (
    RecordingsDelete,
    RecordingsDeleteAck,
    RecordingsEvents,
    RecordingsEventsResult,
    RecordingsList,
    RecordingsListResult,
    RecordingsUsage,
    RecordingSummary,
    validate_message,
)
from vibemix.ui_bus.messages import _SCHEMA

_REPO_ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Test 1 — ipc.recordings.list (empty request)
# ---------------------------------------------------------------------------


def test_recordings_list_roundtrips() -> None:
    msg = RecordingsList.make()
    raw = msg.to_json()
    parsed = json.loads(raw)
    validate_message(parsed)
    assert parsed["type"] == "ipc.recordings.list"
    assert parsed["payload"] == {}


# ---------------------------------------------------------------------------
# Test 2 — ipc.recordings.list_result (RecordingSummary array)
# ---------------------------------------------------------------------------


def test_recordings_list_result_roundtrips_with_session_summary() -> None:
    sessions = (
        RecordingSummary(
            session_dir="20260513-210410",
            started_at_iso="2026-05-13T21:04:10+02:00",
            duration_s=5040.0,
            event_count=38,
            bytes_total=12345678,
            crashed=False,
        ),
    )
    msg = RecordingsListResult.make(sessions=sessions, bytes_total=12345678)
    raw = msg.to_json()
    parsed = json.loads(raw)
    validate_message(parsed)
    assert parsed["type"] == "ipc.recordings.list_result"
    # `sessions` tuple must serialize as a JSON array.
    assert isinstance(parsed["payload"]["sessions"], list)
    assert parsed["payload"]["sessions"][0]["session_dir"] == "20260513-210410"
    assert parsed["payload"]["bytes_total"] == 12345678


def test_recordings_list_result_accepts_empty_sessions_array() -> None:
    msg = RecordingsListResult.make(sessions=(), bytes_total=0)
    parsed = json.loads(msg.to_json())
    validate_message(parsed)
    assert parsed["payload"]["sessions"] == []
    assert parsed["payload"]["bytes_total"] == 0


# ---------------------------------------------------------------------------
# Test 3 — ipc.recordings.delete + path-traversal regex
# ---------------------------------------------------------------------------


def test_recordings_delete_accepts_valid_session_dir() -> None:
    msg = RecordingsDelete.make(session_dir="20260513-210410")
    parsed = json.loads(msg.to_json())
    validate_message(parsed)
    assert parsed["payload"]["session_dir"] == "20260513-210410"


def test_recordings_delete_rejects_path_traversal() -> None:
    """V12 — schema-level path-traversal gate via ^[0-9]{8}-[0-9]{6}$."""
    bad = RecordingsDelete(
        type="ipc.recordings.delete",
        ts="2026-05-13T21:04:10+00:00",
        payload=type(RecordingsDelete.make(session_dir="20260513-210410").payload)(
            session_dir="../../etc/passwd"
        ),
    )
    with pytest.raises(jsonschema.ValidationError):
        bad.to_json()


# ---------------------------------------------------------------------------
# Test 4 — ipc.recordings.delete_ack with optional error
# ---------------------------------------------------------------------------


def test_recordings_delete_ack_ok_true_with_null_error_roundtrips() -> None:
    msg = RecordingsDeleteAck.make(session_dir="20260513-210410", ok=True, error=None)
    parsed = json.loads(msg.to_json())
    validate_message(parsed)
    assert parsed["payload"]["session_dir"] == "20260513-210410"
    assert parsed["payload"]["ok"] is True
    # error: null is a valid wire shape (matches settings.set ack precedent).
    assert parsed["payload"]["error"] is None


def test_recordings_delete_ack_ok_false_with_string_error_roundtrips() -> None:
    msg = RecordingsDeleteAck.make(
        session_dir="20260513-210410", ok=False, error="locked"
    )
    parsed = json.loads(msg.to_json())
    validate_message(parsed)
    assert parsed["payload"]["ok"] is False
    assert parsed["payload"]["error"] == "locked"


# ---------------------------------------------------------------------------
# Test 5 — ipc.recordings.usage (push)
# ---------------------------------------------------------------------------


def test_recordings_usage_roundtrips() -> None:
    msg = RecordingsUsage.make(sessions=12, bytes_total=3656838349)
    parsed = json.loads(msg.to_json())
    validate_message(parsed)
    assert parsed["payload"]["sessions"] == 12
    assert parsed["payload"]["bytes_total"] == 3656838349


def test_recordings_usage_rejects_negative_counts() -> None:
    """sessions + bytes_total must satisfy minimum: 0."""
    bad = {
        "type": "ipc.recordings.usage",
        "ts": "2026-05-13T21:04:10+00:00",
        "payload": {"sessions": -1, "bytes_total": 100},
    }
    with pytest.raises(jsonschema.ValidationError):
        validate_message(bad)


# ---------------------------------------------------------------------------
# Test 6 — ipc.recordings.events + path-traversal regex
# ---------------------------------------------------------------------------


def test_recordings_events_accepts_valid_session_dir() -> None:
    msg = RecordingsEvents.make(session_dir="20260513-210410")
    parsed = json.loads(msg.to_json())
    validate_message(parsed)
    assert parsed["payload"]["session_dir"] == "20260513-210410"


def test_recordings_events_rejects_path_traversal() -> None:
    """Mirror Test 3 — V12 regex must apply to recordings.events too."""
    bad = RecordingsEvents(
        type="ipc.recordings.events",
        ts="2026-05-13T21:04:10+00:00",
        payload=type(RecordingsEvents.make(session_dir="20260513-210410").payload)(
            session_dir="../../etc/passwd"
        ),
    )
    with pytest.raises(jsonschema.ValidationError):
        bad.to_json()


# ---------------------------------------------------------------------------
# Test 7 — ipc.recordings.events_result open-extensibility
# ---------------------------------------------------------------------------


def test_recordings_events_result_roundtrips_with_heterogeneous_events() -> None:
    """events.jsonl is open by design — each per-event kind has its own
    additional fields. The schema requires `t` + `kind` minimum, allows arbitrary
    extras (additionalProperties: true).
    """
    events = (
        {
            "t": 0.0,
            "kind": "session_start",
            "wall_clock_iso": "2026-05-13T21:04:10+02:00",
            "session_dir": "20260513-210410",
        },
        {"t": 3.21, "kind": "trigger", "reason": "phase_change"},
        {"t": 5.04, "kind": "ai_text", "text": "Nice transition."},
        {"t": 7.11, "kind": "controller_move", "control": "filter_a"},
    )
    msg = RecordingsEventsResult.make(session_dir="20260513-210410", events=events)
    parsed = json.loads(msg.to_json())
    validate_message(parsed)
    assert parsed["payload"]["session_dir"] == "20260513-210410"
    assert isinstance(parsed["payload"]["events"], list)
    assert len(parsed["payload"]["events"]) == 4
    assert parsed["payload"]["events"][0]["kind"] == "session_start"
    assert parsed["payload"]["events"][2]["text"] == "Nice transition."


def test_recordings_events_result_rejects_event_missing_required_fields() -> None:
    """Each event element requires at minimum `t` + `kind`."""
    bad = {
        "type": "ipc.recordings.events_result",
        "ts": "2026-05-13T21:04:10+00:00",
        "payload": {
            "session_dir": "20260513-210410",
            "events": [{"text": "no kind no t — invalid"}],
        },
    }
    with pytest.raises(jsonschema.ValidationError):
        validate_message(bad)


def test_recordings_events_result_rejects_event_with_negative_t() -> None:
    bad = {
        "type": "ipc.recordings.events_result",
        "ts": "2026-05-13T21:04:10+00:00",
        "payload": {
            "session_dir": "20260513-210410",
            "events": [{"t": -1.0, "kind": "session_start"}],
        },
    }
    with pytest.raises(jsonschema.ValidationError):
        validate_message(bad)


def test_recordings_events_result_accepts_empty_events_array() -> None:
    msg = RecordingsEventsResult.make(session_dir="20260513-210410", events=())
    parsed = json.loads(msg.to_json())
    validate_message(parsed)
    assert parsed["payload"]["events"] == []


# ---------------------------------------------------------------------------
# Test 8 — drift-gate count parity (34 oneOf == 34 wrapper dataclasses)
# ---------------------------------------------------------------------------


def test_count_parity_at_34() -> None:
    """Phase 15 Plan 01 bumps the IPC count 27 → 34 (+7 recordings.* families).
    Both sides — schema oneOf and Python wrapper dataclasses — must match exactly.
    """
    from vibemix.ui_bus import messages as ui_bus_messages

    wrapper_count = sum(
        1
        for name in dir(ui_bus_messages)
        if isinstance(obj := getattr(ui_bus_messages, name), type)
        and hasattr(obj, "__dataclass_fields__")
        and "type" in obj.__dataclass_fields__
    )

    assert len(_SCHEMA["oneOf"]) == 34, "schema oneOf count should be 34 after Phase 15-01"
    assert wrapper_count == 34, f"wrapper count {wrapper_count} != 34"


def test_check_ipc_schema_script_exits_zero() -> None:
    """End-to-end CI gate — the script that hard-fails the build on drift."""
    import subprocess
    import sys

    script = _REPO_ROOT / "scripts" / "check_ipc_schema.py"
    res = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(_REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, (
        f"check_ipc_schema.py exited {res.returncode}\n"
        f"stdout: {res.stdout}\nstderr: {res.stderr}"
    )
