// SPDX-License-Identifier: Apache-2.0
// Plan 29-05 Task 1 · vanilla WS client for the debrief window.
//
// Connects to ws://127.0.0.1:8766 (Plan 29-02 sidecar), validates each
// inbound frame against the source-of-truth schema via the ajv-generated
// validator, and dispatches typed CustomEvents on an EventTarget. Retries the
// connection with capped backoff for up to 120s (sidecar boot +
// first-time generation bind 8766 late); only then declares a crash.

import { vmxLog } from "../debug-log.js";
import { stripDrillFields } from "./stripper-roundtrip.js";

export type DebriefFrameKind =
  | "session-loaded"
  | "chapter-list"
  | "near-miss"
  | "tldr-audio"
  | "drills"
  | "citation-tooltip"
  | "error";

export interface DebriefFrame {
  type: string;
  ts: string;
  payload: Record<string, unknown>;
}

export type DebriefMomentFeedbackVerdict = "agree" | "disagree" | "unclear";
export type DebriefMomentFeedbackSurface = "transition" | "live_pill" | "cue";

export interface DebriefMomentFeedbackPayload {
  moment_id: string;
  citation_id: string;
  verdict: DebriefMomentFeedbackVerdict;
  surface: DebriefMomentFeedbackSurface;
}

const KIND_MAP: Record<string, DebriefFrameKind> = {
  "ipc.debrief.session-loaded": "session-loaded",
  "ipc.debrief.chapter-list": "chapter-list",
  "ipc.debrief.near-miss": "near-miss",
  "ipc.debrief.tldr-audio": "tldr-audio",
  "ipc.debrief.drills": "drills",
  "ipc.debrief.citation-tooltip": "citation-tooltip",
  "ipc.debrief.error": "error",
};

// Reconnect policy: the sidecar is one-shot per window, but PyInstaller
// boot and first-time generation happen BEFORE 127.0.0.1:8766 accepts
// connections. Give it a real budget instead of ~1.4s: retry with capped
// backoff for up to RECONNECT_BUDGET_MS, then declare the sidecar crashed.
const RECONNECT_BUDGET_MS = 120_000;
const RECONNECT_DELAY_CAP_MS = 2_000;

export class DebriefWsClient extends EventTarget {
  private url: string;
  private ws: WebSocket | null = null;
  private retries = 0;
  private firstAttemptAt: number | null = null;

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
      this.firstAttemptAt = null;
      vmxLog("[vmx:ws]", "debrief: connection connected", { url: this.url });
      this.dispatchEvent(new CustomEvent("open"));
    };
    this.ws.onmessage = (ev) => {
      this._onMessage(ev.data);
    };
    this.ws.onclose = () => {
      vmxLog("[vmx:ws]", "debrief: connection disconnected", { url: this.url });
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

  sendMomentFeedback(payload: DebriefMomentFeedbackPayload): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
    const frame = {
      type: "ipc.debrief.moment-feedback",
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
    const now = Date.now();
    if (this.firstAttemptAt === null) this.firstAttemptAt = now;
    if (now - this.firstAttemptAt >= RECONNECT_BUDGET_MS) {
      this.dispatchEvent(
        new CustomEvent("error", {
          detail: { reason: "sidecar_crashed" },
        }),
      );
      return;
    }
    const delay = Math.min(RECONNECT_DELAY_CAP_MS, 200 * 2 ** this.retries);
    this.retries += 1;
    this.dispatchEvent(
      new CustomEvent("connecting", {
        detail: { attempt: this.retries, elapsedMs: now - this.firstAttemptAt },
      }),
    );
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
      vmxLog("[vmx:ws]", "debrief: unknown frame kind", { type: frame.type });
      return;
    }
    vmxLog("[vmx:ws]", `debrief: frame ${kind}`, { type: frame.type });
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
