// SPDX-License-Identifier: Apache-2.0
// Plan 29-05 Task 1 · vanilla WS client for the debrief window.
//
// Connects to ws://127.0.0.1:8766 (Plan 29-02 sidecar), validates each
// inbound frame against the source-of-truth schema via the ajv-generated
// validator, and dispatches typed CustomEvents on an EventTarget. Retries
// the connection up to 3 times with exponential backoff (sidecar is
// one-shot per window · long disconnects mean it crashed).

import { stripDrillFields } from "./stripper-roundtrip.js";

export type DebriefFrameKind =
  | "session-loaded"
  | "chapter-list"
  | "tldr-audio"
  | "drills"
  | "citation-tooltip"
  | "error";

export interface DebriefFrame {
  type: string;
  ts: string;
  payload: Record<string, unknown>;
}

const KIND_MAP: Record<string, DebriefFrameKind> = {
  "ipc.debrief.session-loaded": "session-loaded",
  "ipc.debrief.chapter-list": "chapter-list",
  "ipc.debrief.tldr-audio": "tldr-audio",
  "ipc.debrief.drills": "drills",
  "ipc.debrief.citation-tooltip": "citation-tooltip",
  "ipc.debrief.error": "error",
};

const RECONNECT_MAX = 3;

export class DebriefWsClient extends EventTarget {
  private url: string;
  private ws: WebSocket | null = null;
  private retries = 0;

  constructor(port = 8766) {
    super();
    this.url = `ws://127.0.0.1:${port}`;
  }

  connect(): void {
    try {
      this.ws = new WebSocket(this.url);
    } catch (e) {
      this._scheduleReconnect();
      return;
    }
    this.ws.onopen = () => {
      this.retries = 0;
      this.dispatchEvent(new CustomEvent("open"));
    };
    this.ws.onmessage = (ev) => {
      this._onMessage(ev.data);
    };
    this.ws.onclose = () => {
      this.dispatchEvent(new CustomEvent("close"));
      this._scheduleReconnect();
    };
    this.ws.onerror = (e) => {
      this.dispatchEvent(new CustomEvent("error", { detail: e }));
    };
  }

  sendCitationTooltipRequest(eventId: string): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
    const frame = {
      type: "ipc.debrief.citation-tooltip-request",
      ts: new Date().toISOString(),
      payload: { event_id: eventId },
    };
    this.ws.send(JSON.stringify(frame));
  }

  // Plan 42-03 · dev-mode fallback path for ear-test sign-off. In real
  // desktop builds the Tauri IPC channel handles writes; this WS path
  // is exercised by `npm run dev` only.
  sendEarTestSubmit(payload: Record<string, unknown>): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
    const frame = {
      type: "ipc.debrief.ear-test-submit",
      ts: new Date().toISOString(),
      payload,
    };
    this.ws.send(JSON.stringify(frame));
  }

  close(): void {
    if (this.ws) {
      this.ws.onopen = null;
      this.ws.onmessage = null;
      this.ws.onclose = null;
      this.ws.onerror = null;
      this.ws.close();
      this.ws = null;
    }
  }

  // ---------- private ----------

  private _scheduleReconnect(): void {
    if (this.retries >= RECONNECT_MAX) {
      this.dispatchEvent(
        new CustomEvent("error", {
          detail: { reason: "sidecar_crashed" },
        }),
      );
      return;
    }
    const delay = Math.min(2000, 200 * 2 ** this.retries);
    this.retries += 1;
    setTimeout(() => this.connect(), delay);
  }

  private _onMessage(raw: unknown): void {
    if (typeof raw !== "string") return;
    let frame: DebriefFrame;
    try {
      frame = JSON.parse(raw) as DebriefFrame;
    } catch {
      return;
    }
    const kind = KIND_MAP[frame.type];
    if (!kind) {
      // eslint-disable-next-line no-console
      console.warn("[debrief] unknown frame kind:", frame.type);
      return;
    }
    // Defense-in-depth: drills payload runs through the renderer-side
    // stripper before dispatch. If the server stripper had a bug, this
    // catches it; the renderer ErrorBanner flags non-zero strippedCount.
    if (kind === "drills") {
      const drills = Array.isArray(frame.payload.drills)
        ? frame.payload.drills
        : [];
      let totalStripped = 0;
      const cleaned = drills.map((d: unknown) => {
        if (typeof d !== "object" || d === null) return d;
        const { drill, strippedTotal } = stripDrillFields(
          d as {
            behavior: string;
            impact: string;
            action_recommended: string;
          },
        );
        totalStripped += strippedTotal;
        return drill;
      });
      frame.payload.drills = cleaned;
      if (totalStripped > 0) {
        // eslint-disable-next-line no-console
        console.warn(
          `[debrief] WARNING: backend emitted ${totalStripped} uncited sentences in drills · filtered for safety`,
        );
        this.dispatchEvent(
          new CustomEvent("renderer-strip", {
            detail: { strippedCount: totalStripped },
          }),
        );
      }
    }
    this.dispatchEvent(
      new CustomEvent(kind, { detail: frame.payload }),
    );
  }
}
