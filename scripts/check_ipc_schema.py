#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Phase 11 Wave 0 build-time CI gate — IPC schema vs Python dataclasses.

Runs two checks; either failing exits non-zero:

  1. Per-wrapper roundtrip — every wrapper dataclass in
     ``vibemix.ui_bus.messages`` is instantiated with a minimal-valid example
     (the same set tests/ui_bus/test_messages_schema.py uses), serialized via
     ``.to_json()``, parsed back, and validated against the source-of-truth
     schema. Detects "wrapper drifted away from schema field shape".

  2. Count parity — the schema ``oneOf`` length must equal the wrapper-class
     count (dataclasses with a ``type`` field in ``__dataclass_fields__``).
     Detects "schema added without wrapper" and "wrapper added without schema
     entry" — the canonical drift class Wave 0 must catch loud.

This script complements ``npm run check:ipc`` (codegen + tsc --noEmit) — both
are required CI gates per RESEARCH Pattern 3 / D-Area-1.3.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import jsonschema

# Import the wrapper module + bring it into local scope for introspection.
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
from vibemix.ui_bus import messages as ui_bus_messages

# Resolve the schema relative to this script — fails loud if it moves.
_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCHEMA_PATH = _REPO_ROOT / "tauri" / "ui" / "src" / "ipc" / "messages.schema.json"


def _minimal_examples() -> list[tuple[str, object]]:
    """Same minimal-valid examples as tests/ui_bus/test_messages_schema.py.

    Kept in sync intentionally — if a wrapper grows a required field, this
    list updates and the test fixture updates with it.
    """
    return [
        ("IpcBoot", IpcBoot.make(ready=True)),
        ("StatusTick", StatusTick.make(livekit="ok", gemini="ok", midi=1, screen="ok")),
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
            CalibrationMidiEvent.make(
                control_label="Deck A Play", raw="note_on ch=0 note=44"
            ),
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
            CalibrationSmokeTestDone.make(
                transcript="yo we're live, deck spins when you are"
            ),
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


def _count_wrapper_dataclasses() -> int:
    """Wrapper dataclasses == dataclasses with a ``type`` field in their
    ``__dataclass_fields__``. Excludes payload-only structs (``*Payload`` /
    ``DeviceInfo`` / ``WindowInfo``) because they have no ``type`` field.
    """
    count = 0
    for name in dir(ui_bus_messages):
        obj = getattr(ui_bus_messages, name)
        if (
            isinstance(obj, type)
            and hasattr(obj, "__dataclass_fields__")
            and "type" in obj.__dataclass_fields__
        ):
            count += 1
    return count


def main() -> int:
    if not _SCHEMA_PATH.exists():
        print(f"FAIL: schema not found at {_SCHEMA_PATH}", file=sys.stderr)
        return 1

    schema = json.loads(_SCHEMA_PATH.read_text())

    # Sanity — schema must itself be Draft-07 conformant.
    try:
        jsonschema.Draft7Validator.check_schema(schema)
    except jsonschema.SchemaError as e:
        print(f"FAIL: schema is not valid Draft-07: {e}", file=sys.stderr)
        return 1

    # 1) Per-wrapper roundtrip.
    examples = _minimal_examples()
    errors: list[str] = []
    for name, msg in examples:
        try:
            raw = msg.to_json()  # type: ignore[attr-defined]
            parsed = json.loads(raw)
            jsonschema.validate(parsed, schema)
        except jsonschema.ValidationError as e:
            errors.append(f"{name}: schema validation failed — {e.message}")
        except Exception as e:  # noqa: BLE001 — show every failure mode
            errors.append(f"{name}: {type(e).__name__} — {e}")
    if errors:
        print("FAIL: dataclass→schema roundtrip errors:", file=sys.stderr)
        for line in errors:
            print(f"  - {line}", file=sys.stderr)
        return 1

    n_ok = len(examples)
    print(f"OK: {n_ok} dataclasses validate against schema")

    # 2) Count-parity assertion — the load-bearing drift detector.
    oneof_count = len(schema["oneOf"])
    wrapper_count = _count_wrapper_dataclasses()
    if oneof_count != wrapper_count:
        print(
            f"FAIL: schema/dataclass drift — {oneof_count} oneOf entries vs "
            f"{wrapper_count} wrapper dataclasses. Add the missing schema "
            f"definition or wrapper class so both sides stay in sync.",
            file=sys.stderr,
        )
        return 1
    print(
        f"OK: count parity — {oneof_count} oneOf entries == {wrapper_count} "
        f"wrapper dataclasses"
    )

    # 3) Belt-and-braces — every example must also map to one of the schema's
    # oneOf branches. The roundtrip above proves it implicitly; this prints
    # the human-friendly tally so CI logs are useful.
    if n_ok != oneof_count:
        print(
            f"FAIL: example count {n_ok} does not match schema oneOf count "
            f"{oneof_count} — update _minimal_examples().",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
