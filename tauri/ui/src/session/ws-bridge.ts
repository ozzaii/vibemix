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
  SessionSnapshot,
  SessionMute,
  SettingsState,
  StatusTick,
} from "../ipc/messages.js";
import {
  appendMidiEvents,
  appendTranscript,
  setSessionState,
} from "./state.js";
import type { LevelPair, MetersTriple } from "./state.js";
import type { PhaseChunk } from "./components/phase-tape.js";
import type { MidiEvent } from "./components/event-ribbon.js";

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
}

interface WireMutePayload {
  toggle?: boolean;
  muted?: boolean;
}

const SETTINGS_FIELDS = [
  "voice",
  "mode",
  "genre",
  "output_device_id",
  "output_profile",
  "retention_days",
  "push_to_mute_hotkey",
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
 *  Wave 4 wires that). */
export async function sendSettings(
  field: SettingsField,
  value: string | number | null,
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

export function applySettingsState(p: WireSettingsStatePayload): void {
  setSessionState({
    settings: {
      voice: p.voice,
      mode: p.mode,
      genre: p.genre,
      output_device_id: p.output_device_id,
      output_profile: p.output_profile,
      retention_days: p.retention_days,
      push_to_mute_hotkey: p.push_to_mute_hotkey,
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

/** Test-only: reset the singleton so a vitest case can rerun init. */
export function _resetBridgeForTests(): void {
  initialized = false;
}
