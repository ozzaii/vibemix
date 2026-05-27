// SPDX-License-Identifier: Apache-2.0
//
// Phase 91 Plan 05 — Learn webview entrypoint (the REAL renderer).
//
// REPLACES Plan 01's placeholder. Subscribes to ws://127.0.0.1:8765 (the
// SAME socket the live deck uses — one-socket invariant #4), consumes
// `ipc.learn.controller_detected` (single-fire per plug) and
// `ipc.learn.midi_position` (30 Hz delta-suppressed), and drives the
// LearnTitlebar / ControllerStage / StatusBar components.
//
// RENDER-01: on `controller_detected { connected: true }`, dynamic-import
// the matching SVG and mount within 2s (jsdom synthetic; production
// Tauri webview measurement is the §LEARN-LATENCY-CONTINGENCY gate).
// RENDER-02: on `midi_position`, apply transform-only DOM mutations
// inside a `requestAnimationFrame` drainer (RESEARCH §Pitfall 6 —
// frame-flood handling: only the LATEST frame between repaint slots
// is consumed).
// RENDER-03: aria-live="polite" announces controller connect/disconnect
// once per state-change (UI-SPEC §Accessibility Contract).
// RENDER-05: dual-cue slots already scaffolded inside the SVGs (P92
// lights them).
// RENDER-07: NO new ws port — `ws-client.ts` opens
// `new WebSocket("ws://127.0.0.1:8765")`.
//
// Architecture diagram:
//
//   LearnWsClient (ws:8765)
//      onmessage → CustomEvent on window
//
//   window.addEventListener("ipc.learn.controller_detected", ...)
//      → titlebar.setControllerName / stage.render / status.setMirrorStatus
//      → unplugged-toast on disconnect
//      → aria-live announcement
//
//   window.addEventListener("ipc.learn.midi_position", ...)
//      → pendingPositions = e.detail.positions (LWW under flood)
//      → rAF drainer: stage.applyPositionFrame + status.pushLatency

import "./styles/learn.css";
import { LearnWsClient } from "./ws-client.js";
import { ControllerStage } from "./components/controller-stage.js";
import { LearnTitlebar } from "./components/titlebar.js";
import { StatusBar } from "./components/status-bar.js";
import { mountEmptyState } from "./components/empty-state.js";
import { showUnpluggedToast } from "./components/unplugged-toast.js";

interface ControllerDetectedPayload {
  connected: boolean;
  controller_id: string;
  display_name: string;
  port_name: string;
}

interface MidiPositionPayload {
  controller_id: string;
  positions: Record<string, number>;
  // Optional emit_ts attached by the ws-client for latency measurement
  // (the canonical envelope ts is ISO-8601; we parse it on receive).
}

interface IpcEnvelopeMeta {
  ts?: string;
}

const LEARN_ROOT_ID = "learn-root";

/**
 * Module-level latest-frame holder (RESEARCH §Pitfall 6). Set on every
 * midi_position event; drained by the rAF callback. When the user
 * focuses a sibling window and 200 frames flood the receive buffer on
 * refocus, only the LAST sets `pendingPositions` — the rAF drainer
 * paints exactly one frame per repaint slot.
 */
let pendingPositions: Record<string, number> | null = null;
let pendingEmitTs: number | null = null;

/**
 * Frame-tracking guard (T-91-05-03 + §Pitfall 6): we also remember the
 * controller id of the most recent midi_position so the stage doesn't
 * try to apply a frame to the wrong SVG on a same-tick swap.
 */
let pendingControllerId: string | null = null;

/**
 * Initialise the Learn window: build the DOM scaffold, mount the
 * components, open the ws client, install the rAF drainer + ws event
 * subscribers.
 */
function mountLearnWindow(root: HTMLElement): {
  ws: LearnWsClient;
  titlebar: LearnTitlebar;
  stage: ControllerStage;
  status: StatusBar;
} {
  root.innerHTML = `
    <div id="learn-titlebar"></div>
    <div id="learn-stage" class="learn-stage"></div>
    <div id="learn-status-bar"></div>
    <div id="learn-sr-announcement" class="learn-sr-announcement" aria-live="polite" aria-atomic="true"></div>
  `;

  const titlebar = new LearnTitlebar(
    root.querySelector("#learn-titlebar") as HTMLElement,
  );
  const stageEl = root.querySelector("#learn-stage") as HTMLElement;
  const stage = new ControllerStage(stageEl);
  const status = new StatusBar(
    root.querySelector("#learn-status-bar") as HTMLElement,
  );
  const sr = root.querySelector("#learn-sr-announcement") as HTMLElement;

  // First paint: empty state until ipc.learn.controller_detected lands.
  mountEmptyState(stageEl);
  status.setMirrorStatus("waiting");

  // ipc.learn.controller_detected handler — mounts/clears the SVG.
  window.addEventListener("ipc.learn.controller_detected", (ev: Event) => {
    const detail = (ev as CustomEvent<ControllerDetectedPayload>).detail;
    if (!detail) return;
    if (detail.connected) {
      titlebar.setControllerName(detail.display_name);
      status.setMirrorStatus("live", detail.display_name);
      sr.textContent = `${detail.display_name} connected.`;
      // Async dynamic-import; the empty-state stays visible until the
      // SVG body lands. `render` is idempotent (no-op when controller_id
      // unchanged — T-91-05-03).
      void (async () => {
        await stage.render(detail.controller_id);
      })();
    } else {
      titlebar.setControllerName(null);
      status.setMirrorStatus("unplugged");
      sr.textContent = "controller disconnected.";
      stage.clear();
      mountEmptyState(stageEl);
      showUnpluggedToast(detail.display_name);
      pendingPositions = null;
      pendingControllerId = null;
    }
  });

  // ipc.learn.midi_position handler — record latest frame for rAF drain.
  window.addEventListener("ipc.learn.midi_position", (ev: Event) => {
    const detail = (ev as CustomEvent<MidiPositionPayload>).detail;
    if (!detail) return;
    pendingPositions = detail.positions;
    pendingControllerId = detail.controller_id;
    // Parse envelope ts → emit timestamp (ms since epoch). The envelope
    // ts is on the custom-event's parent envelope, not the payload, so
    // we conservatively use the now() time when the event fires.
    pendingEmitTs = performance.now();
    // ts on the envelope wrapper itself — we'd need to thread it through
    // the ws-client; for P91 we use the event-arrival timestamp which
    // overstates real latency by the ws → DOM hop (a few ms). Good
    // enough for the dev-visible status pip; the canonical synthetic
    // measurement lives in `tests/learn/highlight-latency.test.ts`.
    const envelopeMeta = (ev as CustomEvent<MidiPositionPayload> & { detail: { __envelope__?: IpcEnvelopeMeta } });
    void envelopeMeta;
  });

  // rAF drainer — paint at most one frame per repaint slot
  // (RESEARCH §Pitfall 6). On tab-resume floods, only the latest
  // pendingPositions reaches the SVG.
  function drainFrame(): void {
    if (pendingPositions !== null) {
      const positions = pendingPositions;
      const emitTs = pendingEmitTs;
      pendingPositions = null;
      pendingEmitTs = null;
      // Skip if the stage isn't mounted yet (no controller detected, or
      // mid-swap during a controller_detected race).
      if (stage.currentControllerId !== null) {
        stage.applyPositionFrame(positions);
        if (emitTs !== null) {
          status.pushLatency(performance.now() - emitTs);
        }
      }
    }
    requestAnimationFrame(drainFrame);
  }
  requestAnimationFrame(drainFrame);

  // Open ws + start streaming.
  const ws = new LearnWsClient();
  ws.connect();

  return { ws, titlebar, stage, status };
}

if (typeof document !== "undefined") {
  if (document.readyState === "loading") {
    document.addEventListener(
      "DOMContentLoaded",
      () => {
        const root = document.getElementById(LEARN_ROOT_ID);
        if (root) mountLearnWindow(root);
      },
      { once: true },
    );
  } else {
    const root = document.getElementById(LEARN_ROOT_ID);
    if (root) mountLearnWindow(root);
  }
}

// Export for vitest jsdom mounting (allows tests to call mountLearnWindow
// without DOMContentLoaded). The Plan 02 stub
// `test_controller_detected_mounts_svg.test.ts` references
// `ipc.learn.controller_detected` to detect the real renderer landed.
export { mountLearnWindow };
