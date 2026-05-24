/* debug-log-ws.ts — shared WS-bus frame summariser for the observability sink.
 *
 * The direct-WS bus (ws://127.0.0.1:8765) pushes flat live frames at up to
 * 30Hz. Logging every one would flood ui.log into uselessness, so this helper
 * implements the Category-3 policy:
 *
 *   - Connection STATUS changes (connected / reconnecting / disconnected) log
 *     immediately — handled by the caller via vmxLog directly.
 *   - REACTION / ai_text frames (cohost-reaction, ipc.session.cohost-reaction,
 *     anything carrying a `text` field) log IMMEDIATELY and verbatim — these
 *     are the load-bearing "the co-host said something" events.
 *   - Every other inbound frame is SUMMARISED + throttled (at most one summary
 *     line per `THROTTLE_MS`), carrying a compact shape (type + a few key
 *     fields) rather than the full blob.
 *
 * State is per-sink (the `sink` label, e.g. "pill" / "mascot") so two bus
 * clients don't share a throttle clock.
 */

import { vmxLog } from "./debug-log.js";

const THROTTLE_MS = 2000;

/** Per-sink last-summary timestamp (ms). */
const lastSummaryAt = new Map<string, number>();

function isReactionFrame(m: Record<string, unknown>): boolean {
  const t = typeof m.type === "string" ? m.type : "";
  return (
    t === "cohost-reaction" ||
    t === "ipc.session.cohost-reaction" ||
    typeof m.text === "string"
  );
}

/** Compact summary of a flat live frame — just the fields an operator cares
 *  about for "is the bus alive and what's it carrying". Never the full blob. */
function summariseFrame(m: Record<string, unknown>): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  if (typeof m.type === "string") out.type = m.type;
  if ("cohost_status" in m) out.cohost_status = m.cohost_status;
  if (typeof m.voice === "number") out.voice = round3(m.voice);
  if (typeof m.music === "number") out.music = round3(m.music);
  if (typeof m.bpm === "number") out.bpm = m.bpm;
  if ("deck_state" in m && m.deck_state && typeof m.deck_state === "object") {
    out.decks = Object.keys(m.deck_state as Record<string, unknown>);
  }
  return out;
}

function round3(n: number): number {
  return Math.round(n * 1000) / 1000;
}

/**
 * Log one inbound bus frame for the named sink, applying the
 * reaction-immediate / summarise-and-throttle policy above. Safe to call on
 * the hot path — non-reaction frames short-circuit on the throttle clock
 * before any stringify work.
 */
export function logBusFrame(sink: string, msg: unknown): void {
  if (msg == null || typeof msg !== "object") return;
  const m = msg as Record<string, unknown>;

  if (isReactionFrame(m)) {
    // Immediate, verbatim-ish — the operator must see the reaction land.
    vmxLog("[vmx:ws]", `${sink}: reaction`, {
      type: m.type,
      text: m.text,
      citation_strip: m.citation_strip,
    });
    return;
  }

  const now = Date.now();
  const last = lastSummaryAt.get(sink) ?? 0;
  if (now - last < THROTTLE_MS) return;
  lastSummaryAt.set(sink, now);
  vmxLog("[vmx:ws]", `${sink}: frame (throttled ${THROTTLE_MS}ms)`, summariseFrame(m));
}
