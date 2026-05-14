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
import sys
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import jsonschema

from vibemix.ui_bus.schemas.citation import SessionCitationPayload
from vibemix.ui_bus.schemas.debrief import (
    DebriefCitationSummaryPayload,
    DebriefEventTimelinePayload,
    DebriefSessionLoadedPayload,
)
from vibemix.ui_bus.schemas.overlay import SessionOverlayHighlightPayload


def _resolve_schema_path() -> Path:
    rel = Path("tauri") / "ui" / "src" / "ipc" / "messages.schema.json"
    # PyInstaller-frozen bundle: schema bundled under sys._MEIPASS.
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass) / rel
    # Dev source tree: parents[3] from src/vibemix/ui_bus/messages.py == repo root.
    return Path(__file__).resolve().parents[3] / rel


_SCHEMA_PATH = _resolve_schema_path()
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
# Phase 12 — session + settings payload structs
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LevelPair:
    rms: float
    peak: float


@dataclass(frozen=True, slots=True)
class MetersTriple:
    music: LevelPair
    voice: LevelPair
    mic: LevelPair


@dataclass(frozen=True, slots=True)
class PhaseChunk:
    kind: Literal["silent", "groove", "build", "drop-ghost"]
    weight: float
    label: str


@dataclass(frozen=True, slots=True)
class TranscriptLine:
    role: Literal["ai", "user", "system"]
    text: str
    ts: str


@dataclass(frozen=True, slots=True)
class MidiEventEntry:
    control: str
    value: float | str | None
    ts: str


@dataclass(frozen=True, slots=True)
class TrackInfo:
    title: str
    artist: str | None = None
    deck: str | None = None


@dataclass(frozen=True, slots=True)
class SessionSnapshotPayload:
    meters: MetersTriple
    phase: tuple[PhaseChunk, ...]
    phase_now_pct: float
    bpm: float | None
    drop_pred_bars: int | None
    transcript_delta: tuple[TranscriptLine, ...]
    midi_events: tuple[MidiEventEntry, ...]
    track: TrackInfo | None
    cohost_status: Literal["LISTENING", "TALKING", "IDLE"]
    latency_ms: float | None
    grounded: bool


@dataclass(frozen=True, slots=True)
class SessionMutePayload:
    """Asymmetric payload: shell sends ``toggle`` only, sidecar acks with ``muted`` only.

    Both fields optional in the schema; ``make_toggle()`` and ``make_ack()`` factories
    enforce the one-direction asymmetry.
    """

    toggle: bool | None = None
    muted: bool | None = None


@dataclass(frozen=True, slots=True)
class SettingsSetPayload:
    field: Literal[
        "voice",
        "mode",
        "genre",
        "output_device_id",
        "output_profile",
        "retention_days",
        "push_to_mute_hotkey",
        "mood",
        "click_through",
        "lighter_blur",
    ]
    value: str | int | bool | None


@dataclass(frozen=True, slots=True)
class SettingsGetPayload:
    pass


@dataclass(frozen=True, slots=True)
class SettingsStatePayload:
    voice: str
    mode: Literal["hype", "coach"]
    genre: str
    output_device_id: str | None
    output_profile: Literal["hp", "spk"]
    retention_days: int
    push_to_mute_hotkey: str
    muted: bool
    lighter_blur: bool
    # IN-03 in 14-REVIEW.md — optional fields so the SettingsSet enum's
    # 10 fields can round-trip through SettingsState. Default None
    # preserves the wire shape callers had before Phase 14 (the
    # schema's `additionalProperties: false` rejects keys that are
    # literally None when serialized; the wrapper's to_json strips None
    # via _strip_none_optionals — see SettingsState.make).
    mood: Literal["hype-man", "teacher", "coach"] | None = None
    click_through: bool | None = None


@dataclass(frozen=True, slots=True)
class StatusRecheckPayload:
    component: Literal["livekit", "gemini", "midi", "screen"]


@dataclass(frozen=True, slots=True)
class IpcErrorPayload:
    reason: str
    original_type: str | None = None


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


# ---------------------------------------------------------------------------
# Phase 12 wrapper dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SessionSnapshot:
    type: Literal["ipc.session.snapshot"]
    ts: str
    payload: SessionSnapshotPayload

    @classmethod
    def make(
        cls,
        *,
        meters: MetersTriple,
        phase: tuple[PhaseChunk, ...] = (),
        phase_now_pct: float = 0.0,
        bpm: float | None = None,
        drop_pred_bars: int | None = None,
        transcript_delta: tuple[TranscriptLine, ...] = (),
        midi_events: tuple[MidiEventEntry, ...] = (),
        track: TrackInfo | None = None,
        cohost_status: Literal["LISTENING", "TALKING", "IDLE"] = "IDLE",
        latency_ms: float | None = None,
        grounded: bool = False,
    ) -> SessionSnapshot:
        return cls(
            type="ipc.session.snapshot",
            ts=_now_iso(),
            payload=SessionSnapshotPayload(
                meters=meters,
                phase=phase,
                phase_now_pct=phase_now_pct,
                bpm=bpm,
                drop_pred_bars=drop_pred_bars,
                transcript_delta=transcript_delta,
                midi_events=midi_events,
                track=track,
                cohost_status=cohost_status,
                latency_ms=latency_ms,
                grounded=grounded,
            ),
        )

    def to_json(self) -> str:
        return _serialize(self)


@dataclass(frozen=True, slots=True)
class SessionMute:
    type: Literal["ipc.session.mute"]
    ts: str
    payload: SessionMutePayload

    @classmethod
    def make_toggle(cls) -> SessionMute:
        """Shell → sidecar: request a mute toggle."""
        return cls(
            type="ipc.session.mute",
            ts=_now_iso(),
            payload=SessionMutePayload(toggle=True),
        )

    @classmethod
    def make_ack(cls, *, muted: bool) -> SessionMute:
        """Sidecar → shell: ack with new mute state."""
        return cls(
            type="ipc.session.mute",
            ts=_now_iso(),
            payload=SessionMutePayload(muted=muted),
        )

    def to_json(self) -> str:
        # Drop None fields from payload — schema doesn't accept null for
        # toggle/muted (both are individually optional but never null).
        d = _tuples_to_lists(asdict(self))
        d["payload"] = {k: v for k, v in d["payload"].items() if v is not None}
        _validate(d)
        return json.dumps(d, separators=(",", ":"))


@dataclass(frozen=True, slots=True)
class SettingsSet:
    type: Literal["ipc.settings.set"]
    ts: str
    payload: SettingsSetPayload

    @classmethod
    def make(cls, *, field: str, value: str | int | None) -> SettingsSet:
        return cls(
            type="ipc.settings.set",
            ts=_now_iso(),
            payload=SettingsSetPayload(field=field, value=value),  # type: ignore[arg-type]
        )

    def to_json(self) -> str:
        return _serialize(self)


@dataclass(frozen=True, slots=True)
class SettingsGet:
    type: Literal["ipc.settings.get"]
    ts: str
    payload: SettingsGetPayload

    @classmethod
    def make(cls) -> SettingsGet:
        return cls(type="ipc.settings.get", ts=_now_iso(), payload=SettingsGetPayload())

    def to_json(self) -> str:
        return _serialize(self)


@dataclass(frozen=True, slots=True)
class SettingsState:
    type: Literal["ipc.settings.state"]
    ts: str
    payload: SettingsStatePayload

    @classmethod
    def make(
        cls,
        *,
        voice: str,
        mode: Literal["hype", "coach"],
        genre: str,
        output_device_id: str | None,
        output_profile: Literal["hp", "spk"],
        retention_days: int,
        push_to_mute_hotkey: str,
        muted: bool,
        lighter_blur: bool = False,
        # IN-03 in 14-REVIEW.md — optional. Callers that have a
        # MusicState reference (session loop) pass through; callers that
        # don't (tests, boot smoke) leave defaulted-None.
        mood: Literal["hype-man", "teacher", "coach"] | None = None,
        click_through: bool | None = None,
    ) -> SettingsState:
        return cls(
            type="ipc.settings.state",
            ts=_now_iso(),
            payload=SettingsStatePayload(
                voice=voice,
                mode=mode,
                genre=genre,
                output_device_id=output_device_id,
                output_profile=output_profile,
                retention_days=retention_days,
                push_to_mute_hotkey=push_to_mute_hotkey,
                muted=muted,
                lighter_blur=lighter_blur,
                mood=mood,
                click_through=click_through,
            ),
        )

    def to_json(self) -> str:
        return _serialize(self)


@dataclass(frozen=True, slots=True)
class StatusRecheck:
    type: Literal["ipc.status.recheck"]
    ts: str
    payload: StatusRecheckPayload

    @classmethod
    def make(cls, *, component: Literal["livekit", "gemini", "midi", "screen"]) -> StatusRecheck:
        return cls(
            type="ipc.status.recheck",
            ts=_now_iso(),
            payload=StatusRecheckPayload(component=component),
        )

    def to_json(self) -> str:
        return _serialize(self)


@dataclass(frozen=True, slots=True)
class IpcError:
    type: Literal["ipc.error"]
    ts: str
    payload: IpcErrorPayload

    @classmethod
    def make(cls, *, reason: str, original_type: str | None = None) -> IpcError:
        return cls(
            type="ipc.error",
            ts=_now_iso(),
            payload=IpcErrorPayload(reason=reason, original_type=original_type),
        )

    def to_json(self) -> str:
        # original_type is optional in the schema; drop when None.
        d = _tuples_to_lists(asdict(self))
        if d["payload"].get("original_type") is None:
            d["payload"].pop("original_type", None)
        _validate(d)
        return json.dumps(d, separators=(",", ":"))


# ---------------------------------------------------------------------------
# Phase 13-05 — MascotMoodChange envelope
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class MascotMoodChangePayload:
    """ipc.mascot.mood_change payload (Phase 13-05).

    ``mood`` is required; ``previous_mood`` + ``at`` are optional. Per the
    Phase 6 no-pydantic rule, the type is kept as ``str`` here — the
    Literal narrowing happens at the SettingsApplier validation site.
    """

    mood: str  # Literal["hype-man", "teacher", "coach"]
    previous_mood: str | None = None
    at: float | None = None


@dataclass(frozen=True, slots=True)
class MascotMoodChange:
    type: Literal["ipc.mascot.mood_change"]
    ts: str
    payload: MascotMoodChangePayload

    @classmethod
    def make(
        cls,
        *,
        mood: str,
        previous_mood: str | None = None,
        at: float | None = None,
    ) -> MascotMoodChange:
        return cls(
            type="ipc.mascot.mood_change",
            ts=_now_iso(),
            payload=MascotMoodChangePayload(
                mood=mood,
                previous_mood=previous_mood,
                at=at,
            ),
        )

    def to_json(self) -> str:
        # Drop previous_mood/at when None — schema accepts ["string", "null"]
        # for previous_mood + ["number", "null"] for at, but a cleaner wire
        # frame omits optionals when not set.
        d = _tuples_to_lists(asdict(self))
        for opt in ("previous_mood", "at"):
            if d["payload"].get(opt) is None:
                d["payload"].pop(opt, None)
        _validate(d)
        return json.dumps(d, separators=(",", ":"))


# ---------------------------------------------------------------------------
# Phase 15-01 — recordings.* payload structs + wrappers
# ---------------------------------------------------------------------------
# Seven new families: list (request, empty) + list_result (sessions array) +
# delete (request, session_dir) + delete_ack (response) + usage (push) +
# events (request, session_dir) + events_result (response, jsonl record array).
#
# session_dir is enforced at the SCHEMA level via ^[0-9]{8}-[0-9]{6}$ — the
# V12 path-traversal gate. Wrappers do NOT pre-validate; ``.to_json()`` calls
# ``_validate(d)`` which raises jsonschema.ValidationError on a bad value
# (matches the existing Phase 11 W0 invariant: validation lives on the
# serialize path, never inside the constructor).


@dataclass(frozen=True, slots=True)
class RecordingSummary:
    """One entry in ``RecordingsListResultPayload.sessions``.

    Mirrors the on-disk recordings/<YYYYMMDD-HHMMSS>/session.json metadata
    file (Phase 15 Plan 02). Crashed sessions surface ``crashed=True`` so
    the UI can render the row with a distinguishing badge per UI-SPEC.
    """

    session_dir: str
    started_at_iso: str
    duration_s: float
    event_count: int
    bytes_total: int
    crashed: bool


@dataclass(frozen=True, slots=True)
class RecordingsListPayload:
    pass


@dataclass(frozen=True, slots=True)
class RecordingsListResultPayload:
    sessions: tuple[RecordingSummary, ...] = ()
    bytes_total: int = 0


@dataclass(frozen=True, slots=True)
class RecordingsDeletePayload:
    session_dir: str


@dataclass(frozen=True, slots=True)
class RecordingsDeleteAckPayload:
    session_dir: str
    ok: bool
    error: str | None = None


@dataclass(frozen=True, slots=True)
class RecordingsUsagePayload:
    sessions: int
    bytes_total: int


@dataclass(frozen=True, slots=True)
class RecordingsEventsPayload:
    session_dir: str


@dataclass(frozen=True, slots=True)
class RecordingsEventsResultPayload:
    session_dir: str
    # Heterogeneous events.jsonl records — each dict has at least `t` + `kind`
    # plus arbitrary kind-specific extras (validated by the schema's
    # additionalProperties: true on the per-event element). We keep the
    # element type as ``dict`` rather than typing it further so new event
    # kinds (Phase 16 hallucination verifier + Phase 13 mascot mood-change
    # log line) don't churn this signature.
    events: tuple[dict, ...] = ()


@dataclass(frozen=True, slots=True)
class RecordingsList:
    type: Literal["ipc.recordings.list"]
    ts: str
    payload: RecordingsListPayload

    @classmethod
    def make(cls) -> RecordingsList:
        return cls(
            type="ipc.recordings.list",
            ts=_now_iso(),
            payload=RecordingsListPayload(),
        )

    def to_json(self) -> str:
        return _serialize(self)


@dataclass(frozen=True, slots=True)
class RecordingsListResult:
    type: Literal["ipc.recordings.list_result"]
    ts: str
    payload: RecordingsListResultPayload

    @classmethod
    def make(
        cls,
        *,
        sessions: tuple[RecordingSummary, ...] | list[RecordingSummary] = (),
        bytes_total: int = 0,
    ) -> RecordingsListResult:
        return cls(
            type="ipc.recordings.list_result",
            ts=_now_iso(),
            payload=RecordingsListResultPayload(
                sessions=tuple(sessions),
                bytes_total=bytes_total,
            ),
        )

    def to_json(self) -> str:
        return _serialize(self)


@dataclass(frozen=True, slots=True)
class RecordingsDelete:
    type: Literal["ipc.recordings.delete"]
    ts: str
    payload: RecordingsDeletePayload

    @classmethod
    def make(cls, *, session_dir: str) -> RecordingsDelete:
        return cls(
            type="ipc.recordings.delete",
            ts=_now_iso(),
            payload=RecordingsDeletePayload(session_dir=session_dir),
        )

    def to_json(self) -> str:
        return _serialize(self)


@dataclass(frozen=True, slots=True)
class RecordingsDeleteAck:
    type: Literal["ipc.recordings.delete_ack"]
    ts: str
    payload: RecordingsDeleteAckPayload

    @classmethod
    def make(
        cls,
        *,
        session_dir: str,
        ok: bool,
        error: str | None = None,
    ) -> RecordingsDeleteAck:
        return cls(
            type="ipc.recordings.delete_ack",
            ts=_now_iso(),
            payload=RecordingsDeleteAckPayload(
                session_dir=session_dir,
                ok=ok,
                error=error,
            ),
        )

    def to_json(self) -> str:
        return _serialize(self)


@dataclass(frozen=True, slots=True)
class RecordingsUsage:
    type: Literal["ipc.recordings.usage"]
    ts: str
    payload: RecordingsUsagePayload

    @classmethod
    def make(cls, *, sessions: int, bytes_total: int) -> RecordingsUsage:
        return cls(
            type="ipc.recordings.usage",
            ts=_now_iso(),
            payload=RecordingsUsagePayload(sessions=sessions, bytes_total=bytes_total),
        )

    def to_json(self) -> str:
        return _serialize(self)


@dataclass(frozen=True, slots=True)
class RecordingsEvents:
    type: Literal["ipc.recordings.events"]
    ts: str
    payload: RecordingsEventsPayload

    @classmethod
    def make(cls, *, session_dir: str) -> RecordingsEvents:
        return cls(
            type="ipc.recordings.events",
            ts=_now_iso(),
            payload=RecordingsEventsPayload(session_dir=session_dir),
        )

    def to_json(self) -> str:
        return _serialize(self)


@dataclass(frozen=True, slots=True)
class RecordingsEventsResult:
    type: Literal["ipc.recordings.events_result"]
    ts: str
    payload: RecordingsEventsResultPayload

    @classmethod
    def make(
        cls,
        *,
        session_dir: str,
        events: tuple[dict, ...] | list[dict] = (),
    ) -> RecordingsEventsResult:
        return cls(
            type="ipc.recordings.events_result",
            ts=_now_iso(),
            payload=RecordingsEventsResultPayload(
                session_dir=session_dir,
                events=tuple(events),
            ),
        )

    def to_json(self) -> str:
        return _serialize(self)


# ---------------------------------------------------------------------------
# Phase 20-04 — Citation diagnostics IPC
# ---------------------------------------------------------------------------
# GROUND-06 + 20-CONTEXT D-Bypass-Audit-Surface — sidecar→shell push of the
# CitationLinter's slop_ratio + StrippedRateTracker's 15s rolling rate +
# last unverified response text + bypass_active flag. Read-only telemetry;
# the Tauri Settings → Diagnostics surface consumes for live display.
# Payload struct lives in vibemix.ui_bus.schemas.citation (subpackage layout
# adopted in Plan 20-04 — keeps messages.py wrappers thin).


@dataclass(frozen=True, slots=True)
class SessionCitation:
    type: Literal["ipc.session.citation"]
    ts: str
    payload: SessionCitationPayload

    @classmethod
    def make(
        cls,
        *,
        slop_ratio: float,
        stripped_rate_15s: float,
        last_unverified_response: str | None,
        bypass_active: bool,
    ) -> SessionCitation:
        return cls(
            type="ipc.session.citation",
            ts=_now_iso(),
            payload=SessionCitationPayload(
                slop_ratio=slop_ratio,
                stripped_rate_15s=stripped_rate_15s,
                last_unverified_response=last_unverified_response,
                bypass_active=bypass_active,
            ),
        )

    def to_json(self) -> str:
        return _serialize(self)


# ---------------------------------------------------------------------------
# Phase 24-02 — Overlay highlight IPC
# ---------------------------------------------------------------------------
# OVERLAY-01 — sidecar→shell push fired on a valid [screen:<element_id>]
# citation when the citation linter's action is "emit" (i.e. the user
# actually heard the response). The Tauri shell invokes Rust
# show_overlay_highlight; AX query → transparent click-through overlay
# window → amber ring CSS animation → auto-close after duration_ms.
# Payload struct lives in vibemix.ui_bus.schemas.overlay (subpackage layout
# matches Plan 20-04 SessionCitation conventions).


@dataclass(frozen=True, slots=True)
class SessionOverlayHighlight:
    type: Literal["ipc.session.overlay-highlight"]
    ts: str
    payload: SessionOverlayHighlightPayload

    @classmethod
    def make(
        cls,
        *,
        element_id: str,
        color: Literal["amber", "red", "green", "blue"] = "amber",
        duration_ms: int = 1300,
    ) -> SessionOverlayHighlight:
        return cls(
            type="ipc.session.overlay-highlight",
            ts=_now_iso(),
            payload=SessionOverlayHighlightPayload(
                element_id=element_id,
                color=color,
                duration_ms=duration_ms,
            ),
        )

    def to_json(self) -> str:
        return _serialize(self)

    def to_dict(self) -> dict:
        """Convenience: serialize + reparse to a plain dict for ipc_bus.emit
        callers that prefer not to JSON-roundtrip themselves. Mirrors the
        coach.py SessionCitation publish pattern."""
        return json.loads(self.to_json())


# ---------------------------------------------------------------------------
# Phase 25 Plan 25-03 — DEBRIEF architectural slot (3 wrappers)
# ---------------------------------------------------------------------------
# DEBRIEF-01 + DEBRIEF-02: reservation only in v2.0 — the sidecar
# ``--debrief`` flag binds a separate ws bus on 127.0.0.1:8766 (port
# constant in vibemix.__main__.DEBRIEF_PORT) and emits these 3 schemas.
# v2.1 fills in the chaptered TL;DR + drill cards + clickable timeline
# behind the SAME message types — schemas locked here.


@dataclass(frozen=True, slots=True)
class DebriefSessionLoaded:
    type: Literal["ipc.debrief.session-loaded"]
    ts: str
    payload: DebriefSessionLoadedPayload

    @classmethod
    def make(
        cls,
        *,
        session_id: str,
        started_at: float,
        duration_s: float,
    ) -> DebriefSessionLoaded:
        return cls(
            type="ipc.debrief.session-loaded",
            ts=_now_iso(),
            payload=DebriefSessionLoadedPayload(
                session_id=session_id,
                started_at=started_at,
                duration_s=duration_s,
            ),
        )

    def to_json(self) -> str:
        return _serialize(self)


@dataclass(frozen=True, slots=True)
class DebriefCitationSummary:
    type: Literal["ipc.debrief.citation-summary"]
    ts: str
    payload: DebriefCitationSummaryPayload

    @classmethod
    def make(
        cls,
        *,
        total: int,
        valid: int,
        stripped: int,
        bypassed: int,
    ) -> DebriefCitationSummary:
        return cls(
            type="ipc.debrief.citation-summary",
            ts=_now_iso(),
            payload=DebriefCitationSummaryPayload(
                total=total,
                valid=valid,
                stripped=stripped,
                bypassed=bypassed,
            ),
        )

    def to_json(self) -> str:
        return _serialize(self)


@dataclass(frozen=True, slots=True)
class DebriefEventTimeline:
    type: Literal["ipc.debrief.event-timeline"]
    ts: str
    payload: DebriefEventTimelinePayload

    @classmethod
    def make(
        cls,
        *,
        events: tuple[dict, ...] | list[dict],
    ) -> DebriefEventTimeline:
        # Normalize list→tuple for frozen dataclass hashability. The
        # ``_tuples_to_lists`` helper above converts back to list at JSON
        # serialization time so the schema's ``type: array`` is honored.
        events_tuple = tuple(events)
        return cls(
            type="ipc.debrief.event-timeline",
            ts=_now_iso(),
            payload=DebriefEventTimelinePayload(events=events_tuple),
        )

    def to_json(self) -> str:
        return _serialize(self)


# Suppress unused-import flake when ``field`` is not used by any wrapper above.
# Keeping the import allows future wrappers with default factories to use it
# without a churn-only diff.
_ = field
