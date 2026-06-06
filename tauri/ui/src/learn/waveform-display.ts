// SPDX-License-Identifier: Apache-2.0

type DeckId = "A" | "B";

interface WaveformCue {
  label: string;
  start_s: number;
  end_s: number;
}

interface WaveformDeck {
  bpm: number;
  duration_s: number;
  peaks: [number, number, number][];
  cues: WaveformCue[];
  track_id?: string | null;
  title?: string | null;
  artist?: string | null;
  source?: "bundled_demo" | "library_save_mode" | null;
  source_start_s?: number | null;
}

export interface WaveformReadyPayload {
  sample_rate: number;
  beat_interval_s: number;
  decks: Partial<Record<DeckId, WaveformDeck>>;
}

export interface PlayheadTickPayload {
  sample_rate: number;
  decks: Partial<Record<DeckId, { frame: number; position_s: number; bpm: number }>>;
}

export interface WaveformGradePayload {
  verdict: "locked" | "drifting" | "tempo_off" | "trainwreck" | "abstain";
  phase_error_beats: number;
  save_landed?: boolean;
}

export interface WaveformDisplayHandle {
  updateWaveforms(payload: WaveformReadyPayload): void;
  updatePlayhead(payload: PlayheadTickPayload): void;
  updateGrade(payload: WaveformGradePayload): void;
  dispose(): void;
}

interface CachedDeck {
  canvas: HTMLCanvasElement | OffscreenCanvas;
  duration_s: number;
  beat_interval_s: number;
  bpm: number;
  cues: WaveformCue[];
}

const DECKS: DeckId[] = ["A", "B"];
const STRIP_WIDTH = 720;
const STRIP_HEIGHT = 72;
const DPR_MAX = 2;
const GALLOP_SHIFT_PX = 96;

function clamp(value: number, min: number, max: number): number {
  if (!Number.isFinite(value)) return min;
  return Math.min(max, Math.max(min, value));
}

function beatTrainMarkup(deck: DeckId): string {
  const beats = Array.from(
    { length: 9 },
    (_value, index) => `<i style="--beat-index:${index}"></i>`,
  ).join("");
  return `<div class="learn-waveforms__train" data-deck="${deck}">${beats}</div>`;
}

function makeCanvas(width: number, height: number): HTMLCanvasElement | OffscreenCanvas {
  if (typeof OffscreenCanvas !== "undefined") {
    return new OffscreenCanvas(width, height);
  }
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  return canvas;
}

function drawCachedDeck(
  deck: WaveformDeck,
  beatIntervalS: number,
): HTMLCanvasElement | OffscreenCanvas {
  const canvas = makeCanvas(STRIP_WIDTH, STRIP_HEIGHT);
  const ctx = canvas.getContext("2d");
  if (!ctx) return canvas;
  ctx.clearRect(0, 0, STRIP_WIDTH, STRIP_HEIGHT);
  ctx.fillStyle = "rgba(26, 22, 24, 0.92)";
  ctx.fillRect(0, 0, STRIP_WIDTH, STRIP_HEIGHT);

  for (const cue of deck.cues ?? []) {
    const start = (cue.start_s / Math.max(0.001, deck.duration_s)) * STRIP_WIDTH;
    const end = (cue.end_s / Math.max(0.001, deck.duration_s)) * STRIP_WIDTH;
    ctx.fillStyle = cue.label === "drop"
      ? "rgba(255, 165, 223, 0.16)"
      : "rgba(232, 196, 122, 0.10)";
    ctx.fillRect(start, 0, Math.max(1, end - start), STRIP_HEIGHT);
  }

  ctx.strokeStyle = "rgba(255, 220, 240, 0.11)";
  ctx.lineWidth = 1;
  const beatCount = Math.floor(deck.duration_s / Math.max(0.001, beatIntervalS));
  for (let beat = 0; beat <= beatCount; beat += 4) {
    const x = (beat * beatIntervalS / Math.max(0.001, deck.duration_s)) * STRIP_WIDTH;
    ctx.globalAlpha = beat % 16 === 0 ? 0.75 : 0.36;
    ctx.beginPath();
    ctx.moveTo(Math.round(x) + 0.5, 0);
    ctx.lineTo(Math.round(x) + 0.5, STRIP_HEIGHT);
    ctx.stroke();
  }
  ctx.globalAlpha = 1;

  const peaks = deck.peaks ?? [];
  const barW = Math.max(1, STRIP_WIDTH / Math.max(1, peaks.length));
  for (let i = 0; i < peaks.length; i += 1) {
    const peak = peaks[i];
    if (!peak) continue;
    const [low, mid, high] = peak;
    const x = i * barW;
    const lowH = (low / 255) * STRIP_HEIGHT * 0.48;
    const midH = (mid / 255) * STRIP_HEIGHT * 0.34;
    const highH = (high / 255) * STRIP_HEIGHT * 0.22;
    ctx.fillStyle = "rgba(232, 196, 122, 0.45)";
    ctx.fillRect(x, STRIP_HEIGHT - lowH, Math.ceil(barW), lowH);
    ctx.fillStyle = "rgba(255, 165, 223, 0.42)";
    ctx.fillRect(x, STRIP_HEIGHT * 0.52 - midH * 0.5, Math.ceil(barW), midH);
    ctx.fillStyle = "rgba(242, 239, 241, 0.56)";
    ctx.fillRect(x, 10 + highH * 0.2, Math.ceil(barW), highH);
  }
  return canvas;
}

export function WaveformDisplay(host: HTMLElement): WaveformDisplayHandle {
  host.innerHTML = `
    <div class="learn-waveforms" role="img" aria-label="practice waveforms">
      <canvas class="learn-waveform" data-deck="A"></canvas>
      <canvas class="learn-waveform" data-deck="B"></canvas>
      <div class="learn-waveforms__gallop" aria-hidden="true">
        ${beatTrainMarkup("A")}
        ${beatTrainMarkup("B")}
      </div>
    </div>
  `;
  // Start hidden: with no audio loaded the strips are empty boxes parked over
  // the tutor line. CSS reveals the host only once updateWaveforms flags real
  // data ("partial"/"true"); an idle lesson never shows the dead panels.
  host.dataset.ready = "false";
  host.dataset.gallop = "idle";
  host.dataset.gallopSnap = "false";
  host.style.setProperty("--gallop-shift", "0px");
  host.style.setProperty("--gallop-intensity", "0");
  const canvases = new Map<DeckId, HTMLCanvasElement>();
  host.querySelectorAll<HTMLCanvasElement>("canvas[data-deck]").forEach((canvas) => {
    const deck = canvas.dataset.deck as DeckId;
    canvases.set(deck, canvas);
  });

  let cache: Partial<Record<DeckId, CachedDeck>> = {};
  let playheads: PlayheadTickPayload["decks"] = {};
  let raf = 0;

  const size = (): void => {
    const dpr = Math.min(DPR_MAX, window.devicePixelRatio || 1);
    for (const canvas of canvases.values()) {
      const rect = canvas.getBoundingClientRect();
      canvas.width = Math.max(1, Math.floor((rect.width || STRIP_WIDTH) * dpr));
      canvas.height = Math.max(1, Math.floor((rect.height || STRIP_HEIGHT) * dpr));
    }
  };

  const draw = (): void => {
    raf = 0;
    size();
    for (const deck of DECKS) {
      const canvas = canvases.get(deck);
      const cached = cache[deck];
      if (!canvas || !cached) continue;
      const ctx = canvas.getContext("2d");
      if (!ctx) continue;
      const width = canvas.width;
      const height = canvas.height;
      ctx.clearRect(0, 0, width, height);
      ctx.drawImage(cached.canvas, 0, 0, width, height);
      const playhead = playheads[deck];
      const positionS = playhead?.position_s ?? 0;
      const x = (positionS / Math.max(0.001, cached.duration_s)) * width;
      ctx.fillStyle = "rgba(255, 165, 223, 0.88)";
      ctx.fillRect(Math.round(x), 0, Math.max(2, Math.ceil(width / 360)), height);
      ctx.fillStyle = "rgba(242, 239, 241, 0.92)";
      ctx.font = "600 11px JetBrains Mono, ui-monospace, monospace";
      ctx.fillText(`${deck} ${(playhead?.bpm ?? cached.bpm).toFixed(1)} BPM`, 10, 18);
    }
  };

  const requestDraw = (): void => {
    if (!raf) raf = window.requestAnimationFrame(draw);
  };

  return {
    updateWaveforms(payload: WaveformReadyPayload): void {
      const next: Partial<Record<DeckId, CachedDeck>> = {};
      for (const deck of DECKS) {
        const row = payload.decks[deck];
        if (!row) continue;
        next[deck] = {
          canvas: drawCachedDeck(row, payload.beat_interval_s),
          duration_s: row.duration_s,
          beat_interval_s: payload.beat_interval_s,
          bpm: row.bpm,
          cues: row.cues ?? [],
        };
      }
      cache = next;
      // 2 decks = "true", 1 = "partial" (both visible); 0 = "false" so the
      // host hides again when a deck unloads (back to the idle empty state).
      const loaded = Object.keys(next).length;
      host.dataset.ready = loaded >= 2 ? "true" : loaded === 1 ? "partial" : "false";
      requestDraw();
    },
    updatePlayhead(payload: PlayheadTickPayload): void {
      playheads = payload.decks;
      requestDraw();
    },
    updateGrade(payload: WaveformGradePayload): void {
      const phase = clamp(payload.phase_error_beats, -0.5, 0.5);
      const intensity = Math.min(1, Math.abs(phase) / 0.25);
      host.style.setProperty("--gallop-shift", `${phase * GALLOP_SHIFT_PX}px`);
      host.style.setProperty("--gallop-intensity", intensity.toFixed(3));
      host.dataset.gallopPhase = phase.toFixed(4);
      host.dataset.gallopIntensity = intensity.toFixed(3);
      host.dataset.gallopVerdict = payload.verdict;
      host.dataset.gallopSnap = payload.verdict === "locked" ? "true" : "false";
      if (payload.verdict === "locked") {
        host.dataset.gallop = payload.save_landed ? "save" : "locked";
      } else if (payload.verdict === "trainwreck" || payload.verdict === "tempo_off") {
        host.dataset.gallop = "off";
      } else if (phase > 0.005) {
        host.dataset.gallop = "behind";
      } else if (phase < -0.005) {
        host.dataset.gallop = "ahead";
      } else {
        host.dataset.gallop = "center";
      }
    },
    dispose(): void {
      if (raf) window.cancelAnimationFrame(raf);
      host.style.removeProperty("--gallop-shift");
      host.style.removeProperty("--gallop-intensity");
      host.innerHTML = "";
    },
  };
}
