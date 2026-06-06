/* AUTO-GENERATED from messages.schema.json — do not edit. Run 'npm run codegen:ipc'. */

/**
 * Source-of-truth JSON Schema for ipc.* messages exchanged between the Tauri shell (TypeScript webview) and the Python sidecar over the existing 127.0.0.1:8765 ws_bus (Phase 4). Phase 11 Wave 0 freezes this contract before any sidecar packaging, Tauri shell, or wizard UI work begins. Drift between Python (jsonschema) and TS (ajv) is caught by scripts/check_ipc_schema.py (count parity + per-dataclass roundtrip) and tauri/ui's `npm run check:ipc` (codegen + tsc --noEmit). Honors D-Area-1.3 (schema sync) and D-Area-1.1 (ipc.* namespace on existing ws_bus port 8765). Closed payloads (additionalProperties: false) on every definition per RESEARCH Pitfall 10.
 */
export type VibemixIPCMessages =
  | IpcBoot
  | StatusTick
  | PermissionCheck
  | PermissionState
  | CalibrationListDevices
  | CalibrationDeviceList
  | CalibrationProbeAudio
  | CalibrationAudioResult
  | CalibrationUserHeardTone
  | CalibrationStartMidiListen
  | CalibrationMidiEvent
  | CalibrationMidiTimeout
  | CalibrationListWindows
  | CalibrationWindowList
  | CalibrationSmokeTest
  | CalibrationSmokeTestStarted
  | CalibrationSmokeTestDone
  | WizardStart
  | WizardDone
  | WizardSetSkill
  | SessionSnapshot
  | SessionMute
  | SessionCitation
  | SessionSetMode
  | SessionStart
  | SessionStop
  | SettingsSet
  | SettingsGet
  | SettingsState
  | SettingsSetBrain
  | SettingsBrainAck
  | StatusRecheck
  | IpcError
  | MascotMoodChange
  | RecordingsList
  | RecordingsListResult
  | RecordingsDelete
  | RecordingsDeleteAck
  | RecordingsUsage
  | RecordingsEvents
  | RecordingsEventsResult
  | SessionOverlayHighlight
  | SessionCohostReaction
  | DebriefSessionLoaded
  | DebriefChapterList
  | DebriefNearMiss
  | DebriefTldrAudio
  | DebriefDrills
  | DebriefCitationTooltipReq
  | DebriefMomentFeedback
  | DebriefCitationTooltip
  | DebriefError
  | LibraryImport
  | LibraryImportProgress
  | LibraryImportCancel
  | LibraryStalenessNudge
  | LibraryStalenessAction
  | ProfileSetConsent
  | ProfileConsentState
  | ProfileView
  | ProfileViewResult
  | ProfileRegenerate
  | ProfileRegenerateResult
  | ProfileDelete
  | ProfileDeleteAck
  | LearnControllerDetected
  | LearnMidiPosition
  | LearnStartCourse
  | LearnStartLesson
  | LearnCompleteLesson
  | LearnLessonLoaded
  | LearnHighlight
  | LearnAdvance
  | LearnTeachingFocus
  | LearnControlRect
  | LearnAck
  | LearnTutorSpeak
  | LearnLiveGrade
  | LearnWaveformReady
  | LearnPlayheadTick
  | LearnExemplarPlay
  | LearnExemplarStop
  | LearnProgressState;

export interface IpcBoot {
  type: "ipc.boot";
  ts: string;
  payload: {
    ready: boolean;
  };
}
export interface StatusTick {
  type: "ipc.status.tick";
  ts: string;
  payload: {
    livekit: "ok" | "connecting" | "down";
    gemini: "ok" | "down";
    midi: number | null;
    screen: "ok" | "denied" | "unavailable";
    voice?: "ok" | "muted" | null;
    capture_device?: string | null;
    midi_activity?:
      | "disconnected"
      | "connected_no_midi_traffic"
      | "midi_traffic_unmapped"
      | "midi_events_no_moves"
      | "active"
      | "unknown"
      | null;
    midi_device?: string | null;
  };
}
export interface PermissionCheck {
  type: "ipc.permission.check";
  ts: string;
  payload: {
    kind: "screen_recording" | "microphone";
  };
}
export interface PermissionState {
  type: "ipc.permission.state";
  ts: string;
  payload: {
    kind: "screen_recording" | "microphone";
    status: "authorized" | "denied" | "notDetermined" | "restricted";
  };
}
export interface CalibrationListDevices {
  type: "ipc.calibration.list_devices";
  ts: string;
  payload: {};
}
export interface CalibrationDeviceList {
  type: "ipc.calibration.device_list";
  ts: string;
  payload: {
    devices: {
      id: string;
      name: string;
      is_blackhole: boolean;
      variant: string | null;
    }[];
    blackhole_present: boolean;
  };
}
export interface CalibrationProbeAudio {
  type: "ipc.calibration.probe_audio";
  ts: string;
  payload: {
    output_device_id: string;
    expected_rate: 44100 | 48000;
  };
}
export interface CalibrationAudioResult {
  type: "ipc.calibration.audio_result";
  ts: string;
  payload: {
    playback_ok: boolean;
    audible_confirmed: boolean;
    programmatic_pass: boolean;
    actual_rate: number | null;
    error: string | null;
  };
}
export interface CalibrationUserHeardTone {
  type: "ipc.calibration.user_heard_tone";
  ts: string;
  payload: {
    heard: boolean;
  };
}
export interface CalibrationStartMidiListen {
  type: "ipc.calibration.start_midi_listen";
  ts: string;
  payload: {
    timeout_s: number;
  };
}
export interface CalibrationMidiEvent {
  type: "ipc.calibration.midi_event";
  ts: string;
  payload: {
    control_label: string;
    raw: string;
  };
}
export interface CalibrationMidiTimeout {
  type: "ipc.calibration.midi_timeout";
  ts: string;
  payload: {};
}
export interface CalibrationListWindows {
  type: "ipc.calibration.list_windows";
  ts: string;
  payload: {};
}
export interface CalibrationWindowList {
  type: "ipc.calibration.window_list";
  ts: string;
  payload: {
    windows: {
      id: string;
      app_name: string;
      title: string;
      dj_app_hint: string | null;
    }[];
  };
}
export interface CalibrationSmokeTest {
  type: "ipc.calibration.smoke_test";
  ts: string;
  payload: {
    template: "HYPE_BEGINNER";
  };
}
export interface CalibrationSmokeTestStarted {
  type: "ipc.calibration.smoke_test_started";
  ts: string;
  payload: {};
}
export interface CalibrationSmokeTestDone {
  type: "ipc.calibration.smoke_test_done";
  ts: string;
  payload: {
    transcript: string;
  };
}
export interface WizardStart {
  type: "ipc.wizard.start";
  ts: string;
  payload: {};
}
export interface WizardDone {
  type: "ipc.wizard.done";
  ts: string;
  payload: {
    output_device_id: string;
    controller_profile: string;
    target_window_id: string | null;
  };
}
export interface WizardSetSkill {
  type: "ipc.wizard.set_skill";
  ts: string;
  payload: {
    skill: "beginner" | "intermediate" | "pro";
  };
}
export interface SessionSnapshot {
  type: "ipc.session.snapshot";
  ts: string;
  payload: {
    meters: {
      music: LevelPair;
      voice: LevelPair;
      mic: LevelPair;
    };
    phase: {
      kind: "silent" | "groove" | "build" | "drop-ghost";
      weight: number;
      label: string;
    }[];
    phase_now_pct: number;
    bpm: number | null;
    drop_pred_bars: number | null;
    transcript_delta: {
      role: "ai" | "user" | "system";
      text: string;
      ts: string;
    }[];
    midi_events: {
      control: string;
      value: number | string | null;
      ts: string;
    }[];
    track: null | {
      title: string;
      artist?: string | null;
      deck?: string | null;
    };
    cohost_status: "LISTENING" | "TALKING" | "IDLE";
    latency_ms: number | null;
    claim_policy?: null | {
      policy: "requires_more_evidence" | "blocked" | "watch_not_claim" | "candidate_not_verdict" | "supported_verdict";
      level: "green" | "yellow" | "red";
      reason: string | null;
    };
    grounded: boolean;
  };
}
export interface LevelPair {
  rms: number;
  peak: number;
}
export interface SessionMute {
  type: "ipc.session.mute";
  ts: string;
  payload: {
    toggle?: boolean;
    muted?: boolean;
  };
}
export interface SessionCitation {
  type: "ipc.session.citation";
  ts: string;
  payload: {
    slop_ratio: number;
    stripped_rate_15s: number;
    last_unverified_response: string | null;
    bypass_active: boolean;
  };
}
export interface SessionSetMode {
  type: "ipc.session.set_mode";
  ts: string;
  payload: {
    mode: "cohost" | "learn" | "build" | "debrief";
  };
}
export interface SessionStart {
  type: "ipc.session.start";
  ts: string;
  payload: {};
}
export interface SessionStop {
  type: "ipc.session.stop";
  ts: string;
  payload: {};
}
export interface SettingsSet {
  type: "ipc.settings.set";
  ts: string;
  payload: {
    field:
      | "voice"
      | "mode"
      | "genre"
      | "output_device_id"
      | "output_profile"
      | "retention_days"
      | "push_to_mute_hotkey"
      | "mood"
      | "click_through"
      | "lighter_blur"
      | "skill"
      | "lens"
      | "learn.headphone_device_index";
    value: string | number | boolean | null;
  };
}
export interface SettingsGet {
  type: "ipc.settings.get";
  ts: string;
  payload: {};
}
export interface SettingsState {
  type: "ipc.settings.state";
  ts: string;
  payload: {
    voice: string;
    mode: "hype" | "coach";
    genre: string;
    output_device_id: string | null;
    output_profile: "hp" | "spk";
    retention_days: number;
    push_to_mute_hotkey: string;
    muted: boolean;
    lighter_blur: boolean;
    mood?: ("hype-man" | "teacher" | "coach") | null;
    click_through?: boolean | null;
    skill?: ("beginner" | "intermediate" | "pro") | null;
    lens?: ("hype" | "critique" | "tutor") | null;
    "learn.headphone_device_index"?: number | null;
    "session.mode"?: ("cohost" | "learn" | "build" | "debrief") | null;
  };
}
export interface SettingsSetBrain {
  type: "ipc.settings.set_brain";
  ts: string;
  payload: {
    mode: "direct" | "proxy";
    gemini_api_key?: string | null;
  };
}
export interface SettingsBrainAck {
  type: "ipc.settings.brain_ack";
  ts: string;
  payload: {
    ok: boolean;
    mode: "direct" | "proxy";
    key_set: boolean;
    restart_required: boolean;
    error?: string | null;
  };
}
export interface StatusRecheck {
  type: "ipc.status.recheck";
  ts: string;
  payload: {
    component: "livekit" | "gemini" | "midi" | "screen";
  };
}
export interface IpcError {
  type: "ipc.error";
  ts: string;
  payload: {
    reason: string;
    original_type?: string | null;
  };
}
export interface MascotMoodChange {
  type: "ipc.mascot.mood_change";
  ts: string;
  payload: {
    mood: "hype-man" | "teacher" | "coach";
    previous_mood?: "hype-man" | "teacher" | "coach" | null;
    at?: number | null;
  };
}
export interface RecordingsList {
  type: "ipc.recordings.list";
  ts: string;
  payload: {};
}
export interface RecordingsListResult {
  type: "ipc.recordings.list_result";
  ts: string;
  payload: {
    sessions: {
      session_dir: string;
      started_at_iso: string;
      duration_s: number;
      event_count: number;
      bytes_total: number;
      crashed: boolean;
      /**
       * True when recordings/<session_dir>/voice.wav exists as a regular file. Optional for additive compatibility; current sidecars send it so the UI can avoid mounting missing audio assets.
       */
      voice_available?: boolean;
    }[];
    bytes_total: number;
  };
}
export interface RecordingsDelete {
  type: "ipc.recordings.delete";
  ts: string;
  payload: {
    session_dir: string;
  };
}
export interface RecordingsDeleteAck {
  type: "ipc.recordings.delete_ack";
  ts: string;
  payload: {
    session_dir: string;
    ok: boolean;
    error: string | null;
  };
}
export interface RecordingsUsage {
  type: "ipc.recordings.usage";
  ts: string;
  payload: {
    sessions: number;
    bytes_total: number;
  };
}
export interface RecordingsEvents {
  type: "ipc.recordings.events";
  ts: string;
  payload: {
    session_dir: string;
  };
}
export interface RecordingsEventsResult {
  type: "ipc.recordings.events_result";
  ts: string;
  payload: {
    session_dir: string;
    events: {
      t: number;
      kind: string;
      [k: string]: unknown;
    }[];
  };
}
export interface SessionOverlayHighlight {
  type: "ipc.session.overlay-highlight";
  ts: string;
  payload: {
    element_id: string;
    color: "amber" | "red" | "green" | "blue";
    duration_ms: number;
  };
}
export interface SessionCohostReaction {
  type: "ipc.session.cohost-reaction";
  ts: string;
  payload: {
    text: string;
    event_id: string;
    /**
     * @maxItems 3
     */
    citation_strip:
      | []
      | [
          {
            event_id: string;
            verb: string;
            timestamp_s: number;
          }
        ]
      | [
          {
            event_id: string;
            verb: string;
            timestamp_s: number;
          },
          {
            event_id: string;
            verb: string;
            timestamp_s: number;
          }
        ]
      | [
          {
            event_id: string;
            verb: string;
            timestamp_s: number;
          },
          {
            event_id: string;
            verb: string;
            timestamp_s: number;
          },
          {
            event_id: string;
            verb: string;
            timestamp_s: number;
          }
        ];
  };
}
export interface DebriefSessionLoaded {
  type: "ipc.debrief.session-loaded";
  ts: string;
  payload: {
    session_id: string;
    started_at: number;
    duration_s: number;
  };
}
export interface DebriefChapterList {
  type: "ipc.debrief.chapter-list";
  ts: string;
  payload: {
    chapters: {
      id: string;
      start: number;
      end: number;
      label: string;
      kind: "track" | "phase" | "layer" | "mix" | "crowd";
      citation_event_id: string;
    }[];
    derived_at: string;
  };
}
export interface DebriefNearMiss {
  type: "ipc.debrief.near-miss";
  ts: string;
  payload: {
    input_wav_relative_path: string;
    t_center: number | null;
    window: [number, number] | null;
    receipt_text: string;
    friend_line_text: string;
    duration_s: number;
    ear_test_clip_relative_path?: string | null;
    friend_line_audio_relative_path?: string | null;
    waveform_peaks?: [[number, number, number], ...[number, number, number][]] | null;
  };
}
export interface DebriefTldrAudio {
  type: "ipc.debrief.tldr-audio";
  ts: string;
  payload: {
    audio_relative_path: string;
    duration_s: number;
    tldr_sha256: string;
    mime_type: "audio/mpeg";
  };
}
export interface DebriefDrills {
  type: "ipc.debrief.drills";
  ts: string;
  payload: {
    /**
     * @minItems 3
     * @maxItems 3
     */
    drills: [
      {
        situation: string;
        behavior: string;
        impact: string;
        action_recommended: string;
        citation: string;
        learn_referral?: {
          lesson_id: string;
          course_id: string;
          course_label: string;
          skill_id: string;
          skill_label: string;
          title: string;
          reason: string;
          cta: string;
        } | null;
      },
      {
        situation: string;
        behavior: string;
        impact: string;
        action_recommended: string;
        citation: string;
        learn_referral?: {
          lesson_id: string;
          course_id: string;
          course_label: string;
          skill_id: string;
          skill_label: string;
          title: string;
          reason: string;
          cta: string;
        } | null;
      },
      {
        situation: string;
        behavior: string;
        impact: string;
        action_recommended: string;
        citation: string;
        learn_referral?: {
          lesson_id: string;
          course_id: string;
          course_label: string;
          skill_id: string;
          skill_label: string;
          title: string;
          reason: string;
          cta: string;
        } | null;
      }
    ];
  };
}
export interface DebriefCitationTooltipReq {
  type: "ipc.debrief.citation-tooltip-request";
  ts: string;
  payload: {
    event_id: string;
  };
}
export interface DebriefMomentFeedback {
  type: "ipc.debrief.moment-feedback";
  ts: string;
  payload: {
    moment_id: string;
    citation_id: string;
    verdict: "agree" | "disagree" | "unclear";
    surface: "transition" | "live_pill" | "cue";
  };
}
export interface DebriefCitationTooltip {
  type: "ipc.debrief.citation-tooltip";
  ts: string;
  payload: {
    event_id: string;
    evidence_text: string;
    timestamp: number;
    found: boolean;
  };
}
export interface DebriefError {
  type: "ipc.debrief.error";
  ts: string;
  payload: {
    reason:
      | "events_missing"
      | "session_too_short"
      | "invalid_session_dir"
      | "sidecar_crashed"
      | "tldr_generation_failed"
      | "drills_generation_failed"
      | "port_in_use"
      | "unknown_kind";
    message: string;
  };
}
export interface LibraryImport {
  type: "ipc.library.import";
  ts: string;
  payload: {
    path: string;
    schema_version: "1";
  };
}
export interface LibraryImportProgress {
  type: "ipc.library.import_progress";
  ts: string;
  payload: {
    total: number;
    done: number;
    current_track_name: string;
    cache_hits: number;
    cancelled: boolean;
    schema_version: "1";
  };
}
export interface LibraryImportCancel {
  type: "ipc.library.import_cancel";
  ts: string;
  payload: {
    schema_version: "1";
  };
}
export interface LibraryStalenessNudge {
  type: "ipc.library.staleness_nudge";
  ts: string;
  payload: {
    age_days: number;
    snoozed_until_ts: number | null;
    source_path?: string | null;
    source_kind?: "xml" | "folder" | null;
    reason?: string | null;
    schema_version: "1";
  };
}
export interface LibraryStalenessAction {
  type: "ipc.library.staleness_action";
  ts: string;
  payload: {
    action: "dismiss" | "snooze_7d" | "reindex_folder";
    schema_version: "1";
  };
}
export interface ProfileSetConsent {
  type: "ipc.profile.set_consent";
  ts: string;
  payload: {
    consent: boolean;
  };
}
export interface ProfileConsentState {
  type: "ipc.profile.consent_state";
  ts: string;
  payload: {
    consent: boolean;
  };
}
export interface ProfileView {
  type: "ipc.profile.view";
  ts: string;
  payload: {};
}
export interface ProfileViewResult {
  type: "ipc.profile.view_result";
  ts: string;
  payload: {
    profile: {} | null;
    bytes: number;
    consent: boolean;
  };
}
export interface ProfileRegenerate {
  type: "ipc.profile.regenerate";
  ts: string;
  payload: {};
}
export interface ProfileRegenerateResult {
  type: "ipc.profile.regenerate_result";
  ts: string;
  payload: {
    ok: boolean;
    profile: {} | null;
    error: string | null;
  };
}
export interface ProfileDelete {
  type: "ipc.profile.delete";
  ts: string;
  payload: {};
}
export interface ProfileDeleteAck {
  type: "ipc.profile.delete_ack";
  ts: string;
  payload: {
    ok: boolean;
    error: string | null;
  };
}
export interface LearnControllerDetected {
  type: "ipc.learn.controller_detected";
  ts: string;
  payload: {
    connected: boolean;
    controller_id: string;
    display_name: string;
    port_name: string;
  };
}
export interface LearnMidiPosition {
  type: "ipc.learn.midi_position";
  ts: string;
  payload: {
    controller_id: string;
    positions: {
      [k: string]: number;
    };
  };
}
export interface LearnStartCourse {
  type: "ipc.learn.start_course";
  ts: string;
  payload: {
    course_id: "course_0" | "course_1" | "course_2" | "course_3";
    controller_id: string;
  };
}
export interface LearnStartLesson {
  type: "ipc.learn.start_lesson";
  ts: string;
  payload: {
    lesson_id: string;
    level: "fresh" | "replay";
  };
}
export interface LearnCompleteLesson {
  type: "ipc.learn.complete_lesson";
  ts: string;
  payload: {
    lesson_id: string;
    reason: "completed" | "user_skip";
  };
}
export interface LearnLessonLoaded {
  type: "ipc.learn.lesson_loaded";
  ts: string;
  payload: {
    course_id: string;
    lesson_id: string;
    title: string;
    controller_id: string;
    /**
     * @maxItems 32
     */
    progress_dots: {
      lesson_id: string;
      status: "pending" | "current" | "completed";
    }[];
  };
}
export interface LearnHighlight {
  type: "ipc.learn.highlight";
  ts: string;
  payload: {
    control_id: string;
    deck: "" | "A" | "B" | "C" | "D";
    cue_color: "amber" | "warning";
    cue_shape: "pulse-ring" | "static-glow";
    annotation: string;
    expected_action: {
      type: "cc" | "button";
      control: string;
      deck?: "" | "A" | "B" | "C" | "D";
      direction?: "" | "up" | "down";
      min_delta?: number;
    };
  };
}
export interface LearnAdvance {
  type: "ipc.learn.advance";
  ts: string;
  payload: {
    lesson_id: string;
    reason: "action_matched" | "user_skip";
  };
}
export interface LearnTeachingFocus {
  type: "ipc.learn.teaching_focus";
  ts: string;
  payload: {
    control_id: string;
    deck: "" | "A" | "B" | "C" | "D";
    band: "low" | "mid" | "hi" | null;
    phase: "focus" | "reform";
  };
}
export interface LearnControlRect {
  type: "ipc.learn.control_rect";
  ts: string;
  payload: {
    control_id: string;
    deck: "" | "A" | "B" | "C" | "D";
    cx: number;
    cy: number;
  };
}
export interface LearnAck {
  type: "ipc.learn.ack";
  ts: string;
  payload: {
    control_id: string;
    source: "midi" | "click";
    value?: number;
    prev_value?: number;
    direction?: "" | "up" | "down";
  };
}
export interface LearnTutorSpeak {
  type: "ipc.learn.tutor_speak";
  ts: string;
  payload: {
    text: string;
    tts_marker: string;
    /**
     * @maxItems 4
     */
    citations: [] | [string] | [string, string] | [string, string, string] | [string, string, string, string];
    data_state: "active" | "hint";
    teaching_loop?: LearnTeachingLoop;
  };
}
export interface LearnTeachingLoop {
  /**
   * @minItems 5
   * @maxItems 5
   */
  stages: [
    "observe" | "decide" | "teach" | "verify" | "adapt",
    "observe" | "decide" | "teach" | "verify" | "adapt",
    "observe" | "decide" | "teach" | "verify" | "adapt",
    "observe" | "decide" | "teach" | "verify" | "adapt",
    "observe" | "decide" | "teach" | "verify" | "adapt"
  ];
  turn_kind: "teach" | "hint" | "adapt";
  route_path: string;
  observation: {
    lesson_id: string;
    step_id: string;
    kind: string;
    control_id: string;
    /**
     * @minItems 1
     * @maxItems 2
     */
    input_surfaces: ["hardware" | "screen"] | ["hardware" | "screen", "hardware" | "screen"];
    /**
     * @maxItems 12
     */
    backstage_lenses:
      | []
      | [string]
      | [string, string]
      | [string, string, string]
      | [string, string, string, string]
      | [string, string, string, string, string]
      | [string, string, string, string, string, string]
      | [string, string, string, string, string, string, string]
      | [string, string, string, string, string, string, string, string]
      | [string, string, string, string, string, string, string, string, string]
      | [string, string, string, string, string, string, string, string, string, string]
      | [string, string, string, string, string, string, string, string, string, string, string]
      | [string, string, string, string, string, string, string, string, string, string, string, string];
    strikes_used: number;
  };
  verification: {
    kind: "button_press" | "cc_delta";
    control: string;
    deck: string;
    /**
     * @minItems 1
     * @maxItems 4
     */
    observable_control_ids: [string] | [string, string] | [string, string, string] | [string, string, string, string];
    /**
     * @minItems 1
     * @maxItems 2
     */
    input_surfaces: ["hardware" | "screen"] | ["hardware" | "screen", "hardware" | "screen"];
    direction: "" | "up" | "down";
    min_delta: number;
  };
}
export interface LearnLiveGrade {
  type: "ipc.learn.live_grade";
  ts: string;
  payload: {
    verdict: "locked" | "drifting" | "tempo_off" | "trainwreck" | "abstain";
    phase_error_beats: number;
    score: number;
    citation: string | null;
    save_landed?: boolean;
    save_from_verdict?: ("drifting" | "trainwreck") | null;
    save_from_phase_error_beats?: number | null;
    save_recovery_delta_beats?: number | null;
    save_attempt_active?: boolean;
    save_floor_seconds_total?: number | null;
    save_floor_seconds_remaining?: number | null;
    save_floor_expired?: boolean;
    save_difficulty_level?: number;
    save_streak?: number;
    practice_source?: ("bundled_demo" | "library_save_mode") | null;
    deck_a_track_id?: string | null;
    deck_b_track_id?: string | null;
    deck_a_title?: string | null;
    deck_b_title?: string | null;
  };
}
export interface LearnWaveformReady {
  type: "ipc.learn.waveform_ready";
  ts: string;
  payload: {
    sample_rate: number;
    beat_interval_s: number;
    decks: {
      [k: string]: LearnWaveformDeck;
    };
  };
}
export interface LearnWaveformDeck {
  bpm: number;
  duration_s: number;
  /**
   * @minItems 1
   * @maxItems 4096
   */
  peaks: [[number, number, number], ...[number, number, number][]];
  /**
   * @maxItems 16
   */
  cues:
    | []
    | [
        {
          label: string;
          start_s: number;
          end_s: number;
        }
      ]
    | [
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        }
      ]
    | [
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        }
      ]
    | [
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        }
      ]
    | [
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        }
      ]
    | [
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        }
      ]
    | [
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        }
      ]
    | [
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        }
      ]
    | [
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        }
      ]
    | [
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        }
      ]
    | [
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        }
      ]
    | [
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        }
      ]
    | [
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        }
      ]
    | [
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        }
      ]
    | [
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        }
      ]
    | [
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        },
        {
          label: string;
          start_s: number;
          end_s: number;
        }
      ];
  track_id?: string | null;
  title?: string | null;
  artist?: string | null;
  source?: ("bundled_demo" | "library_save_mode") | null;
  source_start_s?: number | null;
  source_reason?: string | null;
}
export interface LearnPlayheadTick {
  type: "ipc.learn.playhead_tick";
  ts: string;
  payload: {
    sample_rate: number;
    decks: {
      [k: string]: {
        frame: number;
        position_s: number;
        bpm: number;
      };
    };
  };
}
export interface LearnExemplarPlay {
  type: "ipc.learn.exemplar_play";
  ts: string;
  payload: {
    track_id: string;
    duration_s: number;
    gain_db: number;
    source?: "library" | "packaged" | null;
    reason?: string | null;
  };
}
export interface LearnExemplarStop {
  type: "ipc.learn.exemplar_stop";
  ts: string;
  payload: {
    track_id: string;
    reason: "completed" | "interrupted";
  };
}
export interface LearnProgressState {
  type: "ipc.learn.progress_state";
  ts: string;
  payload: {
    action: "snapshot" | "reset" | "reset_ack";
    was_recovered?: boolean;
    progress?: {
      schema_version: number;
      courses: {
        [k: string]: {
          completed?: boolean;
          completed_at?: string | null;
        };
      };
      lessons: {
        [k: string]: {
          completed?: boolean;
          completed_at?: string | null;
          strikes_used?: number;
          demonstrated?: boolean;
          practice_sources?: {
            hardware?: number;
            screen?: number;
          };
          last_practice_source?: "hardware" | "screen" | null;
          last_practice_seq?: number;
          practice_feedback?: {
            kind: "beatmatch" | "cue_placement" | "control";
            label: string;
            message: string;
            detail?: string;
          };
          last_feedback_seq?: number;
        };
      };
      course_2_unlocked?: boolean;
      course_3_unlocked?: boolean;
      skills?: {
        [k: string]: {
          live_proof_count: number;
          mastered: boolean;
          first_mastered_at: string | null;
        };
      };
      skill_wall?: {
        skill_id: string;
        stage: "locked" | "competent" | "mastered";
        learn_fill: number;
        competent: boolean;
        live_proof_count: number;
        mastered: boolean;
        first_mastered_at: string | null;
        what_remains: string;
      }[];
      next_practice_mission?: {
        lesson_id: string;
        course_id: string;
        course_label: string;
        skill_id: string;
        skill_label: string;
        title: string;
        mode: "start" | "finish" | "replay" | "prove" | "mastered";
        command: string;
        payoff: string;
        proof: string;
        why: string;
        estimated_minutes: number;
        focus: "first_rep" | "retry" | "proof" | "replay" | "hardware" | "lock" | "mastery" | "recovery";
        focus_label: string;
        challenge: string;
        practice_surface: "screen_deck" | "controller" | "live_proof";
        /**
         * @minItems 1
         * @maxItems 3
         */
        chain?:
          | [
              {
                lesson_id: string;
                course_id: string;
                course_label: string;
                title: string;
                state: "now" | "next" | "locked";
                mode: "start" | "finish" | "replay" | "prove" | "mastered";
                label: string;
              }
            ]
          | [
              {
                lesson_id: string;
                course_id: string;
                course_label: string;
                title: string;
                state: "now" | "next" | "locked";
                mode: "start" | "finish" | "replay" | "prove" | "mastered";
                label: string;
              },
              {
                lesson_id: string;
                course_id: string;
                course_label: string;
                title: string;
                state: "now" | "next" | "locked";
                mode: "start" | "finish" | "replay" | "prove" | "mastered";
                label: string;
              }
            ]
          | [
              {
                lesson_id: string;
                course_id: string;
                course_label: string;
                title: string;
                state: "now" | "next" | "locked";
                mode: "start" | "finish" | "replay" | "prove" | "mastered";
                label: string;
              },
              {
                lesson_id: string;
                course_id: string;
                course_label: string;
                title: string;
                state: "now" | "next" | "locked";
                mode: "start" | "finish" | "replay" | "prove" | "mastered";
                label: string;
              },
              {
                lesson_id: string;
                course_id: string;
                course_label: string;
                title: string;
                state: "now" | "next" | "locked";
                mode: "start" | "finish" | "replay" | "prove" | "mastered";
                label: string;
              }
            ];
        meter_label: string;
        meter_value: number;
        meter_max: number;
        meter_state: "armed" | "retry" | "proof" | "mastered" | "replay";
        meter_caption: string;
        momentum_label: string;
        momentum_value: number;
        momentum_max: number;
        momentum_caption: string;
      };
    };
  };
}
