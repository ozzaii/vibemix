/* Phase 62 Plan 04 — PillBusClient (copied verbatim from the shipped
 * tauri/ui/src/mascot/ws-client.ts — Phase 13 Plan 06).
 *
 * The pill opens its OWN direct WebSocket to ws://127.0.0.1:8765 (the existing
 * Phase 4 ws_broadcast bus) — identical to the mascot's direct-WS pattern. The
 * client is COPIED into src/pill/ (rather than imported from src/mascot/) so
 * the pill is fully decoupled from src/mascot/** and a pill PR does NOT
 * path-trigger the mascot-audit CI fence (62-PATTERNS recommendation). The
 * only delta from the mascot original is the cosmetic log TAG — the reconnect/
 * backoff/silent-drop behaviour is byte-for-byte the same self-healing client.
 *
 * Self-healing properties the PRIMARY surface needs:
 *   - 1s → 2s → 4s → 8s (cap) reconnect backoff; reset to 1s on open.
 *   - Silent drop of non-string / non-JSON / malformed frames (anti-slop) —
 *     a bad frame can never crash the always-on-top pill (T-62-13).
 *   - Lifecycle-independent of the main window (the pill survives a hidden
 *     main window).
 *
 * Purity discipline: this file IS allowed setTimeout (it's the timer surface
 * for backoff). state-machine.ts is NOT — followups are expressed as data.
 */

import { vmxLog } from "../debug-log.js";
import { logBusFrame } from "../debug-log-ws.js";

export type BusListener = (msg: unknown) => void;
export type ConnectionStatus = "connected" | "disconnected" | "reconnecting";
export type StatusListener = (status: ConnectionStatus) => void;

export interface MascotBusClient {
  addMessageListener(l: BusListener): () => void;
  addStatusListener(l: StatusListener): () => void;
  /** Send a JSON control frame back over the live socket (e.g.
   *  next_suggestion.feedback / .choose). Best-effort: a send while
   *  disconnected is silently dropped and never crashes the always-on-top pill. */
  send(msg: unknown): void;
  close(): void;
}

// ── Tuning (CONTEXT.md Area 6 — carried from the mascot) ──────────────────

const DEFAULT_URL = "ws://127.0.0.1:8765";
const BACKOFF_START_MS = 1000;
const BACKOFF_CAP_MS = 8000;

const TAG = "[pill-bus]";
/** Observability label for the file-sink (Category 3 — WS). */
const WS_SINK = "pill";

// ── Implementation ────────────────────────────────────────────────────────

export function connectMascotBus(url: string = DEFAULT_URL): MascotBusClient {
  const messageListeners = new Set<BusListener>();
  const statusListeners = new Set<StatusListener>();

  let ws: WebSocket | null = null;
  let closed = false;
  let backoffMs = BACKOFF_START_MS;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

  function emitStatus(status: ConnectionStatus): void {
    // Category 3 — connection state changes log immediately to the file sink.
    vmxLog("[vmx:ws]", `${WS_SINK}: connection ${status}`, { url });
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
    // Category 3 — reactions/ai_text log immediately; other frames are
    // summarised + throttled inside logBusFrame so 30Hz traffic never floods.
    logBusFrame(WS_SINK, msg);
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
        // here. The bus must be self-healing.
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
    send(msg: unknown): void {
      // Best-effort outbound. The bus is normally receive-only, but the pill
      // emits next_suggestion.feedback/.choose back to the ws_bus inbound
      // handlers. Silent-drop when not OPEN — matching the self-healing /
      // anti-slop discipline: a failed send must never crash the pill.
      if (closed || ws === null || ws.readyState !== WebSocket.OPEN) return;
      try {
        ws.send(JSON.stringify(msg));
      } catch {
        // swallow — reconnect/backoff owns socket health elsewhere
      }
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
