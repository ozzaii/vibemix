// SPDX-License-Identifier: Apache-2.0
//
// Phase 24 Plan 02 — overlay-highlight IPC consumer.
//
// Subscribes to ``ipc.session.overlay-highlight`` envelopes from the
// Python sidecar and invokes the Rust ``show_overlay_highlight``
// command. The Rust side does the AX lookup + WebviewWindow open +
// auto-close — the TS side is just the typed gateway.
//
// Wire-up (the consumer that wires this depends on whether overlay
// receivership lives in main.ts or in session/SessionLayout.ts — that's
// Plan 24-03's job. Plan 24-02 ships the standalone module that anyone
// can import and call `startOverlayHighlightListener()` on).
//
// VIS-02 (43-02) hover-glow scope note: this module is an IPC gateway,
// no DOM. The actual overlay ring (overlay.html + overlay-runtime.ts)
// is `pointer-events: none` and click-through at the OS level — there
// is no element to hover. The hover-glow sweep is correctly scoped to
// the session window's interactive components only.

import { invoke } from "@tauri-apps/api/core";

import { subscribeIpc } from "../ipc/client.js";
import type { VibemixIPCMessages } from "../ipc/messages.js";

/** Narrow the IpcMessage union to the overlay-highlight envelope. */
type OverlayHighlightMsg = Extract<
  VibemixIPCMessages,
  { type: "ipc.session.overlay-highlight" }
>;

/** Boot the overlay-highlight listener. Returns an unsubscribe fn.
 *
 *  Use:
 *    const off = await startOverlayHighlightListener();
 *    // ... later:
 *    off();
 *
 *  Failures (Rust invoke error, schema violation) are logged via
 *  console.warn — the overlay is a non-essential visual cue, so a
 *  miss never blocks the session. */
export async function startOverlayHighlightListener(): Promise<() => void> {
  const unlisten = await subscribeIpc<OverlayHighlightMsg>(
    "ipc.session.overlay-highlight",
    (msg) => {
      const { element_id, color, duration_ms } = msg.payload;
      // Tauri 2.x normalises Rust snake_case params to camelCase by default
      // on the JS side. The Rust signature is
      //   show_overlay_highlight(app, element_id: String, color: String,
      //                          duration_ms: u32)
      // so JS-side keys are elementId / color / durationMs.
      invoke("show_overlay_highlight", {
        elementId: element_id,
        color,
        durationMs: duration_ms,
      }).catch((err: unknown) => {
        // eslint-disable-next-line no-console
        console.warn("[overlay-highlight] invoke failed:", err);
      });
    },
  );
  return unlisten;
}
