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
  | SessionSnapshot
  | SessionMute
  | SessionCitation
  | SettingsSet
  | SettingsGet
  | SettingsState
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
  | DebriefSessionLoaded
  | DebriefCitationSummary
  | DebriefEventTimeline
  | LibraryImport
  | LibraryImportProgress
  | LibraryImportCancel
  | LibrarySearchRequest
  | LibrarySearchResult
  | LibraryConfidence
  | LibraryStalenessNudge
  | LibraryStalenessAction
  | LibrarySimilarRequest
  | LibrarySimilarResult;

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
    screen: "ok" | "denied";
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
      | "lighter_blur";
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
export interface DebriefSessionLoaded {
  type: "ipc.debrief.session-loaded";
  ts: string;
  payload: {
    session_id: string;
    started_at: number;
    duration_s: number;
  };
}
export interface DebriefCitationSummary {
  type: "ipc.debrief.citation-summary";
  ts: string;
  payload: {
    total: number;
    valid: number;
    stripped: number;
    bypassed: number;
  };
}
export interface DebriefEventTimeline {
  type: "ipc.debrief.event-timeline";
  ts: string;
  payload: {
    events: {
      t: number;
      kind: string;
      [k: string]: unknown;
    }[];
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
export interface LibrarySearchRequest {
  type: "ipc.library.search";
  ts: string;
  payload: {
    query: string;
    k: number;
    schema_version: "1";
  };
}
export interface LibrarySearchResult {
  type: "ipc.library.search_result";
  ts: string;
  payload: {
    query: string;
    matches: {
      track_id: string;
      title: string;
      artist: string;
      bpm: number | null;
      confidence: number;
      snippet: string;
    }[];
    cache_hit: boolean;
    schema_version: "1";
  };
}
export interface LibraryConfidence {
  type: "ipc.library.confidence";
  ts: string;
  payload: {
    track_id: string | null;
    cosine: number;
    decision: "cited" | "uncertain" | "below_threshold";
    event_id: string;
    cost_warning: boolean;
    schema_version: "1";
  };
}
export interface LibraryStalenessNudge {
  type: "ipc.library.staleness_nudge";
  ts: string;
  payload: {
    age_days: number;
    snoozed_until_ts: number | null;
    schema_version: "1";
  };
}
export interface LibraryStalenessAction {
  type: "ipc.library.staleness_action";
  ts: string;
  payload: {
    action: "dismiss" | "snooze_7d";
    schema_version: "1";
  };
}
export interface LibrarySimilarRequest {
  type: "ipc.library.similar_request";
  ts: string;
  payload: {
    track_id: string;
    k: number;
    schema_version: "1";
  };
}
export interface LibrarySimilarResult {
  type: "ipc.library.similar_result";
  ts: string;
  payload: {
    track_id: string;
    results: {
      track_id: string;
      similarity: number;
      title: string;
      artist: string;
      bpm: number | null;
    }[];
    schema_version: "1";
  };
}
