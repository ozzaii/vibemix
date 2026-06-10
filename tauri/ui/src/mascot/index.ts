/* Phase 13 Plan 06 — Mascot webview entrypoint (replaces Plan 13-04 stub).
 *
 * Boots the renderer + state machine (carried forward from 13-04) AND
 * wires the WS-bus subscription + event-dispatcher (new in 13-06).
 *
 * Flow per boot:
 *   1. Find <canvas id="mascot-canvas"> in the DOM.
 *   2. loadMascotAssets() (manifest + character GLB + 20 animation GLBs).
 *   3. Construct MascotRenderer(canvas, assets).
 *   4. initialMachineState(performance.now()).
 *   5. crossFadeTo("idle_breathe", 0) — boot pose.
 *   6. connectMascotBus("ws://127.0.0.1:8765") — direct WS subscription
 *      per CONTEXT.md Area 6. Snapshots update a local currentSnapshot
 *      ref (state-reader, not state-writer). Events go through
 *      dispatchEvent → planTransition → renderer.crossFadeTo.
 *   7. Start the rAF loop:
 *      - Fire pendingSwitch when its atTimestamp lands.
 *      - tickIdleTimeout → sleep after 5min idle (Plan 13-04 forward).
 *      - Process pending followups whose afterMs elapsed since dispatch.
 *      - renderer.tick(deltaSeconds).
 *   8. Window resize → renderer.resize.
 *   9. DEV: window.__mascot.requestState(state, opts) is preserved from
 *      13-04 so manual driving still works. Plan 13-06 layers the real
 *      WS subscription on top.
 *  10. DEV `?dev=mascot-mock` URL: SKIP connectMascotBus, install a
 *      deterministic event-injection harness (every 3s fires one event
 *      from the full taxonomy cycle) plus a synthetic snapshot with
 *      bpm=128/confidence=0.85 and a ramping downbeat_phase.
 */

import { Clock, Color } from "three";

import "./chrome.css";
import { loadMascotAssets } from "./asset-loader.js";
import { dispatchEvent, type SnapshotSlice } from "./event-dispatcher.js";
import {
  FocusLayer,
  type ControlRectPayload,
  type FocusableOrganism,
  type TeachingFocusPayload,
} from "./focus-layer.js";
import {
  MOOD_PROFILES,
  getCurrentMood,
  setCurrentMood,
} from "./mood.js";
import { selectReactionIntent } from "./reaction-intent.js";
import { MascotRenderer } from "./renderer.js";
import { isSnapshotFrame } from "./snapshot-frame.js";
import {
  applyTransition,
  initialMachineState,
  planTransition,
  tickIdleTimeout,
  type MachineState,
} from "./state-machine.js";
import { STATE_CLASS } from "./types.js";
import type { MascotState, StateRequest, StateTrigger } from "./types.js";
import { connectMascotBus, type MascotBusClient } from "./ws-client.js";

type MoodName = "hype-man" | "teacher" | "coach";

const TAG = "[mascot]";

// ── Tuning ────────────────────────────────────────────────────────────────

/** DEV-mode warning threshold for dispatch latency. CONTEXT.md Area 6
 *  budget: total <100ms; we warn at 50ms to leave headroom for crossFade
 *  scheduling + the renderer's own per-frame work. */
const DISPATCH_SLOW_MS = 50;

/** Mock harness cycle: one event every 3s. */
const MOCK_EVENT_INTERVAL_MS = 3000;

/** Mock BPM + confidence for the harness — high enough to exercise beat-lock. */
const MOCK_BPM = 128;
const MOCK_BPM_CONFIDENCE = 0.85;

// ── DEV global surface (gated, stripped in production) ────────────────────

interface MascotDevHandle {
  requestState: (state: MascotState, opts?: Partial<StateRequest>) => void;
  getMachine: () => Readonly<MachineState>;
  /**
   * Plan 13-07 — drive a mood swap (puff + lighting + idle_default
   * transition). Plan 13-06 will call the same handler from the WS bus
   * `ipc.mascot.mood_change` message handler.
   */
  setMood: (mood: MoodName) => void;
  /** Current cached mood (mirror of canonical sidecar mood). */
  getMood: () => MoodName;
}

declare global {
  interface Window {
    __mascot?: MascotDevHandle;
  }
}

// ── Followup queue ────────────────────────────────────────────────────────

interface PendingFollowup {
  state: MascotState;
  fireAt: number;
  trigger: StateTrigger;
}

// ── Boot ──────────────────────────────────────────────────────────────────

async function boot(): Promise<void> {
  const canvas = document.getElementById("mascot-canvas");
  if (!(canvas instanceof HTMLCanvasElement)) {
    console.error(
      `${TAG} <canvas id="mascot-canvas"> missing from mascot.html: cannot mount renderer`,
    );
    return;
  }

  let assets;
  try {
    assets = await loadMascotAssets();
  } catch (err) {
    console.error(`${TAG} loadMascotAssets failed:`, err);
    return;
  }
  console.log(
    `${TAG} loaded ${assets.clips.size} animation clips from ${assets.manifest.animations.length} GLBs`,
  );

  const renderer = new MascotRenderer(canvas, assets);

  // ── Teaching-focus layer ───────────────────────────────────────────────
  // Routes ipc.learn.control_rect (registry) + ipc.learn.teaching_focus
  // (dissolve→stream→reform) into the particle organism. The organism is
  // driven through a thin adapter over the renderer's passthrough methods so
  // the FocusLayer stays WebGL-free + testable. Grounding: the organism
  // animates ONLY on a real teaching_focus event.
  const focusLayer = new FocusLayer();
  const focusOrganism: FocusableOrganism = {
    focusAt: (target, nowMs) => renderer.focusOrganismAt(target, nowMs),
    reform: (nowMs) => renderer.reformOrganism(nowMs),
  };

  // TEMP 2026-05-12 — write renderer debug snapshot to the diag overlay
  // so we can see camera framing + material binding without devtools.
  const diag = document.getElementById("mascot-diag");
  if (diag) {
    try {
      diag.textContent =
        `clips=${assets.clips.size} ${renderer.getDebugSnapshot()}`;
    } catch (err) {
      diag.textContent = `getDebugSnapshot threw: ${String(err)}`;
    }
  }

  let machine: MachineState = initialMachineState(performance.now());
  renderer.crossFadeTo("idle_breathe", 0);

  // ── Drag-to-move ───────────────────────────────────────────────────────
  // Tauri's `data-tauri-drag-region` HTML attribute is unreliable on
  // macOS transparent + decorations:false windows. Falling back to the
  // explicit JS API which always works on macOS. Right-click bypasses
  // (reserved for future context menu).
  void (async () => {
    try {
      const mod = await import("@tauri-apps/api/window");
      const tauriWin = mod.getCurrentWindow();
      console.log(`${TAG} drag handler attached on document`);
      document.addEventListener("mousedown", (ev) => {
        const me = ev as MouseEvent;
        if (me.button !== 0) return;              // left-click only
        const target = me.target as HTMLElement | null;
        if (target?.closest("[data-no-drag]")) return;
        // Don't preventDefault — let webview see the click. startDragging
        // doesn't need it.
        tauriWin.startDragging().catch((e: unknown) =>
          console.warn(`${TAG} startDragging() rejected:`, e),
        );
      });
    } catch (err) {
      console.warn(`${TAG} drag handler unavailable (likely test/browser):`, err);
    }
  })();

  // ── Current snapshot ref (state-reader for the dispatcher) ──────────────
  // Updated by every `type: "snapshot"` bus frame. Defaults pre-connect
  // keep beat-lock off until the sidecar's first snapshot arrives.
  const currentSnapshot: SnapshotSlice = {
    bpm: 0,
    bpm_confidence: 0,
    downbeat_phase: 0,
    mood: "hype-man",
    music: 0,
    voice: 0,
  };

  // ── Pending followups (e.g., puff_particle → idle_breathe @500ms) ───────
  // Pure data — no setTimeout. The rAF loop polls this and fires when
  // `fireAt <= now`. Keeps the dispatcher pure AND lets the followup
  // honour priority + beat-lock just like any other transition.
  const followups: PendingFollowup[] = [];
  let lastReactionIntentSeq = 0;

  function settleStateAfterReaction(prior: MascotState): MascotState {
    const priorClass = STATE_CLASS[prior];
    if (priorClass === "idle" || priorClass === "dance") return prior;
    return currentSnapshot.music >= 0.11
      ? "idle_bop_to_beat_energetic"
      : "idle_breathe";
  }

  function handleMessage(message: unknown): void {
    const now = performance.now();

    // Typed ipc.learn.* envelopes carry a `type` string; the live 30Hz
    // mascot frame is FLAT — no `type` key (see snapshot-frame.ts).
    // Route the two teaching-focus envelopes
    // BEFORE the snapshot branch — they drive the particle organism's focus
    // mechanic (control_rect registers a screen rect; teaching_focus fires the
    // dissolve→stream→reform). Grounding: no organism motion without one of
    // these real events.
    if (message && typeof message === "object") {
      const envType = (message as { type?: unknown }).type;
      if (envType === "ipc.learn.control_rect") {
        const payload = (message as { payload?: ControlRectPayload }).payload;
        if (payload) focusLayer.setControlRect(payload);
        return;
      }
      if (envType === "ipc.learn.teaching_focus") {
        const payload = (message as { payload?: TeachingFocusPayload }).payload;
        if (payload) {
          focusLayer.onTeachingFocus(
            payload,
            focusOrganism,
            (cx, cy) => renderer.screenToWorld(cx, cy),
            now,
          );
        }
        return;
      }
    }

    // Snapshots are state-READERS — they update the dispatcher's view
    // of bpm/confidence/downbeat/mood. Snapshots do NOT trigger
    // transitions on their own (events do).
    if (isSnapshotFrame(message)) {
      const m = message as Record<string, unknown>;
      const bpm = typeof m.bpm === "number" ? m.bpm : currentSnapshot.bpm;
      const conf =
        typeof m.bpm_confidence === "number"
          ? m.bpm_confidence
          : currentSnapshot.bpm_confidence;
      const phase =
        typeof m.downbeat_phase === "number"
          ? m.downbeat_phase
          : currentSnapshot.downbeat_phase;
      const mood = typeof m.mood === "string" ? m.mood : currentSnapshot.mood;
      // Phase 56 / LIVE-05a: music/voice arrive as FLAT floats on the live
      // ws frame (levels.snapshot() broadcasts top-level numbers). Read them
      // off the same flat frame; default to the prior value when absent.
      const music =
        typeof m.music === "number" ? m.music : currentSnapshot.music;
      const voice =
        typeof m.voice === "number" ? m.voice : currentSnapshot.voice;
      currentSnapshot.bpm = bpm;
      currentSnapshot.bpm_confidence = conf;
      currentSnapshot.downbeat_phase = phase;
      currentSnapshot.mood = mood;
      currentSnapshot.music = music;
      currentSnapshot.voice = voice;
      const reaction = selectReactionIntent(message, lastReactionIntentSeq);
      if (reaction) {
        lastReactionIntentSeq = reaction.seq;
        const settleState = settleStateAfterReaction(machine.current);
        const plan = {
          action: "switch_now" as const,
          target: reaction.state,
          blendMs: 180,
          reason: "reaction_intent",
        };
        machine = applyTransition(machine, plan, now);
        renderer.crossFadeTo(reaction.state, plan.blendMs);
        followups.push({
          state: settleState,
          fireAt: now + 800,
          trigger: "manual_fire",
        });
      }
      return;
    }

    // Anything else → dispatch.
    const t0 = import.meta.env?.DEV ? performance.now() : 0;
    const result = dispatchEvent(machine, message, now, currentSnapshot);
    if (import.meta.env?.DEV) {
      const dt = performance.now() - t0;
      if (dt > DISPATCH_SLOW_MS) {
        // eslint-disable-next-line no-console
        console.warn(`${TAG} dispatch slow: ${dt.toFixed(1)}ms`);
      }
    }
    if (!result) return;

    // Apply the plan's machine update.
    machine = result.machine;
    if (result.plan.action === "switch_now" && result.plan.target) {
      renderer.crossFadeTo(result.plan.target, result.plan.blendMs);
    }
    // schedule_for_downbeat → rAF loop fires pendingSwitch when timestamp lands.

    if (result.followup) {
      followups.push({
        state: result.followup.state,
        fireAt: now + result.followup.afterMs,
        // The followup's trigger label may differ from the event subtype
        // (e.g., react_surprised's followup carries "track_change" so
        // the audit log knows WHY the second leg fired).
        trigger:
          (result.followup.trigger as StateTrigger | undefined) ?? "manual_fire",
      });
    }
  }

  // ── Bus subscription (or mock harness in DEV) ──────────────────────────
  const devParam =
    typeof window !== "undefined"
      ? new URLSearchParams(window.location.search).get("dev")
      : null;
  const mockMode = import.meta.env?.DEV && devParam === "mascot-mock";
  // ?dev=organism-probe — a runtime VISUAL RECEIPT for the particle organism.
  // jsdom never compiles WebGL, so green vitest cannot prove the GLSL builds or
  // that the teaching-focus dissolve actually moves pixels. This probe drives
  // the organism through real focus/reform cycles (caused motion only, no free
  // animation) over a dark backdrop so a Playwright pixel-variance check can
  // assert the canvas is alive. Same grounding contract: every motion is caused.
  const probeMode = import.meta.env?.DEV && devParam === "organism-probe";

  let bus: MascotBusClient | null = null;
  let mockTimer: ReturnType<typeof setInterval> | null = null;
  let mockEventIndex = 0;
  let mockPhaseStart = performance.now();

  if (mockMode) {
    console.log(`${TAG} ?dev=mascot-mock → bus subscription SKIPPED; event harness active`);
    // Synthesise snapshot: bpm/conf fixed, downbeat_phase ramps 0..1 every bar.
    currentSnapshot.bpm = MOCK_BPM;
    currentSnapshot.bpm_confidence = MOCK_BPM_CONFIDENCE;
    currentSnapshot.mood = "hype-man";

    const mockEvents: unknown[] = [
      { type: "event", subtype: "TRACK_CHANGE", payload: { title: "Mock Track 01" } },
      { type: "event", subtype: "PHASE", payload: { from: "groove", to: "build" } },
      { type: "event", subtype: "PHASE", payload: { from: "build", to: "drop" } },
      { type: "event", subtype: "AI_GENERATING_REPLY", payload: {} },
      { type: "event", subtype: "AI_REPLY_DONE", payload: {} },
      { type: "event", subtype: "MANUAL", payload: {} },
      { type: "ipc.mascot.mood_change", payload: { mood: "teacher", previous_mood: "hype-man" } },
      { type: "ipc.mascot.mood_change", payload: { mood: "coach", previous_mood: "teacher" } },
      { type: "ipc.mascot.mood_change", payload: { mood: "hype-man", previous_mood: "coach" } },
      { type: "event", subtype: "PHASE", payload: { from: "drop", to: "silent" } },
    ];

    mockTimer = setInterval(() => {
      const event = mockEvents[mockEventIndex % mockEvents.length];
      mockEventIndex++;
      console.log(`${TAG} mock event:`, event);
      handleMessage(event);
    }, MOCK_EVENT_INTERVAL_MS);
  } else if (probeMode) {
    console.log(`${TAG} ?dev=organism-probe -> bus SKIPPED; organism focus/reform driver active`);
    // Dark backdrop so the additive-blended organism reads against the page.
    // mascot.html paints the page background on <html>, so set both.
    document.documentElement.style.background = "#0a0708";
    document.body.style.background = "#0a0708";
    // Synthetic transport so beat pulse + breath have live data (the frame loop
    // ramps downbeat_phase and oscillates voice while probeMode is on).
    currentSnapshot.bpm = MOCK_BPM;
    currentSnapshot.bpm_confidence = MOCK_BPM_CONFIDENCE;
    const screenToWorld = (cx: number, cy: number) => renderer.screenToWorld(cx, cy);
    // One caused cycle: register a control rect, dissolve+stream to it, hold,
    // then reform. The motion only ever comes from a real teaching_focus event.
    const driveFocusCycle = (): void => {
      const w = window.innerWidth || 320;
      const h = window.innerHeight || 400;
      focusLayer.setControlRect({ control_id: "probe", deck: "a", cx: w * 0.72, cy: h * 0.34 });
      focusLayer.onTeachingFocus(
        { control_id: "probe", deck: "a", band: "low", phase: "focus" },
        focusOrganism,
        screenToWorld,
        performance.now(),
      );
      console.log(`${TAG} [organism-probe] phase=focus`);
      window.setTimeout(() => {
        focusLayer.onTeachingFocus(
          { control_id: "probe", deck: "a", band: "low", phase: "reform" },
          focusOrganism,
          screenToWorld,
          performance.now(),
        );
        console.log(`${TAG} [organism-probe] phase=reform`);
      }, 1800);
    };
    driveFocusCycle();
    mockTimer = setInterval(driveFocusCycle, 3600);
  } else {
    bus = connectMascotBus("ws://127.0.0.1:8765");
    bus.addMessageListener(handleMessage);
    bus.addStatusListener((status) => {
      if (import.meta.env?.DEV) {
        // eslint-disable-next-line no-console
        console.log(`${TAG} bus status: ${status}`);
      }
      // CONTEXT.md Area 6: "mascot freezes in current state during
      // disconnect, resumes on reconnect; no error UI in the mascot
      // window itself" — so nothing to do here besides the dev log.
    });
  }

  // ── rAF loop ────────────────────────────────────────────────────────────
  const clock = new Clock();

  function frame(): void {
    const now = performance.now();
    const dt = clock.getDelta();

    // 1. Update synthetic downbeat_phase in mock mode (so beat-lock scheduler
    //    has live data). Real mode: snapshots from sidecar update this.
    if (mockMode || probeMode) {
      const msPerBar = (60 / MOCK_BPM) * 4 * 1000;
      const elapsed = (now - mockPhaseStart) % msPerBar;
      currentSnapshot.downbeat_phase = elapsed / msPerBar;
    }
    // Probe: oscillate the voice envelope so breath displacement is visible and
    // the pixel-variance receipt has continuous caused motion to measure.
    if (probeMode) {
      currentSnapshot.voice = 0.5 + 0.45 * Math.sin(now / 600);
    }

    // 2. Process any pending downbeat-scheduled switch.
    const pending = machine.pendingSwitch;
    if (pending && now >= pending.atTimestamp) {
      const target = pending.state;
      const blend = pending.blendMs;
      machine = applyTransition(
        machine,
        {
          action: "switch_now",
          target,
          blendMs: blend,
          reason: "downbeat_fire",
        },
        now,
      );
      renderer.crossFadeTo(target, blend);
    }

    // 3. Fire any followup whose delay has elapsed.
    if (followups.length > 0) {
      const ready: PendingFollowup[] = [];
      const remaining: PendingFollowup[] = [];
      for (const f of followups) {
        if (f.fireAt <= now) ready.push(f);
        else remaining.push(f);
      }
      // Replace in place (cheap — list is at most a handful).
      followups.length = 0;
      for (const f of remaining) followups.push(f);

      for (const f of ready) {
        // Re-enter through the state machine so priority + beat-lock apply.
        const stateClass = f.state; // typed by union
        const req: StateRequest = {
          state: stateClass,
          trigger: f.trigger,
          bpm: currentSnapshot.bpm,
          bpmConfidence: currentSnapshot.bpm_confidence,
          downbeatPhase: currentSnapshot.downbeat_phase,
        };
        const plan = planTransition(machine, req, now);
        machine = applyTransition(machine, plan, now);
        if (plan.action === "switch_now" && plan.target) {
          renderer.crossFadeTo(plan.target, plan.blendMs);
        }
      }
    }

    // 4. Idle-timeout → sleep (CONTEXT Open Q 5).
    const sleepTarget = tickIdleTimeout(machine, now);
    if (sleepTarget) {
      const plan = planTransition(
        machine,
        { state: sleepTarget, trigger: "idle_timeout" },
        now,
      );
      machine = applyTransition(machine, plan, now);
      if (plan.action === "switch_now" && plan.target) {
        renderer.crossFadeTo(plan.target, plan.blendMs);
      }
    }

    // 5. Plan 14-05 — repaint the bottom state caption only when
    //    machine.current has actually changed (free no-op on most frames).
    writeStateCaptionIfChanged();

    renderer.setOrganismSignals({
      voice: currentSnapshot.voice,
      beatPhase: currentSnapshot.downbeat_phase,
      bpmConfidence: currentSnapshot.bpm_confidence,
    });
    renderer.tick(dt);
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);

  // ── Resize ──────────────────────────────────────────────────────────────
  window.addEventListener("resize", () => {
    renderer.resize(window.innerWidth, window.innerHeight);
    writeOverlayCaption();
  });

  // ── Teardown (best-effort; HMR-friendly) ───────────────────────────────
  window.addEventListener("beforeunload", () => {
    if (bus) bus.close();
    if (mockTimer !== null) clearInterval(mockTimer);
  });

  // ── Plan 14-05 — overlay chrome captions ───────────────────────────────
  // The mascot.html wrapper carries two silkscreen labels in JetBrains
  // Mono var(--silk-40): a top dimension caption "OVERLAY · STICKY ·
  // ALL SPACES · {W}×{H}" (updates on mount + resize) and a bottom
  // state caption "{class} · {state}" (updates on every rAF tick, but
  // only when the machine.current name changes). Both are defensive
  // querySelector lookups — if mascot.html isn't carrying the v5 chrome
  // wrapper (e.g. unit-test fixtures with a bare canvas), they silently
  // no-op.

  /** Initial top-label dimension text seeded by mascot.html. */
  const overlayCaptionEl = document.querySelector<HTMLElement>(
    ".mascot-window__caption",
  );
  const stateCaptionEl = document.querySelector<HTMLElement>(
    ".mascot-window__state-caption",
  );

  function writeOverlayCaption(): void {
    if (!overlayCaptionEl) {
      console.debug(`${TAG} .mascot-window__caption not present: caption skipped`);
      return;
    }
    overlayCaptionEl.textContent =
      `OVERLAY · STICKY · ALL SPACES · ${window.innerWidth}×${window.innerHeight}`;
  }

  /** Format a MascotState into a "{class} · {state-without-class-prefix}"
   *  silkscreen label, matching the 14-UI-SPEC Copywriting Contract row
   *  "Mascot state label" (lowercase, "·" separator, dashes between words).
   *  Examples:
   *    idle_bop_to_beat_mellow  → "idle · bop-to-beat-mellow"
   *    talk_loop_energetic      → "talk · loop-energetic"
   *    react_drop               → "react · drop"
   *    puff_particle            → "effect · particle"
   *    sleep                    → "idle · sleep"
   */
  function formatStateLabel(state: MascotState): string {
    const cls = STATE_CLASS[state];
    // Strip the class-prefix from the state name if present (idle_breathe
    // → breathe, talk_loop_calm → loop_calm). Some states (celebrate,
    // sleep, locomotion_*, puff_particle) don't carry the class prefix
    // verbatim — fall back to the full state name then.
    const lower = state.toLowerCase();
    const stripped = lower.startsWith(`${cls}_`) ? lower.slice(cls.length + 1) : lower;
    return `${cls} · ${stripped.replace(/_/g, "-")}`;
  }

  let lastStateLabelWritten = "";
  function writeStateCaptionIfChanged(): void {
    if (!stateCaptionEl) return;
    const label = formatStateLabel(machine.current);
    if (label !== lastStateLabelWritten) {
      stateCaptionEl.textContent = label;
      lastStateLabelWritten = label;
    }
  }

  // Initial mount — seed both captions from current state.
  writeOverlayCaption();
  writeStateCaptionIfChanged();

  // ── Plan 13-07 — mood-change handler ─────────────────────────────────
  // Plan 13-06 will route ipc.mascot.mood_change → handleMoodChange(); for
  // now this is exposed via the DEV global only. The handler is the single
  // authoritative entry point for the four-step mood swap:
  //   1. setCurrentMood (local cache update)
  //   2. compute accent THREE.Color from --accent CSS var
  //   3. renderer.playParticlePuff (visual mask)
  //   4. renderer.setMoodLighting (ambient/key intensity shift)
  // The state machine independently transitions to `puff_particle` (Plan
  // 13-06 dispatcher), then to MOOD_PROFILES[mood].idle_default (the
  // mood-aware boot/return state) — we drive that here in step 5.

  /**
   * Resolve a CSS variable to a THREE.Color. Falls back to a literal hex
   * if the var is missing/empty (the variable may not be present in the
   * mascot window's reduced stylesheet at boot, or jsdom-stripped during
   * tests).
   *
   * Fallback hexes track the RESOLVED token values (--amber -> rose #FFA5DF
   * now that it aliases --brand; --silk #d6cfc7) from tokens.css, duplicated
   * here only as literal-string defaults for THREE.Color when CSS resolution
   * fails. They must match what the token resolves to, or the failure path
   * paints an off-brand color (the retired v5 amber was exactly that stale
   * mismatch). The coach branch uses a flat slate hex (#3d424c) directly
   * because --silk-40's alpha channel is dropped by THREE.Color (see
   * WR-02 in 14-REVIEW.md). tokens.css remains the single
   * source-of-truth for accent paint at the CSS layer; these three hex
   * literals (#FFA5DF, #d6cfc7, #3d424c) are the only hex literals
   * permitted outside tokens.css (audit gate).
   */
  function resolveCssColor(varName: string, fallback: string): Color {
    try {
      const root = document.documentElement;
      const raw = getComputedStyle(root).getPropertyValue(varName).trim();
      const value = raw.length > 0 ? raw : fallback;
      return new Color(value);
    } catch {
      return new Color(fallback);
    }
  }

  function handleMoodChange(mood: MoodName): void {
    // Step 1 — update local cache (throws on unknown; bus-side validator
    // catches it first, this is belt-and-braces).
    setCurrentMood(mood);
    const profile = MOOD_PROFILES[mood];

    // Step 2 — pick destination-mood tint.
    //   hype-man → rose (warm) — --amber aliases --brand
    //   teacher  → silk (cream-leaning) — --silk
    //   coach    → slate constant (distinct from teacher's silk)
    let color: Color;
    if (mood === "hype-man") {
      color = resolveCssColor("--amber", "#FFA5DF");
    } else if (mood === "teacher") {
      color = resolveCssColor("--silk", "#d6cfc7");
    } else {
      // coach — slate hex literal. WR-02 in 14-REVIEW.md flagged that
      // routing this through resolveCssColor("--silk-40", ...) collapses
      // to teacher's silk RGB at runtime: --silk-40 resolves to
      // rgba(214, 207, 199, 0.40), THREE.Color silently drops the alpha
      // channel and yields the same RGB as --silk (#d6cfc7), making
      // coach + teacher visually indistinguishable. The hex literal here
      // approximates --silk-40 composited over --void-2 (#05070b) while
      // preserving the intended slate cast — kept as a documented
      // audit-gate exception (alongside #FFA5DF and #d6cfc7).
      color = new Color("#3d424c");
    }

    // Steps 3 + 4 — fire visual.
    renderer.playParticlePuff(color);
    renderer.setMoodLighting(profile);

    // Step 5 — independently schedule the idle_default return. The
    // state-machine's normal `puff_particle` → idle handling lives in
    // Plan 13-06's dispatcher (which subscribes to mood_change too);
    // here we ensure that even without the dispatcher, the mascot ends
    // up in the new mood's idle_default after the puff. We request the
    // mood-aware idle state immediately — the puff effect masks the
    // crossfade visually.
    const now = performance.now();
    const request: StateRequest = {
      state: profile.idle_default,
      trigger: "mood_swap",
    };
    const plan = planTransition(machine, request, now);
    machine = applyTransition(machine, plan, now);
    if (plan.action === "switch_now" && plan.target) {
      renderer.crossFadeTo(plan.target, plan.blendMs);
    }
    console.log(`${TAG} mood change → ${mood} (idle_default=${profile.idle_default})`);
  }

  // ── DEV-only public API ───────────────────────────────────────────────
  // `import.meta.env.DEV` is replaced at build time by Vite — production
  // bundles see `false` and tree-shake the entire branch out.
  if (import.meta.env.DEV) {
    const handle: MascotDevHandle = {
      requestState(state, opts) {
        const trigger: StateTrigger = opts?.trigger ?? "manual_fire";
        const request: StateRequest = {
          state,
          trigger,
          bpm: opts?.bpm,
          bpmConfidence: opts?.bpmConfidence,
          downbeatPhase: opts?.downbeatPhase,
          blendMs: opts?.blendMs,
        };
        const now = performance.now();
        const plan = planTransition(machine, request, now);
        machine = applyTransition(machine, plan, now);
        if (plan.action === "switch_now" && plan.target) {
          renderer.crossFadeTo(plan.target, plan.blendMs);
        }
        // eslint-disable-next-line no-console
        console.log(`${TAG} requestState`, request, "→", plan);
      },
      getMachine() {
        return machine;
      },
      setMood(mood) {
        handleMoodChange(mood);
      },
      getMood() {
        return getCurrentMood();
      },
    };
    window.__mascot = handle;
    // eslint-disable-next-line no-console
    console.log(
      `${TAG} DEV mode: window.__mascot exposed: requestState, getMachine, setMood, getMood; mockMode=${String(mockMode)}`,
    );
  }

  console.log(
    `${TAG} renderer mounted; boot → idle_breathe; ${mockMode ? "mock harness" : "WS bus subscription"} active`,
  );
}

// Three.js needs the DOM to find the canvas; wait for it.
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => {
    void boot();
  });
} else {
  void boot();
}
