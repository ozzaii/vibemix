# SPDX-License-Identifier: Apache-2.0
"""Tests for the drive-vibemix websocket probe helper.

The probe lives in the repo-local Claude skill bundle, but it is part of the
operator path for live DDJ verification. These tests keep the frame builder
schema-valid without touching the real 127.0.0.1:8765 bus.
"""

from __future__ import annotations

import importlib.util
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType


def _load_ws_probe() -> ModuleType:
    repo = Path(__file__).resolve().parents[2]
    path = repo / ".claude" / "skills" / "drive-vibemix" / "scripts" / "ws_probe.py"
    spec = importlib.util.spec_from_file_location("drive_vibemix_ws_probe", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ws_probe_builds_manual_trigger_frame():
    probe = _load_ws_probe()

    frame = probe._build_send_frame(trigger=True, action=None, ipc=None, payload={})

    assert frame == {"action": "trigger"}


def test_ws_probe_builds_schema_valid_typed_ipc_frame():
    probe = _load_ws_probe()

    frame = probe._build_send_frame(
        trigger=False,
        action=None,
        ipc="ipc.status.recheck",
        payload={"component": "midi"},
    )

    assert frame["type"] == "ipc.status.recheck"
    assert frame["payload"] == {"component": "midi"}
    ts = datetime.fromisoformat(frame["ts"])
    assert ts.tzinfo == UTC


def test_ws_probe_builds_bare_action_frame():
    probe = _load_ws_probe()

    frame = probe._build_send_frame(
        trigger=False,
        action="next_suggestion.feedback",
        ipc=None,
        payload={"feedback": "up"},
    )

    assert frame == {"action": "next_suggestion.feedback", "feedback": "up"}


def test_ws_probe_rejects_ipc_as_bare_action():
    probe = _load_ws_probe()

    try:
        probe._build_send_frame(
            trigger=False,
            action="ipc.status.recheck",
            ipc=None,
            payload={"component": "midi"},
        )
    except ValueError as e:
        assert "use --ipc" in str(e)
    else:  # pragma: no cover - assertion branch
        raise AssertionError("expected ValueError")


def test_ws_probe_rejects_non_object_payload_json():
    probe = _load_ws_probe()

    try:
        probe._parse_payload_json("[]")
    except ValueError as e:
        assert "JSON object" in str(e)
    else:  # pragma: no cover - assertion branch
        raise AssertionError("expected ValueError")


def test_ws_probe_main_rejects_payload_without_sender(capsys):
    probe = _load_ws_probe()

    code = probe.main(["--payload-json", '{"component":"midi"}'])

    assert code == 2
    assert "requires --action or --ipc" in capsys.readouterr().err
