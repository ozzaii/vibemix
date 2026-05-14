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
    IpcError,
    LevelPair,
    MascotMoodChange,
    SessionCitation,
    SessionOverlayHighlight,
    MetersTriple,
    PermissionCheck,
    PermissionState,
    RecordingSummary,
    RecordingsDelete,
    RecordingsDeleteAck,
    RecordingsEvents,
    RecordingsEventsResult,
    RecordingsList,
    RecordingsListResult,
    RecordingsUsage,
    SessionMute,
    SessionSnapshot,
    SettingsGet,
    SettingsSet,
    SettingsState,
    StatusRecheck,
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
        # Phase 12 wrappers
        (
            "SessionSnapshot",
            SessionSnapshot.make(
                meters=MetersTriple(
                    music=LevelPair(rms=0.4, peak=0.6),
                    voice=LevelPair(rms=0.0, peak=0.0),
                    mic=LevelPair(rms=0.05, peak=0.1),
                ),
            ),
        ),
        ("SessionMute", SessionMute.make_toggle()),
        ("SettingsSet", SettingsSet.make(field="voice", value="kore")),
        ("SettingsGet", SettingsGet.make()),
        (
            "SettingsState",
            SettingsState.make(
                voice="kore",
                mode="coach",
                genre="tech-house",
                output_device_id=None,
                output_profile="hp",
                retention_days=7,
                push_to_mute_hotkey="cmd+shift+m",
                muted=False,
            ),
        ),
        ("StatusRecheck", StatusRecheck.make(component="midi")),
        (
            "IpcError",
            IpcError.make(reason="invalid payload", original_type="ipc.settings.set"),
        ),
        # Phase 13-05 — mascot mood-swap envelope (Plan 13-05).
        (
            "MascotMoodChange",
            MascotMoodChange.make(mood="teacher", previous_mood="hype-man", at=1234.56),
        ),
        # Phase 15-01 — recordings.* (4 new families surfaced as 7 schema entries).
        ("RecordingsList", RecordingsList.make()),
        (
            "RecordingsListResult",
            RecordingsListResult.make(
                sessions=[
                    RecordingSummary(
                        session_dir="20260513-210410",
                        started_at_iso="2026-05-13T21:04:10+02:00",
                        duration_s=5040.0,
                        event_count=38,
                        bytes_total=12345678,
                        crashed=False,
                    ),
                ],
                bytes_total=12345678,
            ),
        ),
        ("RecordingsDelete", RecordingsDelete.make(session_dir="20260513-210410")),
        (
            "RecordingsDeleteAck",
            RecordingsDeleteAck.make(
                session_dir="20260513-210410", ok=True, error=None
            ),
        ),
        ("RecordingsUsage", RecordingsUsage.make(sessions=12, bytes_total=3656838349)),
        ("RecordingsEvents", RecordingsEvents.make(session_dir="20260513-210410")),
        (
            "RecordingsEventsResult",
            RecordingsEventsResult.make(
                session_dir="20260513-210410",
                events=[
                    {
                        "t": 0.0,
                        "kind": "session_start",
                        "wall_clock_iso": "2026-05-13T21:04:10+02:00",
                        "session_dir": "20260513-210410",
                    },
                    {"t": 3.21, "kind": "trigger", "reason": "phase_change"},
                ],
            ),
        ),
        # Phase 20-04 — citation diagnostics
        (
            "SessionCitation",
            SessionCitation.make(
                slop_ratio=0.12,
                stripped_rate_15s=0.07,
                last_unverified_response=None,
                bypass_active=False,
            ),
        ),
        # Phase 24-02 — overlay-highlight
        (
            "SessionOverlayHighlight",
            SessionOverlayHighlight.make(
                element_id="waveform_a",
                color="amber",
                duration_ms=1300,
            ),
        ),
    ]


_EXAMPLES = _make_examples()


def test_example_count_matches_schema_oneof() -> None:
    """Sentinel: our roundtrip-example list must cover every schema oneOf entry.

    Phase 11 Wave 0 froze 19; Phase 12 added 7 (SessionSnapshot, SessionMute,
    SettingsSet, SettingsGet, SettingsState, StatusRecheck, IpcError) for
    total 26. Phase 13-05 added 1 (MascotMoodChange) → 27. Phase 15-01 adds
    7 (RecordingsList, RecordingsListResult, RecordingsDelete,
    RecordingsDeleteAck, RecordingsUsage, RecordingsEvents,
    RecordingsEventsResult) → 34. Phase 20-04 adds 1 (SessionCitation) → 35.
    Phase 24-02 adds 1 (SessionOverlayHighlight) → 36.
    """
    assert len(_EXAMPLES) == len(_SCHEMA["oneOf"]) == 36


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


def test_schema_oneof_count_is_36() -> None:
    """Plan-locked invariant — Phase 11 Wave 0 froze 19; Phase 12 added 7
    (19 → 26); Phase 13-05 added 1 (MascotMoodChange) → 27; Phase 15-01 adds
    7 recordings.* families → 34; Phase 20-04 adds 1 (SessionCitation) → 35;
    Phase 24-02 adds 1 (SessionOverlayHighlight) → 36.

    ``definitions`` is 37 because ``LevelPair`` is a shared helper ref'd
    from ``SessionSnapshot.meters`` but is not itself a top-level ipc.* message
    (so it counts in ``definitions`` but not in ``oneOf``).
    """
    assert len(_SCHEMA["oneOf"]) == 36
    assert len(_SCHEMA["definitions"]) == 37


def test_no_pydantic_imports_in_ui_bus() -> None:
    """Phase 6 + D-Area-4.4 convention: ``src/vibemix/ui_bus/`` is pydantic-free."""
    pkg = _REPO_ROOT / "src" / "vibemix" / "ui_bus"
    pattern = re.compile(r"^\s*(?:from|import)\s+pydantic\b", re.MULTILINE)
    offenders = []
    for py in pkg.rglob("*.py"):
        if pattern.search(py.read_text()):
            offenders.append(str(py.relative_to(_REPO_ROOT)))
    assert not offenders, f"pydantic import found in ui_bus: {offenders}"
