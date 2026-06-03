/* tray-mood.ts — bridges the system-tray mood selection into the sidecar.
 *
 * 2026-05-24 release-blocker fix (bug 3 — "Coach/Hype mode switch is
 * unresponsive"). The Rust tray (tauri/src-tauri/src/tray.rs) emits a Tauri
 * event `tray-set-mood` carrying the wire-level mood string
 * ("hype-man" | "teacher" | "coach") when the user picks a mood from the
 * tray menu. Until now NOTHING in the webview listened for that event, so
 * the tray menu was a dead control.
 *
 * This module subscribes to `tray-set-mood` and forwards the selection
 * down the SAME path the in-app mascot-group mood pills use:
 *   emitIpc('ipc.settings.set', { field: 'mood', value })
 * The sidecar persists it and broadcasts `ipc.settings.state`, which the
 * ws-bridge writes back into SessionState — so every mood surface (deck
 * persona rocker, drawer, mascot overlay) reflects the change on the next
 * tick. No local DOM mutation needed; the round-trip is the single source
 * of truth (mirrors mascot-group.ts applyMoodChange).
 */

import { emitIpc } from "../ipc/client.js";
import { listenTauri } from "../tauri-runtime.js";
import type { MascotMood } from "./state.js";

const VALID_MOODS: readonly MascotMood[] = ["hype-man", "teacher", "coach"];

function isMood(value: unknown): value is MascotMood {
  return (
    typeof value === "string" &&
    (VALID_MOODS as readonly string[]).includes(value)
  );
}

/** Subscribe to the tray's `tray-set-mood` event and forward the choice to
 *  the sidecar. Returns an unsubscribe fn the session router calls on
 *  teardown. Tolerant of a non-Tauri environment (listen rejects) — the
 *  failure is logged and an inert unsubscribe is returned. */
export async function installTrayMoodListener(): Promise<() => void> {
  try {
    const unlisten = await listenTauri<string>("tray-set-mood", (event) => {
      const mood = event.payload;
      if (!isMood(mood)) {
        // Defensive: a future/out-of-sync tray build could emit an unknown
        // string; drop it rather than poisoning the settings write.
        // eslint-disable-next-line no-console
        console.warn("[tray-mood] ignoring unknown mood payload:", mood);
        return;
      }
      void emitIpc("ipc.settings.set", { field: "mood", value: mood }).catch(
        (err: unknown) => {
          // eslint-disable-next-line no-console
          console.warn("[tray-mood] ipc.settings.set failed:", err);
        },
      );
    });
    return unlisten;
  } catch (err) {
    // eslint-disable-next-line no-console
    console.warn("[tray-mood] listen(tray-set-mood) failed:", err);
    return () => {};
  }
}
