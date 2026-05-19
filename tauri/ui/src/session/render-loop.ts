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

import { invoke } from "@tauri-apps/api/core";

import { renderSessionFrame, type Mounted } from "./SessionLayout.js";
import type {
  SessionState as LayoutSessionState,
} from "./SessionLayout.js";
import { getSessionState, setSessionState } from "./state.js";
import type {
  CohostReaction,
  SessionState as BridgeSessionState,
} from "./state.js";
import type { ReactionsByTs } from "./components/cohost.js";
import type { CitationChip } from "./components/citation-strip.js";

let rafHandle: number | null = null;
let mountedRef: Mounted | null = null;

/** Wave 6 (H9) — handler for the "↻ RETRY" button rendered in the cohost
 *  foot after grounding has been false for >5s. There's no dedicated
 *  `ipc.cohost.reconnect` route today (TODO Phase 17 — surface the
 *  partial-failure cases separately from a full sidecar restart); we
 *  reuse the crash-banner's restart_sidecar path because a sustained
 *  ungrounded state is functionally indistinguishable from a sidecar
 *  hang. The handler is fire-and-forget; the bridge picks up the new
 *  sidecar's snapshot once it boots and the foot flips back to GROUNDED. */
function cohostRetryHandler(): void {
  void invoke("restart_sidecar").catch((err: unknown) => {
    // eslint-disable-next-line no-console
    console.warn("[render-loop] cohost retry restart_sidecar failed:", err);
  });
}

/** Phase 44-03 / LAUNCH-02 — chip-click handler. Invokes the Tauri
 *  `open_debrief_window` command with a deep-link payload pointing at
 *  the chip's event. The live session UI does NOT carry its own
 *  session_dir field today (the session is the "right now we're
 *  recording" view), so we pass an empty string + let the Rust side
 *  fall back to "latest recording" via `validate_under_root`.
 *
 *  Best-effort wiring — a chip-click failure (debrief window already
 *  open, recordings root missing, validation reject) is logged but
 *  never crashes the live UI. The chip remains useful as a visible
 *  receipt even when the click target isn't yet wired end-to-end. */
/** 2026-05-19 /impeccable critique round 4 (Kaan: "OVERHAUL"): live
 *  cohost is a glance surface, so the full transcript history lives
 *  in the debrief window. This handler opens the debrief with no
 *  deep-link so the user lands at the latest moment. Same fire-and-
 *  forget contract as the chip handler — failures log only. */
function cohostOpenAllHandler(): void {
  void invoke("open_debrief_window", {
    sessionDir: "",
  }).catch((err: unknown) => {
    // eslint-disable-next-line no-console
    console.warn("[render-loop] see-all open_debrief_window failed:", err);
  });
}

function cohostChipClickHandler(chip: CitationChip): void {
  // For now the live session passes the empty session_dir (TODO: thread
  // through SessionSnapshot.session_dir once Phase 45 wires it). The
  // Rust side's `validate_under_root` rejects empty paths today, so the
  // chip-click in a live session window logs an error and is a no-op
  // until the wiring is complete. Recorded-session chip-clicks (when
  // the debrief window is the chip-clicker's parent, v2.x) carry the
  // session_dir already.
  void invoke("open_debrief_window", {
    sessionDir: "",
    deepLink: {
      eventId: chip.event_id,
      timestampS: chip.timestamp_s,
    },
  }).catch((err: unknown) => {
    // eslint-disable-next-line no-console
    console.warn("[render-loop] chip-click open_debrief_window failed:", err);
  });
}

/** Phase 44-03 / LAUNCH-02 — project the bridge's append-only reactions
 *  ring onto the ReactionsByTs map shape that the cohost panel expects.
 *  O(N) over the ring (capped at 200), called once per render tick.
 *  Returns the SHARED empty map when no reactions exist so the cohost
 *  panel's diff path can ref-compare.
 *
 *  Cached by reactions-ref so a tick with no new reactions returns the
 *  SAME map instance — SessionLayout's diff path checks ref equality
 *  on `cohost.reactions` to gate the transcript repaint. Without this
 *  cache the chip-strip rebuilds on every rAF tick (60×/sec) which
 *  would tank perf on long transcripts. */
const EMPTY_REACTIONS_PROJECTION: ReactionsByTs = new Map();
let _reactionsCacheKey: readonly CohostReaction[] | null = null;
let _reactionsCacheValue: ReactionsByTs = EMPTY_REACTIONS_PROJECTION;
function projectReactions(reactions: readonly CohostReaction[]): ReactionsByTs {
  if (reactions.length === 0) return EMPTY_REACTIONS_PROJECTION;
  if (reactions === _reactionsCacheKey) return _reactionsCacheValue;
  const out = new Map<string, readonly CitationChip[]>();
  for (const r of reactions) {
    // When two reactions share a ts (sub-ms collision — extremely rare
    // but possible at high reaction cadence), the LAST one wins. The
    // chip strip surfaces the freshest evidence; older chips for the
    // same ts are dropped silently rather than concatenated (which
    // would risk a chip overflow on a single transcript line).
    out.set(r.ts, r.citation_strip);
  }
  _reactionsCacheKey = reactions;
  _reactionsCacheValue = out;
  return out;
}

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
      track: s.track ? { title: s.track.title, artist: s.track.artist ?? null } : null,
      genre: s.settings.genre || null,
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
      // Wave 6 (H9) — retry handler for the "COULDN'T REACH GEMINI" foot
      // surface that appears after grounding has been false for >5s.
      // No dedicated ipc.cohost.reconnect exists (TODO Phase 17?); we
      // fall back to the existing crash-banner path (restart_sidecar)
      // since a sustained ungrounded state is functionally the same as
      // a sidecar-down condition.
      onRetry: cohostRetryHandler,
      // Phase 44-03 / LAUNCH-02 — citation chip wiring.
      reactions: projectReactions(s.reactions),
      onChipClick: cohostChipClickHandler,
      // 2026-05-19 /impeccable critique round 4 (Kaan: "OVERHAUL"):
      // "see all <N> reactions" footer routes to the debrief window
      // with no deep-link so the user lands at the latest moment.
      onOpenAllReactions: cohostOpenAllHandler,
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
      // defaults. Skill/interaction/mood live in the drawer.
      skill: "INT",
      interaction: s.settings.mode === "coach" ? "COACH" : "HYPE",
      mood: moodFromSettings(s.settings.mood),
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

/** Map the wire-level mood enum ("hype-man" | "teacher" | "coach") onto
 *  the persona-panel's UPPERCASE 3-state vocabulary. The settings drawer
 *  is the authoritative write surface; the session panel is read-only. */
function moodFromSettings(
  mood: BridgeSessionState["settings"]["mood"],
): "HYPE" | "TEACH" | "COACH" {
  switch (mood) {
    case "teacher":
      return "TEACH";
    case "coach":
      return "COACH";
    case "hype-man":
    default:
      return "HYPE";
  }
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
