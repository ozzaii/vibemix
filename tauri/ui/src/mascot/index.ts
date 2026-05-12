/* Phase 13 Plan 04 — Mascot webview entrypoint.
 *
 * Replaces the Plan 13-02 placeholder. This module is loaded by mascot.html
 * (the second Tauri webview). It:
 *
 *   1. Finds <canvas id="mascot-canvas"> in the DOM.
 *   2. Awaits loadMascotAssets() (manifest + character GLB + 20 animation
 *      GLBs, retargeted onto the character skeleton).
 *   3. Constructs MascotRenderer(canvas, assets).
 *   4. Initialises the state machine via initialMachineState(performance.now()).
 *   5. Boots to `idle_breathe` with a zero-blend (no source to fade from
 *      on the first frame).
 *   6. Starts a single requestAnimationFrame loop that:
 *      - Fires any pendingSwitch whose atTimestamp has passed.
 *      - Polls tickIdleTimeout → if "sleep" returned, dispatches a sleep
 *        request through the state machine.
 *      - Calls renderer.tick(deltaSeconds).
 *   7. Hooks window 'resize' → renderer.resize.
 *   8. In DEV builds only, exposes window.__mascot.requestState(state, opts)
 *      so Kaan can drive transitions from the browser DevTools. Plan 13-06
 *      replaces this with the real WS-bus subscription; production builds
 *      strip the global via Vite's `import.meta.env.DEV` tree-shake.
 *
 * NOT subscribed to the WS bus — that's Plan 13-06. This plan exposes a
 * clean public requestState API; the WS bridge will become the dominant
 * caller of that API in 13-06.
 */

import { Clock } from "three";

import { loadMascotAssets } from "./asset-loader.js";
import { MascotRenderer } from "./renderer.js";
import {
  applyTransition,
  initialMachineState,
  planTransition,
  tickIdleTimeout,
  type MachineState,
} from "./state-machine.js";
import type { MascotState, StateRequest, StateTrigger } from "./types.js";

const TAG = "[mascot]";

// ── DEV global surface (gated, stripped in production) ────────────────────

/**
 * Public DEV-only handle. Plan 13-06 replaces this with a WS-bus
 * subscription; until then, the global is the one and only entry point
 * for driving the mascot from outside index.ts.
 */
interface MascotDevHandle {
  /**
   * Drive a state transition. The state machine handles priority + beat-
   * lock; the renderer handles the crossfade.
   *
   * @param state The target MascotState.
   * @param opts Optional StateRequest fields. `trigger` defaults to
   *   "manual_fire" when not provided.
   */
  requestState: (state: MascotState, opts?: Partial<StateRequest>) => void;
  /** Read-only snapshot of the current MachineState for diagnostics. */
  getMachine: () => Readonly<MachineState>;
}

declare global {
  interface Window {
    __mascot?: MascotDevHandle;
  }
}

// ── Boot ──────────────────────────────────────────────────────────────────

async function boot(): Promise<void> {
  const canvas = document.getElementById("mascot-canvas");
  if (!(canvas instanceof HTMLCanvasElement)) {
    // Anti-slop discipline: no silent fallback. The mascot.html shell
    // must contain this canvas; if it doesn't, the build is broken and
    // we surface that loud.
    console.error(
      `${TAG} <canvas id="mascot-canvas"> missing from mascot.html — cannot mount renderer`,
    );
    return;
  }

  // Load the full bundle. This is the only true async cost on boot;
  // subsequent frames are sync rAF.
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

  // Initial state — performance.now() is the canonical webview timestamp;
  // it's monotonic + DOMHighResTimeStamp-compatible with requestAnimationFrame.
  let machine: MachineState = initialMachineState(performance.now());

  // Boot to idle_breathe with zero blend (no source action to fade from).
  renderer.crossFadeTo("idle_breathe", 0);

  // ── rAF loop ──────────────────────────────────────────────────────────
  // One clock.getDelta() per frame gives the mixer wall-clock seconds since
  // the previous frame, independent of frame rate.
  const clock = new Clock();

  function frame(): void {
    const now = performance.now();
    const dt = clock.getDelta();

    // Process any pending downbeat-scheduled switch.
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

    // Idle-timeout → sleep (CONTEXT Open Q 5, 300s in idle class).
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

  // ── Resize ────────────────────────────────────────────────────────────
  window.addEventListener("resize", () => {
    renderer.resize(window.innerWidth, window.innerHeight);
  });

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
        // schedule_for_downbeat → rAF loop fires it
        // deny → no visible effect, but caller sees plan.reason via getMachine()
        console.log(`${TAG} requestState`, request, "→", plan);
      },
      getMachine() {
        return machine;
      },
    };
    window.__mascot = handle;
    console.log(
      `${TAG} DEV mode — window.__mascot exposed: requestState(state, opts), getMachine()`,
    );
  }

  console.log(`${TAG} renderer mounted; boot → idle_breathe`);
}

// Three.js needs the DOM to find the canvas; wait for it.
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => {
    void boot();
  });} else {
  void boot();
}
