/* DEMOCRATIZATION-1 — the ipc.* log-redaction guard.
 *
 * `ipc.settings.set_brain` carries the raw Gemini key over the wire. The
 * on-disk log (ui.log) must NEVER see it. `redactForLog` is the single choke
 * point both `sendIpcRequest` and `emitIpc` route their request log through.
 * This pins the branch directly so the schema field stays masked even though
 * Settings no longer renders a BYO key drawer.
 */

import { describe, expect, it, vi } from "vitest";

vi.mock("@tauri-apps/api/core", () => ({ invoke: vi.fn(async () => undefined) }));
vi.mock("@tauri-apps/api/event", () => ({ listen: vi.fn(async () => () => {}) }));

import { redactForLog } from "../../src/ipc/client.js";

const FAKE_KEY = "AIza-test-fake";

describe("redactForLog", () => {
  it("redacts the Gemini key on ipc.settings.set_brain", () => {
    const safe = redactForLog("ipc.settings.set_brain", {
      mode: "direct",
      gemini_api_key: FAKE_KEY,
    });
    expect(safe).toEqual({ mode: "direct", gemini_api_key: "<redacted>" });
    expect(JSON.stringify(safe)).not.toContain(FAKE_KEY);
  });

  it("does not mutate the original payload (the real key still goes on the wire)", () => {
    const original = { mode: "direct", gemini_api_key: FAKE_KEY };
    redactForLog("ipc.settings.set_brain", original);
    expect(original.gemini_api_key).toBe(FAKE_KEY);
  });

  it("leaves a null/absent key untouched (mode-only flip)", () => {
    expect(redactForLog("ipc.settings.set_brain", { mode: "proxy" })).toEqual({ mode: "proxy" });
    expect(
      redactForLog("ipc.settings.set_brain", { mode: "direct", gemini_api_key: null }),
    ).toEqual({ mode: "direct", gemini_api_key: null });
  });

  it("passes non-secret message types through unchanged (same reference)", () => {
    const payload = { field: "voice", value: "kore" };
    expect(redactForLog("ipc.settings.set", payload)).toBe(payload);
  });
});
