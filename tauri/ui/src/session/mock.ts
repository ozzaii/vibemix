/* Phase 12 dev-only — `?dev=session-mock` entry point.
 *
 * Mounts the live session DOM + settings drawer with a fake state animator
 * so Vite dev (no Tauri runtime) shows the Phase 12 UI moving. Skips the
 * IPC bridge (Tauri invoke/listen would fail in pure-browser dev) — every
 * snapshot is synthesised locally.
 *
 * Activated from `main.ts` when `?dev=session-mock` is in the URL. The
 * animator is only loaded via dynamic import so production builds drop it.
 */

import { mountSessionLayout } from "./SessionLayout.js";
import { startRenderLoop, stopRenderLoop } from "./render-loop.js";
import { mountSettingsDrawer } from "../settings/SettingsDrawer.js";
import {
  setSessionState,
  appendTranscript,
  appendMidiEvents,
  getSessionState,
} from "./state.js";
import type { PhaseChunk } from "./components/phase-tape.js";

let animatorHandle: number | null = null;
let startedAtMs = 0;

const TRANSCRIPT_TEXTS: string[] = [
  "warming up, listening for the room",
  "okay this groove's settling in",
  "filter swell coming, eyes on the build",
  "drop in 8 bars, lock in",
  "nice. clean drop, crowd's with you",
  "EQ that low-mid back when you bring the vocal",
  "great call swapping decks here",
  "tempo's drifting a touch, sync it back",
];

const MIDI_LABELS: string[] = [
  "A · CH1 vol ↑",
  "A · LOW EQ ↓",
  "B · CUE 3",
  "X-FADER →",
  "A · FILTER ↑",
  "B · LOOP IN",
  "DECK A · play",
  "B · HI EQ ↑",
];

function tsHHMMSS(elapsedMs: number): string {
  const d = new Date(elapsedMs);
  const h = String(d.getUTCHours()).padStart(2, "0");
  const m = String(d.getUTCMinutes()).padStart(2, "0");
  const s = String(d.getUTCSeconds()).padStart(2, "0");
  return `${h}:${m}:${s}`;
}

const PHASE_CHUNKS: PhaseChunk[] = [
  { kind: "groove", weight: 0.20, label: "GROOVE" },
  { kind: "build", weight: 0.18, label: "BUILD" },
  { kind: "drop-ghost", weight: 0.06, label: "drop?" },
  { kind: "groove", weight: 0.22, label: "GROOVE" },
  { kind: "build", weight: 0.16, label: "BUILD" },
  { kind: "drop-ghost", weight: 0.06, label: "drop?" },
  { kind: "groove", weight: 0.12, label: "GROOVE" },
];

function sineRMS(elapsedMs: number, hz: number, base: number, range: number): number {
  const t = (elapsedMs / 1000) * hz;
  return Math.max(0, Math.min(1, base + Math.sin(t * Math.PI * 2) * range));
}

let lastTranscriptAt = 0;
let lastMidiAt = 0;
let transcriptIdx = 0;
let midiIdx = 0;
let dropBars: number | null = 16;

function tick(): void {
  const now = performance.now();
  const elapsed = now - startedAtMs;

  // Meters — three independent sine waves so the UI feels alive.
  const musicRms = sineRMS(elapsed, 0.6, 0.42, 0.28);
  const voiceRms = sineRMS(elapsed, 0.25, 0.15, 0.45);
  const micRms = sineRMS(elapsed, 1.1, 0.05, 0.08);

  setSessionState({
    meters: {
      music: { rms: musicRms, peak: Math.min(1, musicRms + 0.08) },
      voice: { rms: voiceRms, peak: Math.min(1, voiceRms + 0.05) },
      mic: { rms: micRms, peak: Math.min(1, micRms + 0.02) },
    },
    bpm: 128,
    bpmPeriodMs: 60_000 / 128,
    phaseNowPct: ((elapsed / 240) % 100),
    phase: PHASE_CHUNKS,
    dropPredBars: dropBars,
    cohostStatus: voiceRms > 0.35 ? "TALKING" : "LISTENING",
    grounded: true,
    latencyMs: 380 + Math.floor(Math.sin(elapsed / 1000) * 60),
    status: {
      livekit: "ok",
      gemini: "ok",
      midi: 1,
      screen: "ok",
    },
    track: {
      title: "Strobe (Deadmau5 Remix)",
      artist: "Deadmau5",
      deck: "A",
    },
    clockText: tsHHMMSS(elapsed),
  });

  // Drop countdown — cycles 16 → 0 → null → 16 every ~32s
  const dropCycle = Math.floor(elapsed / 2000) % 18;
  if (dropCycle <= 16) {
    dropBars = 16 - dropCycle;
  } else {
    dropBars = null;
  }

  // Append a transcript line every ~5s.
  if (elapsed - lastTranscriptAt > 5000) {
    const text = TRANSCRIPT_TEXTS[transcriptIdx % TRANSCRIPT_TEXTS.length]!;
    appendTranscript([{ role: "ai", text, ts: tsHHMMSS(elapsed) }]);
    transcriptIdx++;
    lastTranscriptAt = elapsed;
  }

  // Append a MIDI event every ~1.5s.
  if (elapsed - lastMidiAt > 1500) {
    const label = MIDI_LABELS[midiIdx % MIDI_LABELS.length]!;
    appendMidiEvents([{ id: `mock-${midiIdx}`, label, ageMs: 0 }]);
    midiIdx++;
    lastMidiAt = elapsed;
  }

  animatorHandle = requestAnimationFrame(tick);
}

/** Mount the live session UI in mock mode and start the animator.
 *
 * Skips initSessionBridge() — pure-browser Vite dev has no Tauri runtime
 * to talk to. Instead, the local animator drives SessionState directly. */
export async function routeSessionMock(rootEl?: HTMLElement): Promise<void> {
  const root =
    rootEl ??
    (document.getElementById("wizard-app") as HTMLElement | null) ??
    document.body;

  // Tear down anything the wizard left behind.
  root.replaceChildren();

  // Pre-seed transcript with the first 5 lines so the panel doesn't start
  // empty (more dramatic first paint).
  appendTranscript(
    TRANSCRIPT_TEXTS.slice(0, 5).map((text, i) => ({
      role: "ai" as const,
      text,
      ts: tsHHMMSS((i + 1) * 4000),
    })),
  );

  // Mount layout + drawer.
  const m = mountSessionLayout(root);
  mountSettingsDrawer(document.body);

  // Start render loop reading SessionState.
  startRenderLoop(m);

  // Start the synthesizer.
  startedAtMs = performance.now();
  animatorHandle = requestAnimationFrame(tick);

  // eslint-disable-next-line no-console
  console.log(
    "[session-mock] mounted — synthetic state at 60 fps. Click the gear (top-right) to open Settings.",
  );

  // Expose a console handle so Kaan can poke the state if he wants.
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (window as any).__sessionMock = {
    getState: getSessionState,
    setState: setSessionState,
    stop: stopMock,
  };
}

export function stopMock(): void {
  if (animatorHandle !== null) {
    cancelAnimationFrame(animatorHandle);
    animatorHandle = null;
  }
  stopRenderLoop();
}
