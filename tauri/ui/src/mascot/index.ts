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

import { Clock } from "three";

import { loadMascotAssets } from "./asset-loader.js";
import { dispatchEvent, type SnapshotSlice } from "./event-dispatcher.js";
import { MascotRenderer } from "./renderer.js";
import {
  applyTransition,
  initialMachineState,
  planTransition,
  tickIdleTimeout,
  type MachineState,
} from "./state-machine.js";
import type { MascotState, StateRequest, StateTrigger } from "./types.js";
import { connectMascotBus, type MascotBusClient } from "./ws-client.js";

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
      `${TAG} <canvas id="mascot-canvas"> missing from mascot.html — cannot mount renderer`,
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

  let machine: MachineState = initialMachineState(performance.now());
  renderer.crossFadeTo("idle_breathe", 0);

  // ── Current snapshot ref (state-reader for the dispatcher) ──────────────
  // Updated by every `type: "snapshot"` bus frame. Defaults pre-connect
  // keep beat-lock off until the sidecar's first snapshot arrives.
  const currentSnapshot: SnapshotSlice = {
    bpm: 0,
    bpm_confidence: 0,
    downbeat_phase: 0,
    mood: "hype-man",
  };

  // ── Pending followups (e.g., puff_particle → idle_breathe @500ms) ───────
  // Pure data — no setTimeout. The rAF loop polls this and fires when
  // `fireAt <= now`. Keeps the dispatcher pure AND lets the followup
  // honour priority + beat-lock just like any other transition.
  const followups: PendingFollowup[] = [];

  function handleMessage(message: unknown): void {
    const now = performance.now();

    // Snapshots are state-READERS — they update the dispatcher's view
    // of bpm/confidence/downbeat/mood. Snapshots do NOT trigger
    // transitions on their own (events do).
    if (
      message &&
      typeof message === "object" &&
      (message as { type?: unknown }).type === "snapshot"
    ) {
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
      currentSnapshot.bpm = bpm;
      currentSnapshot.bpm_confidence = conf;
      currentSnapshot.downbeat_phase = phase;
      currentSnapshot.mood = mood;
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
  const mockMode =
    import.meta.env?.DEV &&
    typeof window !== "undefined" &&
    new URLSearchParams(window.location.search).get("dev") === "mascot-mock";

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
    if (mockMode) {
      const msPerBar = (60 / MOCK_BPM) * 4 * 1000;
      const elapsed = (now - mockPhaseStart) % msPerBar;
      currentSnapshot.downbeat_phase = elapsed / msPerBar;
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

    renderer.tick(dt);
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);

  // ── Resize ──────────────────────────────────────────────────────────────
  window.addEventListener("resize", () => {
    renderer.resize(window.innerWidth, window.innerHeight);
  });

  // ── Teardown (best-effort; HMR-friendly) ───────────────────────────────
  window.addEventListener("beforeunload", () => {
    if (bus) bus.close();
    if (mockTimer !== null) clearInterval(mockTimer);
  });

  // ── DEV-only public API ─────────────────────────────────────────────────
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
    };
    window.__mascot = handle;
    // eslint-disable-next-line no-console
    console.log(
      `${TAG} DEV mode — window.__mascot exposed: requestState(state, opts), getMachine(); mockMode=${String(mockMode)}`,
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
