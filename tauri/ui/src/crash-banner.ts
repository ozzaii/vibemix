/* Phase 11 Wave 2 · crash banner subscription.
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
 * webview is forbidden from talking to localhost:8765 directly · the
 * Rust shell is the single client.
 */

import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";

interface CrashPayload {
  restart_count: number;
  last_error: string;
  // Set by the Rust watchdog when the sidecar exited with a fatal
  // sentinel (sidecar.rs treats exit 2/3 as do-not-retry). Lets the
  // banner route to a tailored message instead of the generic
  // "crashed after N restarts" string.
  reason?: "port-in-use" | "audio-device-missing" | string;
}

interface StatePayload {
  state: "running" | "restarting" | "stopped";
  attempt?: number;
}

let bannerEls: {
  banner: HTMLElement;
  errLine: HTMLElement;
  restartBtn: HTMLButtonElement;
} | null = null;

function reasonMessage(reason: string | undefined, fallback: string): string {
  switch (reason) {
    case "port-in-use":
      return "Another vibemix is already running. Quit it (Cmd+Q) and try again.";
    case "audio-device-missing":
      return "BlackHole 2ch audio driver isn't installed. Run `brew install blackhole-2ch` or visit existential.audio/blackhole.";
    case "session-mount-failed":
      return fallback || "Session UI failed to mount.";
    case "ws-unreachable":
      return "vibemix-core stopped responding. The Restart button below will relaunch it.";
    default:
      return fallback || "(no error line captured)";
  }
}

/** Programmatically surface a fatal-error banner from the webview side
 *  (e.g., routeSession threw, so the user would otherwise see a blank
 *  window). Routes through the same DOM as a Rust-emitted crash so the
 *  recovery affordances stay consistent. */
export function showFatalBanner(reason: string, detail?: string): void {
  if (!bannerEls) return;
  bannerEls.errLine.textContent = reasonMessage(reason, detail ?? "");
  bannerEls.banner.hidden = false;
}

export function initCrashBanner(): void {
  const banner = document.getElementById("crash-banner");
  const errLine = document.getElementById("crash-error-line");
  const restartBtn = document.getElementById("crash-restart") as HTMLButtonElement | null;

  if (!banner || !errLine || !restartBtn) {
    // Wave 2 placeholder DOM is missing · defensive guard so Wave 3
    // re-arranging the DOM doesn't crash the module on load.
    console.warn("[crash-banner] DOM elements missing · banner inert");
    return;
  }

  bannerEls = { banner, errLine, restartBtn };

  listen<CrashPayload>("sidecar-crashed", (event) => {
    const msg = reasonMessage(event.payload.reason, event.payload.last_error);
    errLine.textContent = msg;
    banner.hidden = false;
  });

  listen<StatePayload>("sidecar-state", (event) => {
    if (event.payload.state === "running") {
      banner.hidden = true;
    }
  });

  // ws-state: "unreachable" fires after ~30s of failed reconnects to
  // 127.0.0.1:8765 (ws_client.rs UNREACHABLE_AFTER). On "connected" the
  // sidecar is fine again · clear the banner unless a separate crash
  // event has set it for a different reason.
  listen<string>("ws-state", (event) => {
    if (event.payload === "unreachable") {
      errLine.textContent = reasonMessage("ws-unreachable", "");
      banner.hidden = false;
    } else if (event.payload === "connected") {
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
