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

// ---------------------------------------------------------------------------
// Phase 12 — session + settings message families
// ---------------------------------------------------------------------------

describe("parseIpcMessage — ipc.session.snapshot", () => {
  const validMeters = {
    music: { rms: 0.4, peak: 0.6 },
    voice: { rms: 0.0, peak: 0.0 },
    mic: { rms: 0.1, peak: 0.2 },
  };
  const baseSnapshot = {
    type: "ipc.session.snapshot",
    ts: TS,
    payload: {
      meters: validMeters,
      phase: [{ kind: "groove", weight: 1.0, label: "groove" }],
      phase_now_pct: 50.0,
      bpm: 124.0,
      drop_pred_bars: 16,
      transcript_delta: [{ role: "ai", text: "yo", ts: TS }],
      midi_events: [{ control: "FX_FILTER", value: 0.8, ts: TS }],
      track: { title: "Strobe", artist: "deadmau5", deck: "A" },
      cohost_status: "LISTENING",
      latency_ms: 820,
      grounded: true,
    },
  };

  it("accepts a fully-valid snapshot", () => {
    expect(() => parseIpcMessage(baseSnapshot)).not.toThrow();
  });

  it("accepts null bpm and null drop_pred_bars", () => {
    const msg = {
      ...baseSnapshot,
      payload: { ...baseSnapshot.payload, bpm: null, drop_pred_bars: null },
    };
    expect(() => parseIpcMessage(msg)).not.toThrow();
  });

  it("rejects rms > 1.0", () => {
    const msg = {
      ...baseSnapshot,
      payload: {
        ...baseSnapshot.payload,
        meters: { ...validMeters, music: { rms: 1.5, peak: 1.0 } },
      },
    };
    expect(() => parseIpcMessage(msg)).toThrow(/IPC schema violation/);
  });

  it("rejects unknown phase chunk kind", () => {
    const msg = {
      ...baseSnapshot,
      payload: {
        ...baseSnapshot.payload,
        phase: [{ kind: "intermezzo", weight: 1.0, label: "x" }],
      },
    };
    expect(() => parseIpcMessage(msg)).toThrow(/IPC schema violation/);
  });

  it("rejects additionalProperty on payload", () => {
    const msg = {
      ...baseSnapshot,
      payload: { ...baseSnapshot.payload, unknown: true },
    };
    expect(() => parseIpcMessage(msg)).toThrow(/IPC schema violation/);
  });
});

describe("parseIpcMessage — ipc.session.mute", () => {
  it("accepts shell→sidecar {toggle: true}", () => {
    const msg = { type: "ipc.session.mute", ts: TS, payload: { toggle: true } };
    expect(() => parseIpcMessage(msg)).not.toThrow();
  });

  it("accepts sidecar→shell ack {muted: false}", () => {
    const msg = { type: "ipc.session.mute", ts: TS, payload: { muted: false } };
    expect(() => parseIpcMessage(msg)).not.toThrow();
  });

  it("rejects extra payload field", () => {
    const msg = {
      type: "ipc.session.mute",
      ts: TS,
      payload: { toggle: true, stow: "x" },
    };
    expect(() => parseIpcMessage(msg)).toThrow(/IPC schema violation/);
  });
});

describe("parseIpcMessage — ipc.settings.set", () => {
  it("accepts every documented field", () => {
    const fields: { field: string; value: unknown }[] = [
      { field: "voice", value: "kore" },
      { field: "mode", value: "hype" },
      { field: "genre", value: "techno" },
      { field: "output_device_id", value: "dev-3" },
      { field: "output_device_id", value: null },
      { field: "output_profile", value: "spk" },
      { field: "retention_days", value: 14 },
      { field: "push_to_mute_hotkey", value: "ctrl+shift+m" },
    ];
    for (const { field, value } of fields) {
      const msg = { type: "ipc.settings.set", ts: TS, payload: { field, value } };
      expect(() => parseIpcMessage(msg)).not.toThrow();
    }
  });

  it("rejects unknown field name", () => {
    const msg = {
      type: "ipc.settings.set",
      ts: TS,
      payload: { field: "rocket-fuel", value: "high" },
    };
    expect(() => parseIpcMessage(msg)).toThrow(/IPC schema violation/);
  });
});

describe("parseIpcMessage — ipc.settings.state", () => {
  const baseState = {
    type: "ipc.settings.state",
    ts: TS,
    payload: {
      voice: "kore",
      mode: "coach",
      genre: "tech-house",
      output_device_id: null,
      output_profile: "hp",
      retention_days: 7,
      push_to_mute_hotkey: "cmd+shift+m",
      muted: false,
      lighter_blur: false,
    },
  };

  it("accepts a valid full state", () => {
    expect(() => parseIpcMessage(baseState)).not.toThrow();
  });

  it("rejects invalid output_profile", () => {
    const msg = {
      ...baseState,
      payload: { ...baseState.payload, output_profile: "headphones" },
    };
    expect(() => parseIpcMessage(msg)).toThrow(/IPC schema violation/);
  });

  it("rejects negative retention_days", () => {
    const msg = {
      ...baseState,
      payload: { ...baseState.payload, retention_days: -1 },
    };
    expect(() => parseIpcMessage(msg)).toThrow(/IPC schema violation/);
  });
});

describe("parseIpcMessage — ipc.status.recheck", () => {
  it("accepts known component", () => {
    const msg = {
      type: "ipc.status.recheck",
      ts: TS,
      payload: { component: "midi" },
    };
    expect(() => parseIpcMessage(msg)).not.toThrow();
  });

  it("rejects unknown component", () => {
    const msg = {
      type: "ipc.status.recheck",
      ts: TS,
      payload: { component: "everything" },
    };
    expect(() => parseIpcMessage(msg)).toThrow(/IPC schema violation/);
  });
});

describe("parseIpcMessage — ipc.error", () => {
  it("accepts minimal error (reason only)", () => {
    const msg = {
      type: "ipc.error",
      ts: TS,
      payload: { reason: "schema violation" },
    };
    expect(() => parseIpcMessage(msg)).not.toThrow();
  });

  it("accepts error with original_type", () => {
    const msg = {
      type: "ipc.error",
      ts: TS,
      payload: { reason: "bad enum", original_type: "ipc.settings.set" },
    };
    expect(() => parseIpcMessage(msg)).not.toThrow();
  });

  it("rejects payload extra field", () => {
    const msg = {
      type: "ipc.error",
      ts: TS,
      payload: { reason: "x", extra: "y" },
    };
    expect(() => parseIpcMessage(msg)).toThrow(/IPC schema violation/);
  });
});

// ---------------------------------------------------------------------------
// Phase 15-01 — ipc.recordings.* families
// ---------------------------------------------------------------------------

describe("parseIpcMessage — ipc.recordings.list", () => {
  it("accepts an empty-payload request", () => {
    const msg = {
      type: "ipc.recordings.list",
      ts: TS,
      payload: {},
    };
    expect(() => parseIpcMessage(msg)).not.toThrow();
  });

  it("rejects extra payload field", () => {
    const msg = {
      type: "ipc.recordings.list",
      ts: TS,
      payload: { stowaway: true },
    };
    expect(() => parseIpcMessage(msg)).toThrow(/IPC schema violation/);
  });
});

describe("parseIpcMessage — ipc.recordings.list_result", () => {
  const validSummary = {
    session_dir: "20260513-210410",
    started_at_iso: "2026-05-13T21:04:10+02:00",
    duration_s: 5040.0,
    event_count: 38,
    bytes_total: 12345678,
    crashed: false,
  };

  it("accepts a one-session response", () => {
    const msg = {
      type: "ipc.recordings.list_result",
      ts: TS,
      payload: { sessions: [validSummary], bytes_total: 12345678 },
    };
    expect(() => parseIpcMessage(msg)).not.toThrow();
  });

  it("accepts an empty sessions array", () => {
    const msg = {
      type: "ipc.recordings.list_result",
      ts: TS,
      payload: { sessions: [], bytes_total: 0 },
    };
    expect(() => parseIpcMessage(msg)).not.toThrow();
  });

  it("rejects RecordingSummary with non-conforming session_dir", () => {
    const msg = {
      type: "ipc.recordings.list_result",
      ts: TS,
      payload: {
        sessions: [{ ...validSummary, session_dir: "not-a-timestamp" }],
        bytes_total: 12345678,
      },
    };
    expect(() => parseIpcMessage(msg)).toThrow(/IPC schema violation/);
  });
});

describe("parseIpcMessage — ipc.recordings.delete", () => {
  it("accepts a valid session_dir", () => {
    const msg = {
      type: "ipc.recordings.delete",
      ts: TS,
      payload: { session_dir: "20260513-210410" },
    };
    expect(() => parseIpcMessage(msg)).not.toThrow();
  });

  it("rejects ../../etc/passwd (V12 path-traversal gate)", () => {
    const msg = {
      type: "ipc.recordings.delete",
      ts: TS,
      payload: { session_dir: "../../etc/passwd" },
    };
    expect(() => parseIpcMessage(msg)).toThrow(/IPC schema violation/);
  });
});

describe("parseIpcMessage — ipc.recordings.delete_ack", () => {
  it("accepts ok=true with null error", () => {
    const msg = {
      type: "ipc.recordings.delete_ack",
      ts: TS,
      payload: { session_dir: "20260513-210410", ok: true, error: null },
    };
    expect(() => parseIpcMessage(msg)).not.toThrow();
  });

  it("accepts ok=false with string error", () => {
    const msg = {
      type: "ipc.recordings.delete_ack",
      ts: TS,
      payload: { session_dir: "20260513-210410", ok: false, error: "locked" },
    };
    expect(() => parseIpcMessage(msg)).not.toThrow();
  });
});

describe("parseIpcMessage — ipc.recordings.usage", () => {
  it("accepts a sessions + bytes_total push", () => {
    const msg = {
      type: "ipc.recordings.usage",
      ts: TS,
      payload: { sessions: 12, bytes_total: 3656838349 },
    };
    expect(() => parseIpcMessage(msg)).not.toThrow();
  });

  it("rejects negative bytes_total", () => {
    const msg = {
      type: "ipc.recordings.usage",
      ts: TS,
      payload: { sessions: 12, bytes_total: -1 },
    };
    expect(() => parseIpcMessage(msg)).toThrow(/IPC schema violation/);
  });
});

describe("parseIpcMessage — ipc.recordings.events", () => {
  it("accepts a valid session_dir", () => {
    const msg = {
      type: "ipc.recordings.events",
      ts: TS,
      payload: { session_dir: "20260513-210410" },
    };
    expect(() => parseIpcMessage(msg)).not.toThrow();
  });

  it("rejects ../../etc/passwd (V12 path-traversal gate mirror)", () => {
    const msg = {
      type: "ipc.recordings.events",
      ts: TS,
      payload: { session_dir: "../../etc/passwd" },
    };
    expect(() => parseIpcMessage(msg)).toThrow(/IPC schema violation/);
  });
});

describe("parseIpcMessage — ipc.recordings.events_result", () => {
  it("accepts a 3-event sample with heterogeneous kinds (open extensibility)", () => {
    const msg = {
      type: "ipc.recordings.events_result",
      ts: TS,
      payload: {
        session_dir: "20260513-210410",
        events: [
          {
            t: 0.0,
            kind: "session_start",
            wall_clock_iso: "2026-05-13T21:04:10+02:00",
            session_dir: "20260513-210410",
          },
          { t: 5.04, kind: "ai_text", text: "Nice transition." },
          { t: 7.11, kind: "controller_move", control: "filter_a", value: 0.62 },
        ],
      },
    };
    expect(() => parseIpcMessage(msg)).not.toThrow();
  });

  it("accepts an empty events array", () => {
    const msg = {
      type: "ipc.recordings.events_result",
      ts: TS,
      payload: { session_dir: "20260513-210410", events: [] },
    };
    expect(() => parseIpcMessage(msg)).not.toThrow();
  });

  it("rejects events missing required `kind`", () => {
    const msg = {
      type: "ipc.recordings.events_result",
      ts: TS,
      payload: {
        session_dir: "20260513-210410",
        events: [{ t: 1.0 }],
      },
    };
    expect(() => parseIpcMessage(msg)).toThrow(/IPC schema violation/);
  });

  it("rejects events with negative `t`", () => {
    const msg = {
      type: "ipc.recordings.events_result",
      ts: TS,
      payload: {
        session_dir: "20260513-210410",
        events: [{ t: -1.0, kind: "session_start" }],
      },
    };
    expect(() => parseIpcMessage(msg)).toThrow(/IPC schema violation/);
  });
});
