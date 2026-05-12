# SPDX-License-Identifier: Apache-2.0
"""Phase 12 — focused round-trip + reject-on-extra-field tests for the
new session + settings + status-recheck + ipc.error message families.

The blanket round-trip + count-parity assertions in
``tests/ui_bus/test_messages_schema.py`` cover happy-path validation; this
file specifically pins:

  1. ``additionalProperties: false`` blocks unknown fields on every new payload.
  2. ``SessionMute.make_toggle`` and ``SessionMute.make_ack`` emit asymmetric
     payloads (only the relevant field present).
  3. ``IpcError`` serializes without ``original_type`` when the field is None.
  4. ``SettingsSet.field`` enum is enforced.
  5. ``StatusRecheck.component`` enum is enforced.
"""

from __future__ import annotations

import json

import jsonschema
import pytest

from vibemix.ui_bus import (
    IpcError,
    LevelPair,
    MetersTriple,
    SessionMute,
    SessionSnapshot,
    SettingsSet,
    SettingsState,
    StatusRecheck,
)
from vibemix.ui_bus.messages import _SCHEMA


def _validate(d: dict) -> None:
    jsonschema.validate(d, _SCHEMA)


# ---------------------------------------------------------------------------
# SessionSnapshot
# ---------------------------------------------------------------------------


def _base_snapshot() -> SessionSnapshot:
    return SessionSnapshot.make(
        meters=MetersTriple(
            music=LevelPair(rms=0.3, peak=0.5),
            voice=LevelPair(rms=0.0, peak=0.0),
            mic=LevelPair(rms=0.1, peak=0.2),
        ),
    )


def test_session_snapshot_roundtrip_minimal() -> None:
    msg = _base_snapshot()
    raw = msg.to_json()
    parsed = json.loads(raw)
    assert parsed["type"] == "ipc.session.snapshot"
    assert parsed["payload"]["meters"]["music"]["rms"] == 0.3
    _validate(parsed)


def test_session_snapshot_rejects_extra_field() -> None:
    parsed = json.loads(_base_snapshot().to_json())
    parsed["payload"]["unknown"] = True
    with pytest.raises(jsonschema.ValidationError):
        _validate(parsed)


def test_session_snapshot_rejects_meters_extra_field() -> None:
    parsed = json.loads(_base_snapshot().to_json())
    parsed["payload"]["meters"]["bass"] = {"rms": 0.5, "peak": 1.0}
    with pytest.raises(jsonschema.ValidationError):
        _validate(parsed)


def test_session_snapshot_rms_out_of_range_rejected() -> None:
    parsed = json.loads(_base_snapshot().to_json())
    parsed["payload"]["meters"]["music"]["rms"] = 1.5
    with pytest.raises(jsonschema.ValidationError):
        _validate(parsed)


# ---------------------------------------------------------------------------
# SessionMute — asymmetric payloads
# ---------------------------------------------------------------------------


def test_session_mute_toggle_payload_has_only_toggle() -> None:
    msg = SessionMute.make_toggle()
    parsed = json.loads(msg.to_json())
    assert parsed["payload"] == {"toggle": True}
    _validate(parsed)


def test_session_mute_ack_payload_has_only_muted() -> None:
    msg = SessionMute.make_ack(muted=True)
    parsed = json.loads(msg.to_json())
    assert parsed["payload"] == {"muted": True}
    _validate(parsed)


def test_session_mute_rejects_extra_field() -> None:
    parsed = json.loads(SessionMute.make_toggle().to_json())
    parsed["payload"]["unknown"] = "x"
    with pytest.raises(jsonschema.ValidationError):
        _validate(parsed)


# ---------------------------------------------------------------------------
# SettingsSet — enum enforcement on `field`
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "field,value",
    [
        ("voice", "kore"),
        ("mode", "hype"),
        ("genre", "techno"),
        ("output_device_id", "dev-3"),
        ("output_device_id", None),
        ("output_profile", "spk"),
        ("retention_days", 14),
        ("push_to_mute_hotkey", "ctrl+shift+m"),
    ],
)
def test_settings_set_accepts_known_field(field: str, value: object) -> None:
    msg = SettingsSet.make(field=field, value=value)  # type: ignore[arg-type]
    parsed = json.loads(msg.to_json())
    _validate(parsed)
    assert parsed["payload"]["field"] == field


def test_settings_set_rejects_unknown_field() -> None:
    # Bypass the dataclass typing — construct the dict directly to test schema rejection.
    parsed = {
        "type": "ipc.settings.set",
        "ts": "2026-05-12T00:00:00Z",
        "payload": {"field": "nope", "value": "x"},
    }
    with pytest.raises(jsonschema.ValidationError):
        _validate(parsed)


# ---------------------------------------------------------------------------
# SettingsState — enum enforcement on `mode` + `output_profile`
# ---------------------------------------------------------------------------


def test_settings_state_full_roundtrip() -> None:
    msg = SettingsState.make(
        voice="puck",
        mode="hype",
        genre="dnb",
        output_device_id="dev-7",
        output_profile="spk",
        retention_days=30,
        push_to_mute_hotkey="ctrl+shift+m",
        muted=True,
    )
    parsed = json.loads(msg.to_json())
    _validate(parsed)
    assert parsed["payload"]["mode"] == "hype"
    assert parsed["payload"]["output_profile"] == "spk"
    assert parsed["payload"]["muted"] is True


def test_settings_state_rejects_invalid_mode() -> None:
    parsed = {
        "type": "ipc.settings.state",
        "ts": "2026-05-12T00:00:00Z",
        "payload": {
            "voice": "kore",
            "mode": "neutral",  # not in enum
            "genre": "techno",
            "output_device_id": None,
            "output_profile": "hp",
            "retention_days": 7,
            "push_to_mute_hotkey": "cmd+shift+m",
            "muted": False,
        },
    }
    with pytest.raises(jsonschema.ValidationError):
        _validate(parsed)


# ---------------------------------------------------------------------------
# StatusRecheck — enum enforcement
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("component", ["livekit", "gemini", "midi", "screen"])
def test_status_recheck_accepts_known_component(component: str) -> None:
    msg = StatusRecheck.make(component=component)  # type: ignore[arg-type]
    parsed = json.loads(msg.to_json())
    _validate(parsed)


def test_status_recheck_rejects_unknown_component() -> None:
    parsed = {
        "type": "ipc.status.recheck",
        "ts": "2026-05-12T00:00:00Z",
        "payload": {"component": "everything"},
    }
    with pytest.raises(jsonschema.ValidationError):
        _validate(parsed)


# ---------------------------------------------------------------------------
# IpcError — original_type optional
# ---------------------------------------------------------------------------


def test_ipc_error_without_original_type() -> None:
    msg = IpcError.make(reason="schema violation")
    parsed = json.loads(msg.to_json())
    assert "original_type" not in parsed["payload"]
    assert parsed["payload"]["reason"] == "schema violation"
    _validate(parsed)


def test_ipc_error_with_original_type() -> None:
    msg = IpcError.make(reason="bad field value", original_type="ipc.settings.set")
    parsed = json.loads(msg.to_json())
    assert parsed["payload"]["original_type"] == "ipc.settings.set"
    _validate(parsed)


def test_ipc_error_rejects_extra_field() -> None:
    parsed = {
        "type": "ipc.error",
        "ts": "2026-05-12T00:00:00Z",
        "payload": {"reason": "x", "extra": "y"},
    }
    with pytest.raises(jsonschema.ValidationError):
        _validate(parsed)
