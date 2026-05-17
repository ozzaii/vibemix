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
 *   - sendMute(toggle) — fire-and-forget ipc.session.mute; the sidecar
 *     replies with the same type carrying {muted: bool} which we already
 *     subscribe to.
 *
 * On boot the bridge fires a single ipc.settings.get so a freshly-mounted
 * session has the full settings tree before the user opens the drawer.
 * The sidecar's run_session also emits a settings.state on its own boot,
 * so the get/reply pair is belt-and-suspenders.
 *
 * Plan §Notes — transcript scroll behaviour belongs in render-loop.ts;
 * the bridge does NOT touch the DOM.
 */

import { emitIpc, subscribeIpc } from "../ipc/client.js";
import type {
  RecordingsUsage,
  SessionCohostReaction,
  SessionSnapshot,
  SessionMute,
  SettingsState,
  StatusTick,
} from "../ipc/messages.js";
import { setRecordingsSlice } from "../settings/state.js";
import {
  appendMidiEvents,
  appendReaction,
  appendTranscript,
  getSessionState,
  setSessionState,
} from "./state.js";
import type { LevelPair, MascotMood, MetersTriple } from "./state.js";
import type { PhaseChunk } from "./components/phase-tape.js";
import type { MidiEvent } from "./components/event-ribbon.js";
import type { CitationChip } from "./components/citation-strip.js";

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
}

interface WireStatusTickPayload {
  livekit: "ok" | "connecting" | "down";
  gemini: "ok" | "down";
  midi: number | null;
  screen: "ok" | "denied";
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
// SettingsSet schema enum at messages.schema.json:529 and the Python
// SettingsSetPayload.field Literal at src/vibemix/ui_bus/messages.py.
// All three must list the same 10 fields. Today mascot-group.ts
// bypasses sendSettings via direct emitIpc for mood + click_through,
// but any future caller using sendSettings would hit the runtime
// `unknown field` throw without this entry.
const SETTINGS_FIELDS = [
  "voice",
  "mode",
  "genre",
  "output_device_id",
  "output_profile",
  "retention_days",
  "push_to_mute_hotkey",
  "mood",            // Plan 13-05
  "click_through",   // Plan 13-05
  "lighter_blur",    // Plan 14-04
] as const;
export type SettingsField = (typeof SETTINGS_FIELDS)[number];

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
    // eslint-disable-next-line no-console
    console.warn("[ws-bridge] ipc.settings.get failed:", err);
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

/** Fire-and-forget: ipc.session.mute. The sidecar replies with the same
 *  type carrying {muted: bool} which writes SessionState.muted on the
 *  round-trip.
 *
 *  When `toggle` is undefined the shell sends {toggle: true} — the
 *  global-shortcut handler in Rust calls this without args. */
export async function sendMute(toggle: boolean = true): Promise<void> {
  await emitIpc("ipc.session.mute", { toggle });
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
}

export function applyStatusTick(p: WireStatusTickPayload): void {
  setSessionState({
    status: {
      livekit: p.livekit,
      gemini: p.gemini,
      midi: p.midi,
      screen: p.screen,
    },
  });
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

export function applySettingsState(p: WireSettingsStatePayload): void {
  // Preserve current Phase 13 fields if the sidecar hasn't sent them yet
  // (Plan 13-05 extends the sidecar payload). Defensive narrowing keeps a
  // rogue future-string from poisoning the MascotMood union.
  const current = getSessionState().settings;
  setSessionState({
    settings: {
      voice: p.voice,
      mode: p.mode,
      genre: p.genre,
      output_device_id: p.output_device_id,
      output_profile: p.output_profile,
      retention_days: p.retention_days,
      push_to_mute_hotkey: p.push_to_mute_hotkey,
      mood: narrowMood(p.mood, current.mood),
      click_through:
        typeof p.click_through === "boolean"
          ? p.click_through
          : current.click_through,
      lighter_blur:
        typeof p.lighter_blur === "boolean"
          ? p.lighter_blur
          : current.lighter_blur,
    },
    muted: p.muted,
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
}
