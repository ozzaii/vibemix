/* Phase 13 Plan 06 — MascotBusClient.
 *
 * Mascot webview's OWN WebSocket subscription to ws://127.0.0.1:8765
 * (the existing Phase 4 ws_broadcast bus, extended by Plan 13-05 with
 * mood + bpm_confidence + downbeat_phase + bpm fields). The main session
 * UI consumes the same bus via the Rust ws_client.rs → tauri-event bridge
 * (`tauri/ui/src/session/ws-bridge.ts`), but per CONTEXT.md Area 6 the
 * mascot opens its own direct WebSocket — that decouples it from the
 * main window's lifecycle (the mascot survives when the user hides the
 * main window via the Phase 13-02 tray Quit-prevention).
 *
 * Reconnect schedule (CONTEXT.md Area 6):
 *   1s → 2s → 4s → 8s (cap)
 * Reset to 1s on successful onopen.
 *
 * Purity discipline (load-bearing — Plan 13-06 verifier greps):
 *   - This file IS allowed setTimeout (it's the timer surface for backoff).
 *   - event-dispatcher.ts is NOT allowed setTimeout / Date.now() —
 *     followups are expressed as data and the caller schedules them.
 */

export type BusListener = (msg: unknown) => void;
export type ConnectionStatus = "connected" | "disconnected" | "reconnecting";
export type StatusListener = (status: ConnectionStatus) => void;

export interface MascotBusClient {
  addMessageListener(l: BusListener): () => void;
  addStatusListener(l: StatusListener): () => void;
  close(): void;
}

// ── Tuning (CONTEXT.md Area 6) ────────────────────────────────────────────

const DEFAULT_URL = "ws://127.0.0.1:8765";
const BACKOFF_START_MS = 1000;
const BACKOFF_CAP_MS = 8000;

const TAG = "[mascot-bus]";

// ── Implementation ────────────────────────────────────────────────────────

export function connectMascotBus(url: string = DEFAULT_URL): MascotBusClient {
  const messageListeners = new Set<BusListener>();
  const statusListeners = new Set<StatusListener>();

  let ws: WebSocket | null = null;
  let closed = false;
  let backoffMs = BACKOFF_START_MS;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

  function emitStatus(status: ConnectionStatus): void {
    for (const l of statusListeners) {
      try {
        l(status);
      } catch (err) {
        if (import.meta.env?.DEV) {
          // eslint-disable-next-line no-console
          console.warn(`${TAG} status listener threw:`, err);
        }
      }
    }
  }

  function emitMessage(msg: unknown): void {
    for (const l of messageListeners) {
      try {
        l(msg);
      } catch (err) {
        if (import.meta.env?.DEV) {
          // eslint-disable-next-line no-console
          console.warn(`${TAG} message listener threw:`, err);
        }
      }
    }
  }

  function scheduleReconnect(): void {
    if (closed) return;
    if (reconnectTimer !== null) return;
    emitStatus("reconnecting");
    const delay = backoffMs;
    // Escalate backoff for the NEXT failure. Cap at 8s.
    backoffMs = Math.min(backoffMs * 2, BACKOFF_CAP_MS);
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null;
      open();
    }, delay);
  }

  function open(): void {
    if (closed) return;
    let socket: WebSocket;
    try {
      socket = new WebSocket(url);
    } catch (err) {
      if (import.meta.env?.DEV) {
        // eslint-disable-next-line no-console
        console.warn(`${TAG} WebSocket construct failed:`, err);
      }
      scheduleReconnect();
      return;
    }
    ws = socket;

    socket.onopen = () => {
      // On a SUCCESSFUL connect, reset the backoff so a subsequent
      // disconnect starts at 1s again.
      backoffMs = BACKOFF_START_MS;
      emitStatus("connected");
    };

    socket.onmessage = (ev: MessageEvent) => {
      // Localhost bus is always text frames (JSON). Drop non-string
      // silently — no exception bubbles to listeners.
      const data = ev.data;
      if (typeof data !== "string") return;
      try {
        const parsed = JSON.parse(data) as unknown;
        emitMessage(parsed);
      } catch {
        // Anti-slop discipline: malformed frames are dropped silently
        // here AND in dispatchEvent. The bus must be self-healing.
        if (import.meta.env?.DEV) {
          // eslint-disable-next-line no-console
          console.warn(`${TAG} non-JSON frame dropped`);
        }
      }
    };

    socket.onclose = () => {
      ws = null;
      if (closed) return;
      emitStatus("disconnected");
      scheduleReconnect();
    };

    socket.onerror = () => {
      // onclose will fire after onerror — let scheduleReconnect handle
      // backoff in one place. Silent here in production.
      if (import.meta.env?.DEV) {
        // eslint-disable-next-line no-console
        console.warn(`${TAG} socket error (close will follow)`);
      }
    };
  }

  // Kick off the first connection.
  open();

  return {
    addMessageListener(l: BusListener): () => void {
      messageListeners.add(l);
      return () => messageListeners.delete(l);
    },
    addStatusListener(l: StatusListener): () => void {
      statusListeners.add(l);
      return () => statusListeners.delete(l);
    },
    close(): void {
      closed = true;
      if (reconnectTimer !== null) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
      }
      if (ws) {
        try {
          ws.close();
        } catch {
          // best-effort
        }
        ws = null;
      }
    },
  };
}
