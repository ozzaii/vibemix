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
    # Phase 92 LESSON-01..LESSON-06 / TONE-02 / TONE-04 / RENDER-04 — Learn
    # lesson-runtime envelopes + AI highlight contract.
    LearnAck,
    LearnAdvance,
    LearnCompleteLesson,
    # Phase 91 RENDER-01 / RENDER-02 / RENDER-07 — Learn module envelopes.
    LearnControllerDetected,
    LearnExemplarPlay,
    LearnExemplarStop,
    LearnHighlight,
    LearnLessonLoaded,
    LearnMidiPosition,
    LearnProgressDot,
    LearnProgressState,
    LearnStartCourse,
    LearnStartLesson,
    LearnTeachingLoopPayload,
    LearnTeachingObservationPayload,
    LearnTeachingVerificationPayload,
    LearnTutorSpeak,
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
    # Phase 32 — long-term DJ profile wrappers (PROFILE-04/05/07).
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
        # Phase 25/29 — DEBRIEF window messages
        (
            "DebriefSessionLoaded",
            DebriefSessionLoaded.make(
                session_id="20260513-210410",
                started_at=1715616250.0,
                duration_s=5040.0,
            ),
        ),
        # Phase 29 Plan 29-03 — DEBRIEF v2.1 additive wrappers.
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
        # Phase 28 Plan 28-09 — 10 library.* messages.
        (
            "LibraryImport",
            LibraryImport.make(path="/Users/dj/library.xml"),
        ),
        (
            "LibraryImportProgress",
            LibraryImportProgress.make(
                total=120,
                done=45,
                current_track_name="Title — Artist",
                cache_hits=12,
                cancelled=False,
            ),
        ),
        (
            "LibraryImportCancel",
            LibraryImportCancel.make(),
        ),
        (
            "LibraryStalenessNudge",
            LibraryStalenessNudge.make(age_days=37, snoozed_until_ts=None),
        ),
        (
            "LibraryStalenessAction",
            LibraryStalenessAction.make(action="snooze_7d"),
        ),
        # Phase 32 / PROFILE-04..07 — long-term DJ profile IPC (8 wrappers).
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
            ProfileRegenerateResult.make(
                ok=False, profile=None, error="consent_off"
            ),
        ),
        ("ProfileDelete", ProfileDelete.make()),
        ("ProfileDeleteAck", ProfileDeleteAck.make(ok=True, error=None)),
        # Phase 91 Plan 01 — Learn module envelopes (RENDER-01/02/07).
        # Wrappers live in ``vibemix.ui_bus.learn_messages``, re-exported
        # via the package __init__.py to keep the import path uniform.
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


_EXAMPLES = _make_examples()


def test_example_count_matches_schema_oneof() -> None:
    """Sentinel: our roundtrip-example list must cover every schema oneOf entry.

    Phase 11 Wave 0 froze 19; Phase 12 added 7 (SessionSnapshot, SessionMute,
    SettingsSet, SettingsGet, SettingsState, StatusRecheck, IpcError) for
    total 26. Phase 13-05 added 1 (MascotMoodChange) → 27. Phase 15-01 adds
    7 (RecordingsList, RecordingsListResult, RecordingsDelete,
    RecordingsDeleteAck, RecordingsUsage, RecordingsEvents,
    RecordingsEventsResult) → 34. Phase 20-04 adds 1 (SessionCitation) → 35.
    Phase 24-02 adds 1 (SessionOverlayHighlight) → 36. Phase 25/29 keeps 1
    DEBRIEF session wrapper (DebriefSessionLoaded) → 37. Phase 28 Plan 28-09
    adds 5 library import and staleness bus schemas (search/similar use Tauri
    commands) → 42. Phase 29
    Plan 29-03 adds 6 DEBRIEF v2.1 additive wrappers (DebriefChapterList,
    DebriefTldrAudio, DebriefDrills, DebriefCitationTooltipReq,
    DebriefCitationTooltip, DebriefError) → 48.
    Phase 32 Plans 32-04..05 add 8 profile.* schemas (ProfileSetConsent,
    ProfileConsentState, ProfileView, ProfileViewResult, ProfileRegenerate,
    ProfileRegenerateResult, ProfileDelete, ProfileDeleteAck) → 56.
    Phase 44 Plan 44-03 adds 1 (SessionCohostReaction — LAUNCH-02 anti-slop
    citation strip broadcast) → 57. Phase 91 Plan 01 adds 2 (learn.*
    envelopes — LearnControllerDetected + LearnMidiPosition) → 59.
    Phase 92 Plan 92-01 adds 11 (learn.* lesson-runtime envelopes —
    LearnStartCourse / LearnStartLesson / LearnCompleteLesson /
    LearnLessonLoaded / LearnHighlight / LearnAdvance / LearnAck /
    LearnTutorSpeak / LearnExemplarPlay / LearnExemplarStop /
    LearnProgressState) → 70. Phase 97 adds SessionSetMode → 71.
    Quick 260529-ifq adds WizardSetSkill (onboarding skill-level step) → 72.
    """
    assert len(_EXAMPLES) == len(_SCHEMA["oneOf"]) == 72


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


def test_tutor_speak_accepts_optional_teaching_loop_metadata() -> None:
    message = LearnTutorSpeak.make(
        text="press play.",
        tts_marker="L101.beat0",
        citations=(),
        data_state="active",
        teaching_loop=LearnTeachingLoopPayload(
            stages=("observe", "decide", "teach", "verify", "adapt"),
            turn_kind="teach",
            route_path="learn_tutor",
            observation=LearnTeachingObservationPayload(
                lesson_id="L1.01",
                step_id="L1.01.beat.0",
                kind="practice",
                control_id="lesson_continue",
                input_surfaces=("screen",),
                backstage_lenses=("evidence_registry",),
                strikes_used=0,
            ),
            verification=LearnTeachingVerificationPayload(
                kind="button_press",
                control="lesson_continue",
                deck="",
                observable_control_ids=("lesson_continue",),
                input_surfaces=("screen",),
                direction="down",
                min_delta=0,
            ),
        ),
    )

    parsed = json.loads(message.to_json())
    jsonschema.validate(parsed, _SCHEMA)
    assert parsed["payload"]["teaching_loop"]["turn_kind"] == "teach"


def test_tutor_speak_omits_teaching_loop_when_absent() -> None:
    parsed = json.loads(
        LearnTutorSpeak.make(
            text="press play.",
            tts_marker="L101.beat0",
            citations=(),
            data_state="active",
        ).to_json()
    )

    assert "teaching_loop" not in parsed["payload"]


def test_schema_self_validates_against_draft7() -> None:
    """Sanity: the schema file itself is conformant Draft-07."""
    jsonschema.Draft7Validator.check_schema(_SCHEMA)


def test_schema_oneof_count_is_72() -> None:
    """Plan-locked invariant — Phase 11 Wave 0 froze 19; Phase 12 added 7
    (19 → 26); Phase 13-05 added 1 (MascotMoodChange) → 27; Phase 15-01 adds
    7 recordings.* families → 34; Phase 20-04 adds 1 (SessionCitation) → 35;
    Phase 24-02 adds 1 (SessionOverlayHighlight) → 36; Phase 25/29 keeps 1
    DEBRIEF session wrapper → 37; Phase 28 Plan 28-09 adds 5 library
    import/staleness messages → 42; Phase 29 Plan 29-03 adds
    6 DEBRIEF v2.1 wrappers → 48; Phase 32 Plans 32-04..05 add
    8 profile.*
    messages (set_consent/consent_state/view/view_result/regenerate/
    regenerate_result/delete/delete_ack) → 56. Phase 44 Plan 44-03 adds 1
    (SessionCohostReaction — LAUNCH-02 anti-slop citation strip
    broadcast) → 57. Phase 91 Plan 01 adds 2 (learn.* envelopes —
    LearnControllerDetected + LearnMidiPosition) → 59. Phase 92 Plan 92-01
    adds 11 (learn.* lesson-runtime envelopes — LearnStartCourse /
    LearnStartLesson / LearnCompleteLesson / LearnLessonLoaded /
    LearnHighlight / LearnAdvance / LearnAck / LearnTutorSpeak /
    LearnExemplarPlay / LearnExemplarStop / LearnProgressState) → 70.
    Phase 97 adds SessionSetMode → 71. Quick 260529-ifq adds WizardSetSkill
    (onboarding skill-level step) → 72.

    ``definitions`` count grows alongside oneOf since every new wrapper
    adds one entry to both. ``LevelPair`` is a shared helper ref'd from
    ``SessionSnapshot.meters`` but is not itself a top-level ipc.* message
    (so it counts in ``definitions`` but not in ``oneOf``); the skew
    between the two counts is 2 after adding the payload-only
    ``LearnTeachingLoop`` helper for ``LearnTutorSpeak`` metadata
    (``WizardSetSkill``'s payload is inlined, not a separate definition,
    so it adds 1 to both counts and the skew stays 2).
    """
    assert len(_SCHEMA["oneOf"]) == 72
    assert len(_SCHEMA["definitions"]) == 74


def test_no_pydantic_imports_in_ui_bus() -> None:
    """Phase 6 + D-Area-4.4 convention: ``src/vibemix/ui_bus/`` is pydantic-free."""
    pkg = _REPO_ROOT / "src" / "vibemix" / "ui_bus"
    pattern = re.compile(r"^\s*(?:from|import)\s+pydantic\b", re.MULTILINE)
    offenders = []
    for py in pkg.rglob("*.py"):
        if pattern.search(py.read_text()):
            offenders.append(str(py.relative_to(_REPO_ROOT)))
    assert not offenders, f"pydantic import found in ui_bus: {offenders}"
