# SPDX-License-Identifier: Apache-2.0
"""ipc.* message dataclasses for the Tauri shell ↔ Python sidecar bridge.

Phase 11 Wave 0 — the source-of-truth schema lives at
``tauri/ui/src/ipc/messages.schema.json`` (Draft-07). Every wrapper dataclass
here mirrors exactly one schema ``oneOf`` entry; the count-parity assertion
in ``scripts/check_ipc_schema.py`` enforces 1:1 correspondence.

Project convention (Phase 6 + D-Area-4.4): no pydantic anywhere in
``src/vibemix/``. Validation is jsonschema-only — pure runtime guard, no
model generation. Wrapper classes are hand-written ``@dataclass(frozen=True,
slots=True)`` instances with a ``.make()`` factory (fills ``type``/``ts``)
and ``.to_json()`` (asdict → validator.validate → ``json.dumps``).

The ``_VALIDATOR = jsonschema.Draft7Validator(_SCHEMA)`` is compiled once at
module import; per-call validation is ``_VALIDATOR.validate(d)`` (Draft-07
ref-resolver is cached internally, much cheaper than top-level
``jsonschema.validate`` which re-compiles each call).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import jsonschema

# Resolve the schema relative to this file:
#   src/vibemix/ui_bus/messages.py  -> parents[3] == repo root.
#   parents[0] = ui_bus, [1] = vibemix, [2] = src, [3] = repo root.
_SCHEMA_PATH = (
    Path(__file__).resolve().parents[3] / "tauri" / "ui" / "src" / "ipc" / "messages.schema.json"
)
_SCHEMA: dict = json.loads(_SCHEMA_PATH.read_text())
_VALIDATOR = jsonschema.Draft7Validator(_SCHEMA)


def _now_iso() -> str:
    """UTC ISO-8601 timestamp matching the schema ``date-time`` format."""
    return datetime.now(UTC).isoformat()


def _tuples_to_lists(value):
    """Recursively convert tuples to lists so jsonschema accepts ``type:array``.

    ``dataclasses.asdict`` preserves tuples (we use tuples on payload structs
    for hashability of frozen dataclasses); jsonschema's Draft-07 type checker
    rejects tuples for ``type: "array"`` since they are not ``list``. JSON
    itself has no tuple concept — once serialized with ``json.dumps``, both
    map to JSON arrays — so converting in-place is the natural fix.
    """
    if isinstance(value, tuple):
        return [_tuples_to_lists(v) for v in value]
    if isinstance(value, list):
        return [_tuples_to_lists(v) for v in value]
    if isinstance(value, dict):
        return {k: _tuples_to_lists(v) for k, v in value.items()}
    return value


# ---------------------------------------------------------------------------
# Payload-only structs
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class IpcBootPayload:
    ready: bool


@dataclass(frozen=True, slots=True)
class StatusTickPayload:
    livekit: Literal["ok", "connecting", "down"]
    gemini: Literal["ok", "down"]
    # ``midi`` is the count of connected MIDI inputs; null when the platform
    # backend is unavailable (e.g. mido import failed). minimum: 0 in schema.
    midi: int | None
    screen: Literal["ok", "denied"]


@dataclass(frozen=True, slots=True)
class PermissionCheckPayload:
    kind: Literal["screen_recording", "microphone"]


@dataclass(frozen=True, slots=True)
class PermissionStatePayload:
    kind: Literal["screen_recording", "microphone"]
    status: Literal["authorized", "denied", "notDetermined", "restricted"]


@dataclass(frozen=True, slots=True)
class DeviceInfo:
    """One entry in ``CalibrationDeviceListPayload.devices``."""

    id: str
    name: str
    is_blackhole: bool
    # ``variant`` is the BlackHole channel-count tag (e.g. "2ch", "16ch",
    # "64ch") when the device matches BlackHole, else None. D-Area-4.1.
    variant: str | None


@dataclass(frozen=True, slots=True)
class CalibrationListDevicesPayload:
    pass


@dataclass(frozen=True, slots=True)
class CalibrationDeviceListPayload:
    devices: tuple[DeviceInfo, ...]
    blackhole_present: bool


@dataclass(frozen=True, slots=True)
class CalibrationProbeAudioPayload:
    output_device_id: str
    expected_rate: Literal[44100, 48000]


@dataclass(frozen=True, slots=True)
class CalibrationAudioResultPayload:
    playback_ok: bool
    audible_confirmed: bool
    programmatic_pass: bool
    # ``actual_rate`` is the sounddevice-negotiated rate after stream open;
    # null on error paths where the stream never opened.
    actual_rate: int | None
    error: str | None


@dataclass(frozen=True, slots=True)
class CalibrationUserHeardTonePayload:
    heard: bool


@dataclass(frozen=True, slots=True)
class CalibrationStartMidiListenPayload:
    timeout_s: float


@dataclass(frozen=True, slots=True)
class CalibrationMidiEventPayload:
    control_label: str
    raw: str


@dataclass(frozen=True, slots=True)
class CalibrationMidiTimeoutPayload:
    pass


@dataclass(frozen=True, slots=True)
class CalibrationListWindowsPayload:
    pass


@dataclass(frozen=True, slots=True)
class WindowInfo:
    """One entry in ``CalibrationWindowListPayload.windows``."""

    id: str
    app_name: str
    title: str
    # DJ-app hint resolved by the platform layer; null when no known DJ app
    # name matches. D-Area-3.2 supported set: djay, rekordbox, serato,
    # traktor, virtualdj.
    dj_app_hint: str | None


@dataclass(frozen=True, slots=True)
class CalibrationWindowListPayload:
    windows: tuple[WindowInfo, ...]


@dataclass(frozen=True, slots=True)
class CalibrationSmokeTestPayload:
    template: Literal["HYPE_BEGINNER"]


@dataclass(frozen=True, slots=True)
class CalibrationSmokeTestStartedPayload:
    pass


@dataclass(frozen=True, slots=True)
class CalibrationSmokeTestDonePayload:
    transcript: str


@dataclass(frozen=True, slots=True)
class WizardStartPayload:
    pass


@dataclass(frozen=True, slots=True)
class WizardDonePayload:
    output_device_id: str
    controller_profile: str
    target_window_id: str | None


# ---------------------------------------------------------------------------
# Wrapper dataclasses (one per schema oneOf entry — 19 total)
# ---------------------------------------------------------------------------
# Each wrapper carries the three-field envelope: ``type`` (const string), ``ts``
# (date-time), ``payload`` (nested struct). Wrapper-class count MUST equal
# schema oneOf count (asserted by scripts/check_ipc_schema.py).


def _validate(d: dict) -> None:
    """Compile-once validator (Draft-07). Raises ``jsonschema.ValidationError``."""
    _VALIDATOR.validate(d)


def _serialize(self) -> str:  # type: ignore[no-untyped-def]
    """Shared ``.to_json`` body — asdict → tuples→lists → validate → dumps.

    Pulled out so every wrapper's ``to_json`` method is a single call rather
    than 19 copies of the same five lines. The tuple-to-list step is required
    because ``dataclasses.asdict`` preserves tuples (we use tuples for
    payload-struct array fields so the frozen wrappers stay hashable);
    jsonschema's Draft-07 type checker rejects tuples for ``type: "array"``.
    """
    d = _tuples_to_lists(asdict(self))
    _validate(d)
    return json.dumps(d, separators=(",", ":"))


@dataclass(frozen=True, slots=True)
class IpcBoot:
    type: Literal["ipc.boot"]
    ts: str
    payload: IpcBootPayload

    @classmethod
    def make(cls, *, ready: bool) -> IpcBoot:
        return cls(type="ipc.boot", ts=_now_iso(), payload=IpcBootPayload(ready=ready))

    def to_json(self) -> str:
        return _serialize(self)


@dataclass(frozen=True, slots=True)
class StatusTick:
    type: Literal["ipc.status.tick"]
    ts: str
    payload: StatusTickPayload

    @classmethod
    def make(
        cls,
        *,
        livekit: Literal["ok", "connecting", "down"],
        gemini: Literal["ok", "down"],
        midi: int | None,
        screen: Literal["ok", "denied"],
    ) -> StatusTick:
        return cls(
            type="ipc.status.tick",
            ts=_now_iso(),
            payload=StatusTickPayload(livekit=livekit, gemini=gemini, midi=midi, screen=screen),
        )

    def to_json(self) -> str:
        return _serialize(self)


@dataclass(frozen=True, slots=True)
class PermissionCheck:
    type: Literal["ipc.permission.check"]
    ts: str
    payload: PermissionCheckPayload

    @classmethod
    def make(cls, *, kind: Literal["screen_recording", "microphone"]) -> PermissionCheck:
        return cls(
            type="ipc.permission.check",
            ts=_now_iso(),
            payload=PermissionCheckPayload(kind=kind),
        )

    def to_json(self) -> str:
        return _serialize(self)


@dataclass(frozen=True, slots=True)
class PermissionState:
    type: Literal["ipc.permission.state"]
    ts: str
    payload: PermissionStatePayload

    @classmethod
    def make(
        cls,
        *,
        kind: Literal["screen_recording", "microphone"],
        status: Literal["authorized", "denied", "notDetermined", "restricted"],
    ) -> PermissionState:
        return cls(
            type="ipc.permission.state",
            ts=_now_iso(),
            payload=PermissionStatePayload(kind=kind, status=status),
        )

    def to_json(self) -> str:
        return _serialize(self)


@dataclass(frozen=True, slots=True)
class CalibrationListDevices:
    type: Literal["ipc.calibration.list_devices"]
    ts: str
    payload: CalibrationListDevicesPayload

    @classmethod
    def make(cls) -> CalibrationListDevices:
        return cls(
            type="ipc.calibration.list_devices",
            ts=_now_iso(),
            payload=CalibrationListDevicesPayload(),
        )

    def to_json(self) -> str:
        return _serialize(self)


@dataclass(frozen=True, slots=True)
class CalibrationDeviceList:
    type: Literal["ipc.calibration.device_list"]
    ts: str
    payload: CalibrationDeviceListPayload

    @classmethod
    def make(
        cls,
        *,
        devices: tuple[DeviceInfo, ...] | list[DeviceInfo],
        blackhole_present: bool,
    ) -> CalibrationDeviceList:
        return cls(
            type="ipc.calibration.device_list",
            ts=_now_iso(),
            payload=CalibrationDeviceListPayload(
                devices=tuple(devices), blackhole_present=blackhole_present
            ),
        )

    def to_json(self) -> str:
        return _serialize(self)


@dataclass(frozen=True, slots=True)
class CalibrationProbeAudio:
    type: Literal["ipc.calibration.probe_audio"]
    ts: str
    payload: CalibrationProbeAudioPayload

    @classmethod
    def make(
        cls, *, output_device_id: str, expected_rate: Literal[44100, 48000]
    ) -> CalibrationProbeAudio:
        return cls(
            type="ipc.calibration.probe_audio",
            ts=_now_iso(),
            payload=CalibrationProbeAudioPayload(
                output_device_id=output_device_id, expected_rate=expected_rate
            ),
        )

    def to_json(self) -> str:
        return _serialize(self)


@dataclass(frozen=True, slots=True)
class CalibrationAudioResult:
    type: Literal["ipc.calibration.audio_result"]
    ts: str
    payload: CalibrationAudioResultPayload

    @classmethod
    def make(
        cls,
        *,
        playback_ok: bool,
        audible_confirmed: bool,
        programmatic_pass: bool,
        actual_rate: int | None,
        error: str | None,
    ) -> CalibrationAudioResult:
        return cls(
            type="ipc.calibration.audio_result",
            ts=_now_iso(),
            payload=CalibrationAudioResultPayload(
                playback_ok=playback_ok,
                audible_confirmed=audible_confirmed,
                programmatic_pass=programmatic_pass,
                actual_rate=actual_rate,
                error=error,
            ),
        )

    def to_json(self) -> str:
        return _serialize(self)


@dataclass(frozen=True, slots=True)
class CalibrationUserHeardTone:
    type: Literal["ipc.calibration.user_heard_tone"]
    ts: str
    payload: CalibrationUserHeardTonePayload

    @classmethod
    def make(cls, *, heard: bool) -> CalibrationUserHeardTone:
        return cls(
            type="ipc.calibration.user_heard_tone",
            ts=_now_iso(),
            payload=CalibrationUserHeardTonePayload(heard=heard),
        )

    def to_json(self) -> str:
        return _serialize(self)


@dataclass(frozen=True, slots=True)
class CalibrationStartMidiListen:
    type: Literal["ipc.calibration.start_midi_listen"]
    ts: str
    payload: CalibrationStartMidiListenPayload

    @classmethod
    def make(cls, *, timeout_s: float) -> CalibrationStartMidiListen:
        return cls(
            type="ipc.calibration.start_midi_listen",
            ts=_now_iso(),
            payload=CalibrationStartMidiListenPayload(timeout_s=timeout_s),
        )

    def to_json(self) -> str:
        return _serialize(self)


@dataclass(frozen=True, slots=True)
class CalibrationMidiEvent:
    type: Literal["ipc.calibration.midi_event"]
    ts: str
    payload: CalibrationMidiEventPayload

    @classmethod
    def make(cls, *, control_label: str, raw: str) -> CalibrationMidiEvent:
        return cls(
            type="ipc.calibration.midi_event",
            ts=_now_iso(),
            payload=CalibrationMidiEventPayload(control_label=control_label, raw=raw),
        )

    def to_json(self) -> str:
        return _serialize(self)


@dataclass(frozen=True, slots=True)
class CalibrationMidiTimeout:
    type: Literal["ipc.calibration.midi_timeout"]
    ts: str
    payload: CalibrationMidiTimeoutPayload

    @classmethod
    def make(cls) -> CalibrationMidiTimeout:
        return cls(
            type="ipc.calibration.midi_timeout",
            ts=_now_iso(),
            payload=CalibrationMidiTimeoutPayload(),
        )

    def to_json(self) -> str:
        return _serialize(self)


@dataclass(frozen=True, slots=True)
class CalibrationListWindows:
    type: Literal["ipc.calibration.list_windows"]
    ts: str
    payload: CalibrationListWindowsPayload

    @classmethod
    def make(cls) -> CalibrationListWindows:
        return cls(
            type="ipc.calibration.list_windows",
            ts=_now_iso(),
            payload=CalibrationListWindowsPayload(),
        )

    def to_json(self) -> str:
        return _serialize(self)


@dataclass(frozen=True, slots=True)
class CalibrationWindowList:
    type: Literal["ipc.calibration.window_list"]
    ts: str
    payload: CalibrationWindowListPayload

    @classmethod
    def make(cls, *, windows: tuple[WindowInfo, ...] | list[WindowInfo]) -> CalibrationWindowList:
        return cls(
            type="ipc.calibration.window_list",
            ts=_now_iso(),
            payload=CalibrationWindowListPayload(windows=tuple(windows)),
        )

    def to_json(self) -> str:
        return _serialize(self)


@dataclass(frozen=True, slots=True)
class CalibrationSmokeTest:
    type: Literal["ipc.calibration.smoke_test"]
    ts: str
    payload: CalibrationSmokeTestPayload

    @classmethod
    def make(cls, *, template: Literal["HYPE_BEGINNER"]) -> CalibrationSmokeTest:
        return cls(
            type="ipc.calibration.smoke_test",
            ts=_now_iso(),
            payload=CalibrationSmokeTestPayload(template=template),
        )

    def to_json(self) -> str:
        return _serialize(self)


@dataclass(frozen=True, slots=True)
class CalibrationSmokeTestStarted:
    type: Literal["ipc.calibration.smoke_test_started"]
    ts: str
    payload: CalibrationSmokeTestStartedPayload

    @classmethod
    def make(cls) -> CalibrationSmokeTestStarted:
        return cls(
            type="ipc.calibration.smoke_test_started",
            ts=_now_iso(),
            payload=CalibrationSmokeTestStartedPayload(),
        )

    def to_json(self) -> str:
        return _serialize(self)


@dataclass(frozen=True, slots=True)
class CalibrationSmokeTestDone:
    type: Literal["ipc.calibration.smoke_test_done"]
    ts: str
    payload: CalibrationSmokeTestDonePayload

    @classmethod
    def make(cls, *, transcript: str) -> CalibrationSmokeTestDone:
        return cls(
            type="ipc.calibration.smoke_test_done",
            ts=_now_iso(),
            payload=CalibrationSmokeTestDonePayload(transcript=transcript),
        )

    def to_json(self) -> str:
        return _serialize(self)


@dataclass(frozen=True, slots=True)
class WizardStart:
    type: Literal["ipc.wizard.start"]
    ts: str
    payload: WizardStartPayload

    @classmethod
    def make(cls) -> WizardStart:
        return cls(type="ipc.wizard.start", ts=_now_iso(), payload=WizardStartPayload())

    def to_json(self) -> str:
        return _serialize(self)


@dataclass(frozen=True, slots=True)
class WizardDone:
    type: Literal["ipc.wizard.done"]
    ts: str
    payload: WizardDonePayload

    @classmethod
    def make(
        cls,
        *,
        output_device_id: str,
        controller_profile: str,
        target_window_id: str | None,
    ) -> WizardDone:
        return cls(
            type="ipc.wizard.done",
            ts=_now_iso(),
            payload=WizardDonePayload(
                output_device_id=output_device_id,
                controller_profile=controller_profile,
                target_window_id=target_window_id,
            ),
        )

    def to_json(self) -> str:
        return _serialize(self)


# Suppress unused-import flake when ``field`` is not used by any wrapper above.
# Keeping the import allows future wrappers with default factories to use it
# without a churn-only diff.
_ = field
