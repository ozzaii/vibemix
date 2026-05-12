# SPDX-License-Identifier: Apache-2.0
"""Wave-0 roundtrip tests for every ipc.* wrapper dataclass.

Each test:
  1. Constructs a wrapper via ``.make()`` with the minimal-valid inputs.
  2. Asserts ``.to_json()`` returns a string.
  3. Parses the string back and asserts it validates against the source-of-truth
     schema (``tauri/ui/src/ipc/messages.schema.json``).

The plan's done-criterion is "all 19 wrappers roundtrip". Parametrization
provides a sentinel — if a 20th wrapper ships without a schema oneOf entry,
or vice versa, ``scripts/check_ipc_schema.py`` catches the drift (count
parity) and this file catches the type-of-failure (instantiation or
validation). Anti-pydantic: hand-written dataclasses only; the
``test_no_pydantic_imports`` test pins the Phase 6 convention from
CLAUDE.md.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import jsonschema
import pytest

from vibemix.ui_bus import (
    CalibrationAudioResult,
    CalibrationDeviceList,
    CalibrationListDevices,
    CalibrationListWindows,
    CalibrationMidiEvent,
    CalibrationMidiTimeout,
    CalibrationProbeAudio,
    CalibrationSmokeTest,
    CalibrationSmokeTestDone,
    CalibrationSmokeTestStarted,
    CalibrationStartMidiListen,
    CalibrationUserHeardTone,
    CalibrationWindowList,
    DeviceInfo,
    IpcBoot,
    PermissionCheck,
    PermissionState,
    StatusTick,
    WindowInfo,
    WizardDone,
    WizardStart,
)
from vibemix.ui_bus.messages import _SCHEMA

# Repository root — used by the no-pydantic-import grep.
_REPO_ROOT = Path(__file__).resolve().parents[2]


def _make_examples() -> list[tuple[str, object]]:
    """Return (name, message) pairs covering every wrapper dataclass.

    These are the minimal-valid instances required by Action A10 (per-class
    roundtrip example) and consumed by ``scripts/check_ipc_schema.py``.
    """
    return [
        ("IpcBoot", IpcBoot.make(ready=True)),
        (
            "StatusTick",
            StatusTick.make(livekit="ok", gemini="ok", midi=1, screen="ok"),
        ),
        ("PermissionCheck", PermissionCheck.make(kind="screen_recording")),
        (
            "PermissionState",
            PermissionState.make(kind="microphone", status="authorized"),
        ),
        ("CalibrationListDevices", CalibrationListDevices.make()),
        (
            "CalibrationDeviceList",
            CalibrationDeviceList.make(
                devices=[
                    DeviceInfo(
                        id="1",
                        name="BlackHole 2ch",
                        is_blackhole=True,
                        variant="2ch",
                    ),
                    DeviceInfo(
                        id="2",
                        name="MacBook Pro Speakers",
                        is_blackhole=False,
                        variant=None,
                    ),
                ],
                blackhole_present=True,
            ),
        ),
        (
            "CalibrationProbeAudio",
            CalibrationProbeAudio.make(output_device_id="dev-1", expected_rate=48000),
        ),
        (
            "CalibrationAudioResult",
            CalibrationAudioResult.make(
                playback_ok=True,
                audible_confirmed=True,
                programmatic_pass=True,
                actual_rate=48000,
                error=None,
            ),
        ),
        ("CalibrationUserHeardTone", CalibrationUserHeardTone.make(heard=True)),
        (
            "CalibrationStartMidiListen",
            CalibrationStartMidiListen.make(timeout_s=10.0),
        ),
        (
            "CalibrationMidiEvent",
            CalibrationMidiEvent.make(control_label="Deck A Play", raw="note_on ch=0 note=44"),
        ),
        ("CalibrationMidiTimeout", CalibrationMidiTimeout.make()),
        ("CalibrationListWindows", CalibrationListWindows.make()),
        (
            "CalibrationWindowList",
            CalibrationWindowList.make(
                windows=[
                    WindowInfo(
                        id="0",
                        app_name="djay Pro AI",
                        title="djay Pro — Main",
                        dj_app_hint="djay",
                    )
                ]
            ),
        ),
        ("CalibrationSmokeTest", CalibrationSmokeTest.make(template="HYPE_BEGINNER")),
        ("CalibrationSmokeTestStarted", CalibrationSmokeTestStarted.make()),
        (
            "CalibrationSmokeTestDone",
            CalibrationSmokeTestDone.make(transcript="yo we're live, deck spins when you are"),
        ),
        ("WizardStart", WizardStart.make()),
        (
            "WizardDone",
            WizardDone.make(
                output_device_id="dev-1",
                controller_profile="pioneer_ddj_flx4",
                target_window_id="win-42",
            ),
        ),
    ]


_EXAMPLES = _make_examples()


def test_example_count_matches_schema_oneof() -> None:
    """Sentinel: our roundtrip-example list must cover every schema oneOf entry."""
    assert len(_EXAMPLES) == len(_SCHEMA["oneOf"]) == 19


@pytest.mark.parametrize(
    "name,message",
    _EXAMPLES,
    ids=[name for name, _ in _EXAMPLES],
)
def test_wrapper_roundtrip_validates_against_schema(name: str, message: object) -> None:
    """Every wrapper's ``.to_json()`` parses back to a dict that satisfies the schema."""
    raw = message.to_json()  # type: ignore[attr-defined]
    assert isinstance(raw, str)
    parsed = json.loads(raw)
    assert isinstance(parsed, dict)
    jsonschema.validate(parsed, _SCHEMA)


def test_schema_self_validates_against_draft7() -> None:
    """Sanity: the schema file itself is conformant Draft-07."""
    jsonschema.Draft7Validator.check_schema(_SCHEMA)


def test_schema_oneof_count_is_19() -> None:
    """Plan-locked invariant — Wave 0 freezes 19 ipc.* messages."""
    assert len(_SCHEMA["oneOf"]) == 19
    assert len(_SCHEMA["definitions"]) == 19


def test_no_pydantic_imports_in_ui_bus() -> None:
    """Phase 6 + D-Area-4.4 convention: ``src/vibemix/ui_bus/`` is pydantic-free."""
    pkg = _REPO_ROOT / "src" / "vibemix" / "ui_bus"
    pattern = re.compile(r"^\s*(?:from|import)\s+pydantic\b", re.MULTILINE)
    offenders = []
    for py in pkg.rglob("*.py"):
        if pattern.search(py.read_text()):
            offenders.append(str(py.relative_to(_REPO_ROOT)))
    assert not offenders, f"pydantic import found in ui_bus: {offenders}"
