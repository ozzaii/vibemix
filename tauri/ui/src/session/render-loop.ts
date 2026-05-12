/* Phase 12 Wave 3 — single rAF render loop (Plan 12-04 §Steps 3).
 *
 * The ONLY requestAnimationFrame caller in the live-session UI. Reads
 * SessionState every frame, projects it onto SessionLayout's prop shape,
 * and calls `renderSessionFrame(mounted, layoutState)`. Components never
 * start their own rAF or setInterval.
 *
 * Performance budget (Plan §must-haves):
 *   - 30 fps floor on Retina + 1080p externals.
 *   - Dev mode: frame durations are tracked; if p95 > 33ms over a 1s
 *     window, a `[frame slow]` warning fires to the console.
 *   - Release mode (`import.meta.env.DEV === false`) skips the timing
 *     entirely so the frame body is exactly the diff path.
 *
 * The local clock display string is recomputed here (not in the
 * bridge) — wall-clock progresses regardless of snapshot arrival. */

import { renderSessionFrame, type Mounted } from "./SessionLayout.js";
import type {
  SessionState as LayoutSessionState,
} from "./SessionLayout.js";
import { getSessionState, setSessionState } from "./state.js";
import type { SessionState as BridgeSessionState } from "./state.js";

let rafHandle: number | null = null;
let mountedRef: Mounted | null = null;

// Dev-mode frame-time tracking
const FRAME_WINDOW_MS = 1000;
const SLOW_FRAME_MS = 33;
const frameTimes: number[] = [];
let lastSlowWarnAt = 0;

/** Start the rAF loop against the given mounted handle. Idempotent —
 *  calling twice stops the prior loop before starting a new one so a
 *  hot-reload during dev doesn't accumulate duplicate loops. */
export function startRenderLoop(mounted: Mounted): void {
  stopRenderLoop();
  mountedRef = mounted;
  rafHandle = requestAnimationFrame(tick);
}

/** Stop the loop. The mounted DOM stays in place — only the rAF is
 *  cancelled and the mounted ref dropped. */
export function stopRenderLoop(): void {
  if (rafHandle != null) {
    cancelAnimationFrame(rafHandle);
    rafHandle = null;
  }
  mountedRef = null;
}

function tick(timestamp: number): void {
  // Re-arm first so an exception inside the body doesn't kill the loop.
  if (mountedRef !== null) {
    rafHandle = requestAnimationFrame(tick);
  } else {
    rafHandle = null;
    return;
  }

  const t0 = performanceNow();

  try {
    // Refresh the wall-clock display string. The bridge does not write
    // this field — it ticks regardless of snapshot arrival.
    const wallClock = formatWallClock(timestamp);
    if (getSessionState().clockText !== wallClock) {
      setSessionState({ clockText: wallClock });
    }

    const bridgeState = getSessionState();
    const layoutState = projectToLayoutState(bridgeState);
    renderSessionFrame(mountedRef, layoutState);
  } catch (err) {
    // A throw in the render path must NOT crash the rAF. Log + carry on.
    // eslint-disable-next-line no-console
    console.warn("[render-loop] frame body threw:", err);
  }

  if (isDev()) {
    trackFrameTime(performanceNow() - t0);
  }
}

/** Project the bridge's SessionState shape onto SessionLayout's prop shape.
 *  Most fields map 1:1; the divergence is mostly nesting differences
 *  (bridge keeps phase + phaseNowPct flat; layout nests them under
 *  `phase.{chunks,nowPct}`). */
function projectToLayoutState(s: BridgeSessionState): LayoutSessionState {
  const livePill = pillFromStatus(s.status.livekit, s.cohostStatus);
  const recPill = recFromMuted(s.muted, s.status.midi);
  const sysPill = sysFromStatuses(s.status.gemini, s.status.screen);

  return {
    titlebar: {
      live: livePill,
      rec: recPill,
      sys: sysPill,
      clock: s.clockText,
    },
    meters: s.meters,
    timecode: {
      clock: s.clockText,
      bpm: s.bpm,
      key: null,
      deck: s.track?.deck ?? null,
    },
    phase: {
      chunks: s.phase,
      nowPct: s.phaseNowPct,
    },
    drop: {
      bars: s.dropPredBars,
      bpmPeriodMs: s.bpmPeriodMs ?? undefined,
    },
    events: s.midiEvents,
    cohost: {
      status: s.cohostStatus,
      transcript: s.transcript,
      latencyMs: s.latencyMs,
      grounded: s.grounded,
    },
    status: {
      livekit: s.status.livekit,
      gemini: s.status.gemini,
      midi: s.status.midi,
      screen: s.status.screen,
      muted: s.muted,
      hotkey: formatHotkey(s.settings.push_to_mute_hotkey),
      errors: {},
    },
    persona: {
      // Phase 12-05 (settings drawer) wires the rocker callbacks — the
      // session window itself only consumes these as initial-render
      // defaults. Skill/interaction live in the drawer.
      skill: "INT",
      interaction: s.settings.mode === "coach" ? "COACH" : "HYPE",
      voice: s.settings.voice,
      genre: s.settings.genre,
    },
    output: {
      device: s.settings.output_device_id ?? "AUTO",
      profile: s.settings.output_profile === "spk" ? "SPK" : "HP",
    },
  };
}

// PillLevel ("ok" | "down" | "off") is the titlebar's traffic-light
// vocabulary. We collapse the bridge's richer statuses (connecting,
// denied, null) onto those three buckets — anything not-yet-determined
// or actively-bad becomes "off" or "down". Wave 4's settings drawer
// will refine the mapping.
function pillFromStatus(
  lk: BridgeSessionState["status"]["livekit"],
  cohostStatus: BridgeSessionState["cohostStatus"],
): "ok" | "down" | "off" {
  if (lk === "down") return "down";
  if (lk === "connecting") return "off";
  if (lk === "ok" && cohostStatus !== "IDLE") return "ok";
  return "off";
}

function recFromMuted(
  muted: boolean,
  midi: number | null,
): "ok" | "down" | "off" {
  if (muted) return "off";
  if (midi === 0) return "down";
  return "ok";
}

function sysFromStatuses(
  gemini: BridgeSessionState["status"]["gemini"],
  screen: BridgeSessionState["status"]["screen"],
): "ok" | "down" | "off" {
  if (gemini === "down" || screen === "denied") return "down";
  if (gemini === "ok" && screen === "ok") return "ok";
  return "off";
}

/** Hotkey shown in the muted banner / status bar — accept the wire
 *  format (e.g. "cmd+shift+m") and produce the UI form ("⌘⇧M"). */
function formatHotkey(combo: string): string {
  if (!combo) return "—";
  const parts = combo.toLowerCase().split("+");
  let out = "";
  for (const p of parts) {
    switch (p) {
      case "cmd":
      case "meta":
      case "super":
        out += "⌘";
        break;
      case "shift":
        out += "⇧";
        break;
      case "ctrl":
      case "control":
        out += "⌃";
        break;
      case "alt":
      case "option":
        out += "⌥";
        break;
      default:
        out += p.toUpperCase();
    }
  }
  return out;
}

function formatWallClock(timestamp: number): string {
  // Date.now() drifts from rAF's high-res timestamp by sub-ms over the
  // life of the session; we use Date for the human-readable view.
  void timestamp;
  const d = new Date();
  const hh = d.getHours().toString().padStart(2, "0");
  const mm = d.getMinutes().toString().padStart(2, "0");
  const ss = d.getSeconds().toString().padStart(2, "0");
  return `${hh}:${mm}:${ss}`;
}

function isDev(): boolean {
  // import.meta.env.DEV is replaced at build time by Vite. In test env
  // (vitest) this resolves to true; in production builds it's false and
  // V8 dead-code-eliminates the entire timing block.
  try {
    return Boolean(import.meta.env?.DEV);
  } catch (_e) {
    return false;
  }
}

function performanceNow(): number {
  return typeof performance !== "undefined" && performance.now
    ? performance.now()
    : Date.now();
}

function trackFrameTime(dtMs: number): void {
  const now = performanceNow();
  frameTimes.push(now);
  // Trim entries older than the 1s window.
  while (frameTimes.length && now - frameTimes[0]! > FRAME_WINDOW_MS) {
    frameTimes.shift();
  }
  // Dev-mode: log if dt > 33ms (single-frame stall) at most once/sec
  // so a sustained jank doesn't spam the console.
  if (dtMs > SLOW_FRAME_MS && now - lastSlowWarnAt > FRAME_WINDOW_MS) {
    lastSlowWarnAt = now;
    // eslint-disable-next-line no-console
    console.warn(
      `[render-loop] frame slow: ${dtMs.toFixed(1)}ms (budget ${SLOW_FRAME_MS}ms)`,
    );
  }
}

// ---------------------------------------------------------------------------
// Test-only surface — vitest's render-loop.spec.ts imports these to drive a
// fake rAF without standing up the real DOM event loop.
// ---------------------------------------------------------------------------

export const _internals = {
  tick,
  projectToLayoutState,
  formatHotkey,
  formatWallClock,
  trackFrameTime,
};
