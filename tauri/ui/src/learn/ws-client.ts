// SPDX-License-Identifier: Apache-2.0
//
// Phase 91 Plan 05 — Learn event client.
//
// Production Tauri path: subscribes to the established Rust event bridge.
// The Rust shell owns the ws://127.0.0.1:8765 sidecar connection and emits
// dashed Tauri events; `subscribeIpc` validates and hands us typed ipc.*
// envelopes. This keeps Learn on the same IPC seam as the session UI.
//
// Browser/dev fallback: if the Tauri event plugin is absent, connect directly
// to ws://127.0.0.1:8765. That fallback is the path used by Vite/Playwright
// harnesses and is still pinned by `tests/learn/test_no_new_ws_port.py` plus
// `test_ws_client_uses_8765.spec.ts`.
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

import { subscribeIpc, type IpcMessage } from "../ipc/client.js";
import { listenTauri } from "../tauri-runtime.js";
import {
  normalizeOperatorAction,
  type LearnOperatorAction,
} from "./lesson/operator-action.js";

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
const WS_READY_OPEN = 1;
const MAX_OUTBOUND_QUEUE = 32;

// The shared ws:8765 socket carries multiple envelope families: the
// legacy 30 Hz mascot frame (a flat dict with no `type` field), the
// ~15 Hz `ipc.session.snapshot`, the ~1 Hz `ipc.status.tick`, mascot
// mood-change events, and finally the `ipc.learn.*` envelopes the Learn
// webview cares about. CR-03 (REVIEW.md): pre-filter to `ipc.learn.*`
// BEFORE the validator + the missing-type warning, otherwise the
// learn-window devtools console takes ~30 console.warn() calls per
// second from the mascot frame alone (~108k/hour) and real schema-drift
// warnings get buried.
const MESSAGE_TYPE_PREFIX = "ipc.learn.";
const COURSE3_LENS_EVENT = "learn.course3_lens";
const COURSE3_LENS_TAURI_EVENT = "learn-course3-lens";
const OPERATOR_ACTION_EVENT = "learn.operator_action";
const OPERATOR_ACTION_TAURI_EVENT = "learn-operator-action";

const LEARN_INBOUND_TYPES = [
  "ipc.learn.controller_detected",
  "ipc.learn.midi_position",
  "ipc.learn.lesson_loaded",
  "ipc.learn.highlight",
  "ipc.learn.advance",
  "ipc.learn.complete_lesson",
  "ipc.learn.tutor_speak",
  "ipc.learn.exemplar_play",
  "ipc.learn.exemplar_stop",
  "ipc.learn.progress_state",
] as const;

type AjvValidator = ((data: unknown) => boolean) & {
  errors?: Array<{ instancePath?: string; message?: string }> | null;
};

type LearnEnvelope = Extract<IpcMessage, { type: (typeof LEARN_INBOUND_TYPES)[number] }>;
type LearnOutboundEnvelope = {
  type: string;
  ts: string;
  payload: Record<string, unknown>;
};
type UnlistenMaybeAsync = () => void | Promise<void>;
type Course3LensPayload = {
  session_active: boolean;
  phrase_position_confidence: number;
  next_phrase_at: number | null;
  next_phrase_cue_id: string | null;
  audio_active: boolean;
  deck_attributed: boolean;
  deck_track_citable: boolean;
  cue_ready: boolean;
  blockers: string[];
  operator_action?: LearnOperatorAction;
};

const validate = validateGenerated as AjvValidator;

export class LearnWsClient extends EventTarget {
  private ws: WebSocket | null = null;
  private stopped = false;
  private tauriUnlisteners: UnlistenMaybeAsync[] = [];
  private outboundQueue: LearnOutboundEnvelope[] = [];

  constructor() {
    super();
  }

  connect(): void {
    if (this.stopped) return;
    if (hasTauriEventBridge()) {
      void this.connectTauriEvents();
      return;
    }
    this.connectWebSocket();
  }

  private connectWebSocket(): void {
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
      this.flushOutboundQueue();
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
    this.outboundQueue = [];
    for (const unlisten of this.tauriUnlisteners.splice(0)) {
      void Promise.resolve(unlisten()).catch(() => {
        // swallow
      });
    }
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

  sendIpc(type: string, payload: Record<string, unknown>): void {
    if (this.stopped) return;
    const envelope = {
      type,
      ts: new Date().toISOString(),
      payload,
    };
    if (this.sendEnvelope(envelope)) return;
    this.outboundQueue.push(envelope);
    if (this.outboundQueue.length > MAX_OUTBOUND_QUEUE) {
      this.outboundQueue.shift();
    }
  }

  // ---- private ----

  private scheduleReconnect(): void {
    if (this.stopped) return;
    setTimeout(() => this.connect(), RECONNECT_DELAY_MS);
  }

  private flushOutboundQueue(): void {
    if (this.outboundQueue.length === 0) return;
    const pending = this.outboundQueue.splice(0);
    for (const envelope of pending) {
      if (this.sendEnvelope(envelope)) continue;
      this.outboundQueue.unshift(envelope, ...pending.slice(pending.indexOf(envelope) + 1));
      break;
    }
  }

  private sendEnvelope(envelope: LearnOutboundEnvelope): boolean {
    if (!this.ws || this.ws.readyState !== WS_READY_OPEN) return false;
    try {
      this.ws.send(JSON.stringify(envelope));
      return true;
    } catch (e) {
      // eslint-disable-next-line no-console
      console.warn("[learn:ws] outbound send failed; queueing frame", e);
      return false;
    }
  }

  private async connectTauriEvents(): Promise<void> {
    try {
      const [learnUnlisteners, course3LensUnlisten, operatorActionUnlisten] = await Promise.all([
        Promise.all(
          LEARN_INBOUND_TYPES.map((type) =>
            subscribeIpc<LearnEnvelope>(type, (envelope) => {
              this.dispatchLearnEnvelope(envelope);
            }),
          ),
        ),
        listenTauri<unknown>(COURSE3_LENS_TAURI_EVENT, (event) => {
          this.dispatchCourse3LensFrame(event.payload);
        }),
        listenTauri<unknown>(OPERATOR_ACTION_TAURI_EVENT, (event) => {
          this.dispatchOperatorActionFrame(event.payload);
        }),
      ]);
      if (this.stopped) {
        for (const unlisten of [...learnUnlisteners, course3LensUnlisten, operatorActionUnlisten]) {
          void Promise.resolve(unlisten()).catch(() => {
            // swallow
          });
        }
        return;
      }
      this.tauriUnlisteners = [...learnUnlisteners, course3LensUnlisten, operatorActionUnlisten];
      this.dispatchEvent(new CustomEvent("open"));
    } catch (e) {
      // eslint-disable-next-line no-console
      console.warn("[learn:ws] Tauri event bridge failed; falling back to ws", e);
      this.connectWebSocket();
    }
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
    // CR-03: filter to ipc.learn.* BEFORE the missing-type warning + the
    // validator. ws:8765 is shared with the mascot bus (30 Hz flat dict,
    // no `type` field) + ipc.session.snapshot (~15 Hz) + ipc.status.tick
    // (~1 Hz) + mascot mood-change events; the learn webview is only
    // concerned with ipc.learn.*. Without this early-drop, every mascot
    // frame logged a missing-type warning to devtools (108k/hour) and
    // every status/snapshot envelope did wasted validate + dispatch work.
    // Course 3 is the only Learn-owned field riding on that flat frame:
    // dispatch it through a small local event. Grounded one-action operator
    // hints can also ride as ``learn_operator_action`` for future courses and
    // readiness doctors without adding a new visible surface.
    this.dispatchCourse3LensFrame(envelope);
    this.dispatchOperatorActionFrame(envelope);
    // Silent drop — no warn — keeps real schema-drift warnings legible.
    const t = envelope?.type;
    if (typeof t !== "string" || !t.startsWith(MESSAGE_TYPE_PREFIX)) {
      return;
    }
    this.dispatchValidatedEnvelope(envelope);
  }

  private dispatchValidatedEnvelope(envelope: { type?: string; payload?: unknown }): void {
    const ok = validate(envelope);
    if (!ok) {
      const t = envelope.type ?? "unknown";
      // eslint-disable-next-line no-console
      console.warn(`[learn:ws] validate failed for ${t}; dropping`);
      return;
    }
    this.dispatchLearnEnvelope(envelope as LearnEnvelope);
  }

  private dispatchLearnEnvelope(envelope: LearnEnvelope): void {
    const t = envelope.type;
    if (!t.startsWith(MESSAGE_TYPE_PREFIX)) return;
    // We dispatch on `window` so any component (controller-stage,
    // status-bar, etc.) can subscribe via `addEventListener` without
    // needing a reference to this ws client. `t` is the type-narrowed
    // string from the prefix filter above; using it (not `envelope.type`)
    // keeps the type system happy without re-asserting non-undefined.
    window.dispatchEvent(new CustomEvent(t, { detail: envelope.payload }));
  }

  private dispatchCourse3LensFrame(frame: unknown): void {
    const lens = extractCourse3Lens(frame);
    if (!lens) return;
    window.dispatchEvent(new CustomEvent(COURSE3_LENS_EVENT, { detail: lens }));
  }

  private dispatchOperatorActionFrame(frame: unknown): void {
    const extracted = extractOperatorActionFrame(frame);
    if (!extracted.present) return;
    window.dispatchEvent(new CustomEvent(OPERATOR_ACTION_EVENT, { detail: extracted.action }));
  }
}

type OperatorActionExtraction =
  | { present: true; action: LearnOperatorAction | null }
  | { present: false };

function extractOperatorActionFrame(frame: unknown): OperatorActionExtraction {
  if (!isRecord(frame)) return { present: false };
  if ("learn_operator_action" in frame) {
    return normalizeExplicitOperatorAction(frame.learn_operator_action);
  }
  if ("operator_action" in frame) {
    return normalizeExplicitOperatorAction(frame.operator_action);
  }
  if ("type" in frame || "course3_lens" in frame || !("prompt" in frame)) {
    return { present: false };
  }
  return normalizeExplicitOperatorAction(frame);
}

function normalizeExplicitOperatorAction(raw: unknown): OperatorActionExtraction {
  if (raw === null) return { present: true, action: null };
  const action = normalizeOperatorAction(raw);
  return action ? { present: true, action } : { present: false };
}

function extractCourse3Lens(frame: unknown): Course3LensPayload | null {
  if (!isRecord(frame)) return null;
  const rawLens = frame.course3_lens;
  if (!isRecord(rawLens)) return null;
  const confidence =
    typeof rawLens.phrase_position_confidence === "number" &&
    Number.isFinite(rawLens.phrase_position_confidence)
      ? Math.min(1, Math.max(0, rawLens.phrase_position_confidence))
      : 0;
  const nextPhraseAt =
    typeof rawLens.next_phrase_at === "number" &&
    Number.isFinite(rawLens.next_phrase_at)
      ? rawLens.next_phrase_at
      : null;
  const cueId =
    typeof rawLens.next_phrase_cue_id === "string" && rawLens.next_phrase_cue_id.length > 0
      ? rawLens.next_phrase_cue_id
      : null;
  const blockers = Array.isArray(rawLens.blockers)
    ? rawLens.blockers.filter((blocker): blocker is string => typeof blocker === "string")
    : [];
  const operatorAction = normalizeOperatorAction(rawLens.operator_action);
  const cueReady =
    typeof rawLens.cue_ready === "boolean"
      ? rawLens.cue_ready
      : Boolean(cueId && nextPhraseAt !== null && confidence >= 0.7);
  return {
    session_active: rawLens.session_active === true,
    phrase_position_confidence: confidence,
    next_phrase_at: nextPhraseAt,
    next_phrase_cue_id: cueId,
    audio_active: rawLens.audio_active === true,
    deck_attributed: rawLens.deck_attributed === true,
    deck_track_citable: rawLens.deck_track_citable === true,
    cue_ready: cueReady,
    blockers,
    ...(operatorAction ? { operator_action: operatorAction } : {}),
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function hasTauriEventBridge(): boolean {
  if (typeof window === "undefined") return false;
  const w = window as Window & {
    __TAURI_INTERNALS__?: unknown;
    __TAURI_EVENT_PLUGIN_INTERNALS__?: unknown;
  };
  return (
    typeof w.__TAURI_INTERNALS__ === "object" &&
    w.__TAURI_INTERNALS__ !== null &&
    typeof w.__TAURI_EVENT_PLUGIN_INTERNALS__ === "object" &&
    w.__TAURI_EVENT_PLUGIN_INTERNALS__ !== null
  );
}
