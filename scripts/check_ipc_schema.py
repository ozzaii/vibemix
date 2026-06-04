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
import re
import sys
from pathlib import Path
from typing import get_args, get_type_hints

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
    ChapterRegionPayload,
    DebriefChapterList,
    DebriefCitationTooltip,
    DebriefCitationTooltipReq,
    DebriefDrills,
    DebriefError,
    DebriefSessionLoaded,
    DebriefTldrAudio,
    DeviceInfo,
    DrillPayload,
    IpcBoot,
    IpcError,
    LearnAck,
    LearnAdvance,
    LearnCompleteLesson,
    LearnControllerDetected,
    LearnControlRect,
    LearnExemplarPlay,
    LearnExemplarStop,
    LearnHighlight,
    LearnLessonLoaded,
    LearnLiveGrade,
    LearnMidiPosition,
    LearnPlayheadTick,
    LearnProgressDot,
    LearnProgressState,
    LearnStartCourse,
    LearnStartLesson,
    LearnTeachingFocus,
    LearnTutorSpeak,
    LearnWaveformReady,
    LevelPair,
    LibraryImport,
    LibraryImportCancel,
    LibraryImportProgress,
    LibraryStalenessAction,
    LibraryStalenessNudge,
    MascotMoodChange,
    MetersTriple,
    PermissionCheck,
    PermissionState,
    ProfileConsentState,
    ProfileDelete,
    ProfileDeleteAck,
    ProfileRegenerate,
    ProfileRegenerateResult,
    ProfileSetConsent,
    ProfileView,
    ProfileViewResult,
    RecordingsDelete,
    RecordingsDeleteAck,
    RecordingsEvents,
    RecordingsEventsResult,
    RecordingsList,
    RecordingsListResult,
    RecordingSummary,
    RecordingsUsage,
    SessionCitation,
    SessionCohostReaction,
    SessionMute,
    SessionOverlayHighlight,
    SessionSetMode,
    SessionSnapshot,
    SettingsGet,
    SettingsSet,
    SettingsState,
    StatusRecheck,
    StatusTick,
    WindowInfo,
    WizardDone,
    WizardSetSkill,
    WizardStart,
)
from vibemix.ui_bus import learn_messages as ui_bus_learn_messages
from vibemix.ui_bus import messages as ui_bus_messages

# Resolve the schema relative to this script — fails loud if it moves.
_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCHEMA_PATH = _REPO_ROOT / "tauri" / "ui" / "src" / "ipc" / "messages.schema.json"
_WS_BRIDGE_PATH = _REPO_ROOT / "tauri" / "ui" / "src" / "session" / "ws-bridge.ts"


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
        ("WizardSetSkill", WizardSetSkill.make(skill="intermediate")),
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
        ("SessionSetMode", SessionSetMode.make(mode="build")),
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
        ("IpcError", IpcError.make(reason="invalid payload", original_type="ipc.settings.set")),
        # Phase 13 wrappers
        (
            "MascotMoodChange",
            MascotMoodChange.make(mood="teacher", previous_mood="hype-man", at=1234.56),
        ),
        # Phase 15-01 wrappers — recordings.*
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
                    )
                ],
                bytes_total=12345678,
            ),
        ),
        ("RecordingsDelete", RecordingsDelete.make(session_dir="20260513-210410")),
        (
            "RecordingsDeleteAck",
            RecordingsDeleteAck.make(session_dir="20260513-210410", ok=True, error=None),
        ),
        ("RecordingsUsage", RecordingsUsage.make(sessions=12, bytes_total=3656838349)),
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
        # Phase 44-03 — cohost reaction broadcast (LAUNCH-02)
        (
            "SessionCohostReaction",
            SessionCohostReaction.make(
                text="sick [ev:KICK_SWAP@45.2] kick swap",
                event_id="HEARTBEAT",
                citation_strip=[
                    {
                        "event_id": "ev:KICK_SWAP@45.2",
                        "verb": "kick swap",
                        "timestamp_s": 45.2,
                    }
                ],
            ),
        ),
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
        # Phase 25/29 — DEBRIEF window messages
        (
            "DebriefSessionLoaded",
            DebriefSessionLoaded.make(
                session_id="20260513-210410",
                started_at=1715616250.0,
                duration_s=5040.0,
            ),
        ),
        # Phase 29 Plan 29-03 — DEBRIEF v2.1 additive wrappers
        (
            "DebriefChapterList",
            DebriefChapterList.make(
                chapters=(
                    ChapterRegionPayload(
                        id="track-01",
                        start=0.0,
                        end=300.0,
                        label="Track 1: Opening",
                        kind="track",
                        citation_event_id="ev:TRACK_CHANGE@00:00",
                    ),
                ),
                derived_at="2026-05-15T11:21:39.656+00:00",
            ),
        ),
        (
            "DebriefTldrAudio",
            DebriefTldrAudio.make(
                audio_relative_path="debrief_tldr.mp3",
                duration_s=75.0,
                tldr_sha256="a" * 64,
                mime_type="audio/mpeg",
            ),
        ),
        (
            "DebriefDrills",
            DebriefDrills.make(
                drills=tuple(
                    DrillPayload(
                        situation=f"Drill {i} situation",
                        behavior=f"Behavior [ev:MIX_MOVE@01:0{i}]",
                        impact=f"Impact [ev:PHASE@01:1{i}]",
                        action_recommended=f"Action [track:t{i}]",
                        citation=f"[ev:MIX_MOVE@01:0{i}]",
                    )
                    for i in range(3)
                ),
            ),
        ),
        (
            "DebriefCitationTooltipReq",
            DebriefCitationTooltipReq.make(event_id="ev:MIX_MOVE@01:23"),
        ),
        (
            "DebriefCitationTooltip",
            DebriefCitationTooltip.make(
                event_id="ev:MIX_MOVE@01:23",
                evidence_text="A_filter boost at 1:23",
                timestamp=83.0,
                found=True,
            ),
        ),
        (
            "DebriefError",
            DebriefError.make(
                reason="session_too_short",
                message="Session is 120s; need >= 300s.",
            ),
        ),
        # Phase 28 Plan 09 — Library IPC
        (
            "LibraryImport",
            LibraryImport.make(path="/tmp/lib.xml"),
        ),
        (
            "LibraryImportProgress",
            LibraryImportProgress.make(
                total=10,
                done=5,
                current_track_name="Artist — Track",
                cache_hits=3,
            ),
        ),
        ("LibraryImportCancel", LibraryImportCancel.make()),
        (
            "LibraryStalenessNudge",
            LibraryStalenessNudge.make(age_days=45, snoozed_until_ts=None),
        ),
        (
            "LibraryStalenessAction",
            LibraryStalenessAction.make(action="snooze_7d"),
        ),
        # Phase 32 — long-term DJ profile wrappers (PROFILE-04/05/07)
        ("ProfileSetConsent", ProfileSetConsent.make(consent=False)),
        ("ProfileConsentState", ProfileConsentState.make(consent=False)),
        ("ProfileView", ProfileView.make()),
        (
            "ProfileViewResult",
            ProfileViewResult.make(profile=None, bytes=0, consent=False),
        ),
        ("ProfileRegenerate", ProfileRegenerate.make()),
        (
            "ProfileRegenerateResult",
            ProfileRegenerateResult.make(ok=False, profile=None, error="consent_off"),
        ),
        ("ProfileDelete", ProfileDelete.make()),
        ("ProfileDeleteAck", ProfileDeleteAck.make(ok=True, error=None)),
        # Phase 91 RENDER-01 / RENDER-02 / RENDER-07 — Learn envelopes
        # (wrappers live in vibemix.ui_bus.learn_messages, not messages.py;
        # the introspection in _count_wrapper_dataclasses scans both modules)
        (
            "LearnControllerDetected",
            LearnControllerDetected.make(
                connected=True,
                controller_id="pioneer_ddj_flx4",
                display_name="Pioneer DDJ-FLX4",
                port_name="DDJ-FLX4 USB MIDI Input",
            ),
        ),
        (
            "LearnMidiPosition",
            LearnMidiPosition.make(
                controller_id="pioneer_ddj_flx4",
                positions={"eq_hi:A": 64, "xfader": 64},
            ),
        ),
        # Phase 92 Plan 92-01 — 11 lesson-runtime envelopes.
        (
            "LearnStartCourse",
            LearnStartCourse.make(
                course_id="course_0",
                controller_id="pioneer_ddj_flx4",
            ),
        ),
        (
            "LearnStartLesson",
            LearnStartLesson.make(
                lesson_id="L0.00-press-play",
                level="fresh",
            ),
        ),
        (
            "LearnCompleteLesson",
            LearnCompleteLesson.make(
                lesson_id="L0.00-press-play",
                reason="completed",
            ),
        ),
        (
            "LearnLessonLoaded",
            LearnLessonLoaded.make(
                course_id="course_0",
                lesson_id="L0.00-press-play",
                title="press play",
                controller_id="pioneer_ddj_flx4",
                progress_dots=(
                    LearnProgressDot(
                        lesson_id="L0.00-press-play",
                        status="current",
                    ),
                ),
            ),
        ),
        (
            "LearnHighlight",
            LearnHighlight.make(
                control_id="play",
                deck="A",
                cue_color="amber",
                cue_shape="pulse-ring",
                annotation="press play",
                expected_action={
                    "type": "button",
                    "control": "play",
                    "deck": "A",
                    "direction": "down",
                },
            ),
        ),
        (
            "LearnAdvance",
            LearnAdvance.make(
                lesson_id="L0.00-press-play",
                reason="action_matched",
            ),
        ),
        # Organism focus mechanic — teaching_focus + control_rect relay.
        (
            "LearnTeachingFocus",
            LearnTeachingFocus.make(
                control_id="eq_low",
                deck="A",
                band="low",
                phase="focus",
            ),
        ),
        (
            "LearnControlRect",
            LearnControlRect.make(
                control_id="eq_low",
                deck="A",
                cx=120.5,
                cy=240.0,
            ),
        ),
        (
            "LearnAck",
            LearnAck.make(
                control_id="play:A",
                source="midi",
                value=127,
                direction="down",
            ),
        ),
        (
            "LearnTutorSpeak",
            LearnTutorSpeak.make(
                text="find deck A play button",
                tts_marker="L000.beat0",
                citations=(),
                data_state="active",
            ),
        ),
        (
            "LearnLiveGrade",
            LearnLiveGrade.make(
                verdict="locked",
                phase_error_beats=0.0,
                score=1.0,
                citation="[ev:BEATMATCH_GRADED@12.345]",
            ),
        ),
        (
            "LearnWaveformReady",
            LearnWaveformReady.make(
                sample_rate=44_100,
                beat_interval_s=0.46875,
                decks={
                    "A": {
                        "bpm": 128.0,
                        "duration_s": 30.0,
                        "peaks": ((16, 32, 64), (24, 48, 96)),
                        "cues": (
                            {"label": "intro", "start_s": 0.0, "end_s": 8.0},
                        ),
                    },
                    "B": {
                        "bpm": 128.0,
                        "duration_s": 30.0,
                        "peaks": ((12, 36, 72), (20, 40, 88)),
                        "cues": (
                            {"label": "drop", "start_s": 8.0, "end_s": 16.0},
                        ),
                    },
                },
            ),
        ),
        (
            "LearnPlayheadTick",
            LearnPlayheadTick.make(
                sample_rate=44_100,
                decks={
                    "A": {"frame": 1024.0, "position_s": 0.023, "bpm": 128.0},
                    "B": {"frame": 2048.0, "position_s": 0.046, "bpm": 127.2},
                },
            ),
        ),
        (
            "LearnExemplarPlay",
            LearnExemplarPlay.make(
                track_id="track_0001",
                duration_s=30.0,
                gain_db=-12.0,
            ),
        ),
        (
            "LearnExemplarStop",
            LearnExemplarStop.make(
                track_id="track_0001",
                reason="completed",
            ),
        ),
        (
            "LearnProgressState",
            LearnProgressState.make(
                action="snapshot",
                progress={
                    "schema_version": 1,
                    "courses": {},
                    "lessons": {},
                },
            ),
        ),
    ]


def _is_envelope_type_field(type_field) -> bool:  # type: ignore[no-untyped-def]
    """Return True iff ``type_field`` is the envelope-discriminator field
    (``type: Literal["ipc.xxx.yyy"]``). False for nested-object types like
    ``LearnExpectedAction.type: Literal["cc", "button"]`` which use ``type``
    as a sub-domain discriminator (RESEARCH.md Pitfall 7 — heuristic collision).

    Implementation: introspect the dataclass field's annotation; the
    canonical ``ipc.*`` literal namespace is the only valid envelope
    discriminator. Anything else (``cc``/``button``, etc.) is a nested
    dataclass that happens to share the ``type`` field name.
    """
    # Phase 92 fix: type_field.type can be a string forward-ref (when
    # ``from __future__ import annotations`` is active) OR a typing object.
    # In both cases the substring ``"ipc.`` is the load-bearing marker.
    raw = getattr(type_field, "type", None)
    if raw is None:
        return False
    # Stringified form (forward-ref): the annotation source is the raw string
    # like ``Literal["ipc.learn.start_course"]`` — substring match is robust.
    if isinstance(raw, str):
        return '"ipc.' in raw or "'ipc." in raw
    # Typing-object form: stringify and check the same substring.
    return '"ipc.' in repr(raw) or "'ipc." in repr(raw)


def _count_wrapper_dataclasses() -> int:
    """Wrapper dataclasses == dataclasses with a ``type`` field whose
    annotation is ``Literal["ipc.<domain>.<verb>"]`` (the envelope-
    discriminator literal). Excludes payload-only structs (``*Payload`` /
    ``DeviceInfo`` / ``WindowInfo``) because they have no ``type`` field,
    AND excludes nested dataclasses that re-use the ``type`` field name
    for a sub-domain discriminator (e.g. ``LearnExpectedAction.type:
    Literal["cc", "button"]`` lives inside ``LearnHighlight.payload`` but
    is not itself a top-level envelope — RESEARCH.md Pitfall 7).

    Phase 91 RENDER-01 split the Learn-envelope wrappers into a sibling
    module (``learn_messages.py``) per the plan's modular-naming
    decision; introspection scans both modules and de-duplicates the
    result so a future re-export from ``messages.py`` cannot double-count.
    """
    count = 0
    seen: set[type] = set()
    for module in (ui_bus_messages, ui_bus_learn_messages):
        for name in dir(module):
            obj = getattr(module, name)
            if (
                isinstance(obj, type)
                and hasattr(obj, "__dataclass_fields__")
                and "type" in obj.__dataclass_fields__
                and _is_envelope_type_field(obj.__dataclass_fields__["type"])
                and obj not in seen
            ):
                seen.add(obj)
                count += 1
    return count


def _settings_set_schema_fields(schema: dict) -> list[str]:
    return schema["definitions"]["SettingsSet"]["properties"]["payload"]["properties"]["field"][
        "enum"
    ]


def _settings_set_python_fields() -> list[str]:
    hints = get_type_hints(ui_bus_messages.SettingsSetPayload)
    return list(get_args(hints["field"]))


def _settings_state_schema_fields(schema: dict) -> list[str]:
    return list(
        schema["definitions"]["SettingsState"]["properties"]["payload"]["properties"].keys()
    )


def _settings_state_python_fields() -> list[str]:
    hints = get_type_hints(ui_bus_messages.SettingsStatePayload)
    mapped: list[str] = []
    for field_name in hints:
        if field_name == "session_mode":
            mapped.append("session.mode")
        elif field_name == "learn_headphone_device_index":
            mapped.append("learn.headphone_device_index")
        else:
            mapped.append(field_name)
    return mapped


def _settings_bridge_fields() -> list[str]:
    text = _WS_BRIDGE_PATH.read_text(encoding="utf-8")
    match = re.search(
        r"export const SETTINGS_FIELDS = \[(?P<body>.*?)\] as const;",
        text,
        flags=re.S,
    )
    if match is None:
        raise RuntimeError(f"SETTINGS_FIELDS not found in {_WS_BRIDGE_PATH}")
    return re.findall(r'"([^"]+)"', match.group("body"))


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
        except Exception as e:
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
    print(f"OK: count parity — {oneof_count} oneOf entries == {wrapper_count} wrapper dataclasses")

    # 3) Field-enum parity for settings. The wrapper roundtrip only tests a
    # representative value, so a valid runtime setting can drift out of the
    # schema/Python/TS allowlists unless we compare the whole enum.
    settings_schema_fields = _settings_set_schema_fields(schema)
    settings_python_fields = _settings_set_python_fields()
    settings_bridge_fields = _settings_bridge_fields()
    if settings_schema_fields != settings_python_fields:
        print(
            "FAIL: SettingsSet field drift — schema enum does not match "
            "SettingsSetPayload.field Literal.",
            file=sys.stderr,
        )
        print(f"  schema: {settings_schema_fields}", file=sys.stderr)
        print(f"  python: {settings_python_fields}", file=sys.stderr)
        return 1
    if settings_schema_fields != settings_bridge_fields:
        print(
            "FAIL: SettingsSet field drift — schema enum does not match ws-bridge SETTINGS_FIELDS.",
            file=sys.stderr,
        )
        print(f"  schema: {settings_schema_fields}", file=sys.stderr)
        print(f"  bridge: {settings_bridge_fields}", file=sys.stderr)
        return 1
    print("OK: SettingsSet field enum parity")

    state_schema_fields = sorted(_settings_state_schema_fields(schema))
    state_python_fields = sorted(_settings_state_python_fields())
    if state_schema_fields != state_python_fields:
        print(
            "FAIL: SettingsState payload drift — schema properties do not match "
            "SettingsStatePayload fields.",
            file=sys.stderr,
        )
        print(f"  schema: {state_schema_fields}", file=sys.stderr)
        print(f"  python: {state_python_fields}", file=sys.stderr)
        return 1
    print("OK: SettingsState payload parity")

    # 4) Belt-and-braces — every example must also map to one of the schema's
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
