/* Phase 11 Wave 2 — crash banner subscription.
 *
 * Subscribes to the Rust shell's lifecycle events:
 *   - "sidecar-crashed"  fired after 4th consecutive non-zero exit
 *   - "sidecar-state"    fired on every spawn / restart attempt / clean exit
 *
 * When the crash banner is visible, the Restart button invokes the
 * `restart_sidecar` Tauri command. Wave 2 stub kills the (already-dead)
 * child and emits a state event so the user gets feedback even though
 * the supervisor loop has exited; Wave 4 wires the actual respawn path.
 *
 * Anti-pattern guard: this file MUST NOT open its own WebSocket. The
 * webview is forbidden from talking to localhost:8765 directly — the
 * Rust shell is the single client.
 */

import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";

interface CrashPayload {
  restart_count: number;
  last_error: string;
}

interface StatePayload {
  state: "running" | "restarting" | "stopped";
  attempt?: number;
}

export function initCrashBanner(): void {
  const banner = document.getElementById("crash-banner");
  const errLine = document.getElementById("crash-error-line");
  const restartBtn = document.getElementById("crash-restart") as HTMLButtonElement | null;

  if (!banner || !errLine || !restartBtn) {
    // Wave 2 placeholder DOM is missing — defensive guard so Wave 3
    // re-arranging the DOM doesn't crash the module on load.
    console.warn("[crash-banner] DOM elements missing — banner inert");
    return;
  }

  listen<CrashPayload>("sidecar-crashed", (event) => {
    errLine.textContent = event.payload.last_error || "(no error line captured)";
    banner.hidden = false;
  });

  listen<StatePayload>("sidecar-state", (event) => {
    if (event.payload.state === "running") {
      banner.hidden = true;
    }
  });

  restartBtn.addEventListener("click", async () => {
    restartBtn.disabled = true;
    const originalLabel = restartBtn.textContent ?? "[ Restart ]";
    restartBtn.textContent = "WORKING…";
    try {
      await invoke("restart_sidecar");
    } catch (err) {
      errLine.textContent = `restart failed: ${err}`;
    } finally {
      restartBtn.disabled = false;
      restartBtn.textContent = originalLabel;
    }
  });
}
