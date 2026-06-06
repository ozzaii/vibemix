// SPDX-License-Identifier: Apache-2.0
//
// The activation bridge: a one-way feed from the live session state onto the
// shell's self-arranging activation + connection. The shell store knows nothing
// about the ws bus by design; this is the only place the two meet.
//
//   - Activation (idle/listening/live) mirrors the co-host's own status, which
//     the session already derives (cohostStatus). The session state singleton
//     has no pub/sub, so the bridge polls getSessionState() on a low-frequency
//     interval and pushes ONLY on a real transition — a stable status must never
//     re-fire setActivation(), or its panel side-effect would slam shut a panel
//     the user opened by hand (invariant: the shell self-arranges, it doesn't
//     fight the user).
//   - Connection mirrors the Rust↔sidecar ws bridge (the `ws-state` Tauri
//     event), with a status-tick fallback. A live ipc.status.tick proves the
//     pipe is up even if the shell mounted after the last ws-state event.
//     This stays independent of whether music is playing (idle is
//     connected-but-quiet, never a fault; cardinal invariant #5).

import type { CohostStatus } from "../session/cohost-model.js";
import { getSessionState } from "../session/state.js";
import { subscribeIpc } from "../ipc/client.js";
import type { StatusTick } from "../ipc/messages.js";
import { listenTauri } from "../tauri-runtime.js";
import type { ActivationState, ConnectionState, ShellStore } from "./shell-store.js";

/** Map the co-host's own status onto the shell's three activation states. */
export function activationForCohost(status: CohostStatus): ActivationState {
  switch (status) {
    case "TALKING":
      return "live";
    case "LISTENING":
      return "listening";
    default:
      return "idle";
  }
}

/** Map a `ws-state` payload onto the footer connection dot. Anything that is not
 *  explicitly connected/reconnecting reads as disconnected (honest, not a
 *  fault — the dot is steady-lit when connected and dim otherwise). */
export function connectionForWsState(state: string): ConnectionState {
  switch (state) {
    case "connected":
      return "connected";
    case "connecting":
    case "reconnecting":
      return "reconnecting";
    default:
      // "unreachable", "disconnected", or any unknown payload.
      return "disconnected";
  }
}

export interface ActivationBridgeOpts {
  /** Poll cadence for the (pub/sub-less) session state. Ambient, so low. */
  intervalMs?: number;
  /** Test seam; production subscribes to ipc.status.tick through the IPC client. */
  subscribeStatusTick?: (callback: (msg: StatusTick) => void) => Promise<() => void>;
}

/**
 * Wire the live session onto the shell store. Returns a teardown that stops the
 * poll and detaches the ws-state/status listeners.
 */
export function wireActivation(store: ShellStore, opts: ActivationBridgeOpts = {}): () => void {
  // Connection ← the Rust ws bridge state.
  const unlistenPromise = listenTauri<string>("ws-state", (event) => {
    store.setConnection(connectionForWsState(String(event.payload)));
  });
  const subscribeStatusTick =
    opts.subscribeStatusTick ??
    ((callback: (msg: StatusTick) => void) =>
      subscribeIpc<StatusTick>("ipc.status.tick", callback));
  const unlistenStatusPromise = subscribeStatusTick(() => {
    store.setConnection("connected");
  });

  // Activation ← the co-host status, pushed only on a real transition.
  let prev: ActivationState | null = null;
  const tick = (): void => {
    const next = activationForCohost(getSessionState().cohostStatus);
    if (next !== prev) {
      store.setActivation(next);
      prev = next;
    }
  };
  tick();
  const timer = globalThis.setInterval(tick, opts.intervalMs ?? 500);

  return (): void => {
    globalThis.clearInterval(timer);
    void unlistenPromise.then((unlisten) => unlisten?.()).catch(() => {});
    void unlistenStatusPromise.then((unlisten) => unlisten?.()).catch(() => {});
  };
}
