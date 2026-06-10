/* Phase 12 Wave 3 — IPC ↔ SessionState bridge (Plan 12-04 §Steps 2).
 *
 * Subscribes to every ipc.* message the live-session UI needs and writes
 * the parsed payload into the SessionState singleton. Owns the only
 * write path; the rAF loop is read-only.
 *
 * Subscriptions:
 *   - ipc.session.snapshot (30Hz) — meters, phase, bpm, drop bars,
 *     transcript delta (append + cap 200), midi events (append + cap 12),
 *     track, cohost_status, latency, grounded.
 *   - ipc.status.tick (1Hz) — livekit/gemini/midi/screen badges.
 *   - ipc.settings.state — settings snapshot + muted flag.
 *   - ipc.session.mute — sidecar ack of a mute toggle (sidecar replies
 *     with {muted: bool}). Writes state.muted so the UI updates.
 *
 * Outbound helpers:
 *   - sendSettings(field, value) — fire-and-forget ipc.settings.set;
 *     the sidecar replies with ipc.settings.state which we already
 *     subscribe to, so the UI reflects the change on the round-trip.
 *   - sendMute(toggle) — optimistic ipc.session.mute; the sidecar replies
 *     with the same type carrying {muted: bool} which we already subscribe to.
 *
 * On boot the bridge fires a single ipc.settings.get so a freshly-mounted
 * session has the full settings tree before the user opens the drawer.
 * The sidecar's run_session also emits a settings.state on its own boot,
 * so the get/reply pair is belt-and-suspenders.
 *
 * Plan §Notes — transcript scroll behaviour belongs in render-loop.ts;
 * the bridge does NOT touch the DOM.
 */

import { vmxLog } from "../debug-log.js";
import { emitIpc, subscribeIpc } from "../ipc/client.js";
import type {
  IpcError,
  RecordingsUsage,
  SessionCitation,
  SessionCohostReaction,
  SessionSnapshot,
  SessionMute,
  SettingsState,
  StatusTick,
} from "../ipc/messages.js";
import { setRecordingsSlice } from "../settings/state.js";
import { setCitationDiagnosticsSnapshot } from "../settings/components/citation-diagnostics.js";
import {
  appendMidiEvents,
  appendReaction,
  appendTranscript,
  getSessionState,
  setSessionState,
} from "./state.js";
import type {
  ClaimPolicyLevel,
  ClaimPolicyState,
  LevelPair,
  MascotMood,
  MetersTriple,
  SessionMode,
  SessionState,
  SharedLens,
  SkillLevel,
} from "./state.js";
import type { PhaseChunk } from "./components/phase-tape.js";
import type { MidiEvent } from "./components/event-ribbon.js";
import type { CitationChip } from "./components/citation-strip.js";

function isTauriRuntimeUnavailable(err: unknown): boolean {
  return err instanceof Error && err.message === "Tauri runtime unavailable";
}

/** Wire payload shape mirrors src/ipc/messages.ts SessionSnapshot. We
 *  re-declare narrow shapes here so the bridge can be unit-tested against
 *  fake messages without round-tripping through the validator. */
interface WireSnapshotPayload {
  meters: {
    music: LevelPair;
    voice: LevelPair;
    mic: LevelPair;
  };
  phase: Array<{
    kind: "silent" | "groove" | "build" | "drop-ghost";
    weight: number;
    label: string;
  }>;
  phase_now_pct: number;
  bpm: number | null;
  drop_pred_bars: number | null;
  transcript_delta: Array<{
    role: "ai" | "user" | "system";
    text: string;
    ts: string;
  }>;
  midi_events: Array<{
    control: string;
    value: number | string | null;
    ts: string;
  }>;
  track: null | {
    title: string;
    artist?: string | null;
    deck?: string | null;
  };
  cohost_status: "LISTENING" | "TALKING" | "IDLE";
  latency_ms: number | null;
  grounded: boolean;
  claim_policy?: {
    policy: string;
    level: ClaimPolicyLevel;
    reason: string | null;
  } | null;
  run_state?: "armed" | "running" | null;
}

interface WireStatusTickPayload {
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
}

interface WireIpcErrorPayload {
  reason: string;
  original_type: string | null;
}

interface WireSessionCitationPayload {
  slop_ratio: number;
  stripped_rate_15s: number;
  last_unverified_response: string | null;
  bypass_active: boolean;
}

interface WireSettingsStatePayload {
  voice: string;
  mode: "hype" | "coach";
  genre: string;
  output_device_id: string | null;
  output_profile: "hp" | "spk";
  retention_days: number;
  push_to_mute_hotkey: string;
  muted: boolean;
  // --- 2026-05-25 (persona-level) — the sidecar emits this once skill is
  //     persisted in ConfigStore.extra; absent on pre-skill disk state, so
  //     we narrow defensively and keep the current value when it's missing.
  skill?: SkillLevel | string;
  lens?: SharedLens | string | null;
  "learn.headphone_device_index"?: number | null;
  // --- Phase 13 (mascot overlay) additions — sidecar wires these in Plan
  //     13-05; until then they arrive as undefined and we keep the
  //     SessionState defaults. Narrowed defensively in applySettingsState
  //     so a stray string from a future-out-of-sync sidecar can't poison
  //     the union (T-13-03-01 mitigation).
  mood?: MascotMood | string;
  click_through?: boolean;
  // --- Phase 14-04 (perf-blur) addition — boot snapshot includes this
  //     once SettingsApplier persists it through ConfigStore. Until first
  //     write the field is absent; ws-bridge keeps the SessionState
  //     default (false → full v5 visual contract).
  lighter_blur?: boolean;
  // --- Phase 97 (ONBOARD-01) — top-level app mode. The sidecar persists
  //     this under ConfigStore.extra["session.mode"] and echoes it on
  //     settings.state so cold boot lights the last-picked segment.
  "session.mode"?: SessionMode | string | null;
}

interface WireMutePayload {
  toggle?: boolean;
  muted?: boolean;
}

// Phase 15 Plan 05 — recordings.usage push. Sidecar broadcasts on every
// sweep (startup / retention-change / session-close / delete) so the disk
// usage line reflects the live folder state without a list re-fetch.
interface WireRecordingsUsagePayload {
  sessions: number;
  bytes_total: number;
}

// Phase 44-03 / LAUNCH-02 — cohost-reaction push. Sidecar broadcasts once
// per AI reaction the user actually heard, carrying the structured
// citation_strip derived from the EvidenceRegistry. Mirror of the
// Python SessionCohostReactionPayload — kept as a local narrow shape so
// the bridge can be unit-tested without round-tripping through ajv.
interface WireCohostReactionPayload {
  text: string;
  event_id: string;
  citation_strip: Array<{
    event_id: string;
    verb: string;
    timestamp_s: number;
  }>;
}

// WR-04 in 14-REVIEW.md — keep this allowlist in sync with the
// SettingsSet schema enum and the Python SettingsSetPayload.field Literal.
// Some older controls still bypass sendSettings via direct emitIpc; this
// list is the guard for every drawer-side caller that uses the helper.
export const SETTINGS_FIELDS = [
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
  "skill",
  "lens",
  "learn.headphone_device_index",
] as const;
export type SettingsField = (typeof SETTINGS_FIELDS)[number];

// SHIP-WIRE START-gate — run-state reconciliation hold. Start/Stop clicks
// repaint optimistically; snapshots already in flight may still carry the
// pre-click run_state, so the click arms a short hold during which the
// optimistic value wins. Outside the hold the wire is authoritative — a
// restarted sidecar (fresh boot = armed) can never strand a "running" deck.
export const RUN_STATE_HOLD_MS = 2500;
let runStateHoldUntilMs = 0;

/** Called by the render-loop's Start/Stop handlers at click time. */
export function holdRunStateReconciliation(ms: number = RUN_STATE_HOLD_MS): void {
  runStateHoldUntilMs = Date.now() + ms;
}

let initialized = false;

/** Idempotent boot. Returns the unsubscribe fns the caller can wire to
 *  teardown — typically the session router on route exit, though in
 *  practice the bridge runs for the life of the webview. */
export async function initSessionBridge(): Promise<{
  unsubscribeAll: () => void;
}> {
  if (initialized) {
    // Bridge is singleton — calling twice would double-subscribe and
    // double-write SessionState on every snapshot. The router only
    // mounts the session once per webview lifetime in practice.
    return { unsubscribeAll: () => {} };
  }
  initialized = true;

  const unsubs: Array<() => void> = [];

  unsubs.push(
    await subscribeIpc<SessionSnapshot>("ipc.session.snapshot", (msg) =>
      applySnapshot(msg.payload as unknown as WireSnapshotPayload),
    ),
  );
  unsubs.push(
    await subscribeIpc<StatusTick>("ipc.status.tick", (msg) =>
      applyStatusTick(msg.payload as unknown as WireStatusTickPayload),
    ),
  );
  unsubs.push(
    await subscribeIpc<SettingsState>("ipc.settings.state", (msg) =>
      applySettingsState(msg.payload as unknown as WireSettingsStatePayload),
    ),
  );
  unsubs.push(
    await subscribeIpc<IpcError>("ipc.error", (msg) =>
      applyIpcError(msg.payload as unknown as WireIpcErrorPayload),
    ),
  );
  unsubs.push(
    await subscribeIpc<SessionCitation>("ipc.session.citation", (msg) =>
      applySessionCitation(msg.payload as unknown as WireSessionCitationPayload),
    ),
  );
  unsubs.push(
    await subscribeIpc<SessionMute>("ipc.session.mute", (msg) =>
      applyMuteAck(msg.payload as unknown as WireMutePayload),
    ),
  );

  // Phase 15 Plan 05 — recordings.usage push. Updates the in-drawer disk
  // usage line (recording-browser.ts setUsage) without rebuilding the
  // session list. UI-SPEC §State Management: sessions array is NOT
  // refetched on usage push (avoids list-flicker mid-interaction). The
  // drawer's recordings.list request handles session-array updates on
  // drawer open.
  unsubs.push(
    await subscribeIpc<RecordingsUsage>("ipc.recordings.usage", (msg) =>
      applyRecordingsUsage(msg.payload as unknown as WireRecordingsUsagePayload),
    ),
  );

  // Phase 44-03 / LAUNCH-02 — cohost-reaction push. Sidecar broadcasts
  // one envelope per AI reaction the user heard, carrying the parsed
  // citation_strip. We forward the ENTIRE envelope (ts + payload) so
  // the render-loop can join chips to the matching transcript line by
  // wire timestamp (the transcript_delta on SessionSnapshot carries
  // the same ts shape — both come from _now_iso() on the sidecar).
  unsubs.push(
    await subscribeIpc<SessionCohostReaction>(
      "ipc.session.cohost-reaction",
      (msg) =>
        applyCohostReaction(
          msg.ts,
          msg.payload as unknown as WireCohostReactionPayload,
        ),
    ),
  );

  // Kick off a single ipc.settings.get so the freshly-mounted UI has
  // the full settings tree before the user opens the drawer. The sidecar
  // replies with ipc.settings.state which our subscriber writes.
  try {
    await emitIpc("ipc.settings.get", {});
  } catch (err) {
    if (!isTauriRuntimeUnavailable(err)) {
      // eslint-disable-next-line no-console
      console.warn("[ws-bridge] ipc.settings.get failed:", err);
    }
  }

  return {
    unsubscribeAll: () => {
      for (const u of unsubs) {
        try {
          u();
        } catch (e) {
          // eslint-disable-next-line no-console
          console.warn("[ws-bridge] unsub failed:", e);
        }
      }
      initialized = false;
    },
  };
}

/** Fire-and-forget: ipc.settings.set. Sidecar replies with
 *  ipc.settings.state on success and ipc.error on failure (which the
 *  validator subscriber surfaces — we don't currently render errors,
 *  Wave 4 wires that). Phase 14-04 widens the value union to include
 *  `boolean` for the lighter_blur perf toggle. */
export async function sendSettings(
  field: SettingsField,
  value: string | number | boolean | null,
): Promise<void> {
  if (!SETTINGS_FIELDS.includes(field)) {
    throw new Error(`sendSettings: unknown field ${field}`);
  }
  await emitIpc("ipc.settings.set", { field, value });
}

/** Optimistic ipc.session.mute. The sidecar replies with the same type carrying
 *  {muted: bool} which writes SessionState.muted on the round-trip.
 *
 *  When `toggle` is undefined the shell sends {toggle: true} — the
 *  global-shortcut handler in Rust calls this without args. */
export async function sendMute(toggle: boolean = true): Promise<void> {
  const wasMuted = getSessionState().muted;
  if (toggle) setSessionState({ muted: !wasMuted });
  try {
    await emitIpc("ipc.session.mute", { toggle });
  } catch (err) {
    if (toggle) setSessionState({ muted: wasMuted });
    throw err;
  }
}

// ---------------------------------------------------------------------------
// Payload appliers (exported for testing).
// ---------------------------------------------------------------------------

export function applySnapshot(p: WireSnapshotPayload): void {
  const meters: MetersTriple = {
    music: p.meters.music,
    voice: p.meters.voice,
    mic: p.meters.mic,
  };
  const phase: PhaseChunk[] = p.phase.map((c) => ({
    kind: c.kind,
    weight: c.weight,
    label: c.label,
  }));
  const bpmPeriodMs =
    p.bpm !== null && p.bpm > 0 ? Math.round(60_000 / p.bpm) : null;

  setSessionState({
    meters,
    phase,
    phaseNowPct: p.phase_now_pct,
    bpm: p.bpm,
    bpmPeriodMs,
    dropPredBars: p.drop_pred_bars,
    track: p.track,
    cohostStatus: p.cohost_status,
    latencyMs: p.latency_ms,
    grounded: p.grounded,
    claimPolicy: normalizeClaimPolicy(p.claim_policy),
  });

  if (p.transcript_delta.length > 0) {
    appendTranscript(p.transcript_delta);
  }

  if (p.midi_events.length > 0) {
    const events: MidiEvent[] = p.midi_events.map((m, idx) => ({
      // Compose a stable-enough id from the wire timestamp + control
      // + the index inside this snapshot's delta. The render-loop
      // diffs by array ref so id only matters for the renderer's
      // own event-ribbon diffing.
      id: `${m.ts}-${m.control}-${idx}`,
      label: m.control,
      // Snapshot is fresh; the renderer reads `ageMs` and re-derives.
      ageMs: 0,
    }));
    appendMidiEvents(events);
  }

  // Authoritative run-state reconciliation (the SessionStart $comment
  // promise, now implemented). null = the emitter doesn't track the live
  // lifecycle — leave the optimistic value alone.
  const wireRunState = p.run_state ?? null;
  if (
    wireRunState !== null &&
    Date.now() >= runStateHoldUntilMs &&
    getSessionState().runState !== wireRunState
  ) {
    setSessionState({ runState: wireRunState });
  }
}

function normalizeClaimPolicy(
  p: WireSnapshotPayload["claim_policy"],
): ClaimPolicyState | null {
  if (!p || !["green", "yellow", "red"].includes(p.level)) return null;
  return {
    policy: p.policy,
    level: p.level,
    reason: p.reason ?? null,
    label: claimPolicyLabel(p.policy),
  };
}

function claimPolicyLabel(policy: string): string {
  switch (policy) {
    case "supported_verdict":
      return "ready to call it";
    case "candidate_not_verdict":
      return "checking the call";
    case "watch_not_claim":
      return "watching only";
    case "blocked":
      return "calls held";
    default:
      return "listening";
  }
}

export function applyStatusTick(p: WireStatusTickPayload): void {
  setSessionState({
    status: {
      livekit: p.livekit,
      gemini: p.gemini,
      midi: p.midi,
      screen: p.screen,
      voice: p.voice ?? null,
      captureDevice: normalizeCaptureDevice(p.capture_device),
      midiActivity: normalizeMidiActivity(p.midi_activity),
      midiDevice: normalizeMidiDevice(p.midi_device),
    },
  });
}

function normalizeCaptureDevice(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const text = value.trim().replace(/\s+/g, " ");
  return text ? text.slice(0, 96) : null;
}

function normalizeMidiActivity(value: unknown): WireStatusTickPayload["midi_activity"] {
  switch (value) {
    case "disconnected":
    case "connected_no_midi_traffic":
    case "midi_traffic_unmapped":
    case "midi_events_no_moves":
    case "active":
    case "unknown":
      return value;
    default:
      return null;
  }
}

function normalizeMidiDevice(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const text = value.trim().replace(/\s+/g, " ");
  return text ? text.slice(0, 96) : null;
}

/** Whitelist of valid mascot moods — anything else from the wire is
 *  dropped (T-13-03-01 tampering mitigation). Keep this in lockstep with
 *  the `MascotMood` literal in state.ts. */
const VALID_MOODS: readonly MascotMood[] = ["hype-man", "teacher", "coach"];

function narrowMood(value: unknown, fallback: MascotMood): MascotMood {
  if (typeof value !== "string") return fallback;
  return (VALID_MOODS as readonly string[]).includes(value)
    ? (value as MascotMood)
    : fallback;
}

/** Whitelist of valid top-level modes — anything else from the wire keeps
 *  the current picker segment lit. */
const VALID_SESSION_MODES: readonly SessionMode[] = [
  "cohost",
  "learn",
  "build",
  "debrief",
];

function narrowSessionMode(value: unknown, fallback: SessionMode): SessionMode {
  if (typeof value !== "string") return fallback;
  return (VALID_SESSION_MODES as readonly string[]).includes(value)
    ? (value as SessionMode)
    : fallback;
}

/** Whitelist of valid skill levels — anything else from the wire (or a
 *  pre-skill sidecar that omits the field) keeps the current value. */
const VALID_SKILLS: readonly SkillLevel[] = ["beginner", "intermediate", "pro"];

function narrowSkill(value: unknown, fallback: SkillLevel): SkillLevel {
  if (typeof value !== "string") return fallback;
  return (VALID_SKILLS as readonly string[]).includes(value)
    ? (value as SkillLevel)
    : fallback;
}

/** Whitelist of valid shared persona lenses. */
const VALID_LENSES: readonly SharedLens[] = ["hype", "critique", "tutor"];

function narrowLens(value: unknown, fallback: SharedLens): SharedLens {
  if (typeof value !== "string") return fallback;
  return (VALID_LENSES as readonly string[]).includes(value)
    ? (value as SharedLens)
    : fallback;
}

function applyBlurPerfPreference(lighter: boolean): void {
  if (typeof document === "undefined") return;
  if (lighter) document.documentElement.setAttribute("data-blur-perf", "on");
  else document.documentElement.removeAttribute("data-blur-perf");
}

export function applySettingsState(p: WireSettingsStatePayload): void {
  // Preserve current Phase 13 fields if the sidecar hasn't sent them yet
  // (Plan 13-05 extends the sidecar payload). Defensive narrowing keeps a
  // rogue future-string from poisoning the MascotMood union.
  const state = getSessionState();
  const current = state.settings;
  const lighterBlur =
    typeof p.lighter_blur === "boolean" ? p.lighter_blur : current.lighter_blur;
  applyBlurPerfPreference(lighterBlur);
  setSessionState({
    settings: {
      voice: p.voice,
      mode: p.mode,
      skill: narrowSkill(p.skill, current.skill),
      lens: narrowLens(p.lens, current.lens),
      genre: p.genre,
      output_device_id: p.output_device_id,
      output_profile: p.output_profile,
      retention_days: p.retention_days,
      push_to_mute_hotkey: p.push_to_mute_hotkey,
      learn_headphone_device_index:
        typeof p["learn.headphone_device_index"] === "number" &&
        Number.isInteger(p["learn.headphone_device_index"]) &&
        p["learn.headphone_device_index"] >= 0
          ? p["learn.headphone_device_index"]
          : p["learn.headphone_device_index"] === null
            ? null
            : current.learn_headphone_device_index,
      mood: narrowMood(p.mood, current.mood),
      click_through:
        typeof p.click_through === "boolean"
          ? p.click_through
          : current.click_through,
      lighter_blur: lighterBlur,
    },
    muted: p.muted,
    mode: narrowSessionMode(p["session.mode"], state.mode ?? "cohost"),
  });
}

export function applyMuteAck(p: WireMutePayload): void {
  if (typeof p.muted === "boolean") {
    setSessionState({ muted: p.muted });
  }
  // {toggle: true} echoed back means the sidecar accepted the request
  // and emitted a fresh state — we don't need to flip locally because
  // the next ipc.settings.state will overwrite muted anyway.
}

/** Sidecar error broadcast. Every error still lands in the operator log
 *  (DevTools + ui.log via debug_log); whitelisted original_types ALSO
 *  surface on the deck through SessionState.deckNotice — THE single
 *  user-facing ipc.error surface (shared lanes B+D contract). Lane B adds
 *  its types to DECK_NOTICE_ERROR_TYPES instead of building a second rail. */
export const DECK_NOTICE_ERROR_TYPES: ReadonlySet<string> = new Set([
  "ipc.session.start",
  "ipc.session.stop",
  // Capture-open failure — already emitted end-to-end by the sidecar
  // (__main__._set_input_stream_error); pre-included for lane B.
  "audio.capture",
]);

function deckNoticeText(originalType: string, reason: string): string {
  if (originalType === "ipc.session.start") {
    return `couldn't go live — ${reason.replace(/^session\.start failed:\s*/i, "")}`;
  }
  if (originalType === "ipc.session.stop") {
    return `couldn't stop cleanly — ${reason.replace(/^session\.stop failed:\s*/i, "")}`;
  }
  if (originalType === "audio.capture") {
    // The deck flips back to the armed gate alongside this notice — name
    // the recovery action, not just the failure.
    return `${reason} — the deck is back on standby. Go live to retry.`;
  }
  return reason;
}

export function applyIpcError(p: WireIpcErrorPayload): void {
  vmxLog("[vmx:error]", "ipc.error", {
    original_type: p.original_type,
    reason: p.reason,
  });
  const original = p.original_type ?? "";
  if (!DECK_NOTICE_ERROR_TYPES.has(original)) return;
  const patch: Partial<SessionState> = {
    deckNotice: {
      text: deckNoticeText(original, p.reason),
      tone: "error",
      ts: Date.now(),
    },
  };
  if (original === "ipc.session.start" || original === "audio.capture") {
    // The optimistic GO LIVE repaint was wrong — the backend never went
    // live. Reveal the Start gate so the deck stops claiming a session
    // that does not exist. audio.capture is included because a capture-open
    // failure makes ipc.session.start SUCCEED (__main__._set_input_stream_error
    // sets started_event BEFORE run_stop_event) and the backend self-parks;
    // this broadcast is the only wire signal that the running deck is dead.
    patch.runState = "armed";
  }
  setSessionState(patch);
}

/** Anti-slop telemetry from the co-host loop. Store it for the Settings
 *  diagnostics row without routing through SettingsUIState, because the
 *  telemetry cadence is independent from drawer rebuilds. */
export function applySessionCitation(p: WireSessionCitationPayload): void {
  setCitationDiagnosticsSnapshot({
    slopRatio: p.slop_ratio,
    strippedRate15s: p.stripped_rate_15s,
    lastUnverifiedResponse: p.last_unverified_response,
    bypassActive: p.bypass_active,
  });
}

/** Phase 15 Plan 05 — apply a recordings.usage push. Writes the usage
 *  sub-field of the recordings slice ONLY (sessions list untouched —
 *  UI-SPEC §State Management). Exported for vitest coverage. */
export function applyRecordingsUsage(p: WireRecordingsUsagePayload): void {
  setRecordingsSlice({
    usage: { sessions: p.sessions, bytes_total: p.bytes_total },
  });
}

/** Phase 44-03 / LAUNCH-02 — apply a cohost-reaction push. Appends a
 *  new entry to the reactions ring; the render-loop pairs it to the
 *  matching transcript line by `ts` so the chip strip renders under
 *  the right reaction. Exported for vitest coverage.
 *
 *  Defensively narrows each chip — a malformed wire payload (e.g.
 *  missing verb on one chip from a future-out-of-sync sidecar) is
 *  filtered out at this boundary rather than crashing the renderer
 *  downstream. Matches the narrowMood pattern used elsewhere in this
 *  file (T-13-03-01-style mitigation). */
export function applyCohostReaction(
  ts: string,
  p: WireCohostReactionPayload,
): void {
  const chips: CitationChip[] = [];
  for (const c of p.citation_strip) {
    if (
      typeof c.event_id === "string" &&
      c.event_id.length > 0 &&
      typeof c.verb === "string" &&
      c.verb.length > 0 &&
      typeof c.timestamp_s === "number" &&
      Number.isFinite(c.timestamp_s)
    ) {
      chips.push({
        event_id: c.event_id,
        verb: c.verb,
        timestamp_s: c.timestamp_s,
      });
    }
  }
  appendReaction({
    ts,
    text: p.text,
    event_id: p.event_id,
    citation_strip: chips,
  });
}

/** Test-only: reset the singleton so a vitest case can rerun init. */
export function _resetBridgeForTests(): void {
  initialized = false;
  runStateHoldUntilMs = 0;
}
