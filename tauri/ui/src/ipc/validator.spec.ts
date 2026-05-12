/* Phase 11 Wave 0 — vitest cases for the ajv runtime guard.
 *
 * Mirrors tests/ui_bus/test_status_tick.py asserts so both sides catch
 * the same drift. Wave 0 ships ONLY the schema + dual-language gate; runtime
 * wiring (WS bus consumer) lands in Wave 4.
 */

import { describe, expect, it } from "vitest";

import { isIpcMessage, parseIpcMessage } from "./validator.js";

const TS = "2026-05-12T08:00:00+00:00";

function statusTick(payload: Record<string, unknown>): unknown {
  return { type: "ipc.status.tick", ts: TS, payload };
}

describe("parseIpcMessage — ipc.status.tick", () => {
  it("accepts a fully-valid frame", () => {
    const msg = statusTick({ livekit: "ok", gemini: "ok", midi: 1, screen: "ok" });
    expect(() => parseIpcMessage(msg)).not.toThrow();
  });

  it("accepts midi=null (no MIDI backend)", () => {
    const msg = statusTick({ livekit: "ok", gemini: "ok", midi: null, screen: "ok" });
    expect(() => parseIpcMessage(msg)).not.toThrow();
  });

  it("rejects missing payload field", () => {
    const msg = { type: "ipc.status.tick", ts: TS };
    expect(() => parseIpcMessage(msg)).toThrow(/IPC schema violation/);
  });

  it("rejects unknown livekit enum value", () => {
    const msg = statusTick({ livekit: "wat", gemini: "ok", midi: 1, screen: "ok" });
    expect(() => parseIpcMessage(msg)).toThrow(/IPC schema violation/);
  });

  it("rejects additionalProperties drift in payload", () => {
    const msg = statusTick({
      livekit: "ok",
      gemini: "ok",
      midi: 1,
      screen: "ok",
      stowaway: "drift",
    });
    expect(() => parseIpcMessage(msg)).toThrow(/IPC schema violation/);
  });

  it("rejects midi=-1 (schema enforces minimum: 0)", () => {
    const msg = statusTick({ livekit: "ok", gemini: "ok", midi: -1, screen: "ok" });
    expect(() => parseIpcMessage(msg)).toThrow(/IPC schema violation/);
  });
});

describe("parseIpcMessage — ipc.calibration.window_list", () => {
  it("accepts a valid window_list with one entry", () => {
    const msg = {
      type: "ipc.calibration.window_list",
      ts: TS,
      payload: {
        windows: [
          {
            id: "0",
            app_name: "djay Pro AI",
            title: "djay Pro — Main",
            dj_app_hint: "djay",
          },
        ],
      },
    };
    expect(() => parseIpcMessage(msg)).not.toThrow();
  });

  it("accepts dj_app_hint=null when no DJ-app name matches", () => {
    const msg = {
      type: "ipc.calibration.window_list",
      ts: TS,
      payload: {
        windows: [
          {
            id: "1",
            app_name: "Finder",
            title: "Untitled",
            dj_app_hint: null,
          },
        ],
      },
    };
    expect(() => parseIpcMessage(msg)).not.toThrow();
  });

  it("rejects malformed window entry (missing id)", () => {
    const msg = {
      type: "ipc.calibration.window_list",
      ts: TS,
      payload: {
        windows: [
          {
            app_name: "djay Pro AI",
            title: "djay Pro — Main",
            dj_app_hint: "djay",
          },
        ],
      },
    };
    expect(() => parseIpcMessage(msg)).toThrow(/IPC schema violation/);
  });
});

describe("parseIpcMessage — envelope discipline", () => {
  it("rejects unknown ipc.* type", () => {
    const msg = { type: "ipc.unknown.thing", ts: TS, payload: {} };
    expect(() => parseIpcMessage(msg)).toThrow(/IPC schema violation/);
  });

  it("rejects top-level additionalProperties", () => {
    const msg = {
      type: "ipc.wizard.start",
      ts: TS,
      payload: {},
      stowaway: true,
    };
    expect(() => parseIpcMessage(msg)).toThrow(/IPC schema violation/);
  });
});

describe("isIpcMessage — narrowing helper", () => {
  it("returns true on valid frame", () => {
    const msg = statusTick({ livekit: "ok", gemini: "ok", midi: 0, screen: "ok" });
    expect(isIpcMessage(msg)).toBe(true);
  });

  it("returns false on invalid frame (does not throw)", () => {
    expect(isIpcMessage({ type: "garbage" })).toBe(false);
  });
});
