/* Phase 12 dev-only · `?dev=session-mock` entry point.
 *
 * Mounts the live session DOM + settings drawer with a fake state animator
 * so Vite dev (no Tauri runtime) shows the Phase 12 UI moving. Skips the
 * IPC bridge (Tauri invoke/listen would fail in pure-browser dev) · every
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
  appendReaction,
  appendMidiEvents,
  getSessionState,
} from "./state.js";
import type { CitationChip } from "./components/citation-strip.js";
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

/* "The Deck Speaks" rebuild (2026-05-26): the signature gesture (line rises →
 * amber rule draws → cite ignites) only fires when a reaction carries a citation
 * strip joined to the now-line by `ts`. The Phase-12 mock only appended bare
 * transcript lines, so the dev preview never SHOWED the deck's whole reason to
 * exist. Each text now ships a grounded citation atom (one per line, parallel
 * index) so `?dev=session-mock` demonstrates the receipt igniting. The first
 * line is deliberately citation-free (`null`) — "warming up" cites nothing yet,
 * which exercises the calm no-receipt path right next to the lit one. */
const CITATION_VERBS: (Omit<CitationChip, "event_id"> | null)[] = [
  null, // "warming up, listening for the room" — nothing cited yet
  { verb: "steady kick", timestamp_s: 31 }, // groove settling
  { verb: "filter rise", timestamp_s: 48 }, // filter swell
  { verb: "build energy", timestamp_s: 61 }, // drop in 8 bars
  { verb: "drop hit", timestamp_s: 73 }, // clean drop
  { verb: "low-mid clash", timestamp_s: 88 }, // EQ the low-mid
  { verb: "deck swap", timestamp_s: 96 }, // swapping decks
  { verb: "bpm drift", timestamp_s: 109 }, // tempo drifting
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

/** Append a cohost reaction joined to a transcript line by `ts`. The citation
 * strip is the parallel-indexed atom (or empty for the citation-free line), so
 * the render-loop lights the receipt under exactly the right now-line. */
function appendReactionFor(idx: number, text: string, ts: string): void {
  const atom = CITATION_VERBS[idx % CITATION_VERBS.length] ?? null;
  const strip: CitationChip[] = atom
    ? [{ event_id: `ev:${atom.verb.replace(/\s+/g, "_").toUpperCase()}@${atom.timestamp_s}`, ...atom }]
    : [];
  appendReaction({ ts, text, event_id: `mock-react-${idx}`, citation_strip: strip });
}

function tick(): void {
  const now = performance.now();
  const elapsed = now - startedAtMs;

  // Meters · three independent sine waves so the UI feels alive.
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
      key: "5A",
    },
  });

  // Drop countdown · cycles 16 → 0 → null → 16 every ~32s
  const dropCycle = Math.floor(elapsed / 2000) % 18;
  if (dropCycle <= 16) {
    dropBars = 16 - dropCycle;
  } else {
    dropBars = null;
  }

  // Append a transcript line every ~5s — plus its grounded citation so the
  // receipt gesture re-fires on the new now-line (joined by `ts`).
  if (elapsed - lastTranscriptAt > 5000) {
    const idx = transcriptIdx % TRANSCRIPT_TEXTS.length;
    const text = TRANSCRIPT_TEXTS[idx]!;
    const ts = tsHHMMSS(elapsed);
    appendTranscript([{ role: "ai", text, ts }]);
    appendReactionFor(idx, text, ts);
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
 * Skips initSessionBridge() · pure-browser Vite dev has no Tauri runtime
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
  TRANSCRIPT_TEXTS.slice(0, 5).forEach((text, i) => {
    const ts = tsHHMMSS((i + 1) * 4000);
    appendTranscript([{ role: "ai" as const, text, ts }]);
    appendReactionFor(i, text, ts);
  });

  // Mount layout + drawer.
  const m = mountSessionLayout(root);
  mountSettingsDrawer(document.body);

  // Seed a mid-set start so the dev demo's hero ELAPSED window reads
  // ~41 min in rather than 00:00:00. The render-loop reads sessionStartMs
  // and counts up from here (the titlebar keeps the real wall clock).
  setSessionState({ sessionStartMs: Date.now() - (41 * 60 + 12) * 1000 });

  // Start render loop reading SessionState.
  startRenderLoop(m);

  // Start the synthesizer.
  startedAtMs = performance.now();
  animatorHandle = requestAnimationFrame(tick);

  // eslint-disable-next-line no-console
  console.log(
    "[session-mock] mounted · synthetic state at 60 fps. Click the gear (top-right) to open Settings.",
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
