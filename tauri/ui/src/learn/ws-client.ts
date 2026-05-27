// SPDX-License-Identifier: Apache-2.0
//
// Phase 91 Plan 05 — Learn webview ws client.
//
// Connects to ws://127.0.0.1:8765 — the SAME socket the live co-host
// session uses (Invariant #4: one-socket — pinned by
// `tests/learn/test_no_new_ws_port.py` Python-side + the sibling
// `test_ws_client_uses_8765.spec.ts` grep gate on this file).
//
// On each inbound frame: JSON.parse → ajv validate via the pre-compiled
// `validator.generated.mjs` (CSP-safe; the runtime ajv.compile() path is
// forbidden by tauri.conf.json CSP because it uses unsafe-eval) →
// dispatch `CustomEvent(envelope.type, { detail: envelope.payload })`
// on `window` so any component in this webview can subscribe via
// `window.addEventListener("ipc.learn.midi_position", ...)`.
//
// Failure modes (defensive — never crashes the webview):
//   - parse fail → log `[learn:ws]` + drop
//   - validate fail → log `[learn:ws]` + drop
//   - unknown type → log + drop (we only handle ipc.learn.*)
//
// Reconnect on close: 1s linear backoff, infinite retries. The Python
// sidecar is long-lived (shared with the live deck) so a close usually
// means the sidecar crashed → the user-visible status pip in the
// `status-bar` will flip red until reconnect succeeds.

// Pre-compiled ajv validator. Mirror of `src/ipc/validator.ts` — the
// generated file ships without a `.d.ts`, so the import carries a
// ts-expect-error directive identical to the precedent.
// @ts-expect-error — generated file ships without .d.ts
import validateGenerated from "../ipc/validator.generated.mjs";

// The ONE socket every Learn webview targets — Invariant #4 (one-socket).
// Pinned by `tests/learn/test_no_new_ws_port.py` (Python side, grep gate
// on `src/vibemix/learn/`) and `test_ws_client_uses_8765.spec.ts` (TS
// side, grep gate on every WebSocket constructor argument in this dir).
const WS_URL_8765 = "ws://127.0.0.1:8765";

const RECONNECT_DELAY_MS = 1000;

type AjvValidator = ((data: unknown) => boolean) & {
  errors?: Array<{ instancePath?: string; message?: string }> | null;
};

const validate = validateGenerated as AjvValidator;

export class LearnWsClient extends EventTarget {
  private ws: WebSocket | null = null;
  private stopped = false;

  constructor() {
    super();
  }

  connect(): void {
    if (this.stopped) return;
    try {
      this.ws = new WebSocket(WS_URL_8765);
    } catch (e) {
      // eslint-disable-next-line no-console
      console.error("[learn:ws] connect failed", e);
      this.scheduleReconnect();
      return;
    }
    this.ws.onopen = () => {
      this.dispatchEvent(new CustomEvent("open"));
    };
    this.ws.onmessage = (ev) => {
      this.onMessage(ev.data);
    };
    this.ws.onclose = () => {
      this.dispatchEvent(new CustomEvent("close"));
      this.scheduleReconnect();
    };
    this.ws.onerror = (e) => {
      // eslint-disable-next-line no-console
      console.warn("[learn:ws] ws error", e);
    };
  }

  close(): void {
    this.stopped = true;
    if (this.ws) {
      this.ws.onopen = null;
      this.ws.onmessage = null;
      this.ws.onclose = null;
      this.ws.onerror = null;
      try {
        this.ws.close();
      } catch {
        // swallow
      }
      this.ws = null;
    }
  }

  // ---- private ----

  private scheduleReconnect(): void {
    if (this.stopped) return;
    setTimeout(() => this.connect(), RECONNECT_DELAY_MS);
  }

  private onMessage(raw: unknown): void {
    if (typeof raw !== "string") return;
    let envelope: { type?: string; payload?: unknown };
    try {
      envelope = JSON.parse(raw) as { type?: string; payload?: unknown };
    } catch (e) {
      // eslint-disable-next-line no-console
      console.warn("[learn:ws] parse failed; dropping frame", e);
      return;
    }
    if (typeof envelope?.type !== "string") {
      // eslint-disable-next-line no-console
      console.warn("[learn:ws] envelope missing type; dropping");
      return;
    }
    // Pre-compiled ajv validator — CSP-safe (no unsafe-eval). The
    // static default-import above guarantees synchronous availability;
    // the `await` keyword on this method exists for parity with the
    // earlier dynamic-import path. Future schema additions automatically
    // flow through `npm run codegen:ipc`.
    const ok = validate(envelope);
    if (!ok) {
      // eslint-disable-next-line no-console
      console.warn(
        `[learn:ws] validate failed for ${envelope.type}; dropping`,
      );
      return;
    }
    // We dispatch on `window` so any component (controller-stage,
    // status-bar, etc.) can subscribe via `addEventListener` without
    // needing a reference to this ws client.
    window.dispatchEvent(
      new CustomEvent(envelope.type, { detail: envelope.payload }),
    );
  }
}
