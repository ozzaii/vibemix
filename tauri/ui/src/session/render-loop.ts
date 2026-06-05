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

import { emitIpc } from "../ipc/client.js";
import { renderSessionFrame, type Mounted } from "./SessionLayout.js";
import type {
  SessionState as LayoutSessionState,
} from "./SessionLayout.js";
import { getSessionState, setSessionState } from "./state.js";
import type {
  CohostReaction,
  SessionState as BridgeSessionState,
} from "./state.js";
import { sendMute } from "./ws-bridge.js";
import type { ReactionsByTs } from "./cohost-model.js";
import type { CitationChip } from "./components/citation-strip.js";

let rafHandle: number | null = null;
let mountedRef: Mounted | null = null;
let modeChangeSeq = 0;

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

/** "The Deck Speaks" rebuild — the deck rail's mute control. Toggles the
 *  co-host mute over the same real channel the push-to-mute hotkey + status
 *  bar use (ipc.session.mute). sendMute flips SessionState optimistically so
 *  the button responds immediately; the sidecar ack remains authoritative. */
function cohostMuteHandler(): void {
  void sendMute(true).catch((err: unknown) => {
    // eslint-disable-next-line no-console
    console.warn("[render-loop] mute emitIpc failed:", err);
  });
}

/** SHIP-WIRE START-gate — Start the live session. The user pressed Start on
 *  the armed deck. Flip the run-state optimistically (the SessionLayout click
 *  handler already flipped data-runstate locally for instant feedback; this
 *  propagates it into the singleton so the next render frame stays running)
 *  then fire ipc.session.start. No ack: the BACKEND-BOOT lane's
 *  register_handler("ipc.session.start", _on_session_start) owns the model
 *  load + silent pre-warm + capture lifecycle in __main__.py, and reflects the
 *  authoritative run-state on its next ipc.session.snapshot. Fire-and-forget;
 *  an emit failure logs only (the optimistic deck stays running). */
function sessionStartHandler(): void {
  if (getSessionState().runState === "running") return;
  setSessionState({ runState: "running" });
  void emitIpc("ipc.session.start", {}).catch((err: unknown) => {
    // eslint-disable-next-line no-console
    console.warn("[render-loop] session.start emitIpc failed:", err);
  });
}

/** SHIP-WIRE START-gate — Stop the live session, returning to the armed (idle)
 *  deck. Same optimistic-then-emit shape as start; the backend
 *  register_handler("ipc.session.stop", _on_session_stop) ends capture and
 *  parks/unloads the model. Fire-and-forget; failure logs only. */
function sessionStopHandler(): void {
  if (getSessionState().runState !== "running") return;
  setSessionState({ runState: "armed" });
  void emitIpc("ipc.session.stop", {}).catch((err: unknown) => {
    // eslint-disable-next-line no-console
    console.warn("[render-loop] session.stop emitIpc failed:", err);
  });
}

/** Compact status-row recovery. The deck row stays presentational; this
 *  handler is the single bridge from a down input label to the sidecar probe
 *  that emits a fresh ipc.status.tick. */
function statusRecheckHandler(
  component: "livekit" | "gemini" | "midi" | "screen",
): void {
  void emitIpc("ipc.status.recheck", { component }).catch((err: unknown) => {
    // eslint-disable-next-line no-console
    console.warn("[render-loop] status recheck emitIpc failed:", err);
  });
}

function openModeSurface(mode: "cohost" | "learn" | "build" | "debrief"): Promise<unknown> {
  if (mode === "learn") return invoke("open_learn_window");
  if (mode === "build") return invoke("open_library_window");
  if (mode === "debrief") return invoke("open_debrief_window", { sessionDir: "" });
  return Promise.resolve();
}

/** Deck persona cycle. Advances the Sven mode HYPE -> COACH -> TEACH -> HYPE
 *  through the `lens` field the live brain reads. Reads live state at click
 *  time (not a captured value), so repeated taps walk the cycle correctly.
 *  Fire-and-forget; the readout reflects the echoed ipc.settings.state on
 *  the next frame, matching the settings drawer's optimistic pattern. */
const LENS_CYCLE = ["hype", "critique", "tutor"] as const;
function cohostLensCycleHandler(): void {
  const cur = getSessionState().settings.lens;
  const idx = LENS_CYCLE.indexOf(cur as (typeof LENS_CYCLE)[number]);
  const next = LENS_CYCLE[(idx + 1) % LENS_CYCLE.length];
  void emitIpc("ipc.settings.set", { field: "lens", value: next }).catch(
    (err: unknown) => {
      // eslint-disable-next-line no-console
      console.warn("[render-loop] lens cycle emitIpc failed:", err);
    },
  );
}

/** Phase 97 / ONBOARD-01 — mode picker handler. Writes the new mode into
 *  the singleton SessionState IMMEDIATELY (the optimistic-repaint half
 *  was already done by the picker's click handler flipping data-active;
 *  this propagates the change into state so subsequent re-renders read
 *  the new mode). Surface modes open their matching windows first; only after
 *  that succeeds does the handler fire `ipc.session.set_mode` so the sidecar
 *  persists. If the owning window fails to open, revert the optimistic local
 *  mode instead of leaving the app claiming a surface the user cannot see. */
function modeChangeHandler(mode: "cohost" | "learn" | "build" | "debrief"): void {
  const previousMode = getSessionState().mode ?? "cohost";
  if (mode === previousMode) return;
  const seq = ++modeChangeSeq;
  // 1. Local state write — keeps the singleton in sync with the DOM.
  setSessionState({ mode });
  void (async () => {
    try {
      await openModeSurface(mode);
    } catch (err: unknown) {
      if (seq !== modeChangeSeq || getSessionState().mode !== mode) return;
      // eslint-disable-next-line no-console
      console.warn("[render-loop] mode surface open failed:", err);
      setSessionState({ mode: previousMode });
      return;
    }

    if (seq !== modeChangeSeq || getSessionState().mode !== mode) return;

    // 2. Wire envelope — sidecar persists via ConfigStore.extra under
    //    "session.mode" so the next launch boots into the last-picked mode.
    try {
      await emitIpc("ipc.session.set_mode", { mode });
    } catch (err: unknown) {
      // eslint-disable-next-line no-console
      console.warn("[render-loop] set_mode emitIpc failed:", err);
    }
  })();
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
  // Rust command resolves an empty session_dir to the latest validated
  // recording directory, so live chips and the "see all" button share
  // the same current-session fallback.
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
 *  ring onto the ReactionsByTs map shape that SessionLayout expects.
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

    // Refresh the SET-elapsed string (hero deck). Seed sessionStartMs on
    // the first tick where it's null (proxy for session start); the mock
    // pre-seeds an offset so the dev demo reads mid-set. Distinct from the
    // wall clock so the deck shows how long the set has run.
    let startMs = getSessionState().sessionStartMs;
    if (startMs == null) {
      startMs = Date.now();
      setSessionState({ sessionStartMs: startMs });
    }
    const elapsed = formatElapsed(Date.now() - startMs);
    if (getSessionState().elapsedText !== elapsed) {
      setSessionState({ elapsedText: elapsed });
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
      // Hero deck shows SET ELAPSED, not the time of day (that's the
      // titlebar clock). Fall back to clockText for older snapshots /
      // tests that don't populate elapsedText.
      clock: s.elapsedText ?? s.clockText,
      bpm: s.bpm,
      key: s.track?.key ?? null,
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
      // Wave 6 (H9) — retry handler for the "AI SERVICE OFFLINE" foot
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
      // "The Deck Speaks" — deck rail mute control → ipc.session.mute.
      onMute: cohostMuteHandler,
    },
    status: {
      livekit: s.status.livekit,
      gemini: s.status.gemini,
      midi: s.status.midi,
      screen: s.status.screen,
      voice: s.status.voice ?? null,
      captureDevice: s.status.captureDevice ?? null,
      midiActivity: s.status.midiActivity ?? null,
      midiDevice: s.status.midiDevice ?? null,
      muted: s.muted,
      hotkey: formatHotkey(s.settings.push_to_mute_hotkey),
      onRecheck: statusRecheckHandler,
      errors: {},
    },
    claimPolicy: s.claimPolicy,
    persona: {
      // 2026-05-25 — the deck is now a read-only glanceable mirror; the
      // settings drawer owns every write. Skill round-trips through
      // ipc.settings.state, so the deck reflects the persisted value
      // instead of the prior hardcoded "INT".
      skill: skillFromSettings(s.settings.skill),
      // Persona is one axis, and `lens` is the field the live brain actually
      // reads (hype -> hype mode, critique/tutor -> coach mode). Derive the
      // deck readout from lens, not the now writer-less `mode`, so the deck
      // never shows a persona the co-host is not running.
      interaction: s.settings.lens === "hype" ? "HYPE" : "COACH",
      mood: lensFromSettings(s.settings.lens),
      voice: s.settings.voice,
      genre: s.settings.genre,
      onCycleMood: cohostLensCycleHandler,
    },
    output: {
      device: s.settings.output_device_id ?? "AUTO",
      profile: s.settings.output_profile === "spk" ? "SPK" : "HP",
    },
    // Phase 97 / ONBOARD-01 — top-level mode + click handler. Mode
    // defaults to "cohost" when undefined (mock / older snapshots) so
    // the picker always lights a segment. The click handler does the
    // local setSessionState + emits ipc.session.set_mode.
    mode: s.mode ?? "cohost",
    onModeChange: modeChangeHandler,
    // SHIP-WIRE START-gate — run-state + Start/Stop handlers. Projection
    // defaults to "running" when the bridge omits runState so existing
    // fixtures/snapshots keep the live deck; the real boot sets runState
    // "armed" in makeDefault(), which drives the idle Start gate here.
    runState: s.runState ?? "running",
    onStart: sessionStartHandler,
    onStop: sessionStopHandler,
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
/** Map the wire-level skill enum ("beginner" | "intermediate" | "pro") onto
 *  the deck's compact 3-state vocabulary (BEG / INT / PRO). The settings
 *  drawer is the authoritative write surface; the deck is read-only. */
function skillFromSettings(
  skill: BridgeSessionState["settings"]["skill"],
): "BEG" | "INT" | "PRO" {
  switch (skill) {
    case "beginner":
      return "BEG";
    case "pro":
      return "PRO";
    case "intermediate":
    default:
      return "INT";
  }
}

function lensFromSettings(
  lens: BridgeSessionState["settings"]["lens"],
): "HYPE" | "TEACH" | "COACH" {
  switch (lens) {
    case "tutor":
      return "TEACH";
    case "critique":
      return "COACH";
    case "hype":
    default:
      return "HYPE";
  }
}

function sysFromStatuses(
  gemini: BridgeSessionState["status"]["gemini"],
  screen: BridgeSessionState["status"]["screen"],
): "ok" | "down" | "off" {
  if (gemini === "down") return "down";
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

/** Format a positive elapsed-ms span as HH:MM:SS (zero-padded, tabular).
 *  Caps at 99:59:59 so a left-running window never overflows the display.
 *  Negative spans (clock skew / future seed) clamp to 0. */
function formatElapsed(ms: number): string {
  const totalSec = Math.max(0, Math.floor(ms / 1000));
  const hh = Math.min(99, Math.floor(totalSec / 3600));
  const mm = Math.floor((totalSec % 3600) / 60);
  const ss = totalSec % 60;
  const p = (n: number): string => n.toString().padStart(2, "0");
  return `${p(hh)}:${p(mm)}:${p(ss)}`;
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
  cohostMuteHandler,
  modeChangeHandler,
  statusRecheckHandler,
  formatHotkey,
  formatWallClock,
  formatElapsed,
  trackFrameTime,
};
